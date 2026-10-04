import cv2
import numpy as np
import pytest
from app.document_ai.image_preprocessor import ImagePreprocessor


def _page_with_block(skew: float = 0.0) -> np.ndarray:
    page = np.full((1100, 850), 255, np.uint8)
    cv2.rectangle(page, (150, 200), (700, 900), 0, -1)
    if skew:
        matrix = cv2.getRotationMatrix2D((425, 550), skew, 1.0)
        page = cv2.warpAffine(page, matrix, (850, 1100), borderValue=255)
    return page


def _skew_of_block(page: np.ndarray) -> float:
    _, binary = cv2.threshold(page, 127, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    angle = cv2.minAreaRect(max(contours, key=cv2.contourArea))[2]
    return min(abs(angle), abs(90 - abs(angle)))


class TestDeskew:
    def setup_method(self):
        self.preprocessor = ImagePreprocessor()

    def test_straight_page_is_not_rotated(self):
        page = _page_with_block()
        assert np.array_equal(self.preprocessor._deskew(page), page)

    @pytest.mark.parametrize("skew", [3, -3, 7, -7])
    def test_skewed_page_is_straightened(self, skew):
        page = _page_with_block(skew)
        assert _skew_of_block(page) == pytest.approx(abs(skew), abs=0.5)
        assert _skew_of_block(self.preprocessor._deskew(page)) < 0.5
