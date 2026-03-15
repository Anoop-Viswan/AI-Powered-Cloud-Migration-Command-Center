# Admin Command Center – Design Spec

**Status:** Design for review (two-role flow)  
**Related:** [Migration Request Flow](./MIGRATION_REQUEST_FLOW.md), Assessment Module Design

---

## 1. Purpose

**Admin-only** dashboard for the **Migration Request** flow. Application Users submit migration requests (profile only); **Admins** view submissions, run research, generate and edit reports, and download.

**Admin responsibilities:**

- View all migration requests (submitted, researching, report_done, error)
- Open a submission and see full application profile
- Run **Research** (KB + optional web; optional manual input/guidance)
- **Generate report** (Summarizer)
- **Edit and enhance** the report (in-place)
- **Download** final report (DOCX/MD)
- Optional: KB management, diagnostics (LLM/agent metrics)

**Audience:** CoE admins, migration specialists. Not Application Users (they only submit).

---

## 2. Two-tab structure

| Tab | Route | Focus |
|-----|-------|-------|
| **Assessments** | `/admin` or `/admin/assessments` | List of migration requests; open → Research, Generate report, Edit report, Download |
| **Knowledge Base** | `/admin` (KB tab) | KB config, seed, usage. Optional: **Diagnostics** (LLM/agent metrics) as third tab or subsection. |

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ADMIN COMMAND CENTER                                                        │
│  ┌─────────────────────┐ ┌─────────────────────┐                           │
│  │ Assessments         │ │ Knowledge Base       │  [Refresh] [Export]        │
│  └─────────────────────┘ └─────────────────────┘                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  Submissions list │ Open submission → Run research → Generate report → Edit → Download
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Tab 1: Assessments (migration requests)

Admins see **all migration requests** submitted by Application Users. Status lifecycle: `submitted` → `researching` → `research_done` → `report_done` (or `error`). **New submissions** are highlighted (e.g. "New" badge or count of unhandled).

### List view

- **Summary cards:** Total, submitted (new), in progress, report_done, error
- **Table:** ID, App name, Status, Submitted at, Updated, Actions (Open, Run research, Generate report, Download)

### Open submission (detail view)

- **Full profile** (read-only): all seven pillars as entered by Application User
- **Admin actions:**
  - **Run research** – Triggers Research Agent (KB + optional Tavily). Admin can add **manual notes or guidance** before/after (stored with assessment).
  - **Generate report** – Triggers Summarizer; report appears for preview.
  - **Edit report** – Rich text or markdown edit; save changes.
  - **Download** – DOCX (or MD).

### Notifications

- Minimum: new rows in list with status `submitted` (admins see them on next load or refresh).
- Optional: in-app badge/count of "submitted" (unhandled), or future email/webhook.

### Layout (summary)

```
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ Total            │ │ New (submitted)  │ │ Errors (24h)     │
│ 12               │ │ 3                │ │ 2                │
└──────────────────┘ └──────────────────┘ └──────────────────┘
┌────────────────────────────────────────────────────────────────────────────┐
│ Migration requests (table)                                                  │
│ ID     │ App name   │ Status     │ Submitted  │ Updated  │ Actions          │
│ abc-123│ OrderSvc   │ submitted  │ 1h ago    │ 1h ago   │ [Open]           │
│ def-456│ FinanceApp │ report_done│ 2d ago    │ 1h ago   │ [Open][Download] │
└────────────────────────────────────────────────────────────────────────────┘
```

**Open** → Detail: Profile (read-only) │ [Run research] [Generate report] [Edit report] [Download]

### Panels

| Panel | Data | API |
|-------|------|-----|
| Summary | Total, submitted, report_done, error counts | `GET /api/admin/assessments/summary` |
| Assessment list | Table: id, app name, status, submitted_at, updated_at | `GET /api/admin/assessments` |
| Detail | Full profile + approach + report (when run) | `GET /api/assessment/{id}` |
| Research / Report / Edit / Download | Admin-only actions | POST research, POST summarize, PUT report, GET report |

---

## 4. Tab 2: Knowledge Base (and optional Diagnostics)

**Knowledge Base:** Config, seed, usage (document count, index stats). Same as current implementation.

**Optional Diagnostics** (third tab or subsection): Agent performance, LLM usage, request-level metrics (see layout below).

### Layout

```
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ LLM invocations  │ │ Tokens used      │ │ Agent calls      │
│ Last 24h: 142    │ │ Input: 45.2K     │ │ Research: 38      │
│ Chat: 89         │ │ Output: 12.1K    │ │ Summarizer: 35    │
│ Research: 38     │ │ Est. cost: $0.42 │ │ Chat: 89          │
│ Summarizer: 35   │ │ (24h)            │ │                   │
└──────────────────┘ └──────────────────┘ └──────────────────┘
┌──────────────────┐ ┌──────────────────┐
│ Data transfers   │ │ Latency (p95)    │
│ KB queries: 156  │ │ Research: 12.3s   │
│ Chunks: 1.2K     │ │ Summarizer: 8.1s  │
│ (24h)            │ │ Chat: 2.4s       │
└──────────────────┘ └──────────────────┘
┌────────────────────────────────────────────────────────────────────────────┐
│ Request log (last 50)                                                        │
│ Time     │ Type       │ Agent/Endpoint │ Tokens In/Out │ Latency │ Status   │
│ 10:45:32 │ research   │ ResearchAgent │ 2.1K / 450   │ 11.2s   │ ok       │
│ 10:44:18 │ summarize  │ Summarizer    │ 3.2K / 1.1K  │ 9.1s    │ ok       │
│ 10:43:02 │ chat       │ Chat          │ 0.8K / 120   │ 2.1s    │ ok       │
│ 10:40:15 │ research   │ ResearchAgent │ 2.0K / —     │ —       │ error    │
└────────────────────────────────────────────────────────────────────────────┘
```

