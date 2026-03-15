# Assessment Module – Design & Architecture

**Status:** Design phase (pre-implementation)  
**Goal:** Multi-agent system for application migration assessments with **two roles**: Application Users submit app data; Admins run research and generate/edit reports.

**Two-role flow:** See [Migration Request Flow](./MIGRATION_REQUEST_FLOW.md). Application Users: profile → validate → **submit** → confirmation. Admins: view submissions → run research → generate report → edit/enhance → download.

**Umbrella document:** See [ARCHITECTURE_DESIGN.md](./ARCHITECTURE_DESIGN.md) for the master index of all design docs.

---

## 0. Decision matrix & framework selection

**Full document:** [DECISION_MATRIX.md](./DECISION_MATRIX.md) · **HTML:** [DECISION_MATRIX.html](./DECISION_MATRIX.html)

Key decisions, candidates, final choice, and rationale:

| Decision | Candidates | Final choice | Rationale |
|----------|------------|--------------|-----------|
| **Multi-agent orchestration** | LangGraph, LangChain LCEL, custom, AutoGen, CrewAI | **LangGraph** | Flow has conditional logic (Research fail → end; else → Summarize). LangGraph's graph model and conditional edges fit. LCEL is linear-only. Custom would reinvent state and tracing. AutoGen/CrewAI target conversational agents. LangGraph gives native LangSmith; used by LinkedIn, Uber, Klarna. |
| **Observability** | LangSmith, custom, OpenTelemetry, Datadog | **LangSmith** | Built for LangChain/LangGraph. Zero config. Custom needs manual instrumentation. OpenTelemetry has experimental support. LangSmith shows trace trees, token costs, latency—what Admin Diagnostics needs. |
| **Vector DB / KB** | Pinecone, Weaviate, Milvus, Chroma, Qdrant | **Pinecone** | Project foundation; already integrated. Switching would mean new index and embeddings. No business reason to change. |
| **LLM** | OpenAI, Anthropic, Azure, Vertex | **OpenAI (GPT-4o-mini)** | Already used for Chat. Adding another provider increases config. GPT-4o-mini balances quality and cost. Consistency and simplicity favor OpenAI. |
| **Web search** | Tavily, Serper, Exa, Bing | **Tavily** | Need clean snippets for LLM context. Tavily built for RAG/LLM. KB-first; Tavily only when sparse, so cost bounded. |
| **State persistence** | SQLite, Postgres, JSON, in-memory | **SQLite** | MVP needs persistence without new infra. SQLite is single file, no server. Pluggable store; migrate to Postgres when scaling. |
| **Async pattern** | Polling, SSE, WebSockets, Celery | **Polling** | Simplest: client polls every 2–3s. SSE needs streaming. Celery needs Redis. Minimal complexity for Phase 1. |
| **Report format** | MD, DOCX, PDF, HTML | **Markdown + DOCX** | LLMs output MD. Preview in UI. Convert to DOCX for download. python-docx already available. |
| **API pattern** | Step-by-step, run all | **Step-by-step** | Users see progress and can retry steps. Single "run all" would be black box. API stays step-by-step for clarity. |
| **Profile UI** | Single form, wizard, tabs | **Wizard + 7 pillar tabs** | Seven pillars would overwhelm single form. Tabs group by domain. "Continue to [next section]" enforces filling all before Research. |

**Decision tree (simplified):**
```
Need orchestrator for multi-agents? → LangGraph
Need observability?                  → LangSmith
Need vector KB?                      → Pinecone (existing)
Need LLM?                            → OpenAI
Need web search when KB sparse?      → Tavily
Need state persistence?              → SQLite
Need async for long ops?             → Polling
```

---

## 1. Executive summary

The Assessment module is a **multi-agent system** with **two roles**:

- **Application User:** Fills the application profile (seven pillars), passes validation and sanity checks, then **submits for assessment**. No research or report—submission is stored and Admins are notified.
- **Admin:** Views submitted requests, runs **Research Agent** (KB + optional web), runs **Summarizer Agent** to generate the report, can **edit/enhance** the report, and **download** (DOCX/MD).

Agents (Research, Summarizer) run only in the Admin flow. See [Migration Request Flow](./MIGRATION_REQUEST_FLOW.md) for the full two-role design.

---

