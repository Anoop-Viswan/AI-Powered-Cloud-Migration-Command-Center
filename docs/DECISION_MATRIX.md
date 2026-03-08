# Decision Matrix – Framework & Tool Selection

**Purpose:** Document key architectural decisions, candidates considered, final choices, and rationale. End-to-end for the Cloud Migration Command Center.

---

## Summary table (with rationale)

| Decision | Candidates | Final choice | Rationale |
|----------|------------|--------------|-----------|
| **Migration request flow** | Single user (profile → research → report), two roles (App User submit / Admin research & report) | **Two roles** | Normal user workflow: Application Users only initiate requests and provide app data; Admins run research, check KB, add manual input, generate and edit reports, download. Separates intake from CoE execution; avoids exposing research/report to all users. See [Migration Request Flow](./MIGRATION_REQUEST_FLOW.md). |
| **Multi-agent orchestration** | LangGraph, LangChain LCEL, custom Python, AutoGen, CrewAI | **LangGraph** | Our flow has conditional logic (Research fail → end; else → Summarize). LangGraph’s graph model and conditional edges fit this. LangChain LCEL is linear-only. Custom Python would require reinventing state and tracing. AutoGen/CrewAI target conversational agents, not our sequential pipeline. LangGraph also gives native LangSmith traces and is used in production by LinkedIn, Uber, Klarna. |
| **Observability** | LangSmith, custom logging, OpenTelemetry, Datadog | **LangSmith** | We use LangChain/LangGraph; LangSmith is built for this stack. Zero config: set env vars and traces appear. Custom logging would need manual instrumentation. OpenTelemetry is vendor-neutral but LangChain support is experimental. Datadog is general APM, not LLM-specific. LangSmith shows trace trees, token costs, latency per step—exactly what Admin Diagnostics needs. |
| **Vector DB / KB** | Pinecone, Weaviate, Milvus, Chroma, Qdrant | **Pinecone** | Project is `pinecone-semantic-search`; Pinecone is already integrated. Switching would mean new index, embeddings, and usage tracking. Weaviate/Milvus/Qdrant need self-host or cloud setup. Chroma is lightweight but less scalable. No business reason to change; Pinecone fits our scale and existing code. |
| **LLM provider** | OpenAI, Anthropic Claude, Azure OpenAI, Vertex | **OpenAI (GPT-4o-mini)** | Chat/summarization already use OpenAI. Adding another provider increases config and testing. GPT-4o-mini balances quality and cost for synthesis. Anthropic has strong reasoning but different API. Azure/Vertex add enterprise setup. Staying with OpenAI minimizes integration work and uses proven LangChain support. |
| **Web search** | Tavily, Serper, Exa, Bing | **Tavily** | We need clean snippets for LLM context, not raw HTML. Tavily is built for RAG/LLM use. Serper returns Google results but less curated. Exa is semantic search over web—different paradigm. Bing needs more setup. Tavily’s API is simple; we call it only when KB is sparse, so cost is bounded. |
| **State persistence** | SQLite, PostgreSQL, JSON files, in-memory | **SQLite** | MVP needs persistence without new infra. SQLite is a single file, no server. Postgres is overkill for current load. JSON files have concurrency issues. In-memory loses data on restart. SQLite gives us a pluggable store; we can migrate to Postgres when we scale. |
| **Async pattern** | Polling, SSE, WebSockets, Celery | **Polling** | Research/Summarize take 10–60s. Polling is simplest: client calls GET every 2–3s. SSE needs streaming endpoints. WebSockets are overkill. Celery needs Redis and workers. We chose minimal complexity for Phase 1; SSE can be added later for better UX. |
| **Report format** | Markdown, DOCX, PDF, HTML | **Markdown + DOCX** | LLMs output Markdown naturally. We preview MD in the UI. For download, we convert to DOCX via python-docx (already in use). PDF is harder to generate. HTML is less portable. MD + DOCX gives quick preview and a standard business deliverable. |
| **API pattern** | Step-by-step, run all | **Step-by-step** | Users need to see progress (Profile → Research → Report). Step-by-step endpoints let them advance one step at a time and retry individual steps. A single “run all” call would be a black box. LangGraph can still run the full flow internally; the API stays step-by-step for clarity and debuggability. |
| **Profile UI** | Single form, wizard, tabs | **Wizard + 7 pillar tabs** | Seven pillars would make a single form overwhelming. Tabs group by domain. A wizard (Profile → Research → Report) guides the flow. “Continue to [next section]” enforces filling all pillars before Research. This matches real migration intake forms. |
| **LLM provider flexibility** | Single provider, abstraction | **Provider abstraction** | `get_llm()` factory supports OpenAI, Anthropic, Azure. Switch via `LLM_PROVIDER` env var. No code changes. Supports enterprise (Azure data residency) and model choice (Anthropic). |

