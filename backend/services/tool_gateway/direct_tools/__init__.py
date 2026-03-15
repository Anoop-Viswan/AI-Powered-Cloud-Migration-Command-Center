"""
Direct tool implementations (REST/SDK calls we own).

- tavily_search: web search via Tavily API; returns list of {title, url, content/snippet}.
Other tools (e.g. teams_notify, send_email) can be added here and registered in the gateway.
"""

from backend.services.tool_gateway.direct_tools import tavily_search

__all__ = ["tavily_search"]
