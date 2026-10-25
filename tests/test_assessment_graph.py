"""Tests for the LangGraph orchestration (research -> summarize) and a real-model agent run.

The graph tests pin langgraph's public API we depend on: StateGraph, START/END,
conditional edges, compile() and invoke(). The agent test uses langchain-core's
real FakeListChatModel (a genuine BaseChatModel, not a MagicMock) so message
handling and the invoke_llm wrapper run through actual langchain-core code.
"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from backend.services.assessment import graph as graph_module
from backend.services.assessment.models import ApplicationProfile
from backend.services.assessment.summarizer_agent import run_summarize


@pytest.fixture
def profile():
    return ApplicationProfile(
        application_name="OrderService",
        description="Order management system",
        tech_stack=["Java 11", "Spring Boot", "Oracle"],
        current_environment="on-prem",
        target_environment="azure",
    )


def test_graph_compiles_with_expected_nodes():
    compiled = graph_module.build_assessment_graph()
    nodes = set(compiled.get_graph().nodes)
    assert {"research", "summarize"} <= nodes


def test_graph_happy_path_runs_research_then_summarize(profile):
    calls = []

    def fake_research(p):
        calls.append(("research", p.application_name))
        return "APPROACH"

    def fake_summarize(p, approach):
        calls.append(("summarize", approach))
        return "REPORT"

    with patch.object(graph_module, "run_research", side_effect=fake_research), \
         patch.object(graph_module, "run_summarize", side_effect=fake_summarize):
        approach, report, error = graph_module.run_assessment_graph(profile)

    assert (approach, report, error) == ("APPROACH", "REPORT", None)
    assert calls == [("research", "OrderService"), ("summarize", "APPROACH")]


def test_graph_research_error_skips_summarize(profile):
    summarize = MagicMock()
    with patch.object(graph_module, "run_research", side_effect=RuntimeError("KB down")), \
         patch.object(graph_module, "run_summarize", summarize):
        approach, report, error = graph_module.run_assessment_graph(profile)

    assert approach is None and report is None
    assert error == "KB down"
    summarize.assert_not_called()  # conditional edge routed straight to END


def test_graph_summarize_error_is_captured(profile):
    with patch.object(graph_module, "run_research", return_value="APPROACH"), \
         patch.object(graph_module, "run_summarize", side_effect=ValueError("LLM timeout")):
        approach, report, error = graph_module.run_assessment_graph(profile)

    assert approach == "APPROACH"
    assert report is None
    assert error == "LLM timeout"


def test_summarizer_with_real_langchain_chat_model(profile):
    """run_summarize end to end through a real BaseChatModel + invoke_llm diagnostics."""
    fake_llm = FakeListChatModel(responses=["# Assessment Report\nMove to Azure SQL."])
    recorded = []

    with patch("backend.services.assessment.summarizer_agent.get_llm", return_value=fake_llm), \
         patch("backend.services.diagnostics.recorder.record_llm_call", side_effect=lambda **kw: recorded.append(kw)):
        report = run_summarize(profile, "Approach: rehost then refactor")

    assert report == "# Assessment Report\nMove to Azure SQL."
    assert recorded and recorded[0]["operation"] == "summarize"
    assert recorded[0]["status"] == "ok"
