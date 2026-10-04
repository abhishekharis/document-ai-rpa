# Investigation: uploads failed with ERROR and empty extraction data

**Severity:** ⭐⭐⭐⭐⭐ Critical — every uploaded document failed; nothing reached RPA.

## Problem

Invoice upload succeeded but processing failed, resulting in ERROR status, 0
page count, and no RPA queue entry despite validation showing PASS.

## Root cause

PaddleOCR initialization in `ocr_service.py` used the deprecated parameter
`show_log=False`, which newer PaddleOCR versions don't support. This caused
immediate OCR failure during processing, preventing the entire pipeline from
completing and leaving extraction data in its default/empty state.

## Approach

- Checked MongoDB for recent invoices: found ERROR status with empty
  extraction data (0 pages, 0 confidence, empty fields).
- Examined audit logs: revealed `Processing failed: Unknown argument: show_log`.
- Tested PDF processing separately: confirmed PyMuPDF worked correctly
  (1 page extracted).
- Tested OCR initialization: discovered PaddleOCR failed with
  `ValueError: Unknown argument: show_log`.
- Traced the execution path: upload → file storage → PDF processing →
  OCR initialization → exception → ERROR status.

## Fix

- Removed `show_log=False` from PaddleOCR initialization.
- Updated OCR result parsing for the new PaddleOCR format (dictionary with
  `rec_texts`, `rec_scores`, `rec_boxes` instead of the old list format).
- Added `paddlepaddle>=2.5.0` to `requirements.txt` and installed it.
- Updated the status flow: validation returns `PROCESSED` instead of
  `APPROVED`, with automatic transitions in `main.py`:
  `PROCESSING → PROCESSED → APPROVED → RPA_QUEUED`.

## Verification

- Uploaded a test invoice with all required fields (vendor_name,
  invoice_number, invoice_date, total, currency).
- Confirmed the MongoDB document shows: status=RPA_QUEUED, page_count=1, high
  confidence (0.98), validation PASS, RPA eligible=true.
- Verified the audit log shows the complete flow:
  UPLOAD → PROCESSING_COMPLETE → AUTO_APPROVED → RPA_QUEUED.
- Confirmed the RPA queue endpoint returns the queued invoice.

## Takeaways

- **Check logs first.** Audit trails often reveal the exact exception before
  you dive into the code.
- **Test components in isolation** (PDF processing, OCR, etc.) to narrow down
  where the failure occurs.
- **Look for early-stage failures.** When a whole pipeline fails, an
  initialization issue upstream often cascades into empty data downstream.
- **Library version changes break code.** Update parameters and result
  parsing to match the installed version.
- **Empty/default data signals early failure** — processing stopped before it
  could fill anything in.
- **Fix the root cause, not the symptom** — don't just change ERROR to
  another status.