## 2. Agent architecture

### 2.1 Agent overview

| Agent | Role | Inputs | Outputs | Tools |
|-------|------|--------|---------|------|
| **Data Collector** | Gather application profile | User form, optional follow-up prompts | Structured `ApplicationProfile` | Form UI, optional LLM for “ask for more” |
| **Research Agent** | Find recommendations & approach | Application profile | Approach document (recommendations, steps, pitfalls) | KB search (Pinecone), Tavily (web search) |
| **Summarizer Agent** | Produce final report | Profile + approach doc + optional clarifications | Assessment report (DOCX/MD) | LLM, optional clarification loop |

### 2.2 Data Collector Agent

**Purpose:** Ensure we have all needed data for the application to be migrated.

**Expanded profile design (for review):** The profile form is organized into **seven architecture pillars** (tabs) to capture real migration-project data. See **[ASSESSMENT_PROFILE_DESIGN.md](./ASSESSMENT_PROFILE_DESIGN.md)** for full spec and **[WIREFRAMES.html](./WIREFRAMES.html)** for wireframes (sections 2a–2g). Pillars: Overview · Architecture (incl. diagram uploads) · Data · BC & DR · Cost · Security · Project & Timeline.

**Behavior:**
- Presents a **structured form** (multi-step or single-page) with fields for:
  - Application name, description, business purpose
  - Technology stack (e.g. Java 11, Spring Boot, Oracle DB)
  - Current environment (on-prem, VM, cloud-legacy)
  - Target environment (e.g. Azure, AWS, GCP)
  - Dependencies (other apps, databases, integrations)
  - Compliance / security requirements (e.g. PCI, HIPAA)
  - Team size, timeline expectations
  - Known risks or constraints
- **Optional:** “Smart” mode where an LLM reviews the form and suggests missing fields or asks for clarification (e.g. “You mentioned Oracle DB—which version? Any custom extensions?”).
- **Output:** `ApplicationProfile` (JSON schema) persisted for the assessment session.

**Data model (ApplicationProfile):**

```json
{
  "application_name": "string",
  "description": "string",
  "business_purpose": "string",
  "tech_stack": ["string"],
  "current_environment": "on-prem|vm|cloud-legacy|other",
  "target_environment": "azure|aws|gcp|other",
  "dependencies": ["string"],
  "integrations": ["string"],
  "compliance_requirements": ["string"],
  "team_size": "string",
  "timeline_expectation": "string",
  "known_risks": "string",
  "constraints": "string",
  "additional_notes": "string"
}
```

**Trade-off:** Start with a **simple form** (no LLM in the collector). Add “smart” clarification later if needed.

---

### 2.3 Research Agent

**Purpose:** Produce an approach document with recommendations, steps, and pitfalls—using either prior migrations (KB) or best practices from the web.

**Behavior:**

1. **KB search (Pinecone):**
   - Query the Knowledge Base with: application name, tech stack, target environment, key terms.
   - Retrieve top-k chunks from past migration docs (e.g. SuperNova report, other assessments).
   - If **similar applications** were migrated before → use those as primary source.

2. **Web search (Tavily):**
   - If KB has little/no relevant content → fall back to web search.
   - Queries: e.g. “{tech_stack} migration to {target} best practices”, “{tech_stack} migration pitfalls”, “{target} migration steps”.
   - Tavily returns snippets/URLs; we pass them to the LLM to synthesize.

3. **Synthesis:**
   - LLM takes: ApplicationProfile + KB chunks + web results.
   - Produces an **Approach Document** with:
     - Recommended migration strategy (lift-and-shift vs refactor vs re-platform)
     - Steps and phases
     - Best practices
     - Pitfalls to avoid
     - References (from KB or web)

**Output:** `ApproachDocument` (structured text / markdown).

**Tools:**
- **Pinecone KB** – already integrated; semantic search over migration docs.
- **Tavily** – web search API; no raw scraping; returns curated snippets. Alternative: Serper, Exa, or Bing Search API.

**Trade-offs:**

| Option | Pros | Cons |
|--------|------|------|
| Tavily | Good for LLM-oriented search, simple API | API limits, cost per query |
| Serper (Google) | Familiar results, cheap | Less “research” oriented |
| Raw scraping | Full control | Legal, maintenance, rate limits |

