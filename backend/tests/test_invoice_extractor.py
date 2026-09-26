import pytest
from app.document_ai.invoice_extractor import InvoiceExtractor


class TestInvoiceExtractor:
    def setup_method(self):
        self.extractor = InvoiceExtractor()
    
    def test_extract_invoice_number_standard(self):
        text = "Invoice # INV-12345 for services"
        raw_results = [
            {'text': 'Invoice # INV-12345', 'confidence': 0.95}
        ]
        result = self.extractor.extract(text, raw_results)
        assert 'invoice_number' in result['fields']
        assert result['fields']['invoice_number']['value'] == 'INV-12345'
    
    def test_extract_invoice_number_variation(self):
        text = "Bill Number: INV-67890"
        raw_results = [
            {'text': 'Bill Number: INV-67890', 'confidence': 0.90}
        ]
        result = self.extractor.extract(text, raw_results)
        assert 'invoice_number' in result['fields']
        assert result['fields']['invoice_number']['value'] == 'INV-67890'
    
    def test_extract_date_standard(self):
        text = "Invoice Date: 2024-01-15"
        raw_results = [
            {'text': 'Invoice Date: 2024-01-15', 'confidence': 0.95}
        ]
        result = self.extractor.extract(text, raw_results)
        assert 'invoice_date' in result['fields']
        assert result['fields']['invoice_date']['value'] == '2024-01-15'
    
    def test_extract_total_with_dollar(self):
        text = "Total: $1,250.00"
        raw_results = [
            {'text': 'Total: $1,250.00', 'confidence': 0.95}
        ]
        result = self.extractor.extract(text, raw_results)
        assert 'total' in result['fields']
        assert result['fields']['total']['value'] == 1250.00
    
    def test_extract_currency_usd(self):
        text = "Total: $1,250.00"
        raw_results = [
            {'text': 'Total: $1,250.00', 'confidence': 0.95}
        ]
        result = self.extractor.extract(text, raw_results)
        assert 'currency' in result['fields']
        assert result['fields']['currency']['value'] == 'USD'
    
    def test_extract_vendor_name(self):
        text = "Acme Corporation\nInvoice # INV-001"
        raw_results = [
            {'text': 'Acme Corporation', 'confidence': 0.95}
        ]
        result = self.extractor.extract(text, raw_results)
        assert 'vendor_name' in result['fields']
        assert result['fields']['vendor_name']['value'] == 'Acme Corporation'
    
    def test_extract_subtotal(self):
        text = "Subtotal: $1,000.00"
        raw_results = [
            {'text': 'Subtotal: $1,000.00', 'confidence': 0.95}
        ]
        result = self.extractor.extract(text, raw_results)
        assert 'subtotal' in result['fields']
        assert result['fields']['subtotal']['value'] == 1000.00
    
    def test_extract_tax(self):
        text = "Tax: $80.00"
        raw_results = [
            {'text': 'Tax: $80.00', 'confidence': 0.95}
        ]
        result = self.extractor.extract(text, raw_results)
        assert 'tax' in result['fields']
        assert result['fields']['tax']['value'] == 80.00
    
    def test_calculate_overall_confidence(self):
        text = "Invoice # INV-001\nTotal: $100.00"
        raw_results = [
            {'text': 'Invoice # INV-001', 'confidence': 0.95},
            {'text': 'Total: $100.00', 'confidence': 0.90}
        ]
        result = self.extractor.extract(text, raw_results)
        assert result['overall_confidence'] > 0
        assert result['overall_confidence'] <= 1.0
    
    def test_extract_no_fields(self):
        text = "Some random text without invoice fields"
        raw_results = [
            {'text': 'Some random text', 'confidence': 0.80}
        ]
        result = self.extractor.extract(text, raw_results)
        assert len(result['fields']) == 0
        assert result['overall_confidence'] == 0.0
    
    def test_extract_due_date(self):
        text = "Due Date: 2024-02-15"
        raw_results = [
            {'text': 'Due Date: 2024-02-15', 'confidence': 0.95}
        ]
        result = self.extractor.extract(text, raw_results)
        assert 'due_date' in result['fields']
        assert result['fields']['due_date']['value'] == '2024-02-15'
