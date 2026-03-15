"""Assessment API: step-by-step endpoints for multi-agent assessment flow."""

import json
import re
import queue
import threading
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from backend.services.assessment.architecture_design_agent import (
    run_architecture_design,
    run_mermaid_from_design,
)
from backend.services.assessment.diagram_export import clear_diagram_artifacts, export_target_diagram
from backend.services.assessment.models import ApplicationProfile
from backend.services.assessment.profile_validator import validate_profile_for_research
from backend.services.assessment.quality_check import run_quality_check
from backend.services.assessment.research_agent import run_research
from backend.services.assessment.store import AssessmentStore
from backend.services.assessment.summarizer_agent import run_summarize

router = APIRouter()


def _user_friendly_error_detail(exc: Exception) -> str:
    """
    Return a user-facing message when research/LLM fails so the user knows
    whether the issue is API key, limit, or something else. All steps should be informed.
    Tavily errors are passed through as-is so the user sees the exact API/network reason.
    """
    msg = str(exc)
    if "tavily" in msg.lower():
        return msg
    msg_lower = msg.lower()
    if "api_key" in msg_lower or "api key" in msg_lower or "authentication" in msg_lower:
        return (
            "LLM or external service failed: API key may be missing or invalid. "
            "Check OPENAI_API_KEY (or ANTHROPIC_API_KEY / AZURE_OPENAI_* for your LLM_PROVIDER) in .env. "
            "See docs/ENV_REFERENCE.md."
        )
    if "401" in msg_lower or "unauthorized" in msg_lower:
        return (
            "Unauthorized: API key may be invalid or expired. Check your LLM provider key in .env. "
            "See docs/ENV_REFERENCE.md."
        )
    if "403" in msg_lower or "forbidden" in msg_lower:
        return (
            "Access forbidden: check API key permissions or quota. See docs/ENV_REFERENCE.md."
        )
    if "429" in msg_lower or "rate limit" in msg_lower or "quota" in msg_lower:
        return (
            "Rate limit or quota exceeded. Wait and retry, or check your provider dashboard. "
            "See docs/ENV_REFERENCE.md."
        )
    return msg


# Upload dir: data/assessment_uploads/{assessment_id}/
def _uploads_dir() -> Path:
    root = Path(__file__).resolve().parent.parent.parent
    return root / "data" / "assessment_uploads"


def get_store() -> AssessmentStore:
    return AssessmentStore()


def _inject_diagram_into_report(report: str, diagram_image_url: str) -> str:
    """Ensure the report contains the diagram as an image (correct URL). Replaces or appends section 4.
    Uses the given URL (our PNG endpoint or mermaid.ink fallback) so the diagram is never blank."""
    # Body to inject: image markdown + caption (no heading so we don't duplicate)
    body = (
        f"![Target State Architecture]({diagram_image_url})\n\n"
        f"*The diagram above follows Microsoft/cloud reference architecture (edge, VNet, app tier, data tier, identity). "
        f"Download the editable Mermaid source (.mmd) or PNG from the assessment page.*"
    )
    # Match section 4: heading line containing "Target State Architecture", then content until next ##
    pattern = r"(\n##\s*[^\n]*[Tt]arget [Ss]tate [Aa]rchitecture[^\n]*\n\n)(.*?)(?=\n##\s|\Z)"
    if re.search(pattern, report, re.DOTALL):
        return re.sub(pattern, r"\g<1>" + body + "\n\n", report, count=1, flags=re.DOTALL)
    # Insert before Migration Strategy if section 4 is missing
    if "## Migration Strategy" in report or "## 5." in report:
        section = "\n\n## Target State Architecture (diagram)\n\n" + body + "\n\n"
        for anchor in ("\n## Migration Strategy", "\n## 5."):
            if anchor in report:
                return report.replace(anchor, section + anchor, 1)
    return report + "\n\n## Target State Architecture (diagram)\n\n" + body + "\n\n"


@router.post("/assessment/start")
def start_assessment(store: AssessmentStore = Depends(get_store)):
    """Create new assessment; returns assessment_id."""
    aid = store.create()
    return {"assessment_id": aid}


