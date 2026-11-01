from app.config import settings
from app.document_ai import ocr_service
from app.document_ai.ocr_service import OCRService


def test_mkldnn_is_disabled_by_default():
    assert settings.ocr_enable_mkldnn is False


def test_engine_receives_mkldnn_setting(monkeypatch):
    captured = {}

    class FakePaddleOCR:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(ocr_service, "PaddleOCR", FakePaddleOCR)
    monkeypatch.setattr(settings, "ocr_enable_mkldnn", False)

    OCRService()._get_ocr_engine()

    assert captured["enable_mkldnn"] is False
    assert captured["lang"] == "en"
