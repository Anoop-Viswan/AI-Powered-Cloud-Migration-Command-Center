# Phase 2 – Admin Flow: Design Review & Implementation Steps

This document reviews the Phase 2 design and lists **detailed implementation steps** in order. Use it to track progress and ensure nothing is missed.

---

## 1. Design recap (Phase 2 scope)

**Goal:** Admins can open a submitted migration request, run research, generate the report, edit it, and download it. Application Users do not see these actions.

**References:**
- [Migration Request Flow](./MIGRATION_REQUEST_FLOW.md) – Admin flow (view → open → research → report → edit → download)
- [Admin Command Center Design](./ADMIN_COMMAND_CENTER_DESIGN.md) – Assessments tab, detail view, actions
- [Wireframes](./WIREFRAMES.html) – Sections 4–6: Admin list, Open submission, Research & Report

**Out of scope for Phase 2:** Tavily/web search, Tool Gateway, Diagnostics tab, notifications (badge/email), manual notes field on assessment. Those can follow in Phase 3+.

---

## 2. What already exists

| Component | Status | Notes |
|-----------|--------|-------|
| `POST /api/assessment/{id}/research` | ✅ Exists | Runs Research Agent; sets status `research_done` |
| `POST /api/assessment/{id}/summarize` | ✅ Exists | Runs Summarizer; sets status `done`, stores report text |
| `GET /api/assessment/{id}` | ✅ Exists | Returns profile, approach_document, report, status |
| `GET /api/admin/assessments` | ✅ Exists | List for admin |
| `GET /api/admin/assessments/summary` | ✅ Exists | Counts: total, done, in_progress, error |
| Admin UI – Assessments tab | ✅ Exists | Scorecards + table; "View" links to `/assessment/:id` |
| Admin UI – Knowledge Base tab | ✅ Exists | Config, usage, seed, manifest |
| Store: `update_approach`, `update_report`, `update_status` | ✅ Exists | Status lifecycle supported |

**Note:** Backend uses status `done` (not `report_done`) when the report is generated; design docs sometimes say "report_done" for clarity. Use `done` in API and store.

**Gaps to fill:**
- Admin list links to **Application User** assessment page; we need an **Admin-only detail page** (profile read-only + Run research / Generate report / Edit report / Download).
- No **PUT report** (edit report body) or **GET report** (download as file).
- Summary API and UI do not expose **submitted** count; list does not show **submitted_at** or "Open" vs "Download" by status.
- No UI for running research, generating report, editing report, or downloading from the admin context.

---

## 3. Implementation steps (detailed)

### Step 1 – Backend: Report update and download

| # | Task | Details |
|---|------|---------|
| 1.1 | Add `PUT /api/assessment/{id}/report` | Body: `{ "report": "markdown or plain text" }`. Store updates `report` column only (status unchanged). Validate assessment exists. |
| 1.2 | Add `GET /api/assessment/{id}/report` for download | Query param or Accept: e.g. `?format=docx` or `Accept: application/vnd.openxmlformats-officedocument.wordprocessingml.document`. Return DOCX file with Content-Disposition. If format=json or no format, return `{ "report": "..." }` for preview/edit. |
| 1.3 | DOCX generation helper | Add a small module (e.g. `backend/services/assessment/report_docx.py`) that takes markdown/report text and returns a BytesIO or bytes DOCX (use python-docx; project already uses it in scripts). |

**Files:** `backend/routers/assessment.py`, new `backend/services/assessment/report_docx.py` (or inline in router), `requirements.txt` (ensure python-docx present).

---

### Step 2 – Backend: Admin summary and list enhancements

