"""
FastAPI backend for pinecone-semantic-search web app.
Run from project root: uvicorn backend.main:app --reload
In production (Docker), static frontend is served from STATIC_DIR when present.
"""
import os
import sys
from pathlib import Path

# Ensure project root is on path so we can import semantic_search, usage_tracker
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.routers import admin, assessment, chat, search
from backend.config import get_project_dir

app = FastAPI(
    title="Center of Excellence – Knowledge Base API",
    description="Search, chat, and admin for the migration CoE knowledge base.",
    version="0.1.0",
)

# In production (e.g. Docker), allow Space or cloud host origin; locally allow dev server
_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if os.getenv("ALLOWED_ORIGINS"):
    _origins.extend(o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip())
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    project_dir = get_project_dir()
    return {
        "status": "ok",
        "project_dir_configured": project_dir is not None,
    }


app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(assessment.router, prefix="/api", tags=["assessment"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])

# Serve built frontend when static dir exists (e.g. in Docker)
STATIC_DIR = _root / "static"
if (STATIC_DIR / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
