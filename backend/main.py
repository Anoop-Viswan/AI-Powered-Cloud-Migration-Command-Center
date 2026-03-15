"""
FastAPI backend for Cloud Migration Command Center.
Run from project root: uvicorn backend.main:app --reload
In production (Docker), static frontend is served from STATIC_DIR when present.
"""
import os
from pathlib import Path

_root = Path(__file__).resolve().parent.parent

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from backend.routers import admin, assessment, chat, diagnostics, search
from backend.config import get_project_dir
from backend.auth import (
    is_admin_protected,
    verify_session_token,
    ADMIN_SESSION_COOKIE,
)

app = FastAPI(
    title="Cloud Migration Command Center – API",
    description="Search, chat, assessment, and admin for the migration command center.",
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


class AdminAuthMiddleware(BaseHTTPMiddleware):
    """Require valid admin session cookie for /api/admin/* except login, logout, me."""

    _SKIP_PATHS = {"/api/admin/login", "/api/admin/logout", "/api/admin/me"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api/admin"):
            return await call_next(request)
        if path in self._SKIP_PATHS:
            return await call_next(request)
        if not is_admin_protected():
            return await call_next(request)
        cookie = request.cookies.get(ADMIN_SESSION_COOKIE)
        if not cookie or not verify_session_token(cookie):
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
        return await call_next(request)


app.add_middleware(AdminAuthMiddleware)


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
app.include_router(diagnostics.router, prefix="/api/admin/diagnostics", tags=["diagnostics"])

# Serve built frontend when static dir exists (e.g. in Docker)
STATIC_DIR = _root / "static"
if (STATIC_DIR / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
