# Design Review Checklist

**Purpose:** Review all designs before implementation. Approve each section, then implement one by one.

---

## 1. Assessment Module (multi-agent)

| Item | Status | Notes |
|------|--------|-------|
| Agent architecture (Data Collector, Research, Summarizer) | ☐ Review | See §2 |
| ApplicationProfile schema | ☐ Review | See §2.2 |
| Tech stack (LangGraph, LangSmith) | ☐ Review | See §6 |
| Modular backend layout | ☐ Review | See §6.3 |
| API design (step-by-step) | ☐ Review | See §4.1 |
| Frontend wizard (Profile → Research → Report) | ☐ Review | See §5 |
| Implementation phases | ☐ Review | See §9 |

**Docs:** `ASSESSMENT_MODULE_DESIGN.md`, `ASSESSMENT_DESIGN.html`

---

## 2. Admin Command Center

| Item | Status | Notes |
|------|--------|-------|
| Two-tab structure | ☐ Review | Tab 1: Assessments | Tab 2: Diagnostics |
| **Tab 1 – Assessments** | | |
| Panels: Assessments summary | ☐ Review | Total, done, in progress, error |
| Panels: KB health | ☐ Review | Reuse existing |
| Panels: Assessment list table | ☐ Review | ID, app, status, error, updated |
| Panels: KB config & seed | ☐ Review | Reuse existing |
| Panels: Recent errors | ☐ Review | From assessments |
| **Tab 2 – Diagnostics** | | |
| Panels: LLM invocations | ☐ Review | Count by type (chat, research, summarizer) |
| Panels: Tokens used | ☐ Review | Input/output, estimated cost |
| Panels: Agent calls | ☐ Review | Per-agent call counts |
| Panels: Data transfers | ☐ Review | KB queries, chunks retrieved |
| Panels: Latency (p95) | ☐ Review | Per-agent performance |
| Panels: Request log | ☐ Review | Last N requests with tokens, latency, status |
| API: assessments | ☐ Review | GET /api/admin/assessments, /summary |
| API: diagnostics | ☐ Review | GET /api/admin/diagnostics/summary, /requests |
| Data source: local metrics store | ☐ Review | Log per-request for dashboard |
| Access control | ☐ Review | URL-based for now |
| Retry / Delete actions | ☐ Review | Optional |

**Docs:** `ADMIN_COMMAND_CENTER_DESIGN.md`, `ASSESSMENT_MODULE_DESIGN.md` §10, `ASSESSMENT_DESIGN.html` §10

---

## 3. Implementation order (after approval)

1. **Assessment module** (if not done) – backend, frontend, tests  
2. **Admin Command Center** – new API, dashboard UI, integrate with existing Admin

---

## 4. Open questions

- [ ] Form fields: any additions to ApplicationProfile?
- [ ] Admin: any extra panels or metrics?
- [ ] Admin: Retry/Delete assessment – needed?
- [ ] Auth: when to add?

---

*Check off items as you review. Proceed to implementation only after approval.*
