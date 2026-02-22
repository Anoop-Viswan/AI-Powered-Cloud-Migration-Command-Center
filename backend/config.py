"""Backend config: load from env (shared with semantic_search)."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def get_project_dir() -> str | None:
    path = os.getenv("PINECONE_PROJECT_DIR")
    if not path:
        return None
    path = os.path.abspath(os.path.expanduser(path))
    return path if os.path.isdir(path) else None
