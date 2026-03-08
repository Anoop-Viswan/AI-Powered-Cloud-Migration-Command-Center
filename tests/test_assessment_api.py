"""Integration tests for assessment API."""

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app
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
    db_path = tmp_path / "api_test.db"
    store = AssessmentStore(db_path=db_path)
    app.dependency_overrides[get_store] = lambda: store
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_store, None)


@pytest.fixture
def assessment_id(client):
    """Create assessment and return id."""
    r = client.post("/api/assessment/start")
    assert r.status_code == 200
    return r.json()["assessment_id"]


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
    """POST /assessment/{id}/research returns approach document."""
    client.put(f"/api/assessment/{assessment_id}/profile", json=VALID_PROFILE)

    mock_research.return_value = "## Approach\n- Step 1\n- Step 2"
    r = client.post(f"/api/assessment/{assessment_id}/research")
    assert r.status_code == 200
    data = r.json()
    assert "## Approach" in data["approach_document"]
    assert data["status"] == "research_done"


def test_summarize_requires_profile(client, assessment_id):
    """POST /assessment/{id}/summarize returns 400 without profile."""
    r = client.post(f"/api/assessment/{assessment_id}/summarize")
    assert r.status_code == 400


def test_summarize_requires_research(client, assessment_id):
    """POST /assessment/{id}/summarize returns 400 without approach doc."""
    client.put(f"/api/assessment/{assessment_id}/profile", json=VALID_PROFILE)
    r = client.post(f"/api/assessment/{assessment_id}/summarize")
    assert r.status_code == 400


@patch("backend.routers.assessment.run_research")
@patch("backend.routers.assessment.run_summarize")
def test_summarize_success(mock_summarize, mock_research, client, assessment_id):
    """POST /assessment/{id}/summarize returns report."""
    client.put(f"/api/assessment/{assessment_id}/profile", json=VALID_PROFILE)
    mock_research.return_value = "## Approach doc"
    client.post(f"/api/assessment/{assessment_id}/research")

    mock_summarize.return_value = "# Assessment Report\n\n## Executive Summary\n..."
    r = client.post(f"/api/assessment/{assessment_id}/summarize")
    assert r.status_code == 200
    data = r.json()
    assert "Assessment Report" in data["report"] or "Executive Summary" in data["report"]
    assert data["status"] == "done"
