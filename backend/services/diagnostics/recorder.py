"""
Record LLM and tool calls for the Diagnostics dashboard.

- record_llm_call: call after each LLM invoke (or use invoke_llm wrapper).
- record_tool_call: call from tool gateway (e.g. Tavily wrapper).
- invoke_llm: optional wrapper that invokes and records in one step.
"""

import time
from typing import Any

from backend.services.diagnostics.store import get_diagnostics_store


def _usage_from_response(response: Any) -> tuple[int | None, int | None]:
    """Extract (input_tokens, output_tokens) from LangChain AIMessage response."""
    if response is None:
        return None, None
    meta = getattr(response, "response_metadata", None) or {}
    usage = meta.get("usage_metadata") or meta.get("usage") or meta.get("token_usage") or {}
    inp = usage.get("input_tokens") or usage.get("prompt_tokens")
    out = usage.get("output_tokens") or usage.get("completion_tokens")
    return inp, out


def _model_from_llm(llm: Any) -> str | None:
    """Get model name from LangChain chat model."""
    return getattr(llm, "model_name", None) or getattr(llm, "model", None) or None


def record_llm_call(
    operation: str,
    model: str | None,
    input_tokens: int | None,
    output_tokens: int | None,
    latency_ms: int | None,
    status: str = "ok",
    error_message: str | None = None,
    assessment_id: str | None = None,
) -> None:
    """Write one LLM call to the diagnostics store."""
    try:
        get_diagnostics_store().record_llm(
            operation=operation,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
            assessment_id=assessment_id,
        )
    except Exception:
        pass  # don't break app if diagnostics DB fails


def record_tool_call(
    tool_name: str,
    latency_ms: int | None,
    status: str = "ok",
    error_message: str | None = None,
    assessment_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Write one tool call (e.g. Tavily) to the diagnostics store."""
    try:
        get_diagnostics_store().record_tool(
            tool_name=tool_name,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
            assessment_id=assessment_id,
            metadata=metadata,
        )
    except Exception:
        pass


def invoke_llm(llm: Any, messages: list, operation: str, assessment_id: str | None = None):
    """
    Invoke the LLM and record the call for Diagnostics. Use this instead of llm.invoke()
    so we capture tokens, latency, and status.
    """
    model = _model_from_llm(llm)
    start = time.perf_counter()
    try:
        response = llm.invoke(messages)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        inp, out = _usage_from_response(response)
        record_llm_call(
            operation=operation,
            model=model,
            input_tokens=inp,
            output_tokens=out,
            latency_ms=elapsed_ms,
            status="ok",
            assessment_id=assessment_id,
        )
        return response
    except Exception as e:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        record_llm_call(
            operation=operation,
            model=model,
            input_tokens=None,
            output_tokens=None,
            latency_ms=elapsed_ms,
            status="error",
            error_message=str(e)[:500],
            assessment_id=assessment_id,
        )
        raise
