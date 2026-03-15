"""
Interface connectivity checks for deployment and pre-push verification.

Each check tries one external dependency (Pinecone, LLM, LangSmith, Tavily, Mermaid.ink)
and returns a result with a very detailed error message on failure so new environments
(e.g. Render) are easy to debug. Used by test_interface_connectivity.py and optionally
by scripts/verify_interfaces.py.

All functions return: {"name": str, "ok": bool, "message": str, "detail": str | None, "setup_steps": list[str] | None}
- name: short label (e.g. "Pinecone")
- ok: True if the check succeeded
- message: one-line summary (or full error for failures)
- detail: optional extra context (env var to set, link to docs, response snippet)
- setup_steps: optional numbered steps for one-time setup (so open-source users know what to do)
"""

import os
import ssl
import urllib.request
from typing import Any


def _env(key: str) -> str:
    return (os.getenv(key) or "").strip()


def _detail(*parts: str) -> str:
    return " ".join(parts) if parts else ""


# ---------------------------------------------------------------------------
# Pinecone
# ---------------------------------------------------------------------------

def check_pinecone() -> dict[str, Any]:
    """Verify PINECONE_API_KEY and that we can reach Pinecone (list_indexes)."""
    name = "Pinecone"
    key = _env("PINECONE_API_KEY")
    if not key:
        return {
            "name": name,
            "ok": False,
            "message": "Pinecone: PINECONE_API_KEY is not set.",
            "detail": "Required for knowledge base search and assessment. Add the key to .env.",
            "setup_steps": [
                "Sign up at https://app.pinecone.io/ and create or open a project.",
                "Create an API key under API Keys in the console.",
                "Add to .env: PINECONE_API_KEY=your-api-key-here",
                "Create the index 'coe-kb-search' (see docs/Setup-and-Reference/One-Time-Setup.md or README). Then run this verification again.",
            ],
        }
    try:
        from pinecone import Pinecone
        from pinecone.exceptions import PineconeException
        pc = Pinecone(api_key=key)
        indexes = list(pc.list_indexes().names() or [])
        index_name = os.getenv("PINECONE_INDEX_NAME", "coe-kb-search")
        if index_name and index_name not in indexes:
            return {
                "name": name,
                "ok": False,
                "message": f"Pinecone: Index '{index_name}' not found. Your API key works but the app expects this index.",
                "detail": f"Your indexes: {indexes or '(none)'}.",
                "setup_steps": [
                    f"Create an index named '{index_name}' in the Pinecone console (https://app.pinecone.io/).",
                    "Use embedding model llama-text-embed-v2 (or compatible), similarity Cosine, field to embed: content.",
                    "Or set PINECONE_INDEX_NAME in .env to an existing index name from the list above.",
                ],
            }
        return {
            "name": name,
            "ok": True,
            "message": f"Pinecone: OK (index '{index_name}' present).",
            "detail": None,
            "setup_steps": None,
        }
    except PineconeException as e:
        err = str(e).strip() or type(e).__name__
        return {
            "name": name,
            "ok": False,
            "message": f"Pinecone: API error – {err}",
            "detail": "Your key may be invalid, revoked, or the project/index not accessible.",
            "setup_steps": [
                "Check PINECONE_API_KEY in .env. Get a new key from https://app.pinecone.io/ if needed.",
                "Ensure the key has access to the project. If you see 403/404, create the index or fix the key.",
            ],
        }
    except Exception as e:
        err = str(e).strip() or type(e).__name__
        return {
            "name": name,
            "ok": False,
            "message": f"Pinecone: Unexpected error – {err}",
            "detail": "Network or firewall may be blocking api.pinecone.io.",
            "setup_steps": ["Check network and firewall. Ensure PINECONE_API_KEY is set correctly in .env."],
        }


# ---------------------------------------------------------------------------
# LLM (OpenAI / Anthropic / Azure)
# ---------------------------------------------------------------------------

