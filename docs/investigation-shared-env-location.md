# Investigation: backend could not find the shared root `.env` file

**Severity:** ⭐⭐ Low — services ran with missing/wrong config until started from the right directory.

## Problem

The backend must start from the `backend/` directory because its Python
module structure expects `app.main:app` from there. But `pydantic_settings`
looks for `.env` based on the process's working directory — so starting from
`backend/` made it search for `backend/.env`, while the real `.env` lived at
the project root. The backend silently ran without the shared configuration
(same `RPA_API_KEY`, storage path, accounting app URL, etc.).

## Fix

Instead of forcing the backend to start from the project root, the
configuration code was updated to search for `.env` in both the service
directory and the project root. The RPA processor was given the same lookup
logic, so each service can start from its own directory while still finding
the same shared `.env`.

Final structure:

```
document-ai-rpa/
├── .env                          ← shared configuration
├── backend/
│   ├── venv/
│   └── app/
│       └── main.py               ← backend starts here
└── rpa/
    ├── venv/
    └── python_rpa_processor.py   ← RPA starts here
```

Both services now locate `document-ai-rpa/.env` and therefore use the same
`RPA_API_KEY` and related settings.

## Follow-up: the first fix pointed one level too shallow

The RPA processor rejected every queue job with `401 Unauthorized`. The
backend's "project root" path was built as `Path(__file__).parent.parent`
from `backend/app/config.py`, which is `backend/`, not the project root. With
no `backend/.env`, the backend silently fell back to the default
`RPA_API_KEY`, while the RPA processor read the real key from the root
`.env`. The keys never matched.

The path is now resolved from `backend/` up one more level to the project
root. Both files are listed explicitly, with the root `.env` taking priority
over an optional `backend/.env` (the same order the RPA processor uses), and
real environment variables override both. A regression test checks the
resolved path, so this can't drift silently again.

## Takeaways

- **Startup directory and `.env` location don't have to match** — as long as
  the configuration code explicitly knows where to search.
- **Missing `.env` fails silently.** `pydantic_settings` falls back to
  defaults, so services appear to run fine while using wrong values — a
  subtle config bug, not a crash.
- **Verify the fix, not just the code.** The first fix looked right but never
  actually loaded the root file. Checking that the backend and RPA processor
  resolve the *same* key would have caught it immediately.
