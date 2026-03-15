"""
Backend config: load from .env (shared with semantic_search).

Architecture:
- Load once at startup: load_dotenv() runs on import so the process env is set.
- No per-request reload: feature status, research, etc. read os.getenv() (process cache).
- When .env or config changes: restart the server, or call reload_env() once (e.g. via
  POST /api/admin/reload-env) to re-read .env from disk and update the process env.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Single load at startup; process env is the cache for all os.getenv() calls
load_dotenv()


def reload_env() -> None:
    """
    Re-read .env from project root and update process env (override=True).
    Call this once when .env was changed and you want to pick up new keys without restarting.
    Used by POST /api/admin/reload-env; can also be called from scripts or admin UI.
    """
    root = Path(__file__).resolve().parent.parent
    load_dotenv(root / ".env", override=True)


def get_project_dir() -> str | None:
    path = os.getenv("PINECONE_PROJECT_DIR")
    if not path:
        return None
    path = os.path.abspath(os.path.expanduser(path))
    return path if os.path.isdir(path) else None