**Recommendation:** Start with **Tavily** for web research; keep KB as primary when similar apps exist.

---

### 2.4 Summarizer Agent

**Purpose:** Combine profile + approach into a **detailed assessment report** and optionally ask for clarification.

**Behavior:**

1. **Input:** ApplicationProfile + ApproachDocument.
2. **Optional clarification loop:**
   - LLM identifies gaps: “Compliance requirements not specified—is this app PCI scope?”
   - Frontend shows these as prompts; user answers; we append to profile.
   - Re-run summarizer with updated profile.
3. **Report generation:**
   - LLM produces a structured report (sections: Executive Summary, Current State, Target Architecture, Recommendations, Risks, Timeline, etc.).
   - Output format: **Markdown** (easy to render) or **DOCX** (for download). We can use `python-docx` to convert MD → DOCX or generate DOCX directly.

**Output:** Assessment report (file or blob) + metadata.

**Trade-off:** First version: **no clarification loop** (single pass). Add loop in v2 if users request it.

---

## 3. End-to-end flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER (Frontend)                                    │
└─────────────────────────────────────────────────────────────────────────────┘
        │
        │ 1. Start assessment
        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  DATA COLLECTOR AGENT                                                        │
│  • Multi-step form (or single page)                                          │
│  • Validates required fields                                                │
│  • Output: ApplicationProfile (JSON)                                         │
└─────────────────────────────────────────────────────────────────────────────┘
        │
        │ 2. Submit profile
        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  RESEARCH AGENT                                                              │
│  • Query KB (Pinecone) with profile keywords                                 │
│  • If KB sparse → Tavily web search                                          │
│  • LLM synthesizes → ApproachDocument                                        │
└─────────────────────────────────────────────────────────────────────────────┘
        │
        │ 3. Approach doc ready
        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  SUMMARIZER AGENT                                                            │
│  • Input: Profile + ApproachDocument                                         │
│  • (Optional) Clarification questions → user answers → re-run                 │
│  • LLM generates final Assessment Report                                     │
└─────────────────────────────────────────────────────────────────────────────┘
        │
        │ 4. Report ready
        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  USER                                                                        │
│  • View report in UI                                                         │
│  • Download DOCX / PDF                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Backend architecture

### 4.1 API design

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/assessment/start` | Create new assessment session; returns `assessment_id` |
| `PUT` | `/api/assessment/{id}/profile` | Save/update ApplicationProfile |
| `POST` | `/api/assessment/{id}/research` | Trigger Research Agent; returns ApproachDocument (sync or async) |
| `POST` | `/api/assessment/{id}/summarize` | Trigger Summarizer; returns report (sync or async) |
| `GET` | `/api/assessment/{id}` | Get full assessment state (profile, approach, report, status) |
| `GET` | `/api/assessment/{id}/report` | Download report file (DOCX) |

**Alternative (orchestrated):**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/assessment/run` | Single call: profile in body → runs research + summarize; returns job_id |
| `GET` | `/api/assessment/job/{job_id}` | Poll for status and result |

**Recommendation:** **Step-by-step** (separate endpoints) for Phase 1. Easier to debug, user sees progress. Add orchestrated “run all” later if desired.

### 4.2 Sync vs async

| Operation | Duration | Recommendation |
|-----------|----------|----------------|
| Save profile | Fast | Sync |
| Research (KB + Tavily + LLM) | 10–60 s | **Async** with polling or SSE |
| Summarize | 5–30 s | **Async** with polling or SSE |

**Implementation options:**
- **A) Background jobs:** Celery, RQ, or FastAPI BackgroundTasks. Store state in DB or file.
- **B) Polling:** Client polls `GET /api/assessment/{id}` every 2–3 s until `status: completed`.
- **C) Server-Sent Events (SSE):** Stream status updates to frontend.

**Recommendation:** **Polling** for Phase 1 (simplest). Add SSE later for better UX.

### 4.3 State persistence

| Option | Pros | Cons |
|--------|------|------|
| **In-memory (dict)** | Simple, no deps | Lost on restart; not multi-instance |
| **SQLite** | Persistent, single file, no server | Need schema; file locking |
| **JSON files** | Simple, human-readable | Concurrency, no querying |
| **PostgreSQL** | Scalable, robust | Overkill for MVP |

