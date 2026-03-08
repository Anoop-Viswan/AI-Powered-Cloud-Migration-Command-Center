# Code Review Guide – Phase 1 (Application User Flow)

Use this order to review the codebase logically: **user entry → API → business logic → data → UI → tests**.

---

## 1. Start: User journey and entry points

**Goal:** See how a user hits the app and what routes exist.

| Order | File | What to look at |
|-------|------|------------------|
| 1 | `frontend/src/App.jsx` | Routes: `/`, `/assessment`, `/assessment/:id`, `/chat`, `/admin`. Assessment is the Phase 1 flow. |
| 2 | `frontend/src/pages/Home.jsx` | Landing page; link to "Assessment" (migration request). |

**Check:** Click path from Home → Assessment makes sense; no dead links.

---

## 2. Backend API: what the frontend calls

**Goal:** See the HTTP contract and request flow.

| Order | File | What to look at |
|-------|------|------------------|
| 3 | `backend/main.py` | App mount: `/api`; which routers are included (assessment, chat, admin). |
| 4 | `backend/routers/assessment.py` | **Main API surface.** Endpoints in order: `POST /assessment/start` → `PUT /assessment/{id}/profile` → `GET /assessment/{id}/validate` → `POST /assessment/{id}/submit` (Phase 1 stop) and later `POST .../research`, `POST .../summarize`. Upload diagram, get assessment, get diagram. |

**Check:** Submit only sets status; no research/summarize called. Validation and profile save are clear.

---

## 3. Data and validation (backend)

**Goal:** Understand profile shape, validation rules, and persistence.

| Order | File | What to look at |
|-------|------|------------------|
| 5 | `backend/services/assessment/models.py` | `ApplicationProfile`: all pillars (overview, architecture, data, BC/DR, cost, security, project). `AssessmentState`: id, profile, approach_document, report, **status** (includes `"submitted"`). |
| 6 | `backend/services/assessment/store.py` | SQLite: create, get, update_profile, update_approach, update_report, **update_status** (used for `submitted`). list_all, get_summary for admin. |
| 7 | `backend/services/assessment/profile_validator.py` | `validate_profile_for_research`: required fields per pillar, sanity (RTO/RPO, data volume, user count), optional LLM completeness, then **content validator**. Returns valid, errors, warnings, suggestions, findings. |
| 8 | `backend/services/assessment/profile_content_validator.py` | Placeholder/nonsense checks (rules + optional LLM). Field map and expected-value guidelines for LLM. |

**Check:** Required fields match design; submit path only validates and sets status.

---

## 4. LLM and agents (used after submit, by Admin later)

**Goal:** See where LangChain/LangSmith and orchestration live; confirm they are not in the Application User submit path.

| Order | File | What to look at |
|-------|------|------------------|
| 9 | `backend/services/llm_provider.py` | `get_llm()`: OpenAI / Anthropic / Azure from env. Single place for all LLM usage. |
| 10 | `backend/services/assessment/research_agent.py` | KB search + `get_llm()`, messages, `invoke` → approach document. **Not called on submit.** |
| 11 | `backend/services/assessment/summarizer_agent.py` | Profile + approach → `get_llm()`, invoke → report. **Not called on submit.** |
| 12 | `backend/services/assessment/graph.py` | LangGraph: Research → Summarize. **Not used by API**; API calls research/summarize step-by-step. |

**Check:** Submit endpoint does not import or call research/summarize/graph.

---

## 5. Frontend: Assessment flow (Phase 1)

**Goal:** Follow the UI from profile to submit to confirmation.

| Order | File | What to look at |
|-------|------|------------------|
| 13 | `frontend/src/pages/Assessment.jsx` | **Single file for the whole flow.** Suggested order inside the file: (1) State and constants (profile, step, status, validation, analysis). (2) Effects: load assessment, sync route id, **fetch validate when step 2 and not submitted**. (3) Handlers: **handleSaveProfile** (validate full → PUT profile → setStep(2)), **handleSubmitClick** (analyze → validate API → findings or **submitRequest**), **submitRequest** (POST submit → set status submitted), **handleConfirmAndSubmit**. (4) Steps: only **Profile** and **Submit** (no Research/Report). (5) Step 1: form, pillars, **Submit for assessment** button. (6) Step 2: if **status === 'submitted'** → confirmation block; else → pre-submit check, review findings, **Submit for assessment** / **I've reviewed — Submit for assessment**, Edit profile. |

**Check:** No research or report step; only two steps; confirmation shows only when status is submitted; POST submit is used and status updated.

---

## 6. Admin (list only; no run research yet)

**Goal:** Confirm admin only lists assessments and does not run research in Phase 1.

| Order | File | What to look at |
|-------|------|------------------|
| 14 | `backend/routers/admin.py` | `GET /assessments`, `GET /assessments/summary`. List and counts only. |
| 15 | `frontend/src/pages/Admin.jsx` | Tabs: Assessments, Knowledge Base. Table of assessments (id, app name, status, etc.). No “Run research” or “Generate report” yet. |

**Check:** Admin is read-only for assessments; no research/summarize from UI.

---

## 7. Tests and docs (sanity check)

**Goal:** Ensure tests cover submit and that docs reflect the flow.

| Order | File | What to look at |
|-------|------|------------------|
| 16 | `tests/test_assessment_api.py` | `test_submit_requires_profile`, `test_submit_rejects_invalid_profile`, `test_submit_success`. Other tests: profile save, validate, research, summarize (for later Admin). |
| 17 | `docs/MIGRATION_REQUEST_FLOW.md` | Two roles: Application User (profile → submit → confirmation); Admin (later: research, report, edit, download). |

**Check:** Submit tests pass; doc matches “submit only” for Application User.

---

## Quick reference: Phase 1 flow in code

```
User: Home → Assessment → fill profile → "Submit for assessment"
  → Frontend: handleSaveProfile (validate → PUT profile → setStep(2))
  → Step 2: handleSubmitClick (GET validate) → findings? review : submitRequest()
  → submitRequest(): POST /assessment/{id}/submit
  → Backend: validate → store.update_status(id, "submitted")
  → Frontend: setStatus("submitted") → show confirmation
```

---

## Checklist for reviewer

- [ ] Routes and navigation (App.jsx, Home) correct.
- [ ] Submit endpoint only validates and sets status (no research/summarize).
- [ ] `AssessmentState.status` includes `"submitted"`.
- [ ] Frontend has only two steps (Profile, Submit) and confirmation when submitted.
- [ ] Submit button and copy say “Submit for assessment”; no “Run research” in app user flow.
- [ ] Admin only lists assessments; no research/report actions yet.
- [ ] Submit tests exist and pass.
- [ ] LLM/orchestration (graph, research, summarizer) not invoked on submit.
