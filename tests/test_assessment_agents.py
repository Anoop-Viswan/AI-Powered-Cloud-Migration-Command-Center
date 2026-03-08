"""Unit tests for assessment agents (mocked LLM and KB)."""

from unittest.mock import patch, MagicMock

import pytest

from backend.services.assessment.models import ApplicationProfile
from backend.services.assessment.research_agent import run_research
from backend.services.assessment.summarizer_agent import run_summarize


@pytest.fixture
def sample_profile():
    return ApplicationProfile(
        application_name="OrderService",
        description="Order management system",
        tech_stack=["Java 11", "Spring Boot", "Oracle"],
        current_environment="on-prem",
        target_environment="azure",
    )


@patch("backend.services.assessment.research_agent._search_kb")
@patch("backend.services.assessment.research_agent.get_llm")
def test_run_research_mocked(mock_get_llm, mock_search_kb, sample_profile):
    """run_research returns approach document from mocked LLM."""
    mock_search_kb.return_value = ["Chunk 1: migration best practices", "Chunk 2: Azure patterns"]
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "## Approach\n- Lift and shift\n- Refactor DB"
    mock_llm.invoke.return_value = mock_response
    mock_get_llm.return_value = mock_llm

    result = run_research(sample_profile)
    assert "## Approach" in result
    assert "Lift and shift" in result
    mock_llm.invoke.assert_called_once()


@patch("backend.services.assessment.research_agent._search_kb")
@patch("backend.services.assessment.research_agent.get_llm")
def test_run_research_empty_kb(mock_get_llm, mock_search_kb, sample_profile):
    """run_research works when KB returns no chunks."""
    mock_search_kb.return_value = []
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "## Approach\nBased on general best practices..."
    mock_llm.invoke.return_value = mock_response
    mock_get_llm.return_value = mock_llm

    result = run_research(sample_profile)
    assert "## Approach" in result
    assert "best practices" in result.lower() or "Approach" in result


@patch("backend.services.assessment.summarizer_agent.get_llm")
def test_run_summarize_mocked(mock_get_llm, sample_profile):
    """run_summarize returns report from mocked LLM."""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "# Assessment Report\n\n## Executive Summary\n..."
    mock_llm.invoke.return_value = mock_response
    mock_get_llm.return_value = mock_llm

    approach = "## Approach\n- Strategy: Refactor\n- Steps: 1, 2, 3"
    result = run_summarize(sample_profile, approach)
    assert "# Assessment Report" in result or "Executive Summary" in result
    mock_llm.invoke.assert_called_once()
