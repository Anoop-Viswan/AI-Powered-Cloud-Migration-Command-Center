"""
Feature status: report which services are configured and why others are not.

Used by GET /api/admin/feature-status so the Admin UI can show informed messages
(e.g. "Tavily: not configured – add TAVILY_API_KEY to .env. See docs/ENV_REFERENCE.md").
Each feature returns: status (ok | disabled | limit_reached | error), message, instruction.
"""

import os
from typing import Any


def _env(key: str) -> str:
    return (os.getenv(key) or "").strip()


def _pinecone_status() -> dict[str, Any]:
    """Pinecone: API key, project dir, and spend limit status."""
    api_key = _env("PINECONE_API_KEY")
    project_dir = _env("PINECONE_PROJECT_DIR")
    if not api_key:
        return {
            "status": "disabled",
            "message": "Pinecone is not configured.",
            "instruction": "Add PINECONE_API_KEY to .env (get key from https://app.pinecone.io/). See docs/ENV_REFERENCE.md.",
        }
    try:
        from backend.usage_tracker import get_estimated_spend, get_spend_limit
        estimated = get_estimated_spend()[0]
        limit = get_spend_limit()
        at_limit = estimated >= limit
        allow_over = _env("PINECONE_ALLOW_OVER_LIMIT").lower() in ("yes", "1", "true")
    except Exception:
        at_limit = False
        allow_over = False
        estimated = 0
        limit = 10

    if at_limit and not allow_over:
        return {
            "status": "limit_reached",
            "message": f"Pinecone estimated spend (${estimated:.2f}) is at or over limit (${limit}).",
            "instruction": "Set PINECONE_ALLOW_OVER_LIMIT=yes in .env to allow, or increase PINECONE_SPEND_LIMIT. See docs/ENV_REFERENCE.md.",
        }
    if not project_dir:
        return {
            "status": "ok",
            "message": "Pinecone API key is set. Project directory not set – use --project-dir or PINECONE_PROJECT_DIR for search/seed.",
            "instruction": "Optional: set PINECONE_PROJECT_DIR in .env for KB search and seed.",
        }
    return {
        "status": "ok",
        "message": f"Pinecone configured. Project dir: {project_dir}.",
        "instruction": None,
    }


def _llm_status() -> dict[str, Any]:
    """LLM: provider and whether the required API key for that provider is set."""
    provider = _env("LLM_PROVIDER") or "openai"
    provider = provider.lower()

    if provider == "openai":
        key = _env("OPENAI_API_KEY")
        if not key:
            return {
                "status": "disabled",
                "message": "OpenAI is selected but OPENAI_API_KEY is not set.",
                "instruction": "Add OPENAI_API_KEY to .env (get key from https://platform.openai.com/). See docs/ENV_REFERENCE.md.",
            }
        model = _env("OPENAI_MODEL") or "gpt-4o-mini"
        return {"status": "ok", "message": f"OpenAI configured (model: {model}).", "instruction": None}

    if provider == "anthropic":
        key = _env("ANTHROPIC_API_KEY")
        if not key:
            return {
                "status": "disabled",
                "message": "Anthropic is selected but ANTHROPIC_API_KEY is not set.",
                "instruction": "Add ANTHROPIC_API_KEY to .env (get key from https://console.anthropic.com/). See docs/ENV_REFERENCE.md.",
            }
        return {"status": "ok", "message": "Anthropic configured.", "instruction": None}

    if provider == "azure_openai":
        endpoint = _env("AZURE_OPENAI_ENDPOINT")
        key = _env("AZURE_OPENAI_API_KEY")
        if not endpoint or not key:
            return {
                "status": "disabled",
                "message": "Azure OpenAI is selected but AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_KEY is not set.",
                "instruction": "Add AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY to .env. See docs/ENV_REFERENCE.md.",
            }
        return {"status": "ok", "message": "Azure OpenAI configured.", "instruction": None}

    return {
        "status": "error",
        "message": f"Unknown LLM_PROVIDER={provider}. Supported: openai, anthropic, azure_openai.",
        "instruction": "Set LLM_PROVIDER in .env to openai, anthropic, or azure_openai. See docs/ENV_REFERENCE.md.",
    }


def _langsmith_status() -> dict[str, Any]:
    """LangSmith: tracing on/off and API key."""
    tracing = _env("LANGCHAIN_TRACING_V2").lower() in ("true", "1", "yes")
    key = _env("LANGCHAIN_API_KEY")
    if not tracing:
        return {
            "status": "disabled",
            "message": "LangSmith tracing is off.",
            "instruction": "Set LANGCHAIN_TRACING_V2=true and LANGCHAIN_API_KEY in .env (get key from https://smith.langchain.com/) to enable tracing. See docs/ENV_REFERENCE.md.",
        }
    if not key:
        return {
            "status": "disabled",
            "message": "LANGCHAIN_TRACING_V2 is set but LANGCHAIN_API_KEY is missing.",
            "instruction": "Add LANGCHAIN_API_KEY to .env. See docs/ENV_REFERENCE.md.",
        }
    return {"status": "ok", "message": "LangSmith tracing enabled.", "instruction": None}


def _tavily_status() -> dict[str, Any]:
    """Tavily: used for official-doc web search when KB confidence is low."""
    key = _env("TAVILY_API_KEY")
    if not key:
        return {
            "status": "disabled",
            "message": "Tavily is not configured. Official-documentation search will be skipped when KB confidence is low.",
            "instruction": "Add TAVILY_API_KEY to .env (get key from https://app.tavily.com/) to enable official-doc search. See docs/ENV_REFERENCE.md.",
        }
    return {"status": "ok", "message": "Tavily configured. Official-doc search will run when KB confidence is below threshold.", "instruction": None}


def get_feature_status() -> dict[str, Any]:
    """Return status for all optional/required features for the Admin UI. Uses env loaded at startup or after POST /api/admin/reload-env."""
    return {
        "pinecone": _pinecone_status(),
        "llm": _llm_status(),
        "langsmith": _langsmith_status(),
        "tavily": _tavily_status(),
    }
