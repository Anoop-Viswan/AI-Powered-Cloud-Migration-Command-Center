# Cloud Migration Command Center – Architecture & Design

**Umbrella document** for all architecture and design artifacts. Single entry point with links to detailed specs.

---

## 1. Overview

The **Cloud Migration Command Center** is an AI-powered CoE (Center of Excellence) application that provides:

- **Semantic Search** – Query the knowledge base with natural language
- **Migration Request (Assessment)** – **Two-role flow:** Application users submit app data; Admins run research and generate/edit reports. See [Migration Request Flow](./MIGRATION_REQUEST_FLOW.md).
- **Chat** – Summarize and discuss documents
- **Admin** – Dashboard for admins: view submitted requests, run research, generate/edit reports, download; KB management; diagnostics

### Two roles

| Role | Flow |
|------|------|
| **Application User** | Fill application profile (all pillars) → validate & sanity checks → **Submit for assessment** → confirmation. No research or report. |
| **Admin** | View submitted requests → open submission → run research (KB + optional manual input) → generate report → **edit/enhance report** → download. |

---

## 2. Design documents index

| Document | Description | Format |
|----------|-------------|--------|
| [**Migration Request Flow**](./MIGRATION_REQUEST_FLOW.md) | **Two-role flow:** Application User (submit request) vs Admin (research, report, edit, download) | MD |
| [Decision Matrix](./DECISION_MATRIX.md) | Framework & tool selection with rationale (LangGraph, LangSmith, Pinecone, etc.) | [MD](./DECISION_MATRIX.md) · [HTML](./DECISION_MATRIX.html) |
| [Assessment Module Design](./ASSESSMENT_MODULE_DESIGN.md) | Multi-agent system, agents, API, phases | MD |
| [Assessment Design](./ASSESSMENT_DESIGN.html) | Architecture & design with diagrams | HTML |
| [Assessment Profile Design](./ASSESSMENT_PROFILE_DESIGN.md) | Seven architecture pillars, fields, validation | MD |
| [Assessment Profile Pillars](./ASSESSMENT_PROFILE_PILLARS.md) | Quick reference for profile sections | MD |
| [Wireframes](./WIREFRAMES.html) | Page mockups: Application User (profile, submit, confirmation) + Admin (submissions, research, report, edit, download) | HTML |
| [Admin Command Center](./ADMIN_COMMAND_CENTER_DESIGN.md) | Admin: submissions list, run research, generate/edit report, download; KB; diagnostics | [MD](./ADMIN_COMMAND_CENTER_DESIGN.md) · [HTML](./ADMIN_COMMAND_CENTER_DESIGN.html) |
| [LLM Dataflow](./DATAFLOW_LLM.md) | How Chat uses KB + LLM for summarization | MD |
| [Deployment](./DEPLOYMENT.md) | Hugging Face Spaces, Docker, cloud deployment | MD |
| [Design Review Checklist](./DESIGN_REVIEW_CHECKLIST.md) | Checklist for design approval | MD |

---

## 3. LLM provider flexibility

The architecture supports **seamless LLM switching** via a provider abstraction. All LLM calls (Chat, Research Agent, Summarizer Agent) use a single `get_llm()` factory.

### How it works

- **Provider selection:** Set `LLM_PROVIDER=openai|anthropic|azure_openai` in `.env`
- **Unified interface:** `backend/services/llm_provider.py` returns a LangChain `BaseChatModel`
- **No code changes:** Switch providers by changing env vars and adding the relevant API key

### Supported providers

| Provider | Env vars | Notes |
|----------|----------|-------|
| **openai** (default) | `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_TEMPERATURE`, `OPENAI_MAX_TOKENS` | Default |
| **anthropic** | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` | Requires `langchain-anthropic` |
| **azure_openai** | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT` | Enterprise / data residency |

### Adding a new provider

1. Add a branch in `backend/services/llm_provider.py` → `get_llm()`
2. Return a LangChain `BaseChatModel` (e.g. `ChatGoogleGenerativeAI` for Vertex)
3. Document env vars in `.env.example`

### Usage

```python
from backend.services.llm_provider import get_llm

llm = get_llm(temperature=0.3, max_tokens=4096)
response = llm.invoke([SystemMessage(...), HumanMessage(...)])
```

---

## 4. Architecture at a glance

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Frontend (React/Vite)                                                   │
│  Home · Assessment (wizard) · Chat · Admin                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Backend (FastAPI)                                                       │
│  /api/search · /api/chat · /api/assessment/* · /api/admin/*              │
└─────────────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  Pinecone    │    │  LLM Provider    │    │  SQLite          │
│  (Vector KB) │    │  (OpenAI /       │    │  (Assessments)   │
│              │    │   Anthropic /     │    │                  │
│              │    │   Azure)          │    │                  │
└──────────────┘    └──────────────────┘    └──────────────────┘
```

---

## 5. Key design decisions

| Decision | Choice | See |
|----------|--------|-----|
| **Migration request flow** | Two roles: Application User (submit only) vs Admin (research, report, edit, download) | [Migration Request Flow](./MIGRATION_REQUEST_FLOW.md) |
| Multi-agent orchestration | LangGraph | [Decision Matrix](./DECISION_MATRIX.md#1-multi-agent-orchestration) |
| Observability | LangSmith | [Decision Matrix](./DECISION_MATRIX.md#2-observability--tracing) |
| Vector DB | Pinecone | [Decision Matrix](./DECISION_MATRIX.md#3-vector-database--knowledge-base) |
| LLM | OpenAI (default); switchable to Anthropic, Azure | [§3 above](#3-llm-provider-flexibility) |
| Profile UI | Wizard + 7 pillar tabs (Application User only) | [Profile Design](./ASSESSMENT_PROFILE_DESIGN.md) |
| Admin | Submissions list; run research, generate/edit report, download; KB; diagnostics | [Admin Design](./ADMIN_COMMAND_CENTER_DESIGN.md) |

---

## 6. Quick links

- **Migration Request Flow:** [MIGRATION_REQUEST_FLOW.md](./MIGRATION_REQUEST_FLOW.md) – Two-role flow (Application User vs Admin)
- **Wireframes:** [WIREFRAMES.html](./WIREFRAMES.html) – Application User + Admin mockups
- **Decision Matrix:** [DECISION_MATRIX.html](./DECISION_MATRIX.html) – Framework choices with rationale
- **Assessment Design:** [ASSESSMENT_DESIGN.html](./ASSESSMENT_DESIGN.html) – Architecture diagrams
- **Admin Design:** [ADMIN_COMMAND_CENTER_DESIGN.html](./ADMIN_COMMAND_CENTER_DESIGN.html) – Admin dashboard

---

*Umbrella document v1.0 · Cloud Migration Command Center*
