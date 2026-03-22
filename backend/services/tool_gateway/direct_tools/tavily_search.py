"""
Tavily web search – direct tool implementation for the Tool Gateway.

Calls the Tavily Search API (POST https://api.tavily.com/search) and returns
a list of results: each with title, url, content (snippet). Used by the Research Agent
when KB confidence is below threshold to fetch official-documentation results.

Requires TAVILY_API_KEY in the environment. If not set, returns an empty list.
On API or network errors, raises TavilySearchError with the exact reason (status, body).

Uses certifi's CA bundle for SSL so HTTPS works on macOS and other environments
where the default system certificates are not available to Python.
"""

import json
import logging
import os
import ssl
import time
import urllib.error
import urllib.request
from typing import Any

import certifi

logger = logging.getLogger(__name__)


class TavilySearchError(Exception):
    """Raised when Tavily API or network request fails; message includes status and reason."""
    pass

# Tool name used in gateway.invoke("web_search", {...})
TOOL_NAME = "web_search"

# Descriptor for docs and for future UTC tool schema
TOOL_DESCRIPTOR = {
    "name": TOOL_NAME,
    "description": "Search the web for current information. Use when the knowledge base has no or few relevant results, or for official documentation (e.g. Microsoft Learn, Snowflake docs).",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "description": "Max results to return (1–20)", "default": 5},
            "search_depth": {"type": "string", "description": "basic | advanced | fast | ultra-fast", "default": "basic"},
            "include_domains": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of domains to restrict results (e.g. learn.microsoft.com)",
            },
        },
        "required": ["query"],
    },
}

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


def _ssl_context() -> ssl.SSLContext:
    """SSL context using certifi's CA bundle so HTTPS works when system certs are missing (e.g. macOS)."""
    ctx = ssl.create_default_context()
    ctx.load_verify_locations(certifi.where())
    return ctx


def tavily_search(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
    include_domains: list[str] | None = None,
    **kwargs: Any,
) -> list[dict[str, str]]:
    """
    Call Tavily Search API and return a list of result dicts: title, url, content (snippet).

    - query: required search string.
    - max_results: 1–20 (default 5).
    - search_depth: "basic" (default), "advanced", "fast", or "ultra-fast".
    - include_domains: optional list of domains to restrict to (e.g. ["learn.microsoft.com"]).
    - **kwargs: ignored (allows gateway to pass extra params without breaking).

    Returns list of {"title": str, "url": str, "content": str}. Empty list if API key
    is missing or the request fails (caller can log and continue with KB-only output).
    """
    api_key = (os.getenv("TAVILY_API_KEY") or "").strip()
    if not api_key:
        return []

    body: dict[str, Any] = {
        "query": query,
        "max_results": min(20, max(1, max_results)),
        "search_depth": search_depth if search_depth in ("basic", "advanced", "fast", "ultra-fast") else "basic",
    }
    if include_domains:
        body["include_domains"] = include_domains[:50]  # API limit

    t0 = time.perf_counter()
    req = urllib.request.Request(
        TAVILY_SEARCH_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30, context=_ssl_context()) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        try:
            from backend.services.diagnostics.recorder import record_tool_call
            record_tool_call(
                "tavily_search",
                latency_ms=int((time.perf_counter() - t0) * 1000),
                status="ok",
                metadata={"result_count": len(data.get("results") or [])},
            )
        except Exception:
            pass
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        try:
            parsed = json.loads(body) if body else {}
            msg = parsed.get("detail") or parsed.get("message") or body or e.reason or str(e)
        except Exception:
            msg = body or e.reason or str(e)
        err_msg = f"Tavily API error ({e.code}): {msg}"
        logger.warning("Tavily search failed: %s", err_msg)
        try:
            from backend.services.diagnostics.recorder import record_tool_call
            record_tool_call("tavily_search", int((time.perf_counter() - t0) * 1000), "error", error_message=err_msg)
        except Exception:
            pass
        raise TavilySearchError(err_msg) from e
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        err_msg = f"Tavily request failed (network or parse): {type(e).__name__}: {e}"
        logger.warning("Tavily search failed: %s", err_msg)
        try:
            from backend.services.diagnostics.recorder import record_tool_call
            record_tool_call("tavily_search", int((time.perf_counter() - t0) * 1000), "error", error_message=err_msg)
        except Exception:
            pass
        raise TavilySearchError(err_msg) from e

    results = data.get("results") or []
    out: list[dict[str, str]] = []
    for r in results:
        if not isinstance(r, dict):
            continue
        title = (r.get("title") or "").strip()
        url = (r.get("url") or "").strip()
        content = (r.get("content") or "").strip()
        out.append({"title": title, "url": url, "content": content})
    return out
