# Investigation: vendor name extracted as garbage

**Severity:** ⭐⭐⭐⭐ High — fabricated vendor values flowed silently downstream.

## Problem

`sample_invoice.pdf` extracted `vendor_name = "INVOICE Invoice Number"` —
document labels, not a business name. Even after the deskew fix made
`ACME OFFICE SUPPLIES` visible to OCR, a second document (`TestInvoice.pdf`)
would have picked up `"Test Invoice ACME Office Supplies"` — the document title
glued to the vendor name.

## Root cause

Two problems in `_extract_vendor()`:

1. **No usable line structure.** OCR boxes were joined with spaces into one
   string per page, so `text.split('\n')` produced a single "line" containing the
   whole page. The `^`-anchored pattern then matched the *entire run of words* at
   the start: `INVOICE Invoice Number…`.
2. **No plausibility check.** Any capitalized run of words was accepted as a
   name. There was also no support for an explicit `Vendor:` label, which
   `TestInvoice.pdf` actually contains.

## Approach

After the deskew fix, the per-line `raw_results` from OCR were dumped. Each entry
is a real visual line (`'ACME OFFICE SUPPLIES'`, `'INVOICE'`,
`'Vendor: ACME Office Supplies'`). Working line-by-line instead of against the
joined page text made the extraction order obvious: an explicit label beats a
positional guess, and a positional guess needs a definition of what a name
*cannot* look like.

## Fix

`_extract_vendor()` now works on OCR lines (`raw_results`), falling back to
newline-split text:

1. Prefer an explicit `Vendor:` / `Supplier:` / `Seller:` / `From` label; if the
   value is on the next line, use that line.
2. Otherwise return the first header line passing `is_plausible_vendor_name()`:
   3–80 chars, letters/digits/`&.,'’-` only, no digit runs of 3+, and no document
   vocabulary (`invoice`, `bill`, `total`, `date`, `tax`, `number`, `amount`…).
3. If nothing qualifies, return `None` — a required field is then reported
   missing instead of fabricated.

## Takeaways

- **Preserve structural information as long as possible.** Joining OCR boxes into
  a flat string threw away the line boundaries that make headers findable.
- **Prefer explicit labels over positional heuristics**, and let positional
  heuristics *decline* rather than guess.
- **A wrong value is worse than a missing one** — missing produces a clear error;
  a wrong value flows silently into the accounting system.
