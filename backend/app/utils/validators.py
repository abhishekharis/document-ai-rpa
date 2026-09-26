import re
from typing import Optional, Tuple
from datetime import datetime


def validate_file_type(filename: str, allowed_types: list[str]) -> bool:
    """Validate file extension."""
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    return ext in allowed_types


def validate_mime_type(content_type: str, allowed_mime_types: list[str]) -> bool:
    """Validate MIME type."""
    return content_type in allowed_mime_types


def validate_file_size(size_bytes: int, max_size_mb: int) -> bool:
    """Validate file size."""
    max_bytes = max_size_mb * 1024 * 1024
    return size_bytes <= max_bytes


def parse_date(date_str: str) -> Optional[str]:
    """Parse various date formats and normalize to YYYY-MM-DD."""
    date_formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m-%d-%Y",
        "%m/%d/%Y",
        "%Y%m%d",
        "%d %b %Y",
        "%b %d, %Y",
    ]
    
    for fmt in date_formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    return None


def parse_amount(amount_str: str) -> Optional[Tuple[float, str]]:
    """
    Parse monetary value and extract currency.
    Returns (amount, currency) tuple or None.
    """
    # Remove commas and spaces
    cleaned = amount_str.replace(",", "").replace(" ", "")
    
    # Extract currency
    currency_match = re.search(r'[A-Z]{3}|[$€£¥]', cleaned)
    if currency_match:
        currency = currency_match.group()
        # Remove currency from amount string
        cleaned = cleaned.replace(currency, "")
    else:
        currency = "USD"
    
    # Extract numeric value
    amount_match = re.search(r'[\d.]+', cleaned)
    if amount_match:
        try:
            amount = float(amount_match.group())
            return (amount, currency)
        except ValueError:
            return None
    
    return None


def validate_date_sequence(invoice_date: str, due_date: str) -> bool:
    """Validate that due date is not before invoice date."""
    try:
        inv_date = datetime.strptime(invoice_date, "%Y-%m-%d")
        due = datetime.strptime(due_date, "%Y-%m-%d")
        return due >= inv_date
    except ValueError:
        return False


def validate_amounts(subtotal: Optional[float], tax: Optional[float], total: float, tolerance: float = 0.01) -> bool:
    """Validate that subtotal + tax ≈ total."""
    if subtotal is None and tax is None:
        return True  # Can't validate without subtotal/tax
    
    calculated_total = (subtotal or 0) + (tax or 0)
    return abs(calculated_total - total) <= tolerance


def sanitize_string(s: str) -> str:
    """Sanitize string input."""
    return s.strip() if s else ""