**Recommendation:** **SQLite** for Phase 1. Schema: `assessments` table (id, profile_json, approach_doc, report_path, status, created_at, updated_at). Easy to migrate to Postgres later.

### 4.4 Backend layout (proposed)

```
backend/
├── routers/
│   ├── assessment.py      # New: assessment endpoints
│   └── ...
├── services/
│   ├── assessment/
│   │   ├── data_collector.py   # Validation, profile schema (no agent logic if form-only)
│   │   ├── research_agent.py   # KB search + Tavily + synthesis
│   │   ├── summarizer_agent.py # Report generation
│   │   └── store.py            # SQLite or file-based persistence
│   └── llm.py
└── ...
```

---

## 5. Frontend architecture

### 5.1 UX flow

1. **Assessment tab** (existing Home page) → “Start new assessment” or “Continue assessment”.
2. **Step 1 – Data collection:** Multi-step form (or accordion) with ApplicationProfile fields. Progress indicator. “Save & continue”.
3. **Step 2 – Research:** “Run research” button. Loading state with message (“Searching knowledge base…”, “Searching web…”, “Synthesizing…”). Display ApproachDocument when done.
4. **Step 3 – Report:** “Generate report” button. Loading state. When done: preview in UI + “Download DOCX” button.
5. **Optional:** List of past assessments (if we persist and allow multiple).

### 5.2 Component structure (proposed)

```
frontend/src/
├── pages/
│   ├── Home.jsx              # Existing; Assessment tab links to Assessment flow
│   └── Assessment.jsx         # New: dedicated assessment page (or keep in Home)
├── components/
│   └── assessment/
│       ├── AssessmentWizard.jsx    # Stepper: Collect → Research → Report
│       ├── ProfileForm.jsx         # Data collection form
│       ├── ResearchStep.jsx        # Trigger research, show approach doc
│       ├── ReportStep.jsx          # Trigger report, preview, download
│       └── AssessmentStatus.jsx    # Loading, error, progress
```

**Trade-off:** Keep assessment **inside Home** (Assessment tab) vs **separate route** `/assessment`. Recommendation: **separate route** `/assessment` for cleaner URL and room to grow (e.g. `/assessment/:id`).

### 5.3 Wireframes (conceptual)

**Step 1 – Profile form:**
- Sections: Basic info | Tech & environment | Dependencies & compliance | Timeline & risks
- Required fields marked; validation on submit
- “Save & continue to research”

**Step 2 – Research:**
- Summary of profile (read-only)
- “Run research” button
- Progress: “Searching KB…” → “Searching web…” → “Synthesizing…”
- Result: Approach document in a scrollable card (markdown rendered)

**Step 3 – Report:**
- “Generate assessment report” button
- Progress: “Generating report…”
- Result: Report preview (markdown or HTML) + “Download DOCX”

---

## 6. Tech stack, orchestration & observability

*See [DECISION_MATRIX.md](./DECISION_MATRIX.md) for full rationale on each choice.*

### 6.1 Agent orchestration: LangGraph

**Choice: LangGraph** for multi-agent orchestration. Graph-based state machine; nodes = agents; typed shared state; conditional edges; checkpointing; native LangSmith integration. **Candidates considered:** LangChain LCEL, custom Python, AutoGen, CrewAI. **Rationale:** Explicit graph model matches our flow; conditional edges for error handling; agents stay standalone; industry adoption.

### 6.2 Observability: LangSmith

**Choice: LangSmith** for full observability. Trace trees (each node, tool, LLM call), costs (token usage, cost by model), performance (latency per step), errors (exceptions, stack traces). **Candidates considered:** Custom logging, OpenTelemetry, Datadog. **Rationale:** Zero-config with LangChain; fallback: if not set, tracing disabled. Setup: `LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT=assessment`.

### 6.3 Modular architecture

```
backend/services/assessment/
├── models.py         # ApplicationProfile, AssessmentState
├── store.py          # SQLite (pluggable)
├── research_agent.py # KB + synthesis (standalone)
├── summarizer_agent.py # Report gen (standalone)
└── graph.py          # LangGraph orchestration
```

Agents are pure functions; store is pluggable; graph is thin.

### 6.4 New dependencies

