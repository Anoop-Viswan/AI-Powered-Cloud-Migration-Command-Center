"""Admin API: config, seed, usage, manifest."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks

from backend.config import get_project_dir

router = APIRouter()

# Status file in project root (parent of backend/)
_SEED_STATUS_PATH = Path(__file__).resolve().parent.parent.parent / ".seed_status.json"


def _write_seed_status(data: dict):
    try:
        _SEED_STATUS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def _run_seed():
    """Run seed in process (blocking). Called from background task. Writes status to .seed_status.json."""
    from semantic_search import (
        get_client,
        seed_documents,
        INDEX_NAME,
    )
    from usage_tracker import check_spend_guardrail
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
    from usage_tracker import get_estimated_spend, get_spend_limit
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
    from semantic_search import load_manifest
    project_dir = get_project_dir()
    if not project_dir:
        return {"applications": {}}
    data = load_manifest(project_dir)
    return {"applications": data}
