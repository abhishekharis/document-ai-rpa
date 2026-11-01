"""Generate a clean text-based sample invoice PDF for smoke tests: make_sample_invoice.py OUT.pdf"""
import sys

import pymupdf

LINES = [
    "ACME Office Supplies",
    "123 Market Street, Austin, TX 78701",
    "",
    "INVOICE",
    "Invoice Number: INV-20260042",
    "Invoice Date: 2026-10-15",
    "Due Date: 2026-11-14",
    "",
    "Description                Qty     Unit Price     Amount",
    "Printer Paper (case)        10         25.00      250.00",
    "Ink Cartridges               4         50.00      200.00",
    "",
    "Subtotal: $450.00",
    "Tax (8%): $36.00",
    "Total: $486.00",
    "Currency: USD",
]


def main(out_path: str) -> None:
    doc = pymupdf.open()
    page = doc.new_page()
    y = 72
    for line in LINES:
        page.insert_text((72, y), line, fontsize=12, fontname="helv")
        y += 22
    doc.save(out_path)


if __name__ == "__main__":
    main(sys.argv[1])
