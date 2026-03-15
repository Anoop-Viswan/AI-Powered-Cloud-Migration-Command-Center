# LLM summarization dataflow

How the app turns a user question into an LLM-summarized answer using the Knowledge Base (RAG).

## Flow overview

```
Frontend (Chat)  →  POST /api/chat  →  backend/routers/chat.py
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
         backend/config.py          semantic_search.py         backend/services/llm.py
         get_project_dir()          search_knowledge_base()    summarize_with_llm()
                    │                         │                         │
                    │                         │                         │
                    └─────────────────────────┼─────────────────────────┘
                                              │
                                    Pinecone index (vectors)
                                    LLM Provider (OpenAI / Anthropic / Azure)
```

## Step-by-step

1. **Entry:** User submits a question in the Chat UI → `POST /api/chat` with `{ query, category?, application?, top_k?, system_prompt?, temperature?, max_tokens? }`.

2. **Router:** `backend/routers/chat.py`
   - `chat()` receives the body and calls:
     - `_search_kb(body.query, ...)` → returns list of text chunks (strings).
     - `summarize_with_llm(body.query, chunks)` → returns a single answer string.
   - Response: `{ query, answer, sources_used }`.

3. **Search:** `_search_kb()` in `chat.py`:
   - Uses `backend.config.get_project_dir()` for `PINECONE_PROJECT_DIR`.
   - Imports from **`semantic_search`** (project root):
     - `get_client()`, `namespace_for_project()`, `search_knowledge_base()`, `INDEX_NAME`.
   - Calls `search_knowledge_base(index, namespace, query, category_filter=..., application_filter=..., top_k=...)`.
   - Extracts text from hits: `h.fields.get("content", "")` for each hit → list of `chunks`.

4. **Vector search:** `semantic_search.py`
   - **Function:** `search_knowledge_base(index, namespace, query, category_filter=None, application_filter=None, top_k=5)` (around line 243).
   - Builds query with `inputs={"text": query}`, optional metadata filters, optional rerank (`bge-reranker-v2-m3`).
   - Returns Pinecone search result; chat router takes `.result.hits` and reads `content` from each hit.

5. **LLM summarization:** `backend/services/llm.py`
   - **Function:** `summarize_with_llm(query: str, context_chunks: list[str]) -> str`.
   - Uses **LLM provider abstraction** (`backend/services/llm_provider.py`): `get_llm()` returns the configured provider (OpenAI, Anthropic, or Azure) based on `LLM_PROVIDER` env var.
   - If no provider is configured → returns a short “LLM not configured” message.
   - Otherwise:
     - Joins up to 10 chunks with `"\n\n---\n\n"` into `context`.
     - Builds LangChain messages (SystemMessage, HumanMessage) and calls `llm.invoke(messages)`.
     - **Provider:** `LLM_PROVIDER` (default `openai`). See [ARCHITECTURE_DESIGN.md](./ARCHITECTURE_DESIGN.md) §3 for switching.
     - **OpenAI defaults:** `OPENAI_MODEL` (gpt-4o-mini), `OPENAI_TEMPERATURE` (0.3), `OPENAI_MAX_TOKENS` (4096).
     - Returns `response.content` or an error string.

## Files and functions summary

| Role | File | Function / constant |
|------|------|---------------------|
| HTTP entry | `backend/routers/chat.py` | `chat()`, `_search_kb()` |
| Config | `backend/config.py` | `get_project_dir()` |
| Vector search | `semantic_search.py` | `search_knowledge_base()` |
| LLM | `backend/services/llm.py` | `summarize_with_llm()`, `DEFAULT_SYSTEM_PROMPT` |
| LLM provider | `backend/services/llm_provider.py` | `get_llm()` – returns OpenAI, Anthropic, or Azure based on `LLM_PROVIDER` |
| App wiring | `backend/main.py` | includes `chat.router` under `/api` |

## Customizing prompts and model settings

- **LLM provider:** Set `LLM_PROVIDER=openai|anthropic|azure_openai` in `.env`. Default: `openai`.
- **System prompt:** Set `OPENAI_SYSTEM_PROMPT` in `.env` to override the default. Optional per-request override via `system_prompt` in the chat request body.
- **Temperature:** Set `OPENAI_TEMPERATURE` in `.env` (e.g. `0.7`). Optional per-request override via `temperature` in the chat request body.
- **Max tokens:** Set `OPENAI_MAX_TOKENS` in `.env` (default `4096`). Optional per-request override via `max_tokens`.
- **Model:** Set `OPENAI_MODEL` in `.env` (default `gpt-4o-mini`). For Anthropic: `ANTHROPIC_MODEL`. For Azure: `AZURE_OPENAI_DEPLOYMENT`.

See `.env.example`, [ARCHITECTURE_DESIGN.md](./ARCHITECTURE_DESIGN.md) §3 (LLM flexibility), and the [README](../README.md) for run instructions.
