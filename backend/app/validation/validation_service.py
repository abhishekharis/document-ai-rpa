from typing import Dict, Any, List
from app.utils.validators import (
    validate_date_sequence, validate_amounts, parse_date,
    is_plausible_vendor_name, is_plausible_invoice_number
)
import logging

logger = logging.getLogger(__name__)


class ValidationService:
    """Validate extracted invoice data."""
    
    REQUIRED_FIELDS = [
        'vendor_name',
        'invoice_number',
        'invoice_date',
        'total',
        'currency'
    ]
    
    def __init__(self, confidence_threshold: float = 0.80):
        self.confidence_threshold = confidence_threshold
    
    def validate(self, extracted_fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate extracted invoice fields.
        
        Args:
            extracted_fields: Dictionary of field_name -> {value, confidence}
            
        Returns:
            Dictionary with validation results:
                - is_valid: boolean
                - errors: list of error messages
                - warnings: list of warning messages
        """
        errors = []
        warnings = []
        
        # Check required fields exist
        for field in self.REQUIRED_FIELDS:
            if field not in extracted_fields:
                errors.append(f"Missing required field: {field}")
            elif not extracted_fields[field]['value']:
                errors.append(f"Empty required field: {field}")
        
        # Warn when required fields hold clearly implausible values; warnings
        # route the document to NEEDS_REVIEW so it cannot be auto-approved
        if 'vendor_name' in extracted_fields:
            vendor = extracted_fields['vendor_name']['value']
            if vendor and not is_plausible_vendor_name(vendor):
                warnings.append(f"Suspicious vendor name: '{vendor}'")
        if 'invoice_number' in extracted_fields:
            invoice_number = extracted_fields['invoice_number']['value']
            if invoice_number and not is_plausible_invoice_number(invoice_number):
                warnings.append(f"Suspicious invoice number: '{invoice_number}'")
        
        # Check confidence thresholds
        for field_name, field_data in extracted_fields.items():
            if field_name in self.REQUIRED_FIELDS:
                if field_data['confidence'] < self.confidence_threshold:
                    warnings.append(
                        f"Low confidence for {field_name}: {field_data['confidence']:.2f} "
                        f"(threshold: {self.confidence_threshold})"
                    )
        
        # Validate dates
        if 'invoice_date' in extracted_fields and 'due_date' in extracted_fields:
            invoice_date = extracted_fields['invoice_date']['value']
            due_date = extracted_fields['due_date']['value']
            
            if invoice_date and due_date:
                if not validate_date_sequence(invoice_date, due_date):
                    errors.append("Due date cannot be before invoice date")
        
        # Validate amounts
        if 'subtotal' in extracted_fields and 'tax' in extracted_fields and 'total' in extracted_fields:
            subtotal = extracted_fields['subtotal']['value']
            tax = extracted_fields['tax']['value']
            total = extracted_fields['total']['value']
            
            if subtotal is not None and tax is not None and total is not None:
                if not validate_amounts(subtotal, tax, total):
                    warnings.append(
                        f"Amount mismatch: subtotal + tax ({subtotal + tax:.2f}) "
                        f"≠ total ({total:.2f})"
                    )
        
        # Validate amounts are non-negative
        for field in ['subtotal', 'tax', 'total']:
            if field in extracted_fields:
                value = extracted_fields[field]['value']
                if value is not None and value < 0:
                    errors.append(f"{field} cannot be negative")
        
        is_valid = len(errors) == 0
        
        logger.info(
            f"Validation complete - valid: {is_valid}, "
            f"errors: {len(errors)}, warnings: {len(warnings)}"
        )
        
        return {
            'is_valid': is_valid,
            'errors': errors,
            'warnings': warnings
        }
    
    def determine_status(self, validation_result: Dict[str, Any], overall_confidence: float) -> str:
        """
        Determine invoice status based on validation and confidence.
        
        Args:
            validation_result: Validation result dictionary
            overall_confidence: Overall extraction confidence
            
        Returns:
            Status string: 'PROCESSED', 'NEEDS_REVIEW', or 'REJECTED'
        """
        if not validation_result['is_valid']:
            return 'REJECTED'
        
        if overall_confidence < self.confidence_threshold:
            return 'NEEDS_REVIEW'
        
        if validation_result['warnings']:
            return 'NEEDS_REVIEW'
        
        return 'PROCESSED'
