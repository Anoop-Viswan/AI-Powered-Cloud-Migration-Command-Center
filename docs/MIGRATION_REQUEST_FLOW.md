# Migration Request Flow – Two-Role Design

**Status:** Design for review (pivot from single-user flow)  
**Purpose:** Define Application User vs Admin workflows. Application users initiate requests and provide app data; Admins run research, generate and edit reports, and download.

---

## 1. Roles

| Role | Who | Goal |
|------|-----|------|
| **Application User** | Business/app owners, project leads | Initiate a migration request and provide all application-related information. No access to research or report generation. |
| **Admin** | CoE admins, migration specialists | Review submitted requests, run research (KB + optional manual input), generate reports, edit/enhance reports, and download. |

---

## 2. Application User Flow

Application users **only**:

1. **Start a migration request** – Create a new assessment (request).
2. **Fill the application profile** – All seven pillars (Overview, Architecture, Data, BC & DR, Cost, Security, Project). Per-section validation; mandatory fields and sanity checks as defined in [PROFILE_VALIDATION.md](./PROFILE_VALIDATION.md).
3. **Pre-submit analysis** – On “Submit for assessment”, run the same validation and content checks (reasonableness, placeholder detection). Show findings; user confirms or edits.
4. **Submit for assessment** – On confirm:
   - Store the profile (status: **submitted**).
   - **Do not** run research or report.
   - Send a **notification to Admins** (e.g. in-app list of new submissions, optional email/webhook later).
5. **Confirmation screen** – “Your migration request has been submitted. Admins will review and produce an assessment report. You can check back later or we will notify you.”

Application users **do not** see Research or Report steps. They never trigger research or report generation.

---

## 3. Admin Flow

Admins:

1. **View submissions** – In the Admin dashboard (Assessments tab), see all migration requests with status: **submitted**, **researching**, **research_done**, **report_done**, **error**. Filter/list by status. New submissions are highlighted (e.g. “New” badge, or “Notify admins” counter).
2. **Open a submission** – View full application profile (all pillars), validation status, submitted-at time. Option to add **manual notes or guidance** (stored with the assessment) before or during research.
3. **Run research** – Admin clicks “Run research”. System queries KB (and optional web search), produces approach document. Admin can **review previous KB**, add manual input or guidance, then re-run or proceed.
4. **Generate report** – Admin clicks “Generate report”. Summarizer produces the assessment report from profile + approach doc.
5. **Edit and enhance report** – Admin can **edit the report** in-place (rich text or markdown). Changes are saved. Option to re-run summarizer for a section or accept manual edits only.
6. **Download** – Admin downloads the final report (DOCX/MD). Option to mark assessment as “delivered” or “complete” for tracking.

Admins also retain: **Knowledge Base** tab (config, seed, usage), and **Diagnostics** (if present) for system/agent metrics.

---

## 4. Data and Storage

- **Assessments** are stored with status lifecycle: `draft` → `submitted` → `researching` → `research_done` → `report_done` (or `error` at any stage).
- **Application user** can only create and update profile and **submit**; status moves from `draft` to `submitted`.
- **Admin** can change status by running research (→ `research_done`) and summarize (→ `report_done`). Admin-only endpoints: run research, generate report, update report (edit), download.
- **Notifications**: For “notify Admins”, minimum implementation: new row in assessments with `submitted` status visible on Admin list. Optional: in-app badge/count of unhandled submissions, or future email/webhook.

---

## 5. API Implications

| Actor | Endpoints |
|-------|-----------|
| **Application User** | `POST /assessment/start`, `PUT /assessment/{id}/profile`, `GET /assessment/{id}/validate`, `POST /assessment/{id}/submit` (new). No research or summarize. |
| **Admin** | All of the above plus: `GET /assessments` (list, filter by status), `GET /assessment/{id}` (full detail), `POST /assessment/{id}/research`, `POST /assessment/{id}/summarize`, `PUT /assessment/{id}/report` (edit report), `GET /assessment/{id}/report` (download). |

Access control can be URL-based (e.g. `/admin` is admin-only) or role-based later.

---

## 6. UI Implications

| Screen | Application User | Admin |
|--------|------------------|--------|
| **Assessment (wizard)** | Steps: 1. Profile (all pillars) → 2. Validate & Submit → 3. Confirmation. No Research or Report step. | Can open any assessment (read-only profile) and see Admin actions: Run research, Generate report, Edit report, Download. |
| **Admin – Assessments tab** | Not visible (or no access). | List of all assessments; status; “New” for submitted; Open → detail view with Research / Report / Edit / Download. |
| **Admin – Knowledge Base tab** | Not visible. | Unchanged: config, seed, usage. |

---

## 7. Summary

- **Application User:** Initiate migration request → fill profile → validate → submit → confirmation. No research or report.
- **Admin:** See submitted requests → open → run research (with optional KB check and manual input) → generate report → edit/enhance report → download.
- Storage and notifications: submitted requests stored with status `submitted`; admins see them in the dashboard (and optionally get notified).

Once this design is approved, implementation will follow: backend (submit endpoint, status lifecycle, admin-only research/summarize), frontend (Application User flow: submit + confirmation; Admin flow: list, open, research, report, edit, download), and wireframes/docs aligned as above.
