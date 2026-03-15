# Plan: Report Transparency, Pillar-Based Extraction, and Target-State Diagram

**Status:** Plan for review  
**Goal:** (1) Make Tavily/LLM outputs transparent and align extraction with architecture pillars so the report is comprehensive and traceable; (2) Generate a target-state architecture diagram from profile data and include it in the assessment.

---

## Part 1: Transparency and Pillar-Based Extraction

### Current gaps

- **Tavily results** are fetched and passed to the LLM, but the user does not see the **raw list** of what was retrieved (title, URL, snippet) in a dedicated, easy-to-scan view.
- The **approach document** is one big LLM output; there is no explicit **“what was extracted and under which pillar”** with source attribution (which Tavily result or KB source led to which finding).
- The **summarizer** gets profile + approach document and writes the report in one shot; it does not consume a **structured extraction** aligned with pillars, so useful content can be diluted or missing.
- **Tavily queries** are generic (e.g. “Azure migration guide”); we do not yet ask for **pillar-specific** content (data, security, BC/DR, etc.) so the most relevant information is not requested up front.

### 1.1 Expose “What was retrieved” (Tavily + KB)

| What | How |
|------|-----|
| **Tavily results** | Already in `ResearchResult.official_docs` (title, url, snippet). Persist them with the assessment (e.g. in store or in the approach payload) and show them in the Admin assessment detail UI in a **“Retrieved official documentation”** panel: one card per result with title, link, and snippet. No extra backend contract if we already return official_docs; ensure the UI and any “research details” API surface them. |
| **KB hits** | Already in `ResearchResult.kb_hits` (file_path, score, why_match, content_preview). Show in a **“KB sources used”** panel so the user sees what the LLM had from the KB. |
| **In the approach doc** | Keep the current “Official documentation (references)” section in the approach document so the report author (and export) still see the same list with snippets. |

**Deliverables:**  
- Admin assessment detail: two panels (or tabs) — **“Retrieved official documentation”** (from Tavily) and **“KB sources used”** (from research), both populated from the research response / stored research result.  
- Ensure research flow stores and returns `official_docs` and `kb_hits` so the UI can render them even after refresh.

---

### 1.2 Pillar-based “what to extract” and extraction step

**Pillars** (from ASSESSMENT_PROFILE_DESIGN): Overview, Architecture, Data, BC/DR, Cost, Security, Project.

Define a **schema of what the report must cover per pillar** (so we know what to extract and what the LLM should prioritize):

| Pillar | What to extract / report |
|--------|---------------------------|
| **Overview** | Business purpose, priority, RTO/RPO, user scale, compliance/risks. |
| **Architecture** | Current vs target stack, migration strategy (lift-and-shift / refactor / re-platform), key components and dependencies. |
| **Data** | DB migration scope, volume, types; ingestion/egress/ETL; retention; target data services. |
| **BC/DR** | Backup, failover, RTO/RPO alignment, DR testing. |
| **Security** | Auth, encryption (rest/transit), compliance requirements, identity. |
| **Cost** | Budget hints, cost drivers, licensing. |
| **Project** | Timeline, phases, risks and mitigations. |

**New step: Extraction (between Research and Summarizer)**  
- **Input:** Profile + full KB context (hits with content_preview) + full list of Tavily results (title, url, snippet).  
- **Process:** One LLM call with a **structured prompt**: “From the following context (KB sources and official documentation), extract the most useful information **by pillar**. For each pillar, output bullet points or short paragraphs that are directly usable in the report, and **cite the source** (e.g. ‘Official 2’, ‘KB Source 1’).”  
- **Output:** Structured “findings per pillar” — e.g. a list of `{ "pillar": "Data", "findings": [ { "text": "...", "sources": ["Official 1", "KB Source 2"] } ] }`. We can ask the LLM to return JSON for this so we can store it and render it.  
- **Transparency:** In the UI, show an **“Extraction by pillar”** section: for each pillar, show the extracted bullets and the sources cited. This answers “how the LLM ranked/extracted and what it used from Tavily/KB.”  
- **Report:** The **Summarizer** then takes **profile + extraction (findings per pillar)** instead of (or in addition to) the free-form approach document. The report is written **explicitly by pillar** so nothing useful is dropped.

**Implementation options**  
- **Option A (recommended):** Add an explicit **Extraction** step (new function in research or a small “extractor” module). It runs after we have approach_document + official_docs + kb_hits; it calls the LLM once with the pillar schema and the combined context; it returns and stores “extraction” (JSON or structured model). The Summarizer receives extraction + profile and writes the report by pillar.  
- **Option B:** No separate extraction; give the Summarizer a much stricter prompt that says “structure your report by these pillars; for each section cite sources (Official N, KB Source M).” Less transparent (no separate “extraction” view) but simpler.

**Deliverables:**  
- Documented “extraction schema” (what we want per pillar).  
- Extraction step (LLM) with structured output and source attribution.  
- Persist extraction with the assessment (e.g. new field or table).  
- UI: “Extraction by pillar” panel with findings and sources.  
- Summarizer: consume extraction + profile; report sections aligned with pillars and citations.

---

### 1.3 Pillar-aware Tavily queries

Today we build a few generic queries (e.g. “Azure migration guide”, “Azure SQL migration”). To get **more relevant** content from the start:

- **Build queries per pillar or theme** (still using profile.target_environment, profile.tech_stack, etc.):
  - **Data:** e.g. “Azure data migration database best practices”, “Azure SQL migration guide”.
  - **Security:** e.g. “Azure migration security compliance”, “Azure identity encryption”.
  - **BC/DR:** e.g. “Azure disaster recovery RTO RPO backup”.
  - **Architecture:** e.g. “Azure migration architecture refactor lift-and-shift”.