@router.delete("/assessment/{assessment_id}")
def delete_assessment(assessment_id: str, store: AssessmentStore = Depends(get_store)):
    """Delete an assessment (e.g. draft or unwanted). Admin or same-user use."""
    if not store.delete(assessment_id):
        raise HTTPException(status_code=404, detail="Assessment not found")
    return {"ok": True, "deleted": assessment_id}


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
        "quality_check": state.quality_check,
        "research_details": state.research_details,
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
    """Serve uploaded architecture diagram (current or future)."""
    if diagram_type not in ALLOWED_DIAGRAM_TYPES:
        raise HTTPException(status_code=404, detail="Not found")
    from fastapi.responses import FileResponse
    upload_dir = _uploads_dir() / assessment_id
    for ext in ALLOWED_EXTENSIONS:
        p = upload_dir / f"{diagram_type}{ext}"
        if p.exists():
            return FileResponse(p, media_type=f"image/{ext[1:]}")
    raise HTTPException(status_code=404, detail="Diagram not found")


@router.get("/assessment/{assessment_id}/diagram/target")
def get_target_diagram(
    assessment_id: str,
    format: str = Query("png", description="png (image) or mmd (editable Mermaid source)"),
):
    """Serve generated target-state architecture diagram: PNG image or editable .mmd file. Generated when you run Generate report."""
    from fastapi.responses import FileResponse
    dir_path = _target_diagram_dir(assessment_id)
    if format and format.lower() == "mmd":
        p = dir_path / "target_architecture.mmd"
        if not p.exists():
            raise HTTPException(status_code=404, detail="Target diagram not found. Generate a report first.")
        return Response(
            content=p.read_text(encoding="utf-8"),
            media_type="text/plain",
            headers={"Content-Disposition": 'attachment; filename="target_architecture.mmd"'},
        )
    p = dir_path / "target_architecture.png"
    if not p.exists():
        raise HTTPException(status_code=404, detail="Target diagram not found. Generate a report first.")
    return FileResponse(p, media_type="image/png")


def _is_rerun(state) -> bool:
    """True if this assessment has already run research or has a report (re-run / regenerate scenario)."""
    if not state:
        return False
    if state.approach_document and state.approach_document.strip():
        return True
    if state.status in ("research_done", "done"):
        return True
    return False


@router.post("/assessment/{assessment_id}/research")
def run_research_step(assessment_id: str, store: AssessmentStore = Depends(get_store)):
    """Trigger Research Agent; returns approach document. Sync (polling via GET for status).
    When re-running research (assessment already has approach or report), strict profile validation
    is skipped so the admin is not stuck; missing data can be requested via clarification later."""
    state = store.get(assessment_id)
    if not state:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if not state.profile:
        raise HTTPException(status_code=400, detail="Profile required before research")

    if not _is_rerun(state):
        validation = validate_profile_for_research(state.profile)
        if not validation.valid:
            msg = "; ".join(validation.errors)
            if validation.suggestions:
                msg += ". Suggestions: " + "; ".join(validation.suggestions[:3])
            raise HTTPException(status_code=400, detail=msg)

    store.clear_artifacts_for_research(assessment_id)
    clear_diagram_artifacts(assessment_id)
    store.update_status(assessment_id, "researching")
    try:
        # run_research returns ResearchResult (approach_document, kb_confidence, kb_hits, official_docs)
        result = run_research(state.profile)
        # Store approach and research_details (kb_hits, official_docs) for transparency in UI
        store.update_approach(
            assessment_id,
            result.approach_document,
            research_details={
                "kb_hits": [h.model_dump() for h in result.kb_hits],
                "official_docs": [d.model_dump() for d in result.official_docs],
            },
        )
        # Return full structured response for UI (confidence, explainability, official_docs)
        return {
            "approach_document": result.approach_document,
            "status": "research_done",
            "kb_confidence": result.kb_confidence.model_dump(),
            "kb_hits": [h.model_dump() for h in result.kb_hits],
            "official_docs": [d.model_dump() for d in result.official_docs],
        }
    except Exception as e:
        detail = _user_friendly_error_detail(e)
        store.update_status(assessment_id, "error", error_message=detail)
        raise HTTPException(status_code=500, detail=detail)


