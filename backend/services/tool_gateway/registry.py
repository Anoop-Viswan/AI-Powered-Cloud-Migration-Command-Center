"""
Tool Gateway registry: register tools by name and invoke them with parameters.

- register_tool(name, descriptor, handler): add a direct tool (e.g. Tavily wrapper).
- invoke(name, params): run a tool by name; returns the handler's return value.
- list_tools(): return registered tool names (for debugging or future UTC schema export).

Handlers are plain functions that accept keyword arguments matching the tool's parameters.
We do not validate params against the descriptor here; the handler can validate or ignore.
"""

from typing import Any, Callable

# Type for a tool descriptor (name, description, parameters schema). We keep it loose for simplicity.
ToolDescriptor = dict[str, Any]
# Handler: async or sync function that takes **kwargs and returns result (often str or list of dicts).
ToolHandler = Callable[..., Any]

_registry: dict[str, tuple[ToolDescriptor, ToolHandler]] = {}
_gateway_instance: "ToolGateway | None" = None


class ToolGateway:
    """
    In-process registry of tools. Agents use this to invoke tools by name
    without knowing whether the tool is implemented directly or via MCP.
    """

    def register_tool(
        self,
        name: str,
        descriptor: ToolDescriptor,
        handler: ToolHandler,
    ) -> None:
        """
        Register a direct tool. name must be unique.
        descriptor: at least "name", "description"; "parameters" optional (for docs/UTC).
        handler: callable that accepts **kwargs; will be called as handler(**params).
        """
        if name in _registry:
            # Allow re-register (e.g. tests or reload); last wins
            pass
        _registry[name] = (descriptor, handler)

    def invoke(self, name: str, params: dict[str, Any]) -> Any:
        """
        Run the tool by name with the given params. Returns whatever the handler returns.
        Raises KeyError if the tool is not registered.
        """
        if name not in _registry:
            raise KeyError(f"Tool not registered: {name}")
        _, handler = _registry[name]
        return handler(**params)

    def list_tools(self) -> list[str]:
        """Return the list of registered tool names."""
        return list(_registry.keys())

    def get_descriptor(self, name: str) -> ToolDescriptor | None:
        """Return the descriptor for a tool, or None if not registered."""
        if name not in _registry:
            return None
        desc, _ = _registry[name]
        return desc


def get_gateway() -> ToolGateway:
    """Return the singleton Tool Gateway and ensure default tools (e.g. web_search) are registered."""
    global _gateway_instance
    if _gateway_instance is None:
        _gateway_instance = ToolGateway()
        # Register built-in direct tools so Research Agent can use them without extra setup
        _register_default_tools(_gateway_instance)
    return _gateway_instance


def _register_default_tools(gateway: ToolGateway) -> None:
    """
    Register default tools (Tavily web search when TAVILY_API_KEY is set).
    Called once when the gateway is first used.
    """
    from backend.services.tool_gateway.direct_tools import tavily_search

    gateway.register_tool(
        name=tavily_search.TOOL_NAME,
        descriptor=tavily_search.TOOL_DESCRIPTOR,
        handler=tavily_search.tavily_search,
    )
