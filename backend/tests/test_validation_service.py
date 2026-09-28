import pytest
from app.validation.validation_service import ValidationService


class TestValidationService:
    def setup_method(self):
        self.validation_service = ValidationService(confidence_threshold=0.80)
    
    def test_validate_all_required_fields_present(self):
        fields = {
            'vendor_name': {'value': 'Test Vendor', 'confidence': 0.95},
            'invoice_number': {'value': 'INV-001', 'confidence': 0.95},
            'invoice_date': {'value': '2024-01-01', 'confidence': 0.95},
            'total': {'value': 100.00, 'confidence': 0.95},
            'currency': {'value': 'USD', 'confidence': 0.95}
        }
        result = self.validation_service.validate(fields)
        assert result['is_valid'] is True
        assert len(result['errors']) == 0
    
    def test_validate_missing_required_field(self):
        fields = {
            'vendor_name': {'value': 'Test Vendor', 'confidence': 0.95},
            'invoice_number': {'value': 'INV-001', 'confidence': 0.95},
            'total': {'value': 100.00, 'confidence': 0.95},
            'currency': {'value': 'USD', 'confidence': 0.95}
            # Missing invoice_date
        }
        result = self.validation_service.validate(fields)
        assert result['is_valid'] is False
        assert any('invoice_date' in error.lower() for error in result['errors'])
    
    def test_validate_low_confidence_warning(self):
        fields = {
            'vendor_name': {'value': 'Test Vendor', 'confidence': 0.75},
            'invoice_number': {'value': 'INV-001', 'confidence': 0.95},
            'invoice_date': {'value': '2024-01-01', 'confidence': 0.95},
            'total': {'value': 100.00, 'confidence': 0.95},
            'currency': {'value': 'USD', 'confidence': 0.95}
        }
        result = self.validation_service.validate(fields)
        assert result['is_valid'] is True  # Low confidence is a warning, not error
        assert len(result['warnings']) > 0
        assert any('vendor_name' in warning.lower() for warning in result['warnings'])
    
    def test_validate_invalid_date_sequence(self):
        fields = {
            'vendor_name': {'value': 'Test Vendor', 'confidence': 0.95},
            'invoice_number': {'value': 'INV-001', 'confidence': 0.95},
            'invoice_date': {'value': '2024-01-30', 'confidence': 0.95},
            'due_date': {'value': '2024-01-01', 'confidence': 0.95},  # Before invoice date
            'total': {'value': 100.00, 'confidence': 0.95},
            'currency': {'value': 'USD', 'confidence': 0.95}
        }
        result = self.validation_service.validate(fields)
        assert result['is_valid'] is False
        assert any('due date' in error.lower() for error in result['errors'])
    
    def test_validate_amount_mismatch(self):
        fields = {
            'vendor_name': {'value': 'Test Vendor', 'confidence': 0.95},
            'invoice_number': {'value': 'INV-001', 'confidence': 0.95},
            'invoice_date': {'value': '2024-01-01', 'confidence': 0.95},
            'subtotal': {'value': 100.00, 'confidence': 0.95},
            'tax': {'value': 8.00, 'confidence': 0.95},
            'total': {'value': 200.00, 'confidence': 0.95},  # Wrong total
            'currency': {'value': 'USD', 'confidence': 0.95}
        }
        result = self.validation_service.validate(fields)
        assert result['is_valid'] is True  # Amount mismatch is a warning
        assert len(result['warnings']) > 0
        assert any('amount' in warning.lower() for warning in result['warnings'])
    
    def test_validate_negative_amount(self):
        fields = {
            'vendor_name': {'value': 'Test Vendor', 'confidence': 0.95},
            'invoice_number': {'value': 'INV-001', 'confidence': 0.95},
            'invoice_date': {'value': '2024-01-01', 'confidence': 0.95},
            'total': {'value': -100.00, 'confidence': 0.95},  # Negative
            'currency': {'value': 'USD', 'confidence': 0.95}
        }
        result = self.validation_service.validate(fields)
        assert result['is_valid'] is False
        assert any('negative' in error.lower() for error in result['errors'])
    
    def test_determine_status_approved(self):
        validation = {'is_valid': True, 'errors': [], 'warnings': []}
        status = self.validation_service.determine_status(validation, 0.95)
        assert status == 'PROCESSED'
    
    def test_determine_status_needs_review_low_confidence(self):
        validation = {'is_valid': True, 'errors': [], 'warnings': []}
        status = self.validation_service.determine_status(validation, 0.75)
        assert status == 'NEEDS_REVIEW'
    
    def test_determine_status_needs_review_warnings(self):
        validation = {'is_valid': True, 'errors': [], 'warnings': ['Low confidence']}
        status = self.validation_service.determine_status(validation, 0.95)
        assert status == 'NEEDS_REVIEW'
    
    def test_determine_status_rejected(self):
        validation = {'is_valid': False, 'errors': ['Missing field'], 'warnings': []}
        status = self.validation_service.determine_status(validation, 0.95)
        assert status == 'REJECTED'
