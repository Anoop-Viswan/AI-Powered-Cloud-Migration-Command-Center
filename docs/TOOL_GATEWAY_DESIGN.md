# Tool Gateway – Standard Framework for Integrations

**Status:** Design  
**Purpose:** A single, extensible layer for all external tools (Tavily, Teams, WhatsApp, email, etc.) so we can add integrations without rewriting agent code. Supports **MCP** (Model Context Protocol) and **UTC** (universal / native LLM tool calling).

---

## 1. Why a tool gateway?

| Without a gateway | With a tool gateway |
|------------------|----------------------|
| Each integration (Tavily, Teams, email) is a one-off in agent code. | One **Tool Gateway**; agents ask the gateway for tools by name or capability. |
| Adding WhatsApp = new API calls scattered in research/summarizer. | Register a new tool (or MCP server); agents use it via the same interface. |
| Hard to swap providers (e.g. Tavily → Serper) or add auth/rate limits in one place. | Gateway handles registration, config, and optional routing/limits. |

**Goal:** Add Tavily now; add Teams, WhatsApp, email, and others later by **registering tools** or **connecting MCP servers**, without changing the Research Agent’s core flow.

---

## 2. High-level architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Agents (Research, Summarizer, future: Notifications, etc.)             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  TOOL GATEWAY                                                            │
│  • Registry: list of tools by name/capability                            │
│  • Invoke: run a tool by name with params                                │
│  • Optional: MCP client (discover & call tools from MCP servers)         │
│  • Optional: UTC adapter (expose tools to LLM native tool-calling)       │
└─────────────────────────────────────────────────────────────────────────┘
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Direct tools │    │ MCP servers  │    │ UTC (LLM     │
│ (Tavily,     │    │ (Tavily MCP, │    │  tool-call   │
│  KB search)  │    │  Email MCP)  │    │  schema)     │
└──────────────┘    └──────────────┘    └──────────────┘
```

- **Direct tools:** Our code implements the tool (e.g. call Tavily REST API); gateway registers and invokes it.
- **MCP:** Gateway acts as MCP client; tools are provided by external MCP servers (e.g. a Tavily MCP server). We discover and call tools by name.
- **UTC (Universal Tool Calling):** Gateway exposes a list of tools in the format the LLM expects (OpenAI/Anthropic tool schema). When the model returns “call tool X with Y”, the gateway executes X and returns the result.

---

## 3. Core concepts

### 3.1 Tool descriptor (protocol-agnostic)

Every tool, whether direct or from MCP, is described in a common shape:

| Field | Description |
|-------|-------------|
| `name` | Unique id (e.g. `web_search`, `send_email`) |
| `description` | Short description for the LLM or for docs |
| `parameters` | JSON schema of inputs (e.g. `query: string`) |
| `handler` | How to run it: direct function, MCP call, or UTC adapter |

### 3.2 Tool Gateway API (proposed)

| Operation | Description |
|-----------|-------------|
| `register_tool(name, descriptor, handler)` | Add a direct tool (e.g. Tavily wrapper). |
| `register_mcp_server(server_url_or_config)` | Connect an MCP server; its tools appear in the registry. |
| `list_tools(capability?)` | Return tools (optionally filter by capability, e.g. `search`, `notify`). |
| `invoke(name, params)` | Execute a tool by name; return result. |
| `get_utc_schemas()` | Return tool definitions in the format required by the LLM’s tool-calling API (OpenAI/Anthropic). |

Agents (Research, Summarizer, future notification agents) call `list_tools` / `invoke` or use `get_utc_schemas` + LLM tool-calling; they do not call Tavily or email APIs directly.

### 3.3 MCP vs UTC – when to use which

| Use case | Preferred approach |
|----------|--------------------|
| We decide when to call (e.g. “if KB sparse → web search”) | **Direct tool** registered with the gateway; agent code calls `gateway.invoke("web_search", {...})`. |
| We want the **model** to decide when to search or notify | **UTC:** give the LLM tool schemas; model returns tool_calls; gateway executes and returns results. |
| We want to plug in many tools from the ecosystem (e.g. Cursor-style MCP servers) | **MCP:** run or connect to MCP servers; gateway discovers their tools and invokes them. |
| We have our own integrations (Tavily, Teams, email) in Python | **Direct tools** first; optionally expose the same tools via MCP server so other apps can use them. |

We can support all three: direct tools, MCP client, and UTC adapter, in one gateway.

---

## 4. Implementation outline

- **Package:** `backend/services/tool_gateway/` (or `backend/tools/`).
  - `registry.py` – Tool registry (name → descriptor + handler).
  - `direct_tools/` – Implementations (e.g. `tavily_search.py`, later `teams_notify.py`).
  - `mcp_client.py` – Optional MCP client (discover and call tools from an MCP server).
  - `utc_adapter.py` – Optional: build OpenAI/Anthropic tool schemas from registry and run `invoke` for each tool_call.
- **Research Agent** (and others) use the gateway:
  - Either: `gateway.invoke("web_search", {"query": "..."})` when we decide.
  - Or: pass `gateway.get_utc_schemas()` to the LLM and, on tool_calls, `gateway.invoke(tool_name, tool_args)`.

Tavily is the first registered tool; Teams, WhatsApp, email, etc. are added as new tools or via MCP (see user guide).

---

## 5. Docs and user guide

- **[Tool Extension Guide](./TOOL_EXTENSION_GUIDE.md)** – How to add a new tool (direct), how to add tools via MCP, and how to expose tools via UTC for LLM tool-calling.

---

## 6. Links

- [MCP – Model Context Protocol](https://modelcontextprotocol.io/) (tool/resource protocol).
- [OpenAI tool calling](https://platform.openai.com/docs/guides/function-calling), [Anthropic tool use](https://docs.anthropic.com/en/docs/build-with-claude/tool-use) – UTC-style APIs.