| Tool | Purpose | Notes |
|------|---------|-------|
| **Tavily** | Web search for best practices, pitfalls | API key; rate limits |
| **python-docx** | Generate DOCX report | Already in requirements for extractors |
| **SQLite** | Persist assessment state | Built-in; or `aiosqlite` for async |

### 6.5 Environment variables

| Variable | Purpose |
|---------|---------|
| `TAVILY_API_KEY` | Tavily search API |
| `OPENAI_API_KEY` | LLM (already used for chat) |
| `PINECONE_*` | KB (already configured) |

(Tavily used in Phase 2 when KB is sparse.)
- **Queries:** e.g. “Spring Boot migration to Azure best practices”, “Oracle to PostgreSQL migration pitfalls”.
- **Output:** Pass snippets to LLM for synthesis; avoid raw HTML scraping.

---

## 7. Trade-offs summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent orchestration | Step-by-step API | Easier to debug; user sees progress |
| Research web tool | Tavily | LLM-oriented; no scraping |
| State persistence | SQLite | Simple, persistent, no extra infra |
| Async pattern | Polling | Simplest; add SSE later |
| Clarification loop | Defer to v2 | Reduce scope for Phase 1 |
| Report format | Markdown + DOCX | MD for preview; DOCX for download |
| Assessment location | New route `/assessment` | Cleaner; supports `/assessment/:id` |

---

## 8. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Tavily rate limits / cost | Cache results; limit queries per assessment; fallback to KB-only |
| LLM token limits | Chunk approach doc; summarize before passing to Summarizer |
| Long-running research | Async + timeout; show partial results if possible |
| Report quality | Provide clear prompts; optional human review step |
| Multi-user concurrency | SQLite handles single-writer; for scale, move to Postgres |

---

## 9. Implementation phases

### Phase 1 – Foundation (MVP)
- [ ] Backend: Assessment router + SQLite store + ApplicationProfile schema
- [ ] Backend: Research Agent (KB only; no Tavily yet)
- [ ] Backend: Summarizer Agent (Markdown report)
- [ ] Frontend: Assessment route + ProfileForm + ResearchStep + ReportStep (polling)
- [ ] End-to-end: Form → Research (KB) → Report (MD)

### Phase 2 – Web research
- [ ] Add Tavily to Research Agent
- [ ] Logic: KB first; if sparse, call Tavily
- [ ] Tune queries and synthesis prompt

### Phase 3 – Polish
- [ ] DOCX report generation (python-docx)
- [ ] Download endpoint
- [ ] Optional: Clarification loop
- [ ] Optional: SSE for progress

### Phase 4 – Scale (future)
- [ ] Postgres or external DB
- [ ] Job queue (Celery/RQ) for heavy workloads
- [ ] Assessment history list in UI

---

## 10. Admin Command Center (Design)

### 10.1 Purpose

An **Admin-only** dashboard that provides a single pane of glass for:
- All assessment statuses, errors, and progress
- Knowledge Base health and usage
- System-level errors and diagnostics
- Quick actions (re-index, view details)

**Audience:** CoE admins, operators, support. Not end users running assessments.

### 10.2 Layout – Command center style

A grid of dashboard panels (cards) with a dark or high-contrast theme to evoke a “command center” feel. Responsive: 1 column on mobile, 2–3 on tablet, 3–4 on desktop.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ADMIN COMMAND CENTER                                    [Refresh] [Export]  │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐           │
│  │ Assessments       │ │ KB Health        │ │ Errors (24h)      │           │
│  │ Total: 12         │ │ Status: OK       │ │ Count: 2          │           │
│  │ Done: 8           │ │ Spend: $2.40     │ │ Last: 10m ago     │           │
│  │ In progress: 2    │ │ Read/Write: 450  │ │ [View all]        │           │
│  │ Error: 2          │ │ [Details]        │ │                   │           │
│  └──────────────────┘ └──────────────────┘ └──────────────────┘           │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ Assessment list (table)                                               │  │
│  │ ID        │ App name    │ Status      │ Error        │ Updated       │  │
│  │ abc-123   │ OrderSvc    │ done        │ —            │ 2h ago        │  │
│  │ def-456   │ FinanceApp  │ error       │ LLM timeout  │ 1h ago        │  │
│  │ ghi-789   │ Inventory   │ researching │ —            │ 5m ago        │  │
│  │ [View] [Retry] [Delete]                                                │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────┐ ┌────────────────────────────┐           │
│  │ KB Config & Seed            │ │ Recent errors (log)         │           │
│  │ Project dir: /path/...      │ │ 10:32 - Research failed...  │           │
│  │ [Run seed]                  │ │ 09:15 - OpenAI rate limit   │           │
│  └────────────────────────────┘ └────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 10.3 Two tabs: Assessments | Diagnostics

