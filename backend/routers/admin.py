"""Admin API: config, seed, usage, manifest, assessments. Login/logout when admin auth is enabled."""
import hmac
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel

from backend.config import get_project_dir, reload_env
from backend.services.assessment.store import AssessmentStore
from backend.services.feature_status import get_feature_status
from backend.auth import (
    get_admin_credentials,
    is_admin_protected,
    create_session_token,
    ADMIN_SESSION_COOKIE,
    ADMIN_SESSION_MAX_AGE,
)


def get_assessment_store() -> AssessmentStore:
    return AssessmentStore()


router = APIRouter()


# ─── Admin login / logout (no auth required) ─────────────────────────────────

class LoginBody(BaseModel):
    username: str = ""
    password: str = ""


@router.post("/login")
def admin_login(body: LoginBody, response: Response):
    """
    Authenticate with ADMIN_USERNAME and ADMIN_PASSWORD from env.
    On success sets an httpOnly session cookie and returns { "ok": true }.
    If admin auth is not configured (env not set), returns 401.
    """
    if not is_admin_protected():
        raise HTTPException(status_code=401, detail="Admin login not configured")
    user, pw = get_admin_credentials()
    # Constant-time compare to reduce timing leaks
    if not (user and pw and body.username == user and _constant_time_compare(body.password, pw)):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_session_token()
    response.set_cookie(
        key=ADMIN_SESSION_COOKIE,
        value=token,
        max_age=ADMIN_SESSION_MAX_AGE,
        httponly=True,
        secure=os.getenv("ALLOWED_ORIGINS", "").strip().lower().startswith("https"),
        samesite="lax",
        path="/",
    )
    return {"ok": True}


def _constant_time_compare(a: str, b: str) -> bool:
    """Constant-time string comparison."""
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


@router.post("/logout")
def admin_logout(response: Response):
    """Clear the admin session cookie."""
    response.delete_cookie(key=ADMIN_SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def admin_me(request: Request):
    """
    Returns 200 { "ok": true } if the request has a valid admin session (for frontend auth check).
    Returns 401 if not authenticated. When admin is not protected, returns 200.
    """
    if not is_admin_protected():
        return {"ok": True}
    from backend.auth import verify_session_token
    cookie = request.cookies.get(ADMIN_SESSION_COOKIE)
    if not cookie or not verify_session_token(cookie):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"ok": True}

# Status file in project root (parent of backend/)
_SEED_STATUS_PATH = Path(__file__).resolve().parent.parent.parent / ".seed_status.json"


def _write_seed_status(data: dict):
    try:
        _SEED_STATUS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def _run_seed():
    """Run seed in process (blocking). Called from background task. Writes status to .seed_status.json."""
    from backend.semantic_search import (
        get_client,
        seed_documents,
        INDEX_NAME,
    )
    from backend.usage_tracker import check_spend_guardrail
    project_dir = get_project_dir()
    if not project_dir:
        _write_seed_status({
            "status": "failed",
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "error": "PINECONE_PROJECT_DIR not set",
        })
        return
    try:
        check_spend_guardrail(allow_over_limit_flag=True)
    except SystemExit:
        pass
    try:
        pc = get_client()
        index = pc.Index(INDEX_NAME)
        namespace, record_count = seed_documents(index, project_dir)
        _write_seed_status({
            "status": "completed",
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "namespace": namespace,
            "records_upserted": record_count,
        })
    except Exception as e:
        _write_seed_status({
            "status": "failed",
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
        })


@router.get("/config")
def get_config():
    project_dir = get_project_dir()
    return {
        "project_dir": project_dir,
        "spend_limit": float(os.getenv("PINECONE_SPEND_LIMIT", "10")),
        "allow_over_limit": os.getenv("PINECONE_ALLOW_OVER_LIMIT", "").strip().lower() in ("yes", "1", "true"),
    }


@router.get("/usage")
def get_usage():
    from backend.usage_tracker import get_estimated_spend, get_spend_limit
    estimated, ru, wu = get_estimated_spend()
    limit = get_spend_limit()
    return {
        "estimated_spend_usd": round(estimated, 4),
        "read_units": ru,
        "write_units": wu,
        "spend_limit_usd": limit,
        "at_or_over_limit": estimated >= limit,
    }


def _read_seed_status():
    if not _SEED_STATUS_PATH.exists():
        return {"status": "idle"}
    try:
        return json.loads(_SEED_STATUS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"status": "idle"}


@router.get("/seed/status")
def get_seed_status():
    """Return current seed job status: idle | running | completed | failed. Poll after POST /seed."""
    return _read_seed_status()


@router.post("/seed")
def trigger_seed(background_tasks: BackgroundTasks):
    if not get_project_dir():
        raise HTTPException(status_code=400, detail="PINECONE_PROJECT_DIR not set")
    _write_seed_status({
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
    })
    background_tasks.add_task(_run_seed)
    return {"status": "started", "message": "Indexing started. Poll GET /api/admin/seed/status for completion."}


@router.get("/manifest")
def get_manifest():
    from backend.semantic_search import load_manifest
    project_dir = get_project_dir()
    if not project_dir:
        return {"applications": {}}
    data = load_manifest(project_dir)
    return {"applications": data}


# ─── Assessments (admin view) ─────────────────────────────────────────────────

@router.get("/assessments/summary")
def get_assessments_summary(store: AssessmentStore = Depends(get_assessment_store)):
    """Summary counts for scorecards: total, done, in_progress, error."""
    return store.get_summary()


@router.get("/assessments")
def list_assessments(
    store: AssessmentStore = Depends(get_assessment_store),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None, description="Filter by status: done, error, draft, etc."),
):
    """List assessments for admin: id, app_name, status, error_message, updated_at."""
    return store.list_all(limit=limit, status_filter=status)


@router.get("/feature-status")
def get_feature_status_endpoint():
    """
    Return status for all features (Pinecone, LLM, LangSmith, Tavily) so the UI
    can show informed messages: what is configured, what is missing, and how to fix.
    Uses env loaded at startup or after POST /api/admin/reload-env.
    """
    return get_feature_status()


@router.post("/reload-env")
def reload_env_endpoint():
    """
    Re-read .env from project root and update process env (one-time refresh).
    Call this after editing .env to pick up new keys (e.g. TAVILY_API_KEY) without restarting the server.
    Then refresh feature-status or run research to use the updated config.
    """
    reload_env()
    return {"ok": True, "message": "Environment reloaded from .env. Refresh feature status or run research to use updated keys."}


@router.post("/assessments/cleanup")
def cleanup_assessments(
    store: AssessmentStore = Depends(get_assessment_store),
    status: str = Query(..., description="Delete all with this status, e.g. draft"),
    limit: int = Query(1000, ge=1, le=5000),
):
    """Delete all assessments with the given status. Use for cleaning up drafts."""
    if status not in ("draft", "error"):
        raise HTTPException(
            status_code=400,
            detail="Cleanup only allowed for status: draft or error",
        )
    deleted = store.delete_by_status(status, limit=limit)
    return {"ok": True, "deleted": deleted}
