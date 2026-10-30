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
        "%d %B %Y",
        "%b %d, %Y",
        "%B %d, %Y",
        "%b %d %Y",
        "%B %d %Y",
    ]
    cleaned = " ".join(date_str.split())
    
    for fmt in date_formats:
        try:
            parsed = datetime.strptime(cleaned, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    return None


# "¥" is ambiguous (JPY/CNY); it is mapped to JPY, the more common reading
CURRENCY_SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}
CURRENCY_CODES = {"USD", "EUR", "GBP", "JPY", "CNY", "CAD", "AUD", "CHF", "INR", "MXN", "SEK", "NZD", "SGD", "HKD"}


def parse_amount(amount_str: str) -> Optional[Tuple[float, str]]:
    """
    Parse monetary value and extract currency.
    Returns (amount, currency) tuple or None.
    """
    # Remove commas and spaces
    cleaned = amount_str.replace(",", "").replace(" ", "")
    
    # Extract currency
    currency_match = next(
        (m for m in re.finditer(r'[A-Z]{3}|[$€£¥]', cleaned)
         if m.group() in CURRENCY_SYMBOLS or m.group() in CURRENCY_CODES),
        None,
    )
    if currency_match:
        symbol_or_code = currency_match.group()
        currency = CURRENCY_SYMBOLS.get(symbol_or_code, symbol_or_code)
        # Remove currency from amount string
        cleaned = cleaned.replace(symbol_or_code, "")
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
    if subtotal is None:
        # Without a subtotal the sum can't be checked, but tax can't exceed the total
        return tax <= total + tolerance
    
    return abs(subtotal + (tax or 0) - total) <= tolerance


DOCUMENT_LABEL_WORDS = {
    "invoice", "receipt", "statement", "quote", "estimate", "bill", "number",
    "date", "due", "total", "subtotal", "tax", "amount", "description", "quantity", "page",
}


def is_plausible_vendor_name(name: Optional[str]) -> bool:
    """Reject values that are document labels or address lines rather than a business name."""
    if not name or not 3 <= len(name.strip()) <= 80:
        return False
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9&.,'’\- ]*", name.strip()):
        return False
    if re.search(r"\d{3,}", name):
        return False
    words = set(re.findall(r"[a-z]+", name.lower()))
    return not words & DOCUMENT_LABEL_WORDS


def is_plausible_invoice_number(value: Optional[str]) -> bool:
    """Reject values without digits or that look like a US state + ZIP code (e.g. 'TX 75201')."""
    if not value or not 3 <= len(value.strip()) <= 30 or not re.search(r"\d", value):
        return False
    return not re.fullmatch(r"[A-Z]{2}\s?\d{5}(?:-\d{4})?", value.strip(), re.IGNORECASE)


def sanitize_string(s: str) -> str:
    """Sanitize string input."""
    return s.strip() if s else ""
