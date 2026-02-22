"""
FastAPI backend for pinecone-semantic-search web app.
Run from project root: uvicorn backend.main:app --reload
"""
import sys
from pathlib import Path

# Ensure project root is on path so we can import semantic_search, usage_tracker
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import admin, chat, search
from backend.config import get_project_dir

app = FastAPI(
    title="Center of Excellence – Knowledge Base API",
    description="Search, chat, and admin for the migration CoE knowledge base.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
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
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
