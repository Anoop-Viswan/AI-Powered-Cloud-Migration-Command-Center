# Assessment Profile – Design Document

**Status:** Design for review  
**Scope:** Profile step for **Application Users** – they fill the profile and **submit for assessment**; Research and Report are **Admin-only**. See [Migration Request Flow](./MIGRATION_REQUEST_FLOW.md).  
**Do not implement until approved.**

---

## 1. Purpose

The profile step collects comprehensive application information needed for a **real migration project**. Instead of a simple source/target form, we use **seven architecture pillars** organized as tabs or cards. This ensures we capture the data PMs, architects, and migration teams actually need.

---

## 2. Design Principles

- **Pillar-based:** Group fields by domain (Overview, Architecture, Data, BC/DR, Cost, Security, Project)
- **Guided flow:** Application users move section-by-section; **per-section validation** blocks advancing until the current section is valid; **"Submit for assessment"** runs full validation and submits the request (no research or report for this role).
- **Required by pillar:** Overview (app name, business purpose, users, priority, RTO, RPO); Architecture (tech stack, envs, description or diagram); Data (DB migration Yes/No; if Yes then data volume, DB types, current DB description); BC&DR (all four); Security (auth, encryption at rest/transit). Cost and Project optional.
- **Real-world alignment:** Fields mirror actual migration intake forms and assessment checklists

---

## 3. Pillar Structure

### Tab 1: General Overview

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Application name | Text | **Yes** | |
| Business purpose | Textarea | **Yes** | At least brief description (min 3 chars) |
| Description | Textarea | No | Brief description |
| User count (estimate) | Text | **Yes** | e.g. 1000, 10K-50K; hints if empty |
| Priority | Select | **Yes** | Critical / High / Medium / Low |
| RTO | Text | **Yes** | Recovery Time Objective; hint: critical → 1h, high → 4h |
| RPO | Text | **Yes** | Recovery Point Objective; hint: critical → 1h or less |
| Compliance requirements | Text (comma-separated) | No | e.g. PCI, HIPAA, SOC2 |
| Known risks | Textarea | No | |
| Constraints | Textarea | No | |
| Additional notes | Textarea | No | |

---

### Tab 2: Architecture

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Tech stack | Text (comma-separated) | **Yes** | At least one technology |
| Current environment | Select | **Yes** | On-prem / VM / Cloud (legacy) / Other |
| Target environment | Select | **Yes** | Azure / AWS / GCP / Other |
| Current state architecture description | Textarea | **One of description or diagram** | Describe current architecture |
| Current state diagram | File upload | **One of description or diagram** | PNG, JPG, WEBP (max 10 MB) |
| Future state architecture description | Textarea | No | Describe target if known; hint if empty |
| Future state diagram | File upload | No | PNG, JPG, WEBP (max 10 MB) |

**UX note:** Either current-state description or current-state diagram is required. Target/future state is encouraged; hint shown if missing.

---

### Tab 3: Data Management

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| **Contains database migration?** | Select (Yes/No) | **Yes** | Mandatory first question |
| Total data volume | Text | **Yes if DB migration = Yes** | e.g. 500 GB, 2 TB |
| Database types | Text (comma-separated) | **Yes if DB migration = Yes** | e.g. Oracle, SQL Server, PostgreSQL |
| Current databases description | Textarea | **Yes if DB migration = Yes** | DBs, sizes, versions |
| Target databases | Textarea | No | If known |
| Data retention requirements | Text | No | e.g. 7 years for compliance |
| **Data ingestion** | Text | No | How data enters: batch, real-time, streaming, APIs, file drops |
| **Ingress** | Textarea | No | Sources, formats, volume – e.g. API from OrderSys, Kafka 10K msg/day |
| **Egress** | Textarea | No | Destinations, formats – e.g. data warehouse, reports, 3rd party APIs |
| **ETL pipelines** | Textarea | No | Tools, schedules – e.g. SSIS daily, Informatica hourly |
| Data migration notes | Textarea | No | Special considerations |

---