---

## Decision tree

```
Need orchestrator for multi-agents? → LangGraph (graph, conditional edges, LangSmith)
Need observability?                  → LangSmith (zero-config, trace trees)
Need vector KB?                      → Pinecone (project foundation)
Need LLM?                            → OpenAI (existing, LangChain support)
Need web search when KB sparse?      → Tavily (LLM-oriented snippets)
Need state persistence?              → SQLite (no infra, pluggable)
Need async for long ops?             → Polling (simplest; SSE later)
Need report output?                  → Markdown + DOCX (preview + download)
```

---

## 1. Multi-agent orchestration

| Aspect | Details |
|--------|---------|
| **Need** | Coordinate Data Collector, Research, Summarizer with conditional logic (e.g. if Research fails, stop; else continue to Summarize) and shared state |
| **Candidates** | LangGraph, LangChain LCEL, custom Python, AutoGen, CrewAI |

| Candidate | Pros | Cons |
|-----------|------|------|
| **LangGraph** | Graph-based; conditional edges; typed state; checkpointing; LangSmith | Newer; learning curve |
| **LangChain LCEL** | Simple; good for linear flows | No branching; no graph viz |
| **Custom Python** | Full control | Reinvent orchestration; no tracing |
| **AutoGen** | Multi-agent conversations | Heavier; different paradigm |
| **CrewAI** | Role-based agents | Less flexible for our flow |

**Analysis:** Our flow is Profile → Research → Summarize with a branch: if Research fails, we end; otherwise we continue. LangChain LCEL is linear. Custom Python would require manual state handling and no built-in tracing. AutoGen and CrewAI focus on conversational multi-agent setups, not our sequential pipeline. LangGraph’s `StateGraph` and conditional edges map directly to our flow. Agents stay as pure functions; the graph is a thin orchestration layer.

**Decision:** **LangGraph**

**Rationale:** Explicit graph model matches our flow. Conditional edges handle errors. Typed shared state (`AssessmentGraphState`). Native LangSmith. Industry adoption (LinkedIn, Uber, Klarna). Can run step-by-step (API) or full graph.

---

## 2. Observability & tracing

| Aspect | Details |
|--------|---------|
| **Need** | Trace agent calls, LLM invocations, token usage, latency, errors for debugging and Admin Diagnostics |
| **Candidates** | LangSmith, custom logging, OpenTelemetry, Datadog |

| Candidate | Pros | Cons |
|-----------|------|------|
| **LangSmith** | Native with LangChain/LangGraph; trace trees; token costs; free tier | Vendor lock-in |
| **Custom logging** | Full control | No structured traces; manual work |
| **OpenTelemetry** | Vendor-neutral | More setup; experimental LangChain support |
| **Datadog** | General APM | Not LLM-specific |

**Analysis:** We use LangChain/LangGraph. LangSmith is built for this stack. Custom logging would need manual instrumentation for each agent and LLM call. OpenTelemetry is vendor-neutral but LangChain integration is experimental. Datadog is general-purpose, not tuned for LLM flows. LangSmith gives trace trees, token usage, and cost per run with minimal setup.

**Decision:** **LangSmith**

**Rationale:** Zero-config with `LANGCHAIN_TRACING_V2=true`. Trace trees show each node, tool, LLM call. Token usage and cost. Fallback: if not configured, tracing disabled. Aligns with Admin Diagnostics (LLM invocations, tokens, latency).

---

## 3. Vector database / Knowledge Base

| Aspect | Details |
|--------|---------|
| **Need** | Semantic search over migration docs for Research Agent |
| **Candidates** | Pinecone, Weaviate, Milvus, Chroma, Qdrant |

| Candidate | Pros | Cons |
|-----------|------|------|
| **Pinecone** | Managed; project already uses it | Vendor; cost at scale |
| **Weaviate** | Open source; hybrid search | Self-host or cloud |
| **Milvus** | Scalable; open source | Heavier; more ops |
| **Chroma** | Lightweight; local | Less scalable |
| **Qdrant** | Good performance | Self-host or cloud |

