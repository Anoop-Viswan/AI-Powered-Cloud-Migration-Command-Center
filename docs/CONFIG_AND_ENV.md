# Config and .env loading architecture

How the app loads and refreshes configuration (`.env` and process environment).

## Design

- **Single source:** `.env` in the project root. All runtime config (Pinecone, LLM, Tavily, etc.) is read via `os.getenv()` from the **process environment**.
- **Load once at startup:** When the backend starts, `load_dotenv()` runs (in `backend/config.py` and in `semantic_search.py`). That reads `.env` and sets `os.environ`, so every `os.getenv()` call uses that cache for the lifetime of the process.
- **No per-request reload:** Feature status, research, chat, and other endpoints do **not** re-read `.env` on every request. They use whatever is already in the process env. This keeps I/O predictable and avoids file reads on every call.
- **When .env or config changes:** You have two options:
  1. **Restart the server** – Process env is re-initialized from `.env` on next startup.
  2. **One-time reload** – Call `POST /api/admin/reload-env`. That runs `load_dotenv(override=True)` once, re-reading `.env` from disk and updating the process env. After that, the next feature-status request, research run, etc. will see the new values. In the Admin UI (Knowledge Base tab), use the **“Reload .env”** button to do this and then refresh the Feature status panel.

## Where it’s implemented

| Piece | Role |
|-------|------|
| `backend/config.py` | `load_dotenv()` on import (startup); `reload_env()` to re-read `.env` with `override=True`. |
| `semantic_search.py` | `load_dotenv()` on import when running CLI/seed. |
| `POST /api/admin/reload-env` | Calls `reload_env()` once; returns `{ "ok": true }`. |
| Admin UI → Knowledge Base | “Reload .env” button → POST reload-env → then refetches feature-status. |

## Summary

- **Cache:** Process environment (`os.environ`) is the cache; it is filled at startup and can be refreshed once via `reload_env()`.
- **Load:** At startup only (or once when you trigger reload).
- **When config changes:** Restart the server, or use “Reload .env” (or `POST /api/admin/reload-env`) once, then continue as normal.