def check_llm() -> dict[str, Any]:
    """Verify configured LLM provider: API key and one minimal invoke."""
    provider = (_env("LLM_PROVIDER") or "openai").strip().lower()
    name = f"LLM ({provider})"

    if provider == "openai":
        key = _env("OPENAI_API_KEY")
        if not key:
            return {
                "name": name,
                "ok": False,
                "message": "OpenAI: OPENAI_API_KEY is not set.",
                "detail": "Required for research, report generation, and chat summarization.",
                "setup_steps": [
                    "Get an API key from https://platform.openai.com/api-keys",
                    "Add to .env: LLM_PROVIDER=openai, OPENAI_API_KEY=sk-..., OPENAI_MODEL=gpt-4o-mini",
                ],
            }
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import HumanMessage
            model = _env("OPENAI_MODEL") or "gpt-4o-mini"
            llm = ChatOpenAI(model=model, api_key=key, temperature=0, max_tokens=10)
            llm.invoke([HumanMessage(content="Say OK")])
            return {"name": name, "ok": True, "message": f"OpenAI: OK (model={model}).", "detail": None, "setup_steps": None}
        except Exception as e:
            err = str(e).strip() or type(e).__name__
            hint = "Check OPENAI_API_KEY and OPENAI_MODEL. 401 = bad key; 429 = rate limit or quota."
            steps = None
            if "401" in err or "Incorrect API key" in err or "invalid_api_key" in err.lower():
                hint = "OPENAI_API_KEY is invalid or revoked."
                steps = ["Get a new API key from https://platform.openai.com/api-keys", "Set OPENAI_API_KEY=sk-... in .env"]
            elif "429" in err or "rate" in err.lower() or "quota" in err.lower():
                hint = "Rate limit or quota exceeded."
                steps = ["Check https://platform.openai.com/usage and billing", "Wait or upgrade your OpenAI plan"]
            return {"name": name, "ok": False, "message": f"OpenAI: {err}", "detail": hint, "setup_steps": steps}

    if provider == "anthropic":
        key = _env("ANTHROPIC_API_KEY")
        if not key:
            return {
                "name": name,
                "ok": False,
                "message": "Anthropic: ANTHROPIC_API_KEY is not set.",
                "detail": "Required for research and report when LLM_PROVIDER=anthropic.",
                "setup_steps": [
                    "Get an API key from https://console.anthropic.com/",
                    "Add to .env: LLM_PROVIDER=anthropic, ANTHROPIC_API_KEY=sk-ant-..., ANTHROPIC_MODEL=claude-3-5-sonnet-20241022",
                ],
            }
        try:
            from langchain_anthropic import ChatAnthropic
            from langchain_core.messages import HumanMessage
            model = _env("ANTHROPIC_MODEL") or "claude-3-5-sonnet-20241022"
            llm = ChatAnthropic(model=model, api_key=key, temperature=0, max_tokens=10)
            llm.invoke([HumanMessage(content="Say OK")])
            return {"name": name, "ok": True, "message": f"Anthropic: OK (model={model}).", "detail": None, "setup_steps": None}
        except Exception as e:
            err = str(e).strip() or type(e).__name__
            return {
                "name": name,
                "ok": False,
                "message": f"Anthropic: {err}",
                "detail": "Check ANTHROPIC_API_KEY and ANTHROPIC_MODEL. 401 = bad key; 429 = rate limit.",
                "setup_steps": ["Get a valid key from https://console.anthropic.com/", "Set ANTHROPIC_API_KEY in .env"],
            }

    if provider == "azure_openai":
        endpoint = _env("AZURE_OPENAI_ENDPOINT")
        key = _env("AZURE_OPENAI_API_KEY")
        if not endpoint or not key:
            return {
                "name": name,
                "ok": False,
                "message": "Azure OpenAI: AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_KEY is not set.",
                "detail": "Required for research and report when LLM_PROVIDER=azure_openai.",
                "setup_steps": [
                    "Create an Azure OpenAI resource and deploy a model (e.g. gpt-4o-mini).",
                    "Add to .env: LLM_PROVIDER=azure_openai, AZURE_OPENAI_ENDPOINT=https://..., AZURE_OPENAI_API_KEY=..., AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini",
                ],
            }
        try:
            from langchain_openai import AzureChatOpenAI
            from langchain_core.messages import HumanMessage
            deployment = _env("AZURE_OPENAI_DEPLOYMENT") or "gpt-4o-mini"
            llm = AzureChatOpenAI(azure_endpoint=endpoint, api_key=key, azure_deployment=deployment, temperature=0, max_tokens=10)
            llm.invoke([HumanMessage(content="Say OK")])
            return {"name": name, "ok": True, "message": f"Azure OpenAI: OK (deployment={deployment}).", "detail": None, "setup_steps": None}
        except Exception as e:
            err = str(e).strip() or type(e).__name__
            return {
                "name": name,
                "ok": False,
                "message": f"Azure OpenAI: {err}",
                "detail": "Check endpoint, key, and deployment name.",
                "setup_steps": ["Verify AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT in .env. See docs/Setup-and-Reference/One-Time-Setup.md."],
            }

    return {
        "name": name,
        "ok": False,
        "message": f"Unknown LLM_PROVIDER={provider}. Supported: openai, anthropic, azure_openai.",
        "detail": "Set LLM_PROVIDER in .env to one of the supported providers.",
        "setup_steps": ["Add to .env: LLM_PROVIDER=openai (or anthropic, azure_openai) and the matching API key(s). See docs/Setup-and-Reference/One-Time-Setup.md."],
    }


# ---------------------------------------------------------------------------
# LangSmith (optional)
# ---------------------------------------------------------------------------

