# Investigation: invoices stuck at RPA_QUEUED and never processed

**Severity:** ⭐⭐⭐⭐ High — the end-to-end automation silently never ran.

## Problem

The flow stopped at `RPA_QUEUED` — invoices were successfully queued but never
progressed to `RPA_PROCESSING` or `RPA_COMPLETED`.

## Root cause

The UiPath RPA workflow was never deployed or running. The backend had all the
correct RPA endpoints, but nothing was polling the queue. UiPath Studio — the
only supported way to build and run the workflow — is Windows-only, so on
macOS there was no executable RPA process at all. The workflow guide itself
stated it was "a guide for implementing the workflow manually in UiPath
Studio" and that "the actual .xaml file cannot be generated without UiPath
Studio."

## Evidence

- Backend API had proper RPA endpoints (`GET /api/rpa/queue`,
  `POST /api/rpa/{document_id}/start`, `POST /api/rpa/{document_id}/result`).
- The RPA queue contained invoices (verified: `DOC-240377FA63A3` was queued).
- The simulated accounting application existed and was properly configured
  (Flask app on port 3001).
- UiPath documentation existed but described a manual, Windows-only setup.
- No running UiPath robot or automation process existed anywhere.

## Fix

Created a Python-based RPA processor that runs on macOS and provides the same
functionality as the UiPath workflow:

- `rpa/python_rpa_processor.py` — polls the RPA queue automatically,
  processes invoices through the complete workflow
  (`RPA_QUEUED → RPA_PROCESSING → accounting app → RPA_COMPLETED`), and
  reports results back to the backend.
- `simulated-accounting-app/app.py` — added a JSON API for programmatic
  invoice submission, returning accounting record IDs while keeping form
  submissions working.
- Configuration — updated `.env.example` with RPA processor settings and
  added `rpa/requirements.txt` plus documentation
  (`rpa/README_PYTHON_RPA.md`).

## Verification

- A queued invoice was picked up by the Python processor and moved
  `RPA_QUEUED → RPA_PROCESSING → RPA_COMPLETED`.
- The accounting record was created in the simulated accounting app, which
  returned the record ID.

## Takeaways

- **A queue without a consumer is a dead end.** The backend can enqueue
  correctly and the status can look healthy while nothing ever runs.
- **Check whether the worker exists, not just the API.** All endpoints were
  correct; the missing piece was a process calling them.
- **Platform constraints are architecture constraints.** UiPath Studio being
  Windows-only meant the documented RPA path simply could not run in this
  development environment — a local alternative was needed.