| # | Task | Details |
|---|------|---------|
| 2.1 | Add `submitted` count to summary | In `AssessmentStore.get_summary()`, add count where `status = 'submitted'`. Return in response as `submitted` (or `new`). Admin UI can show "New (submitted)" card. |
| 2.2 | Optional: `submitted_at` in list | If assessments table has `created_at`, we could add `submitted_at` when status is set to `submitted`. For minimal change, use `updated_at` as "Submitted" column for now, or add a nullable `submitted_at` column and set it in `update_status(..., "submitted")`. **Simplest:** keep list as-is and show `updated_at`; optionally label column "Updated" or "Submitted" for submitted rows. |

**Files:** `backend/services/assessment/store.py`, optionally `backend/routers/admin.py` if response shape changes.

---

### Step 3 – Frontend: Admin assessment detail page (new route)

| # | Task | Details |
|---|------|---------|
| 3.1 | Add route `/admin/assessment/:id` | In `App.jsx`, add route that renders an Admin-only assessment detail component (e.g. `AdminAssessmentDetail` or `AdminAssessment`). |
| 3.2 | Create Admin Assessment Detail page component | New file e.g. `frontend/src/pages/AdminAssessmentDetail.jsx`. Fetch `GET /api/assessment/{id}`. Show: (1) Back link to `/admin`, (2) Read-only profile (all pillars in tabs or accordion), (3) Action buttons: Run research, Generate report, Edit report, Download. |
| 3.3 | Profile read-only view | Reuse profile field structure (pillars) but with `disabled` or read-only rendering; or simple key-value list by pillar. No submit button. |

**Files:** `frontend/src/App.jsx`, new `frontend/src/pages/AdminAssessmentDetail.jsx`.

---

### Step 4 – Frontend: Run research and generate report (Admin detail)

| # | Task | Details |
|---|------|---------|
| 4.1 | "Run research" button | On click: `POST /api/assessment/{id}/research`. Disable button while loading. On success: refetch assessment (or set local state from response); show approach document in a section below. On error: show message. Optional: polling if we later make research async. |
| 4.2 | "Generate report" button | Enabled when `approach_document` exists. On click: `POST /api/assessment/{id}/summarize`. On success: refetch; show report in edit/preview area. On error: show message. |
| 4.3 | Show approach document and report | After research: display approach document (scrollable). After summarize: display report in an editable text area (for Step 5). |

**Files:** `frontend/src/pages/AdminAssessmentDetail.jsx`.

---

### Step 5 – Frontend: Edit report and save

| # | Task | Details |
|---|------|---------|
| 5.1 | Report edit area | Textarea or simple markdown editor bound to report text. Load from `assessment.report` when present. |
| 5.2 | "Save edits" button | On click: `PUT /api/assessment/{id}/report` with body `{ "report": "<current text>" }`. On success: show brief confirmation; optionally refetch. |

**Files:** `frontend/src/pages/AdminAssessmentDetail.jsx`, backend already added in Step 1.

---

### Step 6 – Frontend: Download report

| # | Task | Details |
|---|------|---------|
| 6.1 | "Download DOCX" button | On click: open `GET /api/assessment/{id}/report?format=docx` in new tab or fetch and trigger download (blob). Use suggested filename e.g. `AssessmentReport-{app_name}-{id}.docx`. |
| 6.2 | Handle no report | If report is empty, disable Download or show message "Generate report first." |

**Files:** `frontend/src/pages/AdminAssessmentDetail.jsx`, backend Step 1.

---

### Step 7 – Admin list: link to detail and summary cards

| # | Task | Details |
|---|------|---------|
| 7.1 | Change "View" to "Open" and target | Link to `/admin/assessment/:id` instead of `/assessment/:id` so Admins see the Admin detail page, not the Application User wizard. |
| 7.2 | Add "Download" action on list row | When status is `done`, show a "Download" link/button that goes to `GET /api/assessment/{id}/report?format=docx` (or opens in new tab). Optional: do it from list for quick download without opening detail. |
| 7.3 | Summary cards | Add or rename one card to "New (submitted)" using new `submitted` count from API. Optionally rename "Completed" to "Report done" and keep "In progress" (draft, researching, summarizing, research_done). |
| 7.4 | Status badge | Ensure `submitted` and `research_done` have distinct labels/colors in Admin list (already have statusBadge; add `submitted`, `research_done` if missing). |