def check_langsmith() -> dict[str, Any]:
    """If LANGCHAIN_TRACING_V2=true, verify LANGCHAIN_API_KEY is set and optionally reachable."""
    name = "LangSmith"
    tracing = _env("LANGCHAIN_TRACING_V2").lower() in ("true", "1", "yes")
    key = _env("LANGCHAIN_API_KEY")
    if not tracing:
        return {"name": name, "ok": True, "message": "LangSmith: tracing off (optional).", "detail": None, "setup_steps": None}
    if not key:
        return {
            "name": name,
            "ok": False,
            "message": "LangSmith: LANGCHAIN_TRACING_V2 is set but LANGCHAIN_API_KEY is missing.",
            "detail": "Optional. Add key or turn tracing off.",
            "setup_steps": ["Get key from https://smith.langchain.com/ → Settings → API Keys", "Add LANGCHAIN_API_KEY=lsv2_... to .env", "Or set LANGCHAIN_TRACING_V2=false to disable"],
        }
    return {"name": name, "ok": True, "message": "LangSmith: API key set (tracing enabled).", "detail": None, "setup_steps": None}


# ---------------------------------------------------------------------------
# Tavily (optional for research)
# ---------------------------------------------------------------------------

def check_tavily() -> dict[str, Any]:
    """Verify TAVILY_API_KEY and one minimal search (or key-only if you prefer no network)."""
    name = "Tavily"
    key = _env("TAVILY_API_KEY")
    if not key:
        return {
            "name": name,
            "ok": True,
            "message": "Tavily: not configured (optional for official-doc search).",
            "detail": None,
            "setup_steps": None,
        }
    try:
        import json
        import certifi
        url = "https://api.tavily.com/search"
        ctx = ssl.create_default_context()
        ctx.load_verify_locations(certifi.where())
        req = urllib.request.Request(
            url,
            data=json.dumps({"query": "test", "max_results": 1}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if not isinstance(data, dict):
            return {"name": name, "ok": False, "message": "Tavily: unexpected response format.", "detail": "Check TAVILY_API_KEY.", "setup_steps": ["Get key from https://app.tavily.com/", "Set TAVILY_API_KEY in .env"]}
        return {"name": name, "ok": True, "message": "Tavily: OK.", "detail": None, "setup_steps": None}
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        err = f"HTTP {e.code}: {body or e.reason or str(e)}"
        return {"name": name, "ok": False, "message": f"Tavily: {err}", "detail": "401 = bad key; 429 = rate limit.", "setup_steps": ["Check TAVILY_API_KEY at https://app.tavily.com/", "Set TAVILY_API_KEY in .env"]}
    except Exception as e:
        err = str(e).strip() or type(e).__name__
        return {
            "name": name,
            "ok": False,
            "message": f"Tavily: {err}",
            "detail": "Network or invalid key.",
            "setup_steps": ["Check network and TAVILY_API_KEY in .env. See docs/Setup-and-Reference/One-Time-Setup.md."],
        }


# ---------------------------------------------------------------------------
# Mermaid.ink (diagram images in reports)
# ---------------------------------------------------------------------------

def check_mermaid_ink() -> dict[str, Any]:
    """Verify we can reach mermaid.ink (used for diagram images in reports)."""
    name = "Mermaid.ink"
    url = "https://mermaid.ink/img/"
    try:
        ctx = ssl.create_default_context()
        try:
            import certifi
            ctx.load_verify_locations(certifi.where())
        except Exception:
            pass
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            if resp.status < 400:
                return {"name": name, "ok": True, "message": "Mermaid.ink: reachable.", "detail": None, "setup_steps": None}
        return {"name": name, "ok": False, "message": f"Mermaid.ink: HTTP {resp.status}.", "detail": "Diagram images in reports may not load.", "setup_steps": ["Check network/firewall. Reports will still work; diagrams may be blank. See docs/Setup-and-Reference/One-Time-Setup.md."]}
    except urllib.error.HTTPError as e:
        return {
            "name": name,
            "ok": False,
            "message": f"Mermaid.ink: HTTP {e.code} – {e.reason or str(e)}.",
            "detail": "Report diagrams use mermaid.ink; if unreachable, diagrams may be blank.",
            "setup_steps": ["Check network/firewall/proxy. Optional: app works without it; diagrams in reports may not render."],
        }
    except Exception as e:
        err = str(e).strip() or type(e).__name__
        return {
            "name": name,
            "ok": False,
            "message": f"Mermaid.ink: unreachable – {err}",
            "detail": "Diagram images in reports are served via mermaid.ink. If blocked, reports may show broken images.",
            "setup_steps": ["Check network/firewall. Optional; app works without it. See docs/Setup-and-Reference/One-Time-Setup.md."],
        }


# ---------------------------------------------------------------------------
# All checks
# ---------------------------------------------------------------------------

def run_all_checks() -> list[dict[str, Any]]:
    """Run every interface check and return a list of results (order: Pinecone, LLM, LangSmith, Tavily, Mermaid.ink)."""
    return [
        check_pinecone(),
        check_llm(),
        check_langsmith(),
        check_tavily(),
        check_mermaid_ink(),
    ]
