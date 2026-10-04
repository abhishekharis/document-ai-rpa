# Investigation: invoice date, due date, and tax not extracted

**Severity:** ⭐⭐⭐⭐ High — clean invoices rejected; wrong totals risked reaching accounting.

## Problem

`sample_invoice.pdf` was REJECTED after processing, even though it is a clean,
well-formed invoice. Validation reported `Missing required field: invoice_date`.
The due date and tax fields were also empty, and the extracted total was wrong
($126.98 instead of $137.46).

## Root cause

OCR was working correctly — every field was read at ~99% confidence. The failures
were all in the regex patterns in `invoice_extractor.py`:

1. **Dates:** patterns only recognized numeric dates (`09/26/2026`, `2026-09-26`).
   The invoice writes `September 26, 2026`, and `parse_date()` in `validators.py`
   had no `%B` (full month name) format, so even if a pattern had matched, it could
   not be normalized.
2. **Tax:** the pattern expected an amount directly after the label
   (`tax[:\s]*[$]?amount`), but the invoice writes `Tax (8.25%) $10.48`. The
   `(8.25%)` rate between label and amount broke the match.
3. **Total:** the pattern `total[:\s]*...` also matches inside the word
   **Subtotal**, so `total` captured the subtotal value. This was masked before
   tax extraction worked; once `tax` was extracted, `subtotal + tax ≠ total`
   would have produced a warning and sent the invoice to review anyway — and the
   wrong amount would reach the accounting app.

## Approach

Rather than reading code and guessing, the stored PDF was run through the real
pipeline (PDF → preprocess → OCR → extract → validate) with a small script that
printed each stage's output. Seeing the actual OCR text — near-perfect, with
`September 26, 2026` and `Tax (8.25%) $10.48` plainly visible — made it clear the
bug was downstream of OCR, and comparing that text against each pattern exposed
all three failures at once.

## Fix

- `parse_date()` accepts full/abbreviated month-name dates
  (`September 26, 2026`, `26 Sep 2026`, etc.) and normalizes whitespace first.
- Date patterns gained a month-name alternative.
- Tax patterns allow an optional rate (`(8.25%)` or `20%`) between label and amount.
- Total patterns use a lookbehind `(?<!sub)(?<!sub\s)(?<!sub-)` so `total` never
  matches inside `Subtotal`, `Sub Total`, or `Sub-total`. A narrower lookbehind
  was chosen over `\b` because OCR sometimes drops the leading `S` (`ubtotal`),
  and `\b` would have removed the fallback that still captured a total there.

## Takeaways

- **Print real pipeline output before touching code.** The OCR text showed all
  three bugs in one look; reading the regexes alone would have taken far longer.
- **A passing test suite doesn't mean working extraction.** The bug survived
  because all test fixtures used numeric dates and plain `Tax: $x` labels.
- **Fixing one bug can expose another.** Extracting tax correctly would have
  produced a spurious amount-mismatch warning because `total` was wrong —
  verifying the *combined* result, not each field in isolation, caught it.