**Analysis:** Project is `pinecone-semantic-search`. Pinecone is already integrated with `semantic_search.py`, namespaces, and usage tracking. Switching would require a new index, embedding pipeline, and spend guardrails. Weaviate, Milvus, Qdrant need self-host or cloud setup. Chroma is lighter but less scalable. No strong reason to change.

**Decision:** **Pinecone**

**Rationale:** Project foundation. Existing `search_knowledge_base()`, namespace per project. No new infra. Usage tracker and spend guardrails in place.

---

## 4. LLM provider

| Aspect | Details |
|--------|---------|
| **Need** | LLM for Research synthesis and Summarizer report generation |
| **Candidates** | OpenAI, Anthropic Claude, Azure OpenAI, Google Vertex |

| Candidate | Pros | Cons |
|-----------|------|------|
| **OpenAI (GPT-4o-mini)** | Already used; LangChain support; cost-effective | API dependency |
| **Anthropic Claude** | Strong reasoning; long context | Different API |
| **Azure OpenAI** | Enterprise; data residency | More setup |
| **Vertex** | GCP integration | Different ecosystem |

**Analysis:** Chat and summarization already use OpenAI. Adding another provider means extra config, env vars, and testing. GPT-4o-mini is sufficient for synthesis and report generation at lower cost. Anthropic has strong reasoning but would require a separate integration. Azure/Vertex add enterprise setup. Consistency and simplicity favor staying with OpenAI.

**Decision:** **OpenAI (GPT-4o-mini)**

**Rationale:** Already used in `backend/services/llm.py`. `langchain-openai` with LangSmith. Configurable via `OPENAI_MODEL`, `OPENAI_TEMPERATURE`, `OPENAI_MAX_TOKENS`.

---

## 5. Web search (when KB sparse)

| Aspect | Details |
|--------|---------|
| **Need** | Fetch migration best practices when KB has little relevant content |
| **Candidates** | Tavily, Serper, Exa, Bing |

| Candidate | Pros | Cons |
|-----------|------|------|
| **Tavily** | LLM-oriented; curated snippets; simple API | API limits; cost |
| **Serper** | Google results; cheap | Less research-oriented |
| **Exa** | Semantic search over web | Different use case |
| **Bing** | Enterprise option | More setup |

**Analysis:** We need clean text snippets for LLM context, not raw HTML. Tavily is built for RAG and LLM-augmented search. Serper returns Google results but less curated. Exa is semantic search over the web—different paradigm. We use a KB-first strategy; Tavily is only called when KB is sparse, so cost is bounded.

**Decision:** **Tavily**

**Rationale:** Designed for LLM use. Simple REST API. KB-first; Tavily as fallback. Can swap if limits or cost become an issue.

---

## 6. State persistence

| Aspect | Details |
|--------|---------|
| **Need** | Persist assessment state (profile, approach, report, status) across requests |
| **Candidates** | SQLite, PostgreSQL, JSON files, in-memory |

| Candidate | Pros | Cons |
|-----------|------|------|
| **SQLite** | Single file; no server; persistent | Single-writer |
| **PostgreSQL** | Scalable; robust | Overkill for MVP |
| **JSON files** | Simple | Concurrency; no querying |
| **In-memory** | Simplest | Lost on restart |

**Analysis:** MVP needs persistence without new infrastructure. SQLite is built-in, single file, no server. Postgres is overkill for current load. JSON files have concurrency and query limitations. In-memory loses data on restart. SQLite allows a pluggable store interface; we can migrate to Postgres when scaling.

**Decision:** **SQLite**

**Rationale:** No extra infra. `data/assessments.db`. Pluggable store. Easy migration to Postgres later.

---

## 7. Async pattern (long-running Research/Summarize)

| Aspect | Details |
|--------|---------|
| **Need** | Research 10–60s, Summarize 5–30s; cannot block HTTP |
| **Candidates** | Polling, SSE, WebSockets, Celery |

| Candidate | Pros | Cons |
|-----------|------|------|
| **Polling** | Simplest; works everywhere | More requests |
| **SSE** | Real-time updates | More frontend logic |
| **WebSockets** | Bidirectional | Overkill |
| **Celery/RQ** | Robust job queue | Extra infra (Redis) |