@router.post("/assessment/{assessment_id}/research/stream")
def run_research_stream(
    assessment_id: str,
    store: AssessmentStore = Depends(get_store),
):
    """
    Run research and stream live events (SSE) so the UI can show progress.

    Events: phase (with optional duration_seconds), kb_results, confidence, official_search_results, key_results, done, error.
    Each event is sent as SSE: data: {"type": "...", "payload": {...}}\n\n
    On "done", the approach document is stored and status set to research_done.
    """
    state = store.get(assessment_id)
    if not state:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if not state.profile:
        raise HTTPException(status_code=400, detail="Profile required before research")
    if not _is_rerun(state):
        validation = validate_profile_for_research(state.profile)
        if not validation.valid:
            msg = "; ".join(validation.errors)
            if validation.suggestions:
                msg += ". " + "; ".join(validation.suggestions[:3])
            raise HTTPException(status_code=400, detail=msg)

    event_queue: queue.Queue = queue.Queue()

    def event_callback(event_type: str, payload: dict) -> None:
        """Called from research agent; put events on queue for the SSE generator."""
        event_queue.put((event_type, payload))

    def run_in_thread() -> None:
        try:
            run_research(state.profile, event_callback=event_callback)
        except Exception as e:
            event_queue.put(("error", {"message": _user_friendly_error_detail(e)}))

    store.clear_artifacts_for_research(assessment_id)
    clear_diagram_artifacts(assessment_id)
    store.update_status(assessment_id, "researching")
    thread = threading.Thread(target=run_in_thread)
    thread.start()

    def generate_sse():
        while True:
            try:
                event_type, payload = event_queue.get(timeout=60)
            except queue.Empty:
                break
            event_data = json.dumps({"type": event_type, "payload": payload})
            yield f"data: {event_data}\n\n"
            if event_type == "done":
                approach_document = payload.get("approach_document") or ""
                research_details = None
                if payload.get("kb_hits") is not None or payload.get("official_docs") is not None:
                    research_details = {
                        "kb_hits": payload.get("kb_hits") or [],
                        "official_docs": payload.get("official_docs") or [],
                    }
                store.update_approach(assessment_id, approach_document, research_details=research_details)
                break
            if event_type == "error":
                err_msg = payload.get("message", "Research failed")
                store.update_status(assessment_id, "error", error_message=err_msg)
                break
        thread.join(timeout=1)

    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _target_diagram_dir(assessment_id: str) -> Path:
    """Directory for generated target architecture diagram (.mmd and .png)."""
    root = Path(__file__).resolve().parent.parent.parent
    return root / "data" / "assessment_diagrams" / assessment_id


