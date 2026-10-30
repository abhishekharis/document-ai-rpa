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
        # Only the header-line vendor guess is allowed; required-field validation sends it to review
        assert set(result['fields']) <= {'vendor_name'}
    
    def test_extract_due_date(self):
        text = "Due Date: 2024-02-15"
        raw_results = [
            {'text': 'Due Date: 2024-02-15', 'confidence': 0.95}
        ]
        result = self.extractor.extract(text, raw_results)
        assert 'due_date' in result['fields']
        assert result['fields']['due_date']['value'] == '2024-02-15'

    def test_extract_month_name_dates(self):
        text = "Invoice Date: September 26, 2026 Due Date: October 26, 2026"
        result = self.extractor.extract(text, [])
        assert result['fields']['invoice_date']['value'] == '2026-09-26'
        assert result['fields']['due_date']['value'] == '2026-10-26'

    def test_extract_tax_with_rate(self):
        result = self.extractor.extract("Subtotal $126.98 Tax (8.25%) $10.48 Total $137.46", [])
        assert result['fields']['tax']['value'] == 10.48

    def test_extract_tax_with_unparenthesized_rate(self):
        result = self.extractor.extract("VAT 20%: $40.00", [])
        assert result['fields']['tax']['value'] == 40.00

    def test_extract_total_not_confused_with_subtotal(self):
        result = self.extractor.extract("Subtotal $126.98 Tax (8.25%) $10.48 Total $137.46", [])
        assert result['fields']['subtotal']['value'] == 126.98
        assert result['fields']['total']['value'] == 137.46

    def test_extract_total_not_confused_with_spaced_or_hyphenated_subtotal(self):
        for text in ("Sub Total: $100.00 Total: $108.00", "Sub-total: $100.00 Total: $108.00"):
            assert self.extractor.extract(text, [])['fields']['total']['value'] == 108.00

    def test_extract_sample_invoice_ocr_text(self):
        # Lines as returned by OCR for sample_invoice.pdf
        raw_results = [
            {'text': t, 'confidence': 0.99} for t in [
                'ACME OFFICE SUPPLIES', '123 Market Street', 'Dallas, TX 75201',
                'United States', 'INVOICE', 'Invoice Number:', 'INV-2026-1047',
                'Invoice Date:', 'September 26, 2026', 'Due Date:', 'October 26, 2026',
                'Currency:', 'USD', 'Subtotal', '$126.98', 'Tax (8.25%)', '$10.48',
                'Total', '$137.46', 'Payment Terms: Net 30',
            ]
        ]
        text = ' '.join(r['text'] for r in raw_results)
        fields = self.extractor.extract(text, raw_results)['fields']
        assert fields['vendor_name']['value'] == 'ACME OFFICE SUPPLIES'
        assert fields['invoice_number']['value'] == 'INV-2026-1047'
        assert fields['invoice_date']['value'] == '2026-09-26'
        assert fields['due_date']['value'] == '2026-10-26'
        assert fields['subtotal']['value'] == 126.98
        assert fields['tax']['value'] == 10.48
        assert fields['total']['value'] == 137.46

    def test_extract_invoice_number_after_heading_and_label(self):
        text = "INVOICE Invoice Number: INV-2026-1047"
        fields = self.extractor.extract(text, [])['fields']
        assert fields['invoice_number']['value'] == 'INV-2026-1047'

    def test_extract_invoice_number_ignores_zip_code(self):
        text = "Dallas, TX 75201 INVOICE Invoice Number: INV-1001"
        fields = self.extractor.extract(text, [])['fields']
        assert fields['invoice_number']['value'] == 'INV-1001'

    def test_extract_vendor_prefers_explicit_label(self):
        raw_results = [
            {'text': 'Test Invoice', 'confidence': 0.99},
            {'text': 'Some Other Name', 'confidence': 0.99},
            {'text': 'Vendor: ACME Office Supplies', 'confidence': 0.99},
        ]
        fields = self.extractor.extract(' '.join(r['text'] for r in raw_results), raw_results)['fields']
        assert fields['vendor_name']['value'] == 'ACME Office Supplies'

    def test_extract_vendor_label_value_on_next_line(self):
        raw_results = [
            {'text': 'Vendor:', 'confidence': 0.99},
            {'text': 'ACME Office Supplies', 'confidence': 0.95},
        ]
        fields = self.extractor.extract('Vendor: ACME Office Supplies', raw_results)['fields']
        assert fields['vendor_name']['value'] == 'ACME Office Supplies'

    def test_extract_vendor_skips_invoice_heading(self):
        raw_results = [
            {'text': 'INVOICE', 'confidence': 0.99},
            {'text': 'ACME OFFICE SUPPLIES', 'confidence': 0.99},
            {'text': '123 Market Street', 'confidence': 0.99},
        ]
        fields = self.extractor.extract(' '.join(r['text'] for r in raw_results), raw_results)['fields']
        assert fields['vendor_name']['value'] == 'ACME OFFICE SUPPLIES'

    def test_extract_vendor_not_guessed_from_labels(self):
        raw_results = [
            {'text': 'INVOICE', 'confidence': 0.99},
            {'text': 'Invoice Number: INV-1', 'confidence': 0.99},
        ]
        fields = self.extractor.extract(' '.join(r['text'] for r in raw_results), raw_results)['fields']
        assert 'vendor_name' not in fields
