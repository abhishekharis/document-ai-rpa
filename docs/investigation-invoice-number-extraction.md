# Investigation: invoice number truncated or read from the address

**Severity:** ⭐⭐⭐⭐ High — wrong invoice numbers extracted with no error shown.

## Problem

- `sample_invoice.pdf`: extracted `INV-2026` instead of `INV-2026-1047`.
- `TestInvoice.pdf`: extracted `TX 75201` — the state and ZIP from the address.
- `simple_invoice.png`: extracted `INV-2024` instead of `INV-2024-001`.

## Root cause

Two independent bugs in `_extract_invoice_number()`:

1. **The label was consumed by the previous token.** The labelled pattern
   `invoice\s*(?:no|number|#)?[:\s]*([A-Z0-9\-]+)` matched at the standalone
   heading `INVOICE`, where the capture grabbed the *next word*: `INVOICE`. That
   failed the "must contain a digit" check — but the code used `re.search`, which
   returns only the first match, so it never reached the real
   `Invoice Number: INV-2026-1047` later in the text. The generic fallback
   pattern then matched `INV-2026` (its `\d{4,}` stops at the second hyphen).
2. **The fallback pattern accepted ZIP codes.** `[A-Z]{2,4}[-\s]?\d{4,}` matches
   `TX 75201` — two letters, a space, five digits — so when a labelled number
   was missed, an address fragment won instead.

## Approach

Ran both documents through the extractor and printed each pattern's matches.
`finditer` showed `INVOICE` (heading) matching before `INV-2026-1047`, and showed
`TX 75201` satisfying every existing validation rule (letters + digits, plausible
shape) — which meant the fix needed a *negative* definition of what an invoice
number is not, not just a better positive pattern.

## Fix

- Labelled patterns now require a digit inside the capture
  (`[A-Z0-9\-]*\d[A-Z0-9\-]*`), so `INVOICE` heading can no longer swallow the
  label — the regex slides forward to the real `Invoice Number:` occurrence.
- `re.search` → `re.finditer`: every candidate is tried, in pattern-priority
  order, instead of giving up on the first malformed match.
- Every candidate passes `is_plausible_invoice_number()`: must contain a digit,
  3–30 chars, and must not look like `XX 12345` (US state + ZIP).
- The generic shape pattern is kept as a last resort for unlabeled invoices.

## Takeaways

- **`re.search` hides later, better matches.** When validation can reject a
  match, iterate all matches — don't assume the first is representative.
- **Test negative cases, not just positive ones.** `TX 75201` passed every
  positive check; only an explicit "looks like an address" rejection caught it.
- **Overlapping vocabularies are dangerous.** `INVOICE` as a heading *and* as a
  label prefix is a common invoice-layout trap; write patterns that assume both
  appear.
