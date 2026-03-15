"""
Interface connectivity tests: verify external dependencies with detailed errors.

These tests call real APIs (Pinecone, LLM, Tavily, Mermaid.ink) when the relevant
env vars are set. Run before push or in CI (with GitHub Secrets) to catch env/network
issues that would cause deployment to fail. When a key is missing, the test is skipped
so CI without secrets stays green. When a key is set but the check fails, the test
fails with a very detailed message for easy debugging.

Usage:
  pytest tests/test_interface_connectivity.py -v           # run all (skip when key missing)
  pytest tests/test_interface_connectivity.py -v -m external
  pytest tests/ -m "not external"                         # exclude these (CI without secrets)
"""

import os

import pytest

# Load .env so local runs use it; CI uses env from GitHub Secrets
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from tests.interface_checks import (
    check_pinecone,
    check_llm,
    check_langsmith,
    check_tavily,
    check_mermaid_ink,
)


def _fail_message(result: dict) -> str:
    """Build a full failure message for assertion output (message + detail + setup_steps)."""
    msg = result.get("message", "Check failed")
    parts = [msg]
    detail = result.get("detail")
    if detail:
        parts.append(f"Detail: {detail}")
    steps = result.get("setup_steps")
    if steps:
        parts.append("What to do: " + " ".join(f"{i+1}. {s}" for i, s in enumerate(steps)))
    return "\n".join(parts)


@pytest.mark.external
def test_pinecone_connectivity():
    """Pinecone: API key valid and index exists. Skip if PINECONE_API_KEY not set."""
    result = check_pinecone()
    if not result["ok"] and "not set" in result["message"].lower():
        pytest.skip(f"Pinecone: {result['message']} {result.get('detail') or ''}")
    assert result["ok"], _fail_message(result)


@pytest.mark.external
def test_llm_connectivity():
    """LLM (OpenAI/Anthropic/Azure): API key valid and one minimal invoke. Skip if key not set."""
    result = check_llm()
    if not result["ok"] and ("not set" in result["message"].lower() or "is not set" in result["message"].lower()):
        pytest.skip(f"LLM: {result['message']} {result.get('detail') or ''}")
    assert result["ok"], _fail_message(result)


@pytest.mark.external
def test_langsmith_config():
    """LangSmith: if tracing enabled, API key must be set. Skip if tracing off."""
    result = check_langsmith()
    if not result["ok"] and "not set" in result["message"].lower():
        pytest.skip(f"LangSmith: {result['message']} {result.get('detail') or ''}")
    assert result["ok"], _fail_message(result)


@pytest.mark.external
def test_tavily_connectivity():
    """Tavily: API key valid and one search. Skip if TAVILY_API_KEY not set."""
    result = check_tavily()
    if not result["ok"] and "not configured" in result["message"].lower():
        pytest.skip(f"Tavily: optional; {result.get('detail') or ''}")
    if not result["ok"] and "not set" in result["message"].lower():
        pytest.skip(f"Tavily: {result['message']} {result.get('detail') or ''}")
    assert result["ok"], _fail_message(result)


@pytest.mark.external
def test_mermaid_ink_reachable():
    """Mermaid.ink: service reachable (diagram images in reports). No key; always run."""
    result = check_mermaid_ink()
    assert result["ok"], _fail_message(result)
