"""LangGraph orchestration: Research → Summarize. Used for run-all flow; agents also callable directly."""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from backend.services.assessment.models import ApplicationProfile
from backend.services.assessment.research_agent import run_research
from backend.services.assessment.summarizer_agent import run_summarize


class AssessmentGraphState(TypedDict):
    """State for the assessment graph."""

    profile: ApplicationProfile
    approach_document: str | None
    report: str | None
    error: str | None


def _research_node(state: AssessmentGraphState) -> dict:
    """Research node: KB search + synthesis → approach document."""
    profile = state["profile"]
    try:
        approach = run_research(profile)
        return {"approach_document": approach, "error": None}
    except Exception as e:
        return {"approach_document": None, "error": str(e)}


def _summarize_node(state: AssessmentGraphState) -> dict:
    """Summarize node: profile + approach → report."""
    profile = state["profile"]
    approach = state.get("approach_document") or ""
    if state.get("error"):
        return {"report": None, "error": state["error"]}
    try:
        report = run_summarize(profile, approach)
        return {"report": report, "error": None}
    except Exception as e:
        return {"report": None, "error": str(e)}


def _should_continue_after_research(state: AssessmentGraphState) -> str:
    """Route: if error, end; else continue to summarize."""
    return "summarize" if not state.get("error") else "end"


def build_assessment_graph() -> StateGraph:
    """Build and compile the assessment graph."""
    workflow = StateGraph(AssessmentGraphState)

    workflow.add_node("research", _research_node)
    workflow.add_node("summarize", _summarize_node)

    workflow.add_edge(START, "research")
    workflow.add_conditional_edges("research", _should_continue_after_research, {
        "summarize": "summarize",
        "end": END,
    })
    workflow.add_edge("summarize", END)

    return workflow.compile()


def run_assessment_graph(profile: ApplicationProfile) -> tuple[str | None, str | None, str | None]:
    """
    Run full assessment: research → summarize.
    Returns (approach_document, report, error_message).
    """
    graph = build_assessment_graph()
    initial: AssessmentGraphState = {
        "profile": profile,
        "approach_document": None,
        "report": None,
        "error": None,
    }
    result = graph.invoke(initial)
    return (
        result.get("approach_document"),
        result.get("report"),
        result.get("error"),
    )
