import re
from difflib import SequenceMatcher
from typing import Optional

VENDOR_SUFFIXES = {"inc", "llc", "ltd", "corp", "corporation", "co", "company", "gmbh", "plc", "limited"}
VENDOR_SIMILARITY_THRESHOLD = 0.85


def normalize_vendor(name: Optional[str]) -> str:
    words = re.findall(r"[a-z0-9]+", (name or "").lower())
    return " ".join(w for w in words if w not in VENDOR_SUFFIXES)


def normalize_invoice_number(number: Optional[str]) -> str:
    return re.sub(r"[^A-Z0-9]", "", (number or "").upper())


def vendor_similarity(a: Optional[str], b: Optional[str]) -> float:
    na, nb = normalize_vendor(a), normalize_vendor(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def duplicate_reason(new: dict, existing: dict) -> Optional[str]:
    """Return why `existing` looks like the same invoice as `new`, or None.

    Both are dicts with vendor_name, invoice_number, invoice_date and total. Matching is
    fuzzy on the vendor (OCR misreads, "Inc." vs "Inc") and normalized on the number.
    """
    if vendor_similarity(new.get("vendor_name"), existing.get("vendor_name")) < VENDOR_SIMILARITY_THRESHOLD:
        return None
    new_number = normalize_invoice_number(new.get("invoice_number"))
    old_number = normalize_invoice_number(existing.get("invoice_number"))
    if new_number and new_number == old_number:
        return "same vendor and invoice number"
    same_total = new.get("total") is not None and new.get("total") == existing.get("total")
    same_date = bool(new.get("invoice_date")) and new.get("invoice_date") == existing.get("invoice_date")
    if same_total and same_date:
        return "same vendor, date and total"
    return None
