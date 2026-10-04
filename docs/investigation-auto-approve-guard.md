# Investigation: wrong values were auto-approved into the RPA queue

**Severity:** ⭐⭐⭐⭐ High — garbage values could reach the accounting queue unchecked.

## Problem

Once extraction was fixed, `sample_invoice.pdf` would flow
`PROCESSED → APPROVED → RPA_QUEUED` automatically — the happy path. But before
the extraction fixes, it would have done the same with a garbage vendor and
truncated invoice number: validation only checked that required fields *exist*,
not that their values make sense. Anything the extractor produced was trusted.

## Root cause

`ValidationService.validate()` had two kinds of checks — presence of required
fields, and cross-field consistency (date order, `subtotal + tax = total`) — but
no per-field *plausibility* checks. `determine_status()` sends any invoice with
no errors and no warnings to `PROCESSED`, and `main.py` auto-approves and
RPA-queues anything `PROCESSED`. So a vendor like `INVOICE Invoice Number` or an
invoice number like `TX 75201` sailed straight into the accounting queue.

## Approach

The extraction fixes themselves remove most bad values at the source. But
extraction is a heuristic layer — it will always have edge cases, and other paths
(edits, reprocessing, future importers) write the same fields. The missing layer
was a cheap last line of defense in validation: if a required field's value is
*clearly* wrong, don't let it auto-approve.

## Fix

Shared helpers in `app/utils/validators.py`, used by both the extractor (to
reject candidates) and the validator (to flag survivors):

- `is_plausible_vendor_name()` — rejects label-like or address-like values.
- `is_plausible_invoice_number()` — rejects digit-less and ZIP-like values.

In `ValidationService.validate()`, implausible values produce **warnings**, not
errors — warnings route to `NEEDS_REVIEW` (human can correct), while errors
reject outright. The existing auto-approve path is untouched: it only fires on
`PROCESSED`, which now requires a clean validation.

## Takeaways

- **Validate values, not just presence.** "Field exists" and "field is correct"
  are different checks, and only the second protects downstream systems.
- **Warnings vs errors is a routing decision.** Clearly-wrong values deserve a
  human (NEEDS_REVIEW); missing/broken invariants deserve rejection. Choose per
  case instead of collapsing both into errors.
- **Defense in depth:** fix extraction at the source *and* guard at the
  validation boundary — each layer catches what the other misses.
