"""Unit tests for assessment agents (mocked LLM and KB)."""

from unittest.mock import MagicMock, patch

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


# _search_kb_full returns list of dicts with score, file_path, application, category, content
@patch("backend.services.assessment.research_agent._get_project_index_namespace", return_value=(MagicMock(), "test-ns"))
@patch("backend.services.assessment.research_agent._search_kb_full")
@patch("backend.services.assessment.research_agent.get_llm")
def test_run_research_mocked(mock_get_llm, mock_search_kb_full, _mock_namespace, sample_profile):
    """run_research returns ResearchResult with approach_document from mocked LLM."""
    mock_search_kb_full.return_value = [
        {"score": 0.85, "file_path": "docs/azure.md", "application": "default", "category": "md", "content": "Azure migration best practices"},
        {"score": 0.72, "file_path": "docs/db.md", "application": "default", "category": "md", "content": "Oracle to Azure SQL patterns"},
    ]
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "## Approach\n- Lift and shift\n- Refactor DB"
    mock_llm.invoke.return_value = mock_response
    mock_get_llm.return_value = mock_llm

    result = run_research(sample_profile)
    assert result.approach_document is not None
    assert "## Approach" in result.approach_document
    assert "Lift and shift" in result.approach_document
    assert result.kb_confidence.value >= 0
    assert len(result.kb_hits) == 2
    mock_llm.invoke.assert_called_once()


@patch("backend.services.assessment.research_agent._run_official_doc_search", return_value=[])
@patch("backend.services.assessment.research_agent._get_project_index_namespace", return_value=(MagicMock(), "test-ns"))
@patch("backend.services.assessment.research_agent._search_kb_full")
@patch("backend.services.assessment.research_agent.get_llm")
def test_run_research_empty_kb(mock_get_llm, mock_search_kb_full, _mock_namespace, _mock_official_docs, sample_profile):
    """run_research works when KB returns no hits; confidence is low; official-doc search mocked to avoid real Tavily call."""
    mock_search_kb_full.return_value = []
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "## Approach\nBased on general best practices..."
    mock_llm.invoke.return_value = mock_response
    mock_get_llm.return_value = mock_llm

    result = run_research(sample_profile)
    assert "## Approach" in result.approach_document
    assert result.kb_confidence.value == 0.0
    assert result.kb_confidence.below_threshold is True
    assert len(result.kb_hits) == 0


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