### Tab 4: Business Continuity & DR

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Current DR strategy | Textarea | **Yes** | e.g. Backup to tape, no replication |
| Backup frequency | Text | **Yes** | e.g. daily, weekly |
| Failover approach | Text | **Yes** | e.g. Manual failover, cold standby |
| DR testing frequency | Text | **Yes** | e.g. quarterly |
| BC/DR additional notes | Textarea | No | |

---

### Tab 5: Cost

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Current annual cost | Text | No | Infra, ops – e.g. $50K/year |
| Migration budget | Text | No | e.g. $100K |
| Cost constraints | Textarea | No | |
| Licensing considerations | Textarea | No | |

---

### Tab 6: Security

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Authentication type | Text | **Yes** | e.g. SAML, OAuth, AD, LDAP |
| Encryption at rest | Text | **Yes** | e.g. AES-256, TDE |
| Encryption in transit | Text | **Yes** | e.g. TLS 1.2 |
| PII handling | Textarea | No | How PII is stored, masked |
| Compliance frameworks | Text (comma-separated) | No | e.g. SOC2, GDPR, HIPAA |

---

### Tab 7: Project & Timeline

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Project manager / owner | Text | No | Name or team |
| Timeline expectation | Text | No | e.g. 6 months |
| Team size | Text | No | e.g. 3-5 |
| Dependencies | Text (comma-separated) | No | Other apps, databases |
| Integrations | Text (comma-separated) | No | e.g. SAP, Salesforce |
| Preferred go-live window | Text | No | e.g. Q2 2025 |

---

## 4. UI Layout

- **Instruction:** "Please fill in all sections before proceeding to Research." (shown at top of profile step)
- **Tab bar** at top: Overview | Architecture | Data | BC & DR | Cost | Security | Project
- **Active tab** highlighted (e.g. teal background)
- **Form content** below tabs; one pillar visible at a time
- **Navigation buttons:**
  - **Sections 1–6:** "Continue to [next section]" (e.g. "Continue to Architecture", "Continue to Data", …)
  - **Section 7 (Project):** **"Submit for assessment"** (runs full validation, then submits; Application User flow ends here with confirmation – no Research/Report for this role)
- **Progress indicator (Application User):** Step 1 (Profile) → Validate & Submit → Confirmation. Research and Report are **Admin-only**.

---

## 5. Validation

- **Per-section:** When user clicks "Continue to [next section]", only the current pillar is validated; if invalid, errors and hints are shown and the user cannot advance.
- **Full validation:** When user clicks **"Submit for assessment"**, all required pillars are validated (Overview, Architecture, Data, BC&DR, Security). On success, the request is stored and Admins are notified; no research or report is run for Application Users.
- **Required by pillar:** See tables above (Overview: app name, business purpose, users, priority, RTO, RPO; Architecture: tech stack, envs, description or diagram; Data: DB migration answer, and if Yes then data volume, DB types, current DB description; BC&DR: all four; Security: auth, encryption at rest/transit). Cost and Project optional.
- **Sanity checks:** Data volume >100 PB, user count >10B, cost >$10B → warnings only. RTO/RPO and user count placeholder checks (e.g. "n/a", "x") → warnings.
- **Optional LLM check:** Set `PROFILE_VALIDATION_USE_LLM=yes` for extra completeness validation.
- **File upload:** PNG, JPG, WEBP; max 10 MB per file.
- **Comma-separated fields:** Trim whitespace; empty entries ignored.

---

## 6. Downstream Use

- **Application User:** Submits validated profile; request is stored with status `submitted`; Admins are notified. No Research or Report in this flow.
- **Admin:** Opens submitted request; **Research Agent** uses profile (all pillars) to build KB search query and LLM context; **Summarizer Agent** produces report; Admin can edit/enhance report and download. See [Migration Request Flow](./MIGRATION_REQUEST_FLOW.md).

---

## 7. Implementation status

- Per-section validation and required fields as above are implemented. Wireframes and [PROFILE_VALIDATION.md](./PROFILE_VALIDATION.md) are aligned with the app.

---

*Design document – aligned with current implementation.*
