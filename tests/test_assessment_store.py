"""Unit tests for assessment store."""

from pathlib import Path

import pytest

from backend.services.assessment.models import ApplicationProfile
from backend.services.assessment.store import AssessmentStore


@pytest.fixture
def temp_store(tmp_path):
    """Store backed by temp SQLite file."""
    db_path = tmp_path / "test.db"
    return AssessmentStore(db_path=db_path)


def test_create(temp_store):
    """create() returns a UUID string."""
    aid = temp_store.create()
    assert isinstance(aid, str)
    assert len(aid) == 36  # UUID format


def test_get_not_found(temp_store):
    """get() returns None for unknown id."""
    assert temp_store.get("nonexistent") is None


def test_create_and_get(temp_store):
    """Create then get returns draft state."""
    aid = temp_store.create()
    state = temp_store.get(aid)
    assert state is not None
    assert state.id == aid
    assert state.profile is None
    assert state.status == "draft"


def test_update_profile(temp_store):
    """update_profile persists profile."""
    aid = temp_store.create()
    profile = ApplicationProfile(
        application_name="TestApp",
        tech_stack=["Java"],
        target_environment="azure",
    )
    temp_store.update_profile(aid, profile)
    state = temp_store.get(aid)
    assert state.profile is not None
    assert state.profile.application_name == "TestApp"
    assert state.profile.tech_stack == ["Java"]


def test_update_approach(temp_store):
    """update_approach persists and sets status research_done."""
    aid = temp_store.create()
    temp_store.update_approach(aid, "## Approach doc")
    state = temp_store.get(aid)
    assert state.approach_document == "## Approach doc"
    assert state.status == "research_done"


def test_update_report(temp_store):
    """update_report persists and sets status done."""
    aid = temp_store.create()
    temp_store.update_report(aid, "# Full Report")
    state = temp_store.get(aid)
    assert state.report == "# Full Report"
    assert state.status == "done"


def test_update_status(temp_store):
    """update_status sets status and optional error."""
    aid = temp_store.create()
    temp_store.update_status(aid, "researching")
    state = temp_store.get(aid)
    assert state.status == "researching"

    temp_store.update_status(aid, "error", error_message="Something failed")
    state = temp_store.get(aid)
    assert state.status == "error"
    assert state.error_message == "Something failed"
