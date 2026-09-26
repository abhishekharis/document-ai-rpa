from typing import Dict, Any
from app.document_ai.pdf_processor import PDFProcessor
from app.document_ai.image_preprocessor import ImagePreprocessor
from app.document_ai.ocr_service import OCRService
from app.document_ai.invoice_extractor import InvoiceExtractor
from app.validation.validation_service import ValidationService
from app.models.invoice import InvoiceStatus, Vendor, Extraction, ExtractionField
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class ProcessingService:
    """Orchestrate the complete invoice processing pipeline."""
    
    def __init__(self):
        self.pdf_processor = PDFProcessor()
        self.image_preprocessor = ImagePreprocessor()
        self.ocr_service = OCRService()
        self.invoice_extractor = InvoiceExtractor()
        self.validation_service = ValidationService(
            confidence_threshold=settings.confidence_threshold
        )
    
    async def process_invoice(
        self,
        file_bytes: bytes,
        filename: str,
        document_id: str
    ) -> Dict[str, Any]:
        """
        Complete processing pipeline for an invoice.
        
        Args:
            file_bytes: Raw file content
            filename: Original filename
            document_id: Document ID
            
        Returns:
            Dictionary with processing results including:
                - status: Final invoice status
                - vendor: Vendor info
                - invoice_number: Invoice number
                - invoice_date: Invoice date
                - due_date: Due date
                - currency: Currency
                - subtotal: Subtotal
                - tax: Tax
                - total: Total
                - extraction: Extraction results
                - validation: Validation results
        """
        logger.info(f"Starting processing for document {document_id}")
        
        try:
            # Step 1: Convert document to images
            logger.info("Step 1: Converting document to images")
            images, page_count = self.pdf_processor.process_document(file_bytes, filename)
            
            # Step 2: Preprocess images
            logger.info("Step 2: Preprocessing images")
            preprocessed_images = []
            for i, image in enumerate(images):
                preprocessed = self.image_preprocessor.preprocess(image)
                preprocessed_images.append(preprocessed)
                logger.info(f"Preprocessed page {i + 1}/{page_count}")
            
            # Step 3: OCR extraction
            logger.info("Step 3: Running OCR")
            ocr_results = self.ocr_service.extract_text_from_images(preprocessed_images)
            
            # Step 4: Invoice field extraction
            logger.info("Step 4: Extracting invoice fields")
            extraction_results = self.invoice_extractor.extract(
                ocr_results['text'],
                ocr_results['raw_results']
            )
            
            # Step 5: Validation
            logger.info("Step 5: Validating extracted data")
            validation_results = self.validation_service.validate(extraction_results['fields'])
            
            # Step 6: Determine status
            logger.info("Step 6: Determining invoice status")
            status = self.validation_service.determine_status(
                validation_results,
                extraction_results['overall_confidence']
            )
            
            # Build extraction object
            extraction = Extraction(
                overall_confidence=extraction_results['overall_confidence'],
                fields={
                    k: ExtractionField(value=v['value'], confidence=v['confidence'])
                    for k, v in extraction_results['fields'].items()
                },
                raw_ocr_text=ocr_results['text'],
                page_count=page_count
            )
            
            # Build vendor object
            vendor_name = extraction_results['fields'].get('vendor_name', {}).get('value', '')
            vendor = Vendor(name=vendor_name)
            
            # Build result dictionary
            result = {
                'status': status,
                'vendor': vendor.model_dump(),
                'invoice_number': extraction_results['fields'].get('invoice_number', {}).get('value', ''),
                'invoice_date': extraction_results['fields'].get('invoice_date', {}).get('value', ''),
                'due_date': extraction_results['fields'].get('due_date', {}).get('value'),
                'currency': extraction_results['fields'].get('currency', {}).get('value', 'USD'),
                'subtotal': extraction_results['fields'].get('subtotal', {}).get('value'),
                'tax': extraction_results['fields'].get('tax', {}).get('value'),
                'total': extraction_results['fields'].get('total', {}).get('value'),
                'extraction': extraction.model_dump(),
                'validation': validation_results
            }
            
            logger.info(f"Processing complete for document {document_id} - status: {status}")
            
            return result
            
        except Exception as e:
            logger.error(f"Processing failed for document {document_id}: {str(e)}")
            raise
