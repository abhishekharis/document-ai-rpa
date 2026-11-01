import cv2
import numpy as np
from PIL import Image
from paddleocr import PaddleOCR
from typing import List, Dict, Any
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class OCRService:
    """OCR service using PaddleOCR."""
    
    def __init__(self):
        self.paddle_ocr = None
        self.use_angle_cls = True
        self.lang = 'en'
    
    def _get_ocr_engine(self):
        """Lazy initialization of PaddleOCR."""
        if self.paddle_ocr is None:
            logger.info("Initializing PaddleOCR")
            try:
                # oneDNN acceleration crashes some PaddlePaddle 3.x CPU builds
                # (ConvertPirAttribute2RuntimeAttribute), so it is off unless enabled
                self.paddle_ocr = PaddleOCR(
                    use_angle_cls=self.use_angle_cls,
                    lang=self.lang,
                    enable_mkldnn=settings.ocr_enable_mkldnn
                )
            except Exception as e:
                logger.error(f"Failed to initialize PaddleOCR: {str(e)}")
                raise
        return self.paddle_ocr
    
    def extract_text(self, image: Image.Image) -> Dict[str, Any]:
        """
        Extract text from image using PaddleOCR.
        
        Args:
            image: PIL Image
            
        Returns:
            Dictionary containing:
                - text: Full extracted text
                - raw_results: List of (text, confidence, bbox) tuples
                - confidence_mean: Average confidence score
                - confidence_min: Minimum confidence score
                - engine: 'paddle'
        """
        try:
            ocr = self._get_ocr_engine()
            
            # Convert PIL to OpenCV format (BGR)
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Run OCR
            results = ocr.ocr(cv_image)
            
            if not results or not results[0]:
                logger.warning("PaddleOCR returned empty results")
                return {
                    'text': '',
                    'raw_results': [],
                    'confidence_mean': 0.0,
                    'confidence_min': 0.0,
                    'engine': 'paddle'
                }
            
            # Extract text and confidence from new PaddleOCR format
            result = results[0]
            text_parts = result.get('rec_texts', [])
            confidences = result.get('rec_scores', [])
            boxes = result.get('rec_boxes', [])
            
            raw_results = []
            for i, text in enumerate(text_parts):
                confidence = confidences[i] if i < len(confidences) else 0.0
                bbox = boxes[i].tolist() if i < len(boxes) else []
                
                raw_results.append({
                    'text': text,
                    'confidence': float(confidence),
                    'bbox': bbox
                })
            
            full_text = ' '.join(text_parts)
            confidence_mean = np.mean(confidences) if confidences else 0.0
            confidence_min = np.min(confidences) if confidences else 0.0
            
            logger.info(
                f"OCR extraction complete - "
                f"text_length: {len(full_text)}, "
                f"num_words: {len(text_parts)}, "
                f"confidence_mean: {confidence_mean:.3f}, "
                f"confidence_min: {confidence_min:.3f}"
            )
            
            return {
                'text': full_text,
                'raw_results': raw_results,
                'confidence_mean': float(confidence_mean),
                'confidence_min': float(confidence_min),
                'engine': 'paddle'
            }
            
        except Exception as e:
            logger.error(f"PaddleOCR extraction failed: {str(e)}")
            raise
    
    def extract_text_from_images(self, images: List[Image.Image]) -> Dict[str, Any]:
        """
        Extract text from multiple images (multi-page document).
        
        Args:
            images: List of PIL Images
            
        Returns:
            Combined OCR results from all pages
        """
        all_text_parts = []
        all_confidences = []
        all_raw_results = []
        
        for page_num, image in enumerate(images):
            logger.info(f"Processing page {page_num + 1}/{len(images)}")
            result = self.extract_text(image)
            
            all_text_parts.append(result['text'])
            all_confidences.extend([r['confidence'] for r in result['raw_results']])
            all_raw_results.extend(result['raw_results'])
        
        full_text = '\n'.join(all_text_parts)
        confidence_mean = np.mean(all_confidences) if all_confidences else 0.0
        confidence_min = np.min(all_confidences) if all_confidences else 0.0
        
        return {
            'text': full_text,
            'raw_results': all_raw_results,
            'confidence_mean': float(confidence_mean),
            'confidence_min': float(confidence_min),
            'engine': 'paddle',
            'page_count': len(images)
        }