- **Tag results** (optional): When we run multiple queries, we can tag each result with the query or pillar (e.g. “data”, “security”) so the Extraction step can prefer the right snippets per pillar.
- **Limit total results** so we don’t overflow context (e.g. cap total Tavily results and/or per-query results).

**Deliverables:**  
- Extend `_build_official_doc_queries` to emit **pillar- or theme-specific** queries (e.g. list of (query, include_domains, theme)).  
- Run Tavily for each (or a subset), aggregate and optionally tag by theme.  
- Pass tagged/organized results into the Extraction step so the LLM can “use Data-themed results for the Data pillar,” etc.

---

## Part 2: Target-State Architecture Diagram

### Goal

From the **collected profile** (target environment, tech stack, data, security, BC/DR, etc.), generate a **target-state architecture diagram** that includes:

- Main **components** (e.g. app tier, database, storage, network).
- **Network** (e.g. VNet, subnets, or logical boundaries).
- **Security** (e.g. firewall, identity, encryption zones).

The diagram should be **viewable in the assessment** and **includable in the report** (e.g. Architecture section and DOCX export).

### 2.1 Approach: diagram-as-code (Mermaid)

- **Why Mermaid:** Text-based, no external diagramming API; we can generate the definition from profile data and render in the browser (e.g. `mermaid.js` in the frontend) or export to image (e.g. mermaid-cli or a small Node script) for DOCX.
- **Content:** A **target-state** view only (we already have current-state description/diagram from the user). We derive target from:
  - `target_environment` (Azure / AWS / GCP / Other),
  - `tech_stack`, `database_types`, `current_architecture_description`, `future_state_architecture_description`,
  - Security (auth, encryption), BC/DR (backup, failover).

**Example (Azure):**  
- High-level: Region → Resource Group → VNet → Subnets (e.g. App, Data, DMZ).  
- Components: App Service / VM, Database (e.g. Azure SQL), Storage, Key Vault, Backup.  
- Security: Firewall, Private Endpoints, identity.  
- We can generate a **Mermaid flowchart or C4-style** diagram (containers: “Web App”, “Database”, “Storage”, “Key Vault”, etc.) with labels from the profile (e.g. app name, DB type).

### 2.2 Data model and generation

- **Target state model (in code):** A small structure, e.g.:
  - `target_platform`: Azure | AWS | GCP | Other  
  - `components`: list of { type, name, description? } (e.g. App Service, Azure SQL, Storage Account, Key Vault, Backup)  
  - `network`: high-level (e.g. “VNet with App / Data subnets”)  
  - `security`: short list (e.g. “Private endpoints”, “Managed identity”, “Encryption at rest”)  
- **Mapping:** A function **profile → target state model** using `ApplicationProfile` (target_environment, tech_stack, database_types, authentication_type, encryption_*, backup_*, etc.).  
- **Templates:** For Azure, we have a default set of components (App, DB, Storage, Key Vault, Backup); we substitute names from `application_name` and DB type from `database_types`. Similar for AWS/GCP (placeholder or simplified).  
- **Mermaid generator:** Function **target state model → Mermaid string** (flowchart or C4). Then:
  - **Backend:** Return Mermaid definition (e.g. in assessment payload or a dedicated endpoint like `GET /assessment/{id}/target-diagram` returning `{ "mermaid": "..." }`).  
  - **Frontend:** Render with `mermaid.js` in the Architecture section of the assessment/report.  
  - **DOCX export:** Optional: server-side or build-time render of Mermaid to PNG/SVG (e.g. `mmdc` or a small script) and embed that image in the DOCX report.

### 2.3 Where it appears

- **Admin assessment detail:** New section **“Target-state architecture”** with the diagram (and optional short legend from the model).  
- **Report:** In the “Target Architecture” (or “Architecture”) section, include the diagram (or its image in DOCX).  
- **No new “third party” beyond:** Mermaid (library + optional CLI for image export). No Lucidchart/Draw.io API.

### 2.4 Deliverables

- **Target state model** (Pydantic or dict) and **profile → target state** mapping.  
- **Target state → Mermaid** generator (e.g. `backend/services/assessment/target_diagram.py`).  
- **API:** Return Mermaid in assessment payload or via `GET /assessment/{id}/target-diagram`.  
- **UI:** “Target-state architecture” panel with Mermaid render (using `mermaid.js`).  
- **Report:** Include diagram in the report view; optionally embed rendered image in DOCX.

---

## Implementation order (suggested)

1. **Part 1.1** – Expose “Retrieved official documentation” and “KB sources used” in the Admin assessment UI (and persist official_docs/kb_hits if not already).  
2. **Part 1.3** – Pillar-aware Tavily queries and optional tagging.  
3. **Part 1.2** – Extraction step (schema, LLM, structured output, storage), “Extraction by pillar” UI, and Summarizer refactor to use extraction.  
4. **Part 2** – Target-state model, Mermaid generator, API, UI panel, and report/DOCX inclusion.

---

## Summary

| Workstream | Outcome |
|------------|---------|
| **Transparency** | User sees exactly what Tavily returned and what KB sources were used; user sees “Extraction by pillar” with source attribution before the report. |
| **Pillar-based extraction** | Clear schema of what to extract per pillar; one LLM extraction step that outputs structured findings with citations; report written from that so it is comprehensive and traceable. |
| **Tavily** | Queries targeted by pillar/theme so the most relevant official docs are retrieved up front. |
| **Target-state diagram** | Generated from profile (Mermaid); includes network and security; shown in assessment UI and in the report; optional image in DOCX. |

If you approve this plan, next step is to implement in the order above (or as you prefer) and wire the new extraction and diagram into the existing research/summarize/report flow and Admin UI.
