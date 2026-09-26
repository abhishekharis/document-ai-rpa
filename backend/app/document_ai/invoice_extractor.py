import re
from typing import Dict, Any, Optional, Tuple
import logging
from app.utils.validators import parse_date, parse_amount

logger = logging.getLogger(__name__)


class InvoiceExtractor:
    """Extract structured invoice fields from OCR text."""
    
    def __init__(self):
        # Patterns for invoice number
        self.invoice_number_patterns = [
            r'(?:invoice\s*(?:no|number|#)?[:\s]*)([A-Z0-9\-]+)',
            r'(?:bill\s*(?:no|number|#)?[:\s]*)([A-Z0-9\-]+)',
            r'(?:inv\s*#[:\s]*)([A-Z0-9\-]+)',
            r'([A-Z]{2,4}[-\s]?\d{4,})',  # Pattern like INV-1234
        ]
        
        # Patterns for dates
        self.date_patterns = [
            r'(?:invoice\s*date|date|dated)[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'(?:invoice\s*date|date|dated)[:\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        ]
        
        # Patterns for due date
        self.due_date_patterns = [
            r'(?:due\s*date|payment\s*due|due)[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'(?:due\s*date|payment\s*due|due)[:\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        ]
        
        # Patterns for vendor name (usually at top)
        self.vendor_patterns = [
            r'^([A-Z][A-Za-z\s&]+(?:LLC|Inc|Corp|Ltd|Co|Company)?)',
            r'^(from[:\s]+)([A-Z][A-Za-z\s&]+)',
            r'(?:vendor|supplier|seller)[:\s]+([A-Z][A-Za-z\s&]+)',
        ]
        
        # Patterns for total amount
        self.total_patterns = [
            r'(?:total|grand\s*total|amount\s*due|balance\s*due)[:\s]*[$€£¥]?([\d,]+\.?\d*)',
            r'total[:\s]*[$€£¥]?([\d,]+\.?\d*)',
            r'[$€£¥]([\d,]+\.?\d*)\s*(?:total|due)',
        ]
        
        # Patterns for subtotal
        self.subtotal_patterns = [
            r'(?:sub\s*total|subtotal)[:\s]*[$€£¥]?([\d,]+\.?\d*)',
        ]
        
        # Patterns for tax
        self.tax_patterns = [
            r'(?:tax|vat|gst|hst)[:\s]*[$€£¥]?([\d,]+\.?\d*)',
            r'(?:sales\s*tax)[:\s]*[$€£¥]?([\d,]+\.?\d*)',
        ]
        
        # Patterns for currency
        self.currency_patterns = [
            r'\b(USD|EUR|GBP|CAD|AUD|JPY)\b',
            r'[$€£¥]',
        ]
    
    def extract(self, ocr_text: str, raw_results: list) -> Dict[str, Any]:
        """
        Extract all invoice fields from OCR results.
        
        Args:
            ocr_text: Full extracted text
            raw_results: List of raw OCR results with confidence scores
            
        Returns:
            Dictionary with extracted fields and their confidence scores
        """
        logger.info("Starting invoice field extraction")
        
        fields = {}
        
        # Extract vendor name
        vendor_name, vendor_conf = self._extract_vendor(ocr_text, raw_results)
        if vendor_name:
            fields['vendor_name'] = {'value': vendor_name, 'confidence': vendor_conf}
        
        # Extract invoice number
        invoice_number, invoice_conf = self._extract_invoice_number(ocr_text, raw_results)
        if invoice_number:
            fields['invoice_number'] = {'value': invoice_number, 'confidence': invoice_conf}
        
        # Extract invoice date
        invoice_date, date_conf = self._extract_invoice_date(ocr_text, raw_results)
        if invoice_date:
            fields['invoice_date'] = {'value': invoice_date, 'confidence': date_conf}
        
        # Extract due date
        due_date, due_conf = self._extract_due_date(ocr_text, raw_results)
        if due_date:
            fields['due_date'] = {'value': due_date, 'confidence': due_conf}
        
        # Extract total
        total, total_conf, currency = self._extract_total(ocr_text, raw_results)
        if total:
            fields['total'] = {'value': total, 'confidence': total_conf}
        
        # Extract currency
        if currency:
            fields['currency'] = {'value': currency, 'confidence': 0.9}
        
        # Extract subtotal
        subtotal, subtotal_conf = self._extract_subtotal(ocr_text, raw_results)
        if subtotal:
            fields['subtotal'] = {'value': subtotal, 'confidence': subtotal_conf}
        
        # Extract tax
        tax, tax_conf = self._extract_tax(ocr_text, raw_results)
        if tax:
            fields['tax'] = {'value': tax, 'confidence': tax_conf}
        
        # Calculate overall confidence
        overall_confidence = self._calculate_overall_confidence(fields)
        
        logger.info(f"Extraction complete - extracted {len(fields)} fields, overall confidence: {overall_confidence:.3f}")
        
        return {
            'fields': fields,
            'overall_confidence': overall_confidence
        }
    
    def _extract_vendor(self, text: str, raw_results: list) -> Tuple[Optional[str], float]:
        """Extract vendor name."""
        lines = text.split('\n')
        
        for i, line in enumerate(lines[:5]):  # Check first 5 lines
            for pattern in self.vendor_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    vendor = match.group(1) if match.lastindex == 1 else match.group(2)
                    vendor = vendor.strip()
                    if len(vendor) > 2:  # Minimum length
                        # Find corresponding OCR confidence
                        conf = self._find_confidence_for_text(vendor, raw_results)
                        return vendor, conf
        
        return None, 0.0
    
    def _extract_invoice_number(self, text: str, raw_results: list) -> Tuple[Optional[str], float]:
        """Extract invoice number."""
        text_lower = text.lower()
        
        for pattern in self.invoice_number_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                invoice_num = match.group(1).strip().upper()
                # Validate format (should have at least one letter and one number)
                if re.search(r'[A-Z]', invoice_num) and re.search(r'\d', invoice_num):
                    conf = self._find_confidence_for_text(invoice_num, raw_results)
                    return invoice_num, conf
        
        return None, 0.0
    
    def _extract_invoice_date(self, text: str, raw_results: list) -> Tuple[Optional[str], float]:
        """Extract invoice date."""
        for pattern in self.date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                date_str = match.group(1)
                normalized = parse_date(date_str)
                if normalized:
                    conf = self._find_confidence_for_text(date_str, raw_results)
                    return normalized, conf
        
        return None, 0.0
    
    def _extract_due_date(self, text: str, raw_results: list) -> Tuple[Optional[str], float]:
        """Extract due date."""
        for pattern in self.due_date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                date_str = match.group(1)
                normalized = parse_date(date_str)
                if normalized:
                    conf = self._find_confidence_for_text(date_str, raw_results)
                    return normalized, conf
        
        return None, 0.0
    
    def _extract_total(self, text: str, raw_results: list) -> Tuple[Optional[float], float, Optional[str]]:
        """Extract total amount and currency."""
        text_lower = text.lower()
        
        for pattern in self.total_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                    # Extract currency from context
                    currency = self._extract_currency(text)
                    conf = self._find_confidence_for_text(match.group(0), raw_results)
                    return amount, conf, currency
                except ValueError:
                    continue
        
        return None, 0.0, None
    
    def _extract_subtotal(self, text: str, raw_results: list) -> Tuple[Optional[float], float]:
        """Extract subtotal."""
        text_lower = text.lower()
        
        for pattern in self.subtotal_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                    conf = self._find_confidence_for_text(match.group(0), raw_results)
                    return amount, conf
                except ValueError:
                    continue
        
        return None, 0.0
    
    def _extract_tax(self, text: str, raw_results: list) -> Tuple[Optional[float], float]:
        """Extract tax amount."""
        text_lower = text.lower()
        
        for pattern in self.tax_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                    conf = self._find_confidence_for_text(match.group(0), raw_results)
                    return amount, conf
                except ValueError:
                    continue
        
        return None, 0.0
    
    def _extract_currency(self, text: str) -> Optional[str]:
        """Extract currency from text."""
        for pattern in self.currency_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                currency = match.group(1) if match.lastindex else self._symbol_to_currency(match.group(0))
                if currency:
                    return currency.upper()
        return "USD"  # Default
    
    def _symbol_to_currency(self, symbol: str) -> Optional[str]:
        """Convert currency symbol to code."""
        symbol_map = {
            '$': 'USD',
            '€': 'EUR',
            '£': 'GBP',
            '¥': 'JPY'
        }
        return symbol_map.get(symbol)
    
    def _find_confidence_for_text(self, text: str, raw_results: list) -> float:
        """Find average confidence for a text segment in raw OCR results."""
        if not raw_results:
            return 0.7  # Default confidence
        
        text_lower = text.lower()
        matching_confidences = []
        
        for result in raw_results:
            ocr_text = result.get('text', '').lower()
            if text_lower in ocr_text or ocr_text in text_lower:
                matching_confidences.append(result.get('confidence', 0.7))
        
        if matching_confidences:
            return sum(matching_confidences) / len(matching_confidences)
        
        return 0.7  # Default confidence if no match found
    
    def _calculate_overall_confidence(self, fields: Dict[str, Any]) -> float:
        """Calculate overall confidence from field confidences."""
        if not fields:
            return 0.0
        
        confidences = [f['confidence'] for f in fields.values()]
        return sum(confidences) / len(confidences)