### Panels

| Panel | Data | Notes |
|-------|------|-------|
| **LLM invocations** | Count by type (chat, research, summarizer) over 24h | Per-agent breakdown |
| **Tokens used** | Input tokens, output tokens, estimated cost | Aggregate + by agent |
| **Agent calls** | Call count per agent (Research, Summarizer, Chat) | Success vs error |
| **Data transfers** | KB queries, chunks retrieved, Tavily calls (if used) | Volume metrics |
| **Latency (p95)** | 95th percentile latency per agent/endpoint | Performance |
| **Request log** | Last N requests: time, type, agent, tokens, latency, status | Drill-down |

---

## 5. Data sources for diagnostics

| Metric | Source | Implementation |
|--------|--------|----------------|
| **LangSmith** | Traces, token usage, costs, latency | When `LANGCHAIN_TRACING_V2=true`; LangSmith UI has this. For our dashboard we need an API or local aggregation. |
| **Local metrics store** | Our own counters and logs | Persist per-request: agent, tokens_in, tokens_out, latency_ms, status. SQLite table or JSON log. |
| **OpenAI usage** | Response headers | `usage.prompt_tokens`, `usage.completion_tokens` in API responses; we log them. |
| **Pinecone** | Read units | Already in `usage_tracker`; extend for query count. |

**Recommendation:** Add a **local metrics store** (e.g. `metrics` table or append-only log) that we populate from each LLM/agent call. LangSmith remains the source of truth for deep traces; our dashboard shows aggregated metrics for quick visibility.

---

## 6. API additions

### Assessments tab (Admin)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/admin/assessments` | List all migration requests (id, app name, status, submitted_at, updated_at). Filter: `?status=submitted`, etc. |
| GET | `/api/admin/assessments/summary` | Counts: total, submitted, researching, report_done, error |
| GET | `/api/assessment/{id}` | Get full assessment (profile, approach, report). Admin opens a submission. |
| POST | `/api/assessment/{id}/research` | Run Research Agent (Admin only) |
| POST | `/api/assessment/{id}/summarize` | Generate report (Admin only) |
| PUT | `/api/assessment/{id}/report` | Update report body (edit/enhance) (Admin only) |
| GET | `/api/assessment/{id}/report` | Download report (DOCX) (Admin only) |

### Diagnostics tab

**Full design and wireframes:** See **[DIAGNOSTICS_DESIGN.md](./DIAGNOSTICS_DESIGN.md)** (X-ray visibility, thresholds, alerts, cost, patterns) and **[DIAGNOSTICS_WIREFRAMES.html](./DIAGNOSTICS_WIREFRAMES.html)** for UI mockups.

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/admin/diagnostics/summary` | Aggregates: LLM calls, tokens, cost, by operation; Tavily/Pinecone; alerts; period=24h\|7d\|30d |
| GET | `/api/admin/diagnostics/interfaces` | Per-interface breakdown (LLM, Tavily, Pinecone): calls, duration, errors, cost |
| GET | `/api/admin/diagnostics/requests` | Request log: last N with time, interface, operation, tokens, latency, status |
| GET | `/api/admin/diagnostics/patterns` | Usage over time, top consumers by cost % |
| GET / PATCH | `/api/admin/diagnostics/config` | Thresholds and alert-at-% (daily token limit, cost limit, etc.) |
| (Optional) | `GET /api/admin/diagnostics/export` | Export metrics (CSV/JSON) for external analysis |

---

## 7. Access control

| Option | Approach | Notes |
|--------|----------|-------|
| **A) URL-based** | `/admin` is admin-only by convention; no auth | Simplest |
| **B) Env flag** | `ADMIN_ENABLED=true`; hide nav when false | Soft gate |
| **C) Auth** | Require login; role=admin | Future |

**Recommendation:** Start with **A**.

---

## 8. Visual design (command center)

- **Theme:** Dark/slate (`#0f172a`, `#1e293b`); status colors (green/amber/red)
- **Tabs:** Clear active state; Assessments | Diagnostics
- **Cards:** Summary metrics in cards; tables for lists/logs
- **Refresh:** Manual + optional auto-refresh (e.g. 30s for Assessments, 15s for Diagnostics)

---

## 9. Implementation order (two-role flow)

1. **Submit endpoint** – Application User: `POST /api/assessment/{id}/submit` (validate, set status=submitted, notify)
2. **Admin Assessments tab** – List submissions (status: submitted, research_done, report_done, error); summary cards; "Open" → detail view
3. **Admin detail view** – Full profile (read-only); actions: Run research, Generate report, Edit report, Download
4. **Report edit** – `PUT /api/assessment/{id}/report` to save admin edits
5. **Tab structure** – Assessments | Knowledge Base (optional Diagnostics)
6. **Polish** – Notifications (e.g. badge for new submissions), auto-refresh

---

## 10. Open questions

- [ ] Time range for diagnostics: 24h default? Configurable?
- [ ] Request log retention: last 50? 100? Configurable?
- [ ] Export format: CSV, JSON, or both?
- [ ] LangSmith integration: link to LangSmith dashboard from our Diagnostics tab?

---

*Document version: 1.0 | Design for review*
