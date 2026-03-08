"""Unit tests for assessment models."""

import pytest
from pydantic import ValidationError

from backend.services.assessment.models import ApplicationProfile, AssessmentState


def test_application_profile_minimal():
    """Minimal valid profile requires only application_name."""
    p = ApplicationProfile(application_name="MyApp")
    assert p.application_name == "MyApp"
    assert p.tech_stack == []
    assert p.current_environment == "on-prem"
    assert p.target_environment == "azure"


def test_application_profile_full():
    """Full profile with all fields."""
    p = ApplicationProfile(
        application_name="OrderService",
        description="Order management",
        business_purpose="Order-to-cash",
        tech_stack=["Java 11", "Spring Boot", "Oracle"],
        current_environment="on-prem",
        target_environment="azure",
        dependencies=["InventoryService", "PaymentGateway"],
        compliance_requirements=["PCI"],
        timeline_expectation="6 months",
    )
    assert p.application_name == "OrderService"
    assert len(p.tech_stack) == 3
    assert p.target_environment == "azure"
    assert "PCI" in p.compliance_requirements


def test_application_profile_application_name_required():
    """application_name is required and must be non-empty."""
    with pytest.raises(ValidationError):
        ApplicationProfile(application_name="")
    with pytest.raises(ValidationError):
        ApplicationProfile()


def test_application_profile_env_values():
    """Environment fields accept only allowed values."""
    p = ApplicationProfile(
        application_name="X",
        current_environment="vm",
        target_environment="aws",
    )
    assert p.current_environment == "vm"
    assert p.target_environment == "aws"
    with pytest.raises(ValidationError):
        ApplicationProfile(application_name="X", current_environment="invalid")


def test_assessment_state():
    """AssessmentState holds profile, approach, report, status."""
    s = AssessmentState(id="abc-123")
    assert s.id == "abc-123"
    assert s.profile is None
    assert s.approach_document is None
    assert s.report is None
    assert s.status == "draft"

    p = ApplicationProfile(application_name="Test")
    s2 = AssessmentState(
        id="xyz",
        profile=p,
        approach_document="## Approach",
        report="# Report",
        status="done",
    )
    assert s2.profile.application_name == "Test"
    assert s2.status == "done"
