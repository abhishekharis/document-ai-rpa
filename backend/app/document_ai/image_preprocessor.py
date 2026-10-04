import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from typing import Optional


class ImagePreprocessor:
    """Preprocess images for OCR using OpenCV."""
    
    def __init__(self):
        self.quality_threshold = 0.5
    
    def preprocess(self, image: Image.Image) -> Image.Image:
        """
        Apply preprocessing pipeline to improve OCR accuracy.
        
        Steps:
        1. Convert to grayscale
        2. Detect and correct skew
        3. Enhance contrast
        4. Denoise if needed
        5. Apply thresholding if needed
        
        Args:
            image: PIL Image
            
        Returns:
            Preprocessed PIL Image
        """
        # Convert PIL to OpenCV format
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        
        # Estimate quality
        quality = self._estimate_quality(cv_image)
        
        # Apply deskewing
        cv_image = self._deskew(cv_image)
        
        # Enhance contrast
        cv_image = self._enhance_contrast(cv_image)
        
        # Denoise if quality is low
        if quality < self.quality_threshold:
            cv_image = self._denoise(cv_image)
        
        # Convert back to PIL
        pil_image = Image.fromarray(cv_image)
        
        return pil_image
    
    def _estimate_quality(self, cv_image: np.ndarray) -> float:
        """
        Estimate image quality based on Laplacian variance.
        
        Returns:
            Quality score between 0.0 and 1.0
        """
        try:
            laplacian_var = cv2.Laplacian(cv_image, cv2.CV_64F).var()
            # Normalize to 0-1 range (typical range is 0-500)
            quality = min(laplacian_var / 200, 1.0)
            return quality
        except:
            return 0.5
    
    def _deskew(self, cv_image: np.ndarray) -> np.ndarray:
        """
        Detect and correct image skew using contour analysis.
        
        Args:
            cv_image: OpenCV grayscale image
            
        Returns:
            Deskewed image
        """
        try:
            # Apply thresholding
            _, binary = cv2.threshold(cv_image, 127, 255, cv2.THRESH_BINARY_INV)
            
            # Find contours
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return cv_image
            
            # Get the largest contour
            largest_contour = max(contours, key=cv2.contourArea)
            
            # Get minimum area rectangle
            rect = cv2.minAreaRect(largest_contour)
            angle = rect[2]
            
            # Normalize to the rotation that straightens the page (-45 to 45)
            if angle < 0:  # OpenCV < 4.5 reports angles in [-90, 0)
                angle = -(90 + angle) if angle < -45 else -angle
            elif angle > 45:  # OpenCV >= 4.5 reports angles in (0, 90]
                angle -= 90
            
            # Only rotate if angle is significant (>1 degree)
            if abs(angle) > 1:
                h, w = cv_image.shape
                center = (w // 2, h // 2)
                rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
                rotated = cv2.warpAffine(
                    cv_image,
                    rotation_matrix,
                    (w, h),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_CONSTANT,
                    borderValue=255
                )
                return rotated
            
            return cv_image
        except Exception:
            return cv_image
    
    def _enhance_contrast(self, cv_image: np.ndarray) -> np.ndarray:
        """
        Enhance image contrast using CLAHE.
        
        Args:
            cv_image: OpenCV grayscale image
            
        Returns:
            Contrast-enhanced image
        """
        try:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(cv_image)
            return enhanced
        except Exception:
            return cv_image
    
    def _denoise(self, cv_image: np.ndarray) -> np.ndarray:
        """
        Remove noise from image using median blur.
        
        Args:
            cv_image: OpenCV grayscale image
            
        Returns:
            Denoised image
        """
        try:
            denoised = cv2.medianBlur(cv_image, 3)
            return denoised
        except Exception:
            return cv_image
    
    def _threshold(self, cv_image: np.ndarray) -> np.ndarray:
        """
        Apply adaptive thresholding to binarize image.
        
        Args:
            cv_image: OpenCV grayscale image
            
        Returns:
            Thresholded binary image
        """
        try:
            binary = cv2.adaptiveThreshold(
                cv_image,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11,
                2
            )
            return binary
        except Exception:
            return cv_image