@router.post("/assessment/{assessment_id}/summarize")
def run_summarize_step(
    assessment_id: str,
    body: SummarizeBody | None = None,
    store: AssessmentStore = Depends(get_store),
):
    """
    Generate report: Phase 1 (architecture design) → optional HITL → Phase 2 (Mermaid from design)
    → export diagram → report narrative. Clears previous report and quality check.
    Body may include clarification_answers when design requested them (human-in-the-loop).
    """
    state = store.get(assessment_id)
    if not state:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if not state.profile:
        raise HTTPException(status_code=400, detail="Profile required")
    if not state.approach_document:
        raise HTTPException(status_code=400, detail="Research (approach document) required before summarize")
    store.clear_report_and_quality_check(assessment_id)
    store.update_status(assessment_id, "summarizing")
    clarification_answers = (body and body.clarification_answers) or None
    skip_clarification = bool(body and body.skip_clarification)
    try:
        design_result = run_architecture_design(
            state.profile,
            state.approach_document,
            research_details=state.research_details,
            clarification_answers=clarification_answers,
            skip_clarification=skip_clarification,
        )
        if design_result.clarifications_needed and not clarification_answers and not skip_clarification:
            store.update_status(assessment_id, "research_done")
            return {
                "status": "needs_clarification",
                "questions": design_result.clarifications_needed,
                "design_instructions": design_result.design_instructions,
                "message": "Architect: please answer the clarification questions so we can generate an accurate diagram, or submit with empty answers to generate anyway.",
            }
        mermaid_code = run_mermaid_from_design(design_result.design_instructions)
        diagram_result = export_target_diagram(assessment_id, mermaid_code)
        # Prefer our PNG URL; when PNG fetch fails we still get mermaid_ink_url so the diagram is not blank
        diagram_image_url = diagram_result.get("image_url") or diagram_result.get("mermaid_ink_url")
        clarification_context = None
        questions = (body and body.clarification_questions) or []
        if clarification_answers:
            parts = []
            for i, a in enumerate(clarification_answers):
                q = questions[i] if i < len(questions) else f"Question {i+1}"
                parts.append(f"  Q: {q}\n  A: {a}")
            clarification_context = "Architect clarifications (human-in-the-loop):\n" + "\n\n".join(parts)
        report = run_summarize(
            state.profile,
            state.approach_document,
            diagram_image_url=diagram_image_url,
            clarification_context=clarification_context,
        )
        if diagram_image_url:
            report = _inject_diagram_into_report(report, diagram_image_url)
        store.update_report(assessment_id, report)
        try:
            qc = run_quality_check(state.profile, report)
            store.update_quality_check(assessment_id, qc)
        except Exception:
            pass
        return {"report": report, "status": "done"}
    except Exception as e:
        detail = _user_friendly_error_detail(e)
        store.update_status(assessment_id, "error", error_message=detail)
        raise HTTPException(status_code=500, detail=detail)


class ReportUpdate(BaseModel):
    """Body for updating report (edit)."""
    report: str = ""


class SummarizeBody(BaseModel):
    """Optional body for summarize: clarification questions/answers (HITL) or skip to generate with current design."""
    clarification_questions: list[str] | None = None  # Questions that were asked (so report can reflect them)
    clarification_answers: list[str] | None = None
    skip_clarification: bool = False  # If True, do not ask for clarifications; generate diagram anyway


@router.post("/assessment/{assessment_id}/quality-check")
def run_quality_check_step(assessment_id: str, store: AssessmentStore = Depends(get_store)):
    """Run quality check on the current report (comprehensive, actionable, useful). Stores and returns the result."""
    state = store.get(assessment_id)
    if not state:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if not state.profile:
        raise HTTPException(status_code=400, detail="Profile required")
    report_text = state.report or ""
    if not report_text.strip():
        raise HTTPException(status_code=400, detail="Report required. Generate a report first.")
    try:
        qc = run_quality_check(state.profile, report_text)
        store.update_quality_check(assessment_id, qc)
        return qc
    except Exception as e:
        detail = _user_friendly_error_detail(e)
        raise HTTPException(status_code=500, detail=detail)


@router.put("/assessment/{assessment_id}/report")
def update_report_body(
    assessment_id: str,
    body: ReportUpdate,
    store: AssessmentStore = Depends(get_store),
):
    """Update report text (Admin edit). Does not change status."""
    if not store.get(assessment_id):
        raise HTTPException(status_code=404, detail="Assessment not found")
    store.update_report_body(assessment_id, body.report or "")
    return {"ok": True}


@router.get("/assessment/{assessment_id}/report")
def get_report(
    assessment_id: str,
    format: str = Query("json", description="json or docx"),
    store: AssessmentStore = Depends(get_store),
):
    """Get report: JSON (report text) or DOCX download."""
    state = store.get(assessment_id)
    if not state:
        raise HTTPException(status_code=404, detail="Assessment not found")
    report_text = state.report or ""
    if format and format.lower() == "docx":
        from backend.services.assessment.report_docx import report_to_docx
        app_name = (state.profile.application_name or "Assessment") if state.profile else "Assessment"
        title = f"Migration Assessment Report — {app_name}"
        docx_bytes = report_to_docx(report_text, title=title, assessment_id=assessment_id)
        filename = f"AssessmentReport-{app_name.replace(' ', '_')}-{assessment_id[:8]}.docx"
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    return {"report": report_text}