**Files:** `frontend/src/pages/Admin.jsx`, backend Step 2 for `submitted` count.

---

### Step 8 – Polling and loading states

| # | Task | Details |
|---|------|---------|
| 8.1 | Research/summarize are synchronous | Current API runs research and summarize synchronously; response returns when done. So no polling required unless we change to async. If we keep sync: disable buttons and show "Running…" until response. |
| 8.2 | Error display | If research or summarize returns 4xx/5xx, show error message and do not clear approach/report. Allow retry. |

**Files:** `AdminAssessmentDetail.jsx`.

---

### Step 9 – Tests and docs

| # | Task | Details |
|---|------|---------|
| 9.1 | API tests | Add tests for `PUT /assessment/{id}/report` (update report body), `GET /assessment/{id}/report` (JSON and DOCX). |
| 9.2 | Update docs | In [ADMIN_COMMAND_CENTER_DESIGN.md](./ADMIN_COMMAND_CENTER_DESIGN.md) or [MIGRATION_REQUEST_FLOW.md](./MIGRATION_REQUEST_FLOW.md), note Phase 2 implemented: Admin detail, research, report, edit, download. Optionally update [CODE_REVIEW_GUIDE.md](./CODE_REVIEW_GUIDE.md) for Admin flow. |

**Files:** `tests/test_assessment_api.py`, `docs/` as needed.

---

## 4. Order of implementation (recommended)

1. **Backend:** Step 1 (PUT report, GET report, DOCX helper) and Step 2 (summary `submitted`).
2. **Frontend:** Step 3 (new route + Admin detail page shell with profile read-only and buttons).
3. **Frontend:** Step 4 (Run research, Generate report, display approach + report).
4. **Frontend:** Step 5 (Edit report, Save edits) and Step 6 (Download).
5. **Frontend:** Step 7 (Admin list: Open → admin detail, Download on row, summary cards, status badges).
6. **Polish:** Step 8 (loading/error states).
7. **Tests & docs:** Step 9.

---

## 5. Checklist summary

- [ ] **1.1** `PUT /api/assessment/{id}/report` implemented
- [ ] **1.2** `GET /api/assessment/{id}/report` (JSON + DOCX) implemented
- [ ] **1.3** DOCX generation helper (markdown/text → DOCX)
- [ ] **2.1** Summary includes `submitted` count
- [ ] **3.1** Route `/admin/assessment/:id` added
- [ ] **3.2** Admin Assessment Detail page created
- [ ] **3.3** Profile read-only view on detail page
- [ ] **4.1** Run research button and integration
- [ ] **4.2** Generate report button and integration
- [ ] **4.3** Display approach document and report
- [ ] **5.1** Report edit area (textarea)
- [ ] **5.2** Save edits → PUT report
- [ ] **6.1** Download DOCX button
- [ ] **6.2** Handle empty report
- [ ] **7.1** Admin list "Open" → `/admin/assessment/:id`
- [ ] **7.2** Download from list (when done)
- [ ] **7.3** Summary card "New (submitted)"
- [ ] **7.4** Status badges for submitted, research_done
- [ ] **8.1** Loading states for research/summarize
- [ ] **8.2** Error display and retry
- [ ] **9.1** Tests for PUT/GET report
- [ ] **9.2** Docs updated

---

## 6. Design references (quick links)

- Admin flow: [MIGRATION_REQUEST_FLOW.md §3](./MIGRATION_REQUEST_FLOW.md#3-admin-flow)
- Admin API: [ADMIN_COMMAND_CENTER_DESIGN.md §6](./ADMIN_COMMAND_CENTER_DESIGN.md#6-api-additions)
- Wireframes: [WIREFRAMES.html §4–6](./WIREFRAMES.html) (Admin list, Open submission, Research & Report)
