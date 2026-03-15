"""
Tool Gateway – single entry point for all external tools (web search, notifications, etc.).

Agents (e.g. Research Agent) call get_gateway().invoke("web_search", {"query": "..."})
instead of calling Tavily or other APIs directly. This keeps the agent simple and
makes it easy to add or swap tools (Tavily, MCP servers, UTC) without changing agent code.

See docs/TOOL_GATEWAY_DESIGN.md and docs/TOOL_EXTENSION_GUIDE.md.
"""

from backend.services.tool_gateway.registry import get_gateway

__all__ = ["get_gateway"]
