"""Assessment API: step-by-step endpoints for multi-agent assessment flow."""

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend.services.assessment.models import ApplicationProfile
from backend.services.assessment.profile_validator import validate_profile_for_research
from backend.services.assessment.research_agent import run_research
from backend.services.assessment.store import AssessmentStore
from backend.services.assessment.summarizer_agent import run_summarize

router = APIRouter()

# Upload dir: data/assessment_uploads/{assessment_id}/
def _uploads_dir() -> Path:
    root = Path(__file__).resolve().parent.parent.parent
    return root / "data" / "assessment_uploads"


def get_store() -> AssessmentStore:
    return AssessmentStore()


@router.post("/assessment/start")
def start_assessment(store: AssessmentStore = Depends(get_store)):
    """Create new assessment; returns assessment_id."""
    aid = store.create()
    return {"assessment_id": aid}


@router.get("/assessment/{assessment_id}")
def get_assessment(assessment_id: str, store: AssessmentStore = Depends(get_store)):
    """Get full assessment state."""
    state = store.get(assessment_id)
    if not state:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return {
        "id": state.id,
        "profile": state.profile.model_dump() if state.profile else None,
        "approach_document": state.approach_document,
        "report": state.report,
        "status": state.status,
        "error_message": state.error_message,
    }


@router.put("/assessment/{assessment_id}/profile")
def save_profile(assessment_id: str, profile: ApplicationProfile, store: AssessmentStore = Depends(get_store)):
    """Save/update application profile."""
    if not store.get(assessment_id):
        raise HTTPException(status_code=404, detail="Assessment not found")
    store.update_profile(assessment_id, profile)
    return {"ok": True}


@router.get("/assessment/{assessment_id}/validate")
def validate_profile(assessment_id: str, store: AssessmentStore = Depends(get_store)):
    """Validate profile for research readiness. Returns validation result."""
    state = store.get(assessment_id)
    if not state:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if not state.profile:
        return {
            "valid": False,
            "errors": ["Profile required. Please fill in the profile before running research."],
            "warnings": [],
            "suggestions": [],
        }
    result = validate_profile_for_research(state.profile)
    return {
        "valid": result.valid,
        "errors": result.errors,
        "warnings": result.warnings,
        "suggestions": result.suggestions,
        "findings": getattr(result, "findings", []),
    }


@router.post("/assessment/{assessment_id}/submit")
def submit_for_assessment(assessment_id: str, store: AssessmentStore = Depends(get_store)):
    """Submit migration request (Application User flow). Validates profile, sets status=submitted. Does not run research."""
    state = store.get(assessment_id)
    if not state:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if not state.profile:
        raise HTTPException(status_code=400, detail="Profile required. Save your profile before submitting.")

    result = validate_profile_for_research(state.profile)
    if not result.valid:
        msg = "; ".join(result.errors)
        if result.suggestions:
            msg += ". " + "; ".join(result.suggestions[:3])
        raise HTTPException(status_code=400, detail=msg)

    store.update_status(assessment_id, "submitted")
    return {"ok": True, "status": "submitted"}


ALLOWED_DIAGRAM_TYPES = {"current", "future"}
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


@router.post("/assessment/{assessment_id}/upload/diagram")
async def upload_diagram(
    assessment_id: str,
    diagram_type: str = Form(..., alias="type"),
    file: UploadFile = File(...),
    store: AssessmentStore = Depends(get_store),
):
    """Upload architecture diagram (current or future state). Returns path to store in profile."""
    if diagram_type not in ALLOWED_DIAGRAM_TYPES:
        raise HTTPException(status_code=400, detail="type must be 'current' or 'future'")
    if not store.get(assessment_id):
        raise HTTPException(status_code=404, detail="Assessment not found")
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Allowed: PNG, JPG, WEBP")
    upload_dir = _uploads_dir() / assessment_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / f"{diagram_type}{ext}"
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10 MB
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")
    dest.write_bytes(content)
    rel_path = f"assessment_uploads/{assessment_id}/{diagram_type}{ext}"
    return {"path": rel_path, "url": f"/api/assessment/{assessment_id}/diagram/{diagram_type}"}


@router.get("/assessment/{assessment_id}/diagram/{diagram_type}")
def get_diagram(assessment_id: str, diagram_type: str):
    """Serve uploaded architecture diagram."""
    if diagram_type not in ALLOWED_DIAGRAM_TYPES:
        raise HTTPException(status_code=404, detail="Not found")
    from fastapi.responses import FileResponse
    upload_dir = _uploads_dir() / assessment_id
    for ext in ALLOWED_EXTENSIONS:
        p = upload_dir / f"{diagram_type}{ext}"
        if p.exists():
            return FileResponse(p, media_type=f"image/{ext[1:]}")
    raise HTTPException(status_code=404, detail="Diagram not found")


@router.post("/assessment/{assessment_id}/research")
def run_research_step(assessment_id: str, store: AssessmentStore = Depends(get_store)):
    """Trigger Research Agent; returns approach document. Sync (polling via GET for status)."""
    state = store.get(assessment_id)
    if not state:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if not state.profile:
        raise HTTPException(status_code=400, detail="Profile required before research")

    validation = validate_profile_for_research(state.profile)
    if not validation.valid:
        msg = "; ".join(validation.errors)
        if validation.suggestions:
            msg += ". Suggestions: " + "; ".join(validation.suggestions[:3])
        raise HTTPException(status_code=400, detail=msg)

    store.update_status(assessment_id, "researching")
    try:
        approach = run_research(state.profile)
        store.update_approach(assessment_id, approach)
        return {"approach_document": approach, "status": "research_done"}
    except Exception as e:
        store.update_status(assessment_id, "error", error_message=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assessment/{assessment_id}/summarize")
def run_summarize_step(assessment_id: str, store: AssessmentStore = Depends(get_store)):
    """Trigger Summarizer Agent; returns report."""
    state = store.get(assessment_id)
    if not state:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if not state.profile:
        raise HTTPException(status_code=400, detail="Profile required")
    if not state.approach_document:
        raise HTTPException(status_code=400, detail="Research (approach document) required before summarize")
    store.update_status(assessment_id, "summarizing")
    try:
        report = run_summarize(state.profile, state.approach_document)
        store.update_report(assessment_id, report)
        return {"report": report, "status": "done"}
    except Exception as e:
        store.update_status(assessment_id, "error", error_message=str(e))
        raise HTTPException(status_code=500, detail=str(e))
