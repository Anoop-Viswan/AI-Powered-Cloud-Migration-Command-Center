# Tool Extension Guide – Adding Tools via MCP or UTC

This guide explains how to extend the **Tool Gateway** with new integrations (e.g. Tavily, Teams, WhatsApp, email) using:

1. **Direct registration** – Implement the tool in Python and register it with the gateway.
2. **MCP (Model Context Protocol)** – Connect an MCP server that exposes tools; the gateway discovers and invokes them.
3. **UTC (Universal Tool Calling)** – Expose tools to the LLM so the **model** can decide when to call them (OpenAI/Anthropic tool-calling).

The Tool Gateway design is described in [TOOL_GATEWAY_DESIGN.md](./TOOL_GATEWAY_DESIGN.md).

---

## Prerequisites

- You have (or will have) a **Tool Gateway** service: a registry of tools and a single `invoke(name, params)` (and optional `list_tools`, `get_utc_schemas`).
- For MCP: an MCP server that implements the [Model Context Protocol](https://modelcontextprotocol.io/) (e.g. a Tavily MCP server, or your own).
- For UTC: an LLM that supports tool/function calling (e.g. OpenAI `gpt-4`, Anthropic Claude with tool use).

---

## Part A: Adding a direct tool (e.g. Tavily)

Use this when the integration is a REST or SDK call you implement in Python.

### Step 1: Implement the tool logic

Create a small module that performs the integration (e.g. call Tavily API) and returns a result in a consistent shape (e.g. string or list of snippets).

**Example (Tavily web search):**

```python
# backend/services/tool_gateway/direct_tools/tavily_search.py
import os

def tavily_search(query: str, max_results: int = 5) -> str:
    """Call Tavily API; return concatenated snippets as plain text."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "(Tavily not configured: set TAVILY_API_KEY)"
    # ... HTTP call to Tavily, parse response ...
    return "\n\n".join(snippets)
```

### Step 2: Define the tool descriptor

Describe name, description, and parameters (for docs and for UTC schema).

```python
# Same file or registry
TOOL_DESCRIPTOR = {
    "name": "web_search",
    "description": "Search the web for current information. Use when the knowledge base has no or few relevant results.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "description": "Max results to return", "default": 5},
        },
        "required": ["query"],
    },
}
```

### Step 3: Register with the gateway

On app startup (or when the gateway is built), register the tool:

```python
from backend.services.tool_gateway import get_gateway
from backend.services.tool_gateway.direct_tools.tavily_search import tavily_search, TOOL_DESCRIPTOR

gateway = get_gateway()
gateway.register_tool(
    name=TOOL_DESCRIPTOR["name"],
    descriptor=TOOL_DESCRIPTOR,
    handler=lambda **kwargs: tavily_search(**kwargs),
)
```

### Step 4: Use the tool from an agent

In the Research Agent (or any agent):

```python
from backend.services.tool_gateway import get_gateway

gateway = get_gateway()
if len(kb_chunks) < 3:  # KB sparse
    web_result = gateway.invoke("web_search", {"query": query, "max_results": 5})
    context = kb_context + "\n\n--- Web search ---\n\n" + web_result
```

No MCP or UTC required; the agent just calls the gateway.

---

## Part B: Adding tools via MCP

Use this when the tool is provided by an **MCP server** (e.g. a community Tavily MCP server, or your own server that exposes Teams/WhatsApp/email).

### Step 1: Run or connect to an MCP server

- **Option A:** Use an existing MCP server (e.g. `tavily-mcp-server` if available, or a generic “web search” MCP server).
- **Option B:** Implement your own MCP server that exposes tools (see [MCP spec](https://modelcontextprotocol.io/specification)).

The server typically runs as a process or over stdio/HTTP; the gateway will act as an **MCP client**.

### Step 2: Configure the gateway to use the MCP client

In config or `.env`:

```env
# Example: MCP server for web search
MCP_TAVILY_SERVER_URL=stdio
MCP_TAVILY_COMMAND=path/to/tavily-mcp-server
```

Or for HTTP:

```env
MCP_TAVILY_SERVER_URL=http://localhost:8080
```

### Step 3: Register the MCP server with the gateway

The gateway’s MCP client connects to the server, lists its tools, and registers them so they can be invoked by name.

```python
# Pseudocode – depends on your MCP client library
gateway.register_mcp_server(
    id="tavily",
    transport="stdio",  # or "http"
    config={"command": os.getenv("MCP_TAVILY_COMMAND")},
)
# Gateway discovers tools from the server and adds them to the registry
```

### Step 4: Invoke MCP tools like any other tool

Agents do not need to know the tool is from MCP:

```python
result = gateway.invoke("web_search", {"query": "Azure migration best practices 2024"})
```

The gateway routes `web_search` to the MCP server and returns the result.

### Summary: extending with MCP

| Step | Action |
|------|--------|
| 1 | Run or implement an MCP server that exposes your tool (e.g. Tavily, Teams, email). |
| 2 | Configure connection (URL, command, or transport) in env or config. |
| 3 | Call `gateway.register_mcp_server(...)` so the gateway discovers and registers the server’s tools. |
| 4 | Use `gateway.invoke(tool_name, params)` from agents; no change to agent logic. |

---

## Part C: Exposing tools via UTC (LLM decides when to call)

Use this when you want the **LLM** to decide when to search the web, send an email, or call another tool (e.g. “I need to search for that” or “I should notify the user via Teams”).

### Step 1: Tools must be registered

All tools you want the model to use (direct or MCP) must already be registered with the gateway (Part A or B).

### Step 2: Build UTC schemas from the registry

The gateway exposes a method that returns tool definitions in the format your LLM expects (OpenAI or Anthropic).

```python
# Gateway builds schemas from registered tools
schemas = gateway.get_utc_schemas(provider="openai")  # or "anthropic"
# Returns e.g. [{"type": "function", "function": {"name": "web_search", "description": "...", "parameters": {...}}}]
```

### Step 3: Pass tools to the LLM and handle tool_calls

When calling the LLM, pass the tool definitions and turn on tool/function calling. When the response contains `tool_calls`, run each tool via the gateway and append the results for the next LLM turn.

```python
# Pseudocode
messages = [SystemMessage(...), HumanMessage(content=user_input)]
llm_with_tools = llm.bind_tools(schemas)  # LangChain style
response = llm_with_tools.invoke(messages)

while response.tool_calls:
    for tc in response.tool_calls:
        result = gateway.invoke(tc["name"], tc["args"])
        messages.append(/* tool result message */)
    response = llm_with_tools.invoke(messages)
```

### Step 4: Add a new tool for the model to use

- **Direct:** Implement and register the tool (Part A). It will appear in `get_utc_schemas()` and the model can request it.
- **MCP:** Register the MCP server (Part B). Its tools appear in the registry and in UTC schemas.

No change to the “invoke loop” above; only the registry changes.

### Summary: extending with UTC

| Step | Action |
|------|--------|
| 1 | Register all tools (direct or MCP) with the gateway. |
| 2 | Use `gateway.get_utc_schemas(provider="openai"|"anthropic")` and pass to the LLM. |
| 3 | On `tool_calls`, call `gateway.invoke(name, args)` for each and continue the conversation. |
| 4 | To add a new tool the model can use: add the tool (Part A or B); it automatically appears in UTC. |

---

## Quick reference: which path to use?

| I want to… | Use |
|------------|-----|
| Add Tavily (or another API) and call it from our code when we decide | Part A – Direct tool |
| Use a third-party or in-house MCP server for search/Teams/email | Part B – MCP |
| Let the LLM decide when to search or notify | Part C – UTC (after registering tools with A or B) |
| Add many tools over time without touching agent logic | Gateway + registry; add tools via A or B; optionally expose via UTC (C). |

---

## Future integrations (Teams, WhatsApp, email)

- **Direct:** Implement `teams_notify`, `whatsapp_send`, `send_email` in `direct_tools/`, register with the gateway. Agents or the LLM (via UTC) call them by name.
- **MCP:** Run or connect to MCP servers that expose Teams/WhatsApp/email tools; register those servers with the gateway. Same `invoke(name, params)` from agents or from the UTC loop.

The gateway stays the single place where tools are registered and invoked; only new tools or new MCP servers are added.