**Analysis:** Research and Summarize are long-running. Polling is the simplest: client calls `GET /assessment/{id}` every 2–3s. SSE needs streaming endpoints. WebSockets are overkill for status updates. Celery needs Redis and workers. For Phase 1, we minimize complexity; SSE can be added later for better UX.

**Decision:** **Polling**

**Rationale:** Client polls until `status: completed` or `error`. No streaming infra. Add SSE later for progress messages.

---

## 8. Report output format

| Aspect | Details |
|--------|---------|
| **Need** | Report preview in UI + downloadable file |
| **Candidates** | Markdown, DOCX, PDF, HTML |

| Candidate | Pros | Cons |
|-----------|------|------|
| **Markdown** | Easy for LLM; renders in UI | Not standard for business |
| **DOCX** | Standard; editable | Needs python-docx |
| **PDF** | Universal | Harder to generate |
| **HTML** | Renders well | Less portable |

**Analysis:** LLMs output Markdown naturally. We need both in-UI preview and a downloadable file. Markdown alone is not ideal for business handoff. DOCX is standard. python-docx is already in requirements. PDF is harder to generate. HTML is less portable. Markdown for preview and DOCX for download covers both needs.

**Decision:** **Markdown + DOCX**

**Rationale:** LLM outputs MD. Preview in UI. Convert to DOCX for download. python-docx already available.

---

## 9. API pattern (step-by-step vs run all)

| Aspect | Details |
|--------|---------|
| **Need** | Expose assessment flow to frontend |
| **Candidates** | Step-by-step endpoints, single "run all" endpoint |

| Candidate | Pros | Cons |
|-----------|------|------|
| **Step-by-step** | User sees progress; easier debug; retry per step | More API calls |
| **Run all** | Single call | Black box; harder debug |

**Analysis:** Users move through Profile → Research → Report. Step-by-step lets them see progress and retry individual steps (e.g. re-summarize only). A single "run all" call would hide intermediate state. LangGraph can still run the full flow internally; the API stays step-by-step for clarity.

**Decision:** **Step-by-step**

**Rationale:** `POST /start` → `PUT /profile` → `POST /research` → `POST /summarize`. User advances explicitly. Easier retry and partial re-run.

---

## 10. Frontend assessment flow

| Aspect | Details |
|--------|---------|
| **Need** | Guided UI for profile → research → report |
| **Candidates** | Single form, wizard, separate routes |

| Candidate | Pros | Cons |
|-----------|------|------|
| **Wizard + tabs** | Clear progress; pillars grouped | State management |
| **Separate routes** | Deep links | More routing |
| **Single long form** | Simple | Overwhelming for 7 pillars |

**Analysis:** Seven pillars would make a single form too long. Tabs group by domain (Overview, Architecture, Data, etc.). A wizard (Profile → Research → Report) guides the flow. "Continue to [next section]" ensures all pillars are visited before Research. This aligns with real migration intake forms.

**Decision:** **Wizard + 7 pillar tabs**

**Rationale:** Route `/assessment`. Steps: 1. Profile (7 tabs), 2. Research, 3. Report. Navigation: section-to-section; "Save & continue to research" only on final section. See [ASSESSMENT_PROFILE_DESIGN.md](./ASSESSMENT_PROFILE_DESIGN.md), [WIREFRAMES.html](./WIREFRAMES.html).

---

## 11. LLM provider flexibility

| Aspect | Details |
|--------|---------|
| **Need** | Ability to switch LLM providers (OpenAI, Anthropic, Azure) without code changes |
| **Approach** | Provider abstraction via `get_llm()` factory in `backend/services/llm_provider.py` |

**Implementation:** All LLM calls (Chat, Research Agent, Summarizer Agent) use `get_llm()`. Provider selected via `LLM_PROVIDER=openai|anthropic|azure_openai`. Each provider uses its LangChain integration (ChatOpenAI, ChatAnthropic, AzureChatOpenAI). Adding a new provider = add branch in `get_llm()` + document env vars.

**Rationale:** Single abstraction point. No code changes to switch; only env vars. Supports enterprise requirements (Azure for data residency, Anthropic for alternative models). See [ARCHITECTURE_DESIGN.md](./ARCHITECTURE_DESIGN.md) §3.

---

*Document version: 1.2 | Part of Assessment Module Design*
