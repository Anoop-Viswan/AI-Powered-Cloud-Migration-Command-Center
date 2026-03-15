"""
Diagnostics: local metrics store for LLM and tool calls (tokens, latency, cost).

Enables the Admin Diagnostics tab so you can compare with LangSmith:
- Custom dashboard: summary, request log, thresholds, alerts (our data).
- LangSmith: deep traces (enable via LANGCHAIN_TRACING_V2 + LANGCHAIN_API_KEY).
"""

from backend.services.diagnostics.recorder import record_llm_call, record_tool_call
from backend.services.diagnostics.store import DiagnosticsStore, get_diagnostics_store

__all__ = [
    "get_diagnostics_store",
    "record_llm_call",
    "record_tool_call",
    "DiagnosticsStore",
]
