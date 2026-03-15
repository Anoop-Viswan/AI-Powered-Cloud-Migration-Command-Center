"""Integration tests for assessment API."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app

# Disable admin auth for tests so admin/diagnostics endpoints respond without login
os.environ.pop("ADMIN_USERNAME", None)
os.environ.pop("ADMIN_PASSWORD", None)

from backend.routers.admin import get_assessment_store
from backend.routers.assessment import get_store
from backend.services.assessment.store import AssessmentStore

# Minimal valid profile that passes all mandatory validations (Overview, Arch, Data, BC&DR, Security)
VALID_PROFILE = {
    "application_name": "TestApp",
    "business_purpose": "Order processing and inventory management",
    "user_count_estimate": "5000",
    "priority": "high",
    "rto": "4 hours",
    "rpo": "1 hour",
    "tech_stack": ["Java", "Spring Boot"],
    "current_environment": "on-prem",
    "target_environment": "azure",
    "current_architecture_description": "Three-tier app with web, app, DB layers.",
    "contains_database_migration": "yes",
    "total_data_volume": "500 GB",
    "database_types": ["PostgreSQL"],
    "current_databases_description": "Single PostgreSQL 14 instance.",
    "current_dr_strategy": "Daily backups to NAS.",
    "backup_frequency": "daily",
    "failover_approach": "Manual failover",
    "dr_testing_frequency": "quarterly",
    "authentication_type": "SAML",
    "encryption_at_rest": "AES-256",
    "encryption_in_transit": "TLS 1.2",
}


@pytest.fixture
def client(tmp_path):
    """Test client with temp store."""
    os.environ.pop("ADMIN_USERNAME", None)
    os.environ.pop("ADMIN_PASSWORD", None)
    db_path = tmp_path / "api_test.db"
    store = AssessmentStore(db_path=db_path)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_assessment_store] = lambda: store
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_store, None)
        app.dependency_overrides.pop(get_assessment_store, None)


@pytest.fixture
def assessment_id(client):
    """Create assessment and return id."""
    r = client.post("/api/assessment/start")
    assert r.status_code == 200
    return r.json()["assessment_id"]


@pytest.fixture
def client_and_store(tmp_path):
    """Test client and store, for tests that need to manipulate the store directly."""
    os.environ.pop("ADMIN_USERNAME", None)
    os.environ.pop("ADMIN_PASSWORD", None)
    db_path = tmp_path / "api_test.db"
    store = AssessmentStore(db_path=db_path)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_assessment_store] = lambda: store
    try:
        client = TestClient(app)
        yield client, store
    finally:
        app.dependency_overrides.pop(get_store, None)
        app.dependency_overrides.pop(get_assessment_store, None)


def test_start_assessment(client):
    """POST /assessment/start returns assessment_id."""
    r = client.post("/api/assessment/start")
    assert r.status_code == 200
    data = r.json()
    assert "assessment_id" in data
    assert isinstance(data["assessment_id"], str)


def test_get_assessment_not_found(client):
    """GET /assessment/{id} returns 404 for unknown id."""
    r = client.get("/api/assessment/nonexistent-id-12345")
    assert r.status_code == 404


def test_get_assessment(client, assessment_id):
    """GET /assessment/{id} returns draft state."""
    r = client.get(f"/api/assessment/{assessment_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == assessment_id
    assert data["profile"] is None
    assert data["status"] == "draft"


def test_save_profile(client, assessment_id):
    """PUT /assessment/{id}/profile saves profile."""
    profile = {**VALID_PROFILE, "description": "Test"}
    r = client.put(f"/api/assessment/{assessment_id}/profile", json=profile)
    assert r.status_code == 200
    assert r.json()["ok"] is True

    r2 = client.get(f"/api/assessment/{assessment_id}")
    assert r2.json()["profile"]["application_name"] == "TestApp"


def test_research_requires_profile(client, assessment_id):
    """POST /assessment/{id}/research returns 400 without profile."""
    r = client.post(f"/api/assessment/{assessment_id}/research")
    assert r.status_code == 400


def test_research_rejects_minimal_profile(client, assessment_id):
    """POST /assessment/{id}/research returns 400 when profile has only app name (missing required fields)."""
    profile = {"application_name": "TestApp"}
    client.put(f"/api/assessment/{assessment_id}/profile", json=profile)
    r = client.post(f"/api/assessment/{assessment_id}/research")
    assert r.status_code == 400
    detail = r.json().get("detail", "").lower()
    assert "required" in detail


def test_validate_profile_returns_errors_for_incomplete(client, assessment_id):
    """GET /assessment/{id}/validate returns errors when mandatory fields missing."""
    client.put(f"/api/assessment/{assessment_id}/profile", json={"application_name": "TestApp"})
    r = client.get(f"/api/assessment/{assessment_id}/validate")
    assert r.status_code == 200
    data = r.json()
    assert data.get("valid") is False
    assert len(data.get("errors", [])) > 0


def test_validate_profile_success_with_full_profile(client, assessment_id):
    """GET /assessment/{id}/validate returns valid when all mandatory fields present."""
    client.put(f"/api/assessment/{assessment_id}/profile", json=VALID_PROFILE)
    r = client.get(f"/api/assessment/{assessment_id}/validate")
    assert r.status_code == 200
    data = r.json()
    assert data.get("valid") is True


def test_validate_rejects_db_migration_yes_without_data_fields(client, assessment_id):
    """When contains_database_migration is Yes, data volume/DB types/description are required."""
    profile = {**VALID_PROFILE, "contains_database_migration": "yes", "total_data_volume": "", "database_types": [], "current_databases_description": ""}
    client.put(f"/api/assessment/{assessment_id}/profile", json=profile)
    r = client.get(f"/api/assessment/{assessment_id}/validate")
    assert r.status_code == 200
    data = r.json()
    assert data.get("valid") is False
    err_str = " ".join(data.get("errors", [])).lower()
    assert "data" in err_str or "volume" in err_str or "database" in err_str


def test_validate_returns_findings_for_unreasonable_values(client, assessment_id):
    """Validate returns findings when RTO/RPO or data volume are unusually high."""
    profile = {**VALID_PROFILE, "rto": "10000 hours", "rpo": "1 hour"}
    client.put(f"/api/assessment/{assessment_id}/profile", json=profile)
    r = client.get(f"/api/assessment/{assessment_id}/validate")
    assert r.status_code == 200
    data = r.json()
    assert data.get("valid") is True
    findings = data.get("findings", [])
    assert any(f.get("type") == "rto_very_high" for f in findings)


def test_validate_flags_placeholder_content(client, assessment_id):
    """Validate flags placeholder/nonsense values (e.g. 'architecture is good') via content validation."""
    profile = {**VALID_PROFILE, "current_architecture_description": "architecture is good"}
    client.put(f"/api/assessment/{assessment_id}/profile", json=profile)
    r = client.get(f"/api/assessment/{assessment_id}/validate")
    assert r.status_code == 200
    data = r.json()
    assert data.get("valid") is True
    findings = data.get("findings", [])
    content = [f for f in findings if f.get("type") == "content_placeholder"]
    assert any("architecture" in (f.get("field") or "").lower() or "good" in (f.get("value") or "").lower() for f in content)


def test_submit_requires_profile(client, assessment_id):
    """POST /assessment/{id}/submit returns 400 without profile."""
    r = client.post(f"/api/assessment/{assessment_id}/submit")
    assert r.status_code == 400


def test_submit_rejects_invalid_profile(client, assessment_id):
    """POST /assessment/{id}/submit returns 400 when profile is incomplete."""
    client.put(f"/api/assessment/{assessment_id}/profile", json={"application_name": "TestApp"})
    r = client.post(f"/api/assessment/{assessment_id}/submit")
    assert r.status_code == 400


def test_submit_success(client, assessment_id):
    """POST /assessment/{id}/submit sets status=submitted and does not run research."""
    client.put(f"/api/assessment/{assessment_id}/profile", json=VALID_PROFILE)
    r = client.post(f"/api/assessment/{assessment_id}/submit")
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("status") == "submitted"
    r2 = client.get(f"/api/assessment/{assessment_id}")
    assert r2.json()["status"] == "submitted"
    assert r2.json().get("approach_document") is None


@patch("backend.routers.assessment.run_research")
def test_research_success(mock_research, client, assessment_id):
    """POST /assessment/{id}/research returns approach document and structured KB data."""
    from backend.services.assessment.research_models import KBConfidence, ResearchResult

    client.put(f"/api/assessment/{assessment_id}/profile", json=VALID_PROFILE)
    mock_research.return_value = ResearchResult(
        approach_document="## Approach\n- Step 1\n- Step 2",
        kb_confidence=KBConfidence(value=0.7, label="high", below_threshold=False),
        kb_hits=[],
        official_docs=[],
    )
    r = client.post(f"/api/assessment/{assessment_id}/research")
    assert r.status_code == 200
    data = r.json()
    assert "## Approach" in data["approach_document"]
    assert data["status"] == "research_done"
    assert "kb_confidence" in data
    assert data["kb_confidence"]["label"] == "high"
    assert "kb_hits" in data


def test_summarize_requires_profile(client, assessment_id):
    """POST /assessment/{id}/summarize returns 400 without profile."""
    r = client.post(f"/api/assessment/{assessment_id}/summarize")
    assert r.status_code == 400


def test_summarize_requires_research(client, assessment_id):
    """POST /assessment/{id}/summarize returns 400 without approach doc."""
    client.put(f"/api/assessment/{assessment_id}/profile", json=VALID_PROFILE)
    r = client.post(f"/api/assessment/{assessment_id}/summarize")
    assert r.status_code == 400


@patch("backend.routers.assessment.export_target_diagram")
@patch("backend.routers.assessment.run_mermaid_from_design")
@patch("backend.routers.assessment.run_architecture_design")
@patch("backend.routers.assessment.run_quality_check")
@patch("backend.routers.assessment.run_summarize")
def test_summarize_success(
    mock_summarize,
    mock_quality_check,
    mock_design,
    mock_mermaid,
    mock_export,
    client_and_store,
):
    """POST /assessment/{id}/summarize runs design -> mermaid -> export -> report -> quality check."""
    from backend.services.assessment.architecture_design_agent import DesignResult

    client, store = client_and_store
    r_start = client.post("/api/assessment/start")
    assert r_start.status_code == 200
    assessment_id = r_start.json()["assessment_id"]
    client.put(f"/api/assessment/{assessment_id}/profile", json=VALID_PROFILE)
    store.update_approach(assessment_id, "## Approach doc")

    mock_design.return_value = DesignResult(
        design_instructions="Azure App Service, Azure SQL, Front Door.",
        clarifications_needed=[],
    )
    mock_mermaid.return_value = "flowchart TB\n  A[App]\n  B[DB]\n  A --> B"
    mock_export.return_value = {"image_url": f"/api/assessment/{assessment_id}/diagram/target?format=png"}
    mock_summarize.return_value = "# Assessment Report\n\n## Executive Summary\n..."
    mock_quality_check.return_value = {
        "comprehensive": {"score": 75, "reason": "Covers main sections."},
        "actionable": {"score": 70, "reason": "Clear next steps."},
        "useful": {"score": 80, "reason": "App-specific."},
        "diagrams": {"score": 80, "reason": "Target-state Mermaid diagram present."},
        "overall_pass": True,
        "suggestions": [],
    }
    r = client.post(f"/api/assessment/{assessment_id}/summarize")
    assert r.status_code == 200
    data = r.json()
    assert "Assessment Report" in data["report"] or "Executive Summary" in data["report"]
    assert data["status"] == "done"


@patch("backend.routers.assessment.run_architecture_design")
def test_summarize_needs_clarification(mock_design, client_and_store):
    """POST /assessment/{id}/summarize returns needs_clarification when design asks questions."""
    from backend.services.assessment.architecture_design_agent import DesignResult

    client, store = client_and_store
    r_start = client.post("/api/assessment/start")
    assessment_id = r_start.json()["assessment_id"]
    client.put(f"/api/assessment/{assessment_id}/profile", json=VALID_PROFILE)
    store.update_approach(assessment_id, "## Approach doc")

    mock_design.return_value = DesignResult(
        design_instructions="Target: Azure. App Service, SQL.",
        clarifications_needed=["Who consumes the audit data?", "What is the expected RPO?"],
    )
    r = client.post(f"/api/assessment/{assessment_id}/summarize")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "needs_clarification"
    assert "questions" in data
    assert len(data["questions"]) == 2


def test_get_report_json(client, assessment_id):
    """GET /assessment/{id}/report returns JSON with report text (default)."""
    r = client.get(f"/api/assessment/{assessment_id}/report")
    assert r.status_code == 200
    data = r.json()
    assert "report" in data
    assert data["report"] == "" or isinstance(data["report"], str)

    client.put(
        f"/api/assessment/{assessment_id}/report",
        json={"report": "# My Report\n\nContent here."},
    )
    r2 = client.get(f"/api/assessment/{assessment_id}/report")
    assert r2.status_code == 200
    assert "My Report" in r2.json()["report"]


def test_get_report_docx(client, assessment_id):
    """GET /assessment/{id}/report?format=docx returns DOCX attachment."""
    client.put(
        f"/api/assessment/{assessment_id}/report",
        json={"report": "# Title\n\nParagraph one."},
    )
    r = client.get(f"/api/assessment/{assessment_id}/report?format=docx")
    assert r.status_code == 200
    assert "application/vnd.openxmlformats" in r.headers.get("content-type", "")
    assert "attachment" in r.headers.get("content-disposition", "").lower()
    assert len(r.content) > 100


def test_put_report(client, assessment_id):
    """PUT /assessment/{id}/report updates report body without changing status."""
    r = client.get(f"/api/assessment/{assessment_id}")
    assert r.json()["status"] == "draft"
    r = client.put(
        f"/api/assessment/{assessment_id}/report",
        json={"report": "# Edited Report\n\nNew content."},
    )
    assert r.status_code == 200
    assert r.json().get("ok") is True
    r2 = client.get(f"/api/assessment/{assessment_id}")
    assert r2.json()["report"] == "# Edited Report\n\nNew content."
    assert r2.json()["status"] == "draft"


def test_delete_assessment(client, assessment_id):
    """DELETE /assessment/{id} removes the assessment."""
    r = client.delete(f"/api/assessment/{assessment_id}")
    assert r.status_code == 200
    assert r.json().get("ok") is True
    r2 = client.get(f"/api/assessment/{assessment_id}")
    assert r2.status_code == 404


def test_delete_assessment_not_found(client):
    """DELETE /assessment/{id} returns 404 for unknown id."""
    r = client.delete("/api/assessment/nonexistent-id-12345")
    assert r.status_code == 404


def test_cleanup_drafts(client):
    """POST /api/admin/assessments/cleanup?status=draft removes all drafts."""
    client.post("/api/assessment/start")
    client.post("/api/assessment/start")
    r = client.get("/api/admin/assessments")
    assert len(r.json()) == 2
    r = client.post("/api/admin/assessments/cleanup?status=draft")
    assert r.status_code == 200
    assert r.json().get("ok") is True
    assert r.json().get("deleted") == 2
    r2 = client.get("/api/admin/assessments")
    assert len(r2.json()) == 0


def test_feature_status(client):
    """GET /api/admin/feature-status returns status for pinecone, llm, langsmith, tavily with informed messages."""
    r = client.get("/api/admin/feature-status")
    assert r.status_code == 200
    data = r.json()
    for key in ("pinecone", "llm", "langsmith", "tavily"):
        assert key in data
        entry = data[key]
        assert "status" in entry
        assert "message" in entry
        assert entry["status"] in ("ok", "disabled", "limit_reached", "error")


def test_diagnostics_summary(client):
    """GET /api/admin/diagnostics/summary returns period, llm, tavily, thresholds, alerts."""
    r = client.get("/api/admin/diagnostics/summary?period=24h")
    assert r.status_code == 200
    data = r.json()
    assert "period" in data
    assert data["period"] == "24h"
    assert "llm" in data
    assert "total_calls" in data["llm"]
    assert "approx_cost_usd" in data["llm"]
    assert "tavily" in data
    assert "thresholds" in data
    assert "alerts" in data


def test_diagnostics_requests(client):
    """GET /api/admin/diagnostics/requests returns a list with id, error_message, model, metadata for drill-down."""
    r = client.get("/api/admin/diagnostics/requests?limit=10")
    assert r.status_code == 200
    data = r.json()
    assert "requests" in data
    assert isinstance(data["requests"], list)
    for req in data["requests"]:
        assert "id" in req
        assert "interface" in req
        assert "timestamp" in req
        assert "error_message" in req  # may be None
        assert "metadata" in req  # may be None; for tools
        if req["interface"] == "llm":
            assert "model" in req


def test_diagnostics_interfaces(client):
    """GET /api/admin/diagnostics/interfaces returns llm, tavily, pinecone with latency and status."""
    r = client.get("/api/admin/diagnostics/interfaces?period=24h")
    assert r.status_code == 200
    data = r.json()
    assert "llm" in data
    assert "calls" in data["llm"]
    assert "errors" in data["llm"]
    assert "status" in data["llm"]
    assert "tavily" in data
    assert "pinecone" in data


def test_diagnostics_patterns(client):
    """GET /api/admin/diagnostics/patterns returns top_consumers with cost and pct."""
    r = client.get("/api/admin/diagnostics/patterns?period=7d")
    assert r.status_code == 200
    data = r.json()
    assert "period" in data
    assert "top_consumers" in data
    assert isinstance(data["top_consumers"], list)
