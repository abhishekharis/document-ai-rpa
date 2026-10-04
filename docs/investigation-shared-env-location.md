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

## Takeaways

- **Startup directory and `.env` location don't have to match** — as long as
  the configuration code explicitly knows where to search.
- **Missing `.env` fails silently.** `pydantic_settings` falls back to
  defaults, so services appear to run fine while using wrong values — a
  subtle config bug, not a crash.