**Tab 1 – Assessments:** Business tracking (assessment list, status, errors, KB config, seed).  
**Tab 2 – Diagnostics:** System/agent/request level (LLM invocations, tokens used, agent calls, data transfers, latency, request log).

**Full design:** See **`docs/ADMIN_COMMAND_CENTER_DESIGN.md`** for layout, panels, API, data sources, and implementation order.

### 10.4 Panels (summary)

**Assessments tab:** Assessments summary, KB health, Errors (24h), Assessment list, KB config & seed, Recent errors.  
**Diagnostics tab:** LLM invocations, Tokens used, Agent calls, Data transfers, Latency (p95), Request log.

### 10.5 API additions

**Assessments:** `GET /api/admin/assessments`, `GET /api/admin/assessments/summary`  
**Diagnostics:** `GET /api/admin/diagnostics/summary`, `GET /api/admin/diagnostics/requests`  

See `ADMIN_COMMAND_CENTER_DESIGN.md` for full API spec.

### 10.6 Access control

| Option | Approach | Notes |
|--------|----------|-------|
| **A) URL-based** | `/admin` is admin-only by convention; no auth | Simplest; suitable for internal tool |
| **B) Env flag** | `ADMIN_ENABLED=true`; hide nav when false | Soft gate |
| **C) Auth** | Require login; role=admin | Future; OAuth, API key, or session |

**Recommendation:** Start with **A**. Add **B** or **C** when deploying to shared environments.

### 10.7 Visual design (command center)

- **Theme:** Dark or slate background (`#0f172a`, `#1e293b`) with light text; accent color for status (green=ok, amber=in progress, red=error)
- **Typography:** Monospace for IDs, timestamps; sans-serif for labels
- **Cards:** Subtle border, slight shadow; status indicators (dot or badge)
- **Table:** Striped rows; sortable by status, updated; filter by status
- **Refresh:** Manual refresh button; optional auto-refresh every 30s for “live” feel

### 10.7 Implementation order

1. **Tab structure** – Admin page with Assessments | Diagnostics tabs
2. **Assessments tab** – Backend assessments API; panels (summary, list, KB, errors)
3. **Metrics instrumentation** – Log per-request: agent, tokens, latency, status
4. **Diagnostics tab** – Backend diagnostics API; panels (LLM, tokens, agents, request log)
5. **Polish** – Export, auto-refresh, retry/delete

---

## 11. Open questions for review

1. **Form fields:** Is the ApplicationProfile schema complete for your use case? Any additions (e.g. budget, stakeholder contacts)?
2. **Tavily vs alternatives:** Any preference for Serper, Exa, or Bing? Or stick with Tavily?
3. **Report structure:** Should the report follow a specific template (e.g. SuperNova-style sections)? We can align with `scripts/generate_supernova_assessment.py` structure.
4. **Assessment scope:** One assessment per “application” or support multiple assessments per app (revisions)?
5. **Auth:** Will assessments be user-scoped (require auth) or anonymous for now?
6. **Admin Command Center:** Any additional panels or metrics? Retry/delete assessment actions needed?
7. **Admin Diagnostics:** See **`docs/ADMIN_COMMAND_CENTER_DESIGN.md`** for full two-tab design (Assessments | Diagnostics with agent/LLM/token metrics).

---

## 12. Next steps

1. **Review this design** – Confirm architecture, trade-offs, Admin Command Center, and phased plan.
2. **Finalize ApplicationProfile schema** – Add/remove fields as needed.
3. **Confirm tools** – Tavily vs alternatives; report format (MD vs DOCX first).
4. **Approve Admin Command Center** – Layout, panels, API.
5. **Approve Phase 1 scope** – Then proceed to implementation one by one.

---

*Document version: 1.0 | Last updated: Design phase*
