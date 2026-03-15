# Plan: Reorganize docs, rebrand to Cloud Migration Command Center, CI, and Render deploy

**Purpose:** Clean doc structure, consistent project name (Cloud Migration Command Center) with modules, then CI + Render deployment and push to a new repository.  
**Status:** Draft for your review and sign-off. Do not execute until you approve.

---

## Part A: New documentation structure under `docs/`

Current state: many files in a flat `docs/` (40+ items). Proposed structure:

```
docs/
├── README.md                          # Master index: what this project is, link to all sections
├── index.html                         # GitHub Pages landing (keep; update title/links)
│
├── Architecture/                      # System and module architecture
│   ├── README.md                     # Index for this section
│   ├── ARCHITECTURE_DESIGN.md        # Main architecture (current ARCHITECTURE_DESIGN.md)
│   ├── ARCHITECTURE_DESIGN.html      # HTML version
│   ├── DECISION_MATRIX.md
│   ├── DECISION_MATRIX.html
│   ├── TARGET_ARCHITECTURE_DIAGRAM_DESIGN.md
│   ├── DATAFLOW_LLM.md
│   └── TOOL_GATEWAY_DESIGN.md
│
├── Wireframes/                        # UI wireframes (HTML + key design)
│   ├── README.md                     # Index: list wireframes and what they cover
│   ├── WIREFRAMES.html               # Main app wireframes
│   ├── ASSESSMENT_DESIGN.html
│   ├── DIAGNOSTICS_WIREFRAMES.html
│   ├── ADMIN_COMMAND_CENTER_DESIGN.md
│   └── ADMIN_COMMAND_CENTER_DESIGN.html
│
├── Modules/                            # Per-module design (Assessment, KB, Diagnostics)
│   ├── README.md                     # Index: list modules and their docs
│   ├── ASSESSMENT_MODULE_DESIGN.md
│   ├── ASSESSMENT_PROFILE_DESIGN.md
│   ├── ASSESSMENT_PROFILE_PILLARS.md
│   ├── PROFILE_VALIDATION.md
│   ├── MIGRATION_REQUEST_FLOW.md
│   ├── RESEARCH_FLOW_BLUEPRINT.md
│   └── DIAGNOSTICS_DESIGN.md
│
├── Setup-and-Reference/                # One-time setup, env, config, how-to
│   ├── README.md                     # Index
│   ├── ONE_TIME_SETUP.md
│   ├── ENV_REFERENCE.md
│   ├── CONFIG_AND_ENV.md
│   ├── INTERFACE_TESTS.md
│   ├── SQLITE_GUIDE.md
│   ├── CODE_REVIEW_GUIDE.md
│   ├── PYDANTIC_MODELS.md
│   ├── TOOL_EXTENSION_GUIDE.md
│   └── MANIFEST.md
│
├── Deployment/                         # Deploy and run
│   ├── README.md                     # Index: deployment options, CI/CD
│   ├── DEPLOYMENT.md
│   ├── DEPLOY_RENDER.md
│   ├── CICD_PIPELINE.md
│   └── HANDOFF_DEPLOY_RENDER.md
│
└── Project/                             # Meta: narrative, plans, checklist
    ├── README.md
    ├── AI_ASSISTED_DEVELOPMENT_NARRATIVE.md
    ├── DESIGN_REVIEW_CHECKLIST.md
    ├── PHASE2_IMPLEMENTATION_PLAN.md
    ├── REPORT_TRANSPARENCY_AND_DIAGRAM_PLAN.md
    ├── RECOMMENDATIONS_MIXED_DOCUMENTS.md
    └── RUN_STEPS.md
```

**Actions:**

- Create subdirs: `Architecture/`, `Wireframes/`, `Modules/`, `Setup-and-Reference/`, `Deployment/`, `Project/`.
- Move/copy each listed file into the right folder (move = update all in-repo links; copy = keep originals and duplicate—recommend **move** and then fix links).
- Add a short `README.md` in each subdir describing the section and listing the files (with one-line descriptions).
- Update **docs/README.md** at root to be the master index: project name, one-paragraph description, then sections with links (e.g. “Architecture”, “Wireframes”, “Modules”, “Setup & reference”, “Deployment”, “Project narrative”).
- Fix **internal doc links** in every moved file (e.g. `[DEPLOYMENT](./DEPLOYMENT.md)` → `[DEPLOYMENT](../Deployment/DEPLOYMENT.md)` or relative from new location). Also fix links from root README, ONE_TIME_SETUP, etc. to point into the new paths.
- **docs/index.html**: Update any “Repository” or doc links to use new paths (e.g. `docs/Architecture/`, `docs/Setup-and-Reference/ONE_TIME_SETUP.md`).

**Optional cleanup:** Remove or archive obsolete/duplicate docs (e.g. PHASE2_IMPLEMENTATION_PLAN if fully done, RUN_STEPS if superseded). I can list candidates in a follow-up; for this plan we only reorganize and fix links.

---

## Part B: Project rebrand – “Cloud Migration Command Center”

**Project name:** **Cloud Migration Command Center** (CMCC).  
**Positioning:** Pinecone is one implementation detail (Knowledge Base module); the product name is Cloud Migration Command Center.

### B.1 Where to change “Pinecone Semantic Search” / old title

| Location | Current | New |
|----------|--------|-----|
| **Root README.md** | Title: `# Pinecone Semantic Search (Python)` | `# Cloud Migration Command Center` |
| **Root README.md** | First paragraph | Short description: “Cloud Migration Command Center – modules: Knowledge Base (KB), Assessment, Admin & Diagnostics. KB uses semantic search (e.g. Pinecone).” Keep Pinecone only as KB implementation detail. |
| **backend/main.py** | `title="Center of Excellence – Knowledge Base API"` | `title="Cloud Migration Command Center – API"` (or keep CoE in description only; your choice) |
| **frontend index.html** | `<title>Center of Excellence – Migration CoE</title>` | `<title>Cloud Migration Command Center</title>` |
| **frontend package.json** | `"name": "coe-frontend"` | `"name": "cloud-migration-command-center"` or keep `coe-frontend` (internal only) |
| **docs/index.html** | Already “Cloud Migration Command Center – AI-Powered CoE” | Keep; optionally shorten to “Cloud Migration Command Center” |
| **Other docs** | Any “pinecone-semantic-search” as project name | “Cloud Migration Command Center” or “this project” |
| **Path references** | e.g. `cd pinecone-semantic-search` | `cd cloud-migration-command-center` (or “project root”) |

### B.2 Define “modules” in one place

Add a **Modules** subsection in root **README.md** (and optionally in **docs/README.md**):

- **Knowledge Base (KB)** – Semantic search over migration docs; indexing and search (Pinecone used here).
- **Assessment** – Migration assessment flow: profile → validate → submit (app user); research → report → quality check (admin).
- **Admin & Diagnostics** – Admin command center: assessments list, KB config, Diagnostics (LLM/Tavily/Pinecone usage, thresholds, request log).
- **Planning** (placeholder) – Future: runbooks, checklists.
- **Execution / Handover** (placeholder) – Future: post-migration artifacts.

No code renames (e.g. repo folder can stay `pinecone-semantic-search` until you rename the repo); only user-facing titles and docs.

---

## Part C: CI (already in place)

- **.github/workflows/ci.yml** already runs backend tests (`pytest tests/ -m "not external"`) and frontend build.
- **Action:** Ensure any doc or path references in the repo that CI might use (e.g. in README or scripts) are correct after the doc move. No change to CI logic unless you want to add a “link check” or “build docs” step later.

---

## Part D: Render deployment

- Follow **docs/DEPLOY_RENDER.md** (or **docs/Deployment/DEPLOY_RENDER.md** after move): create Web Service, Docker, env vars (Pinecone, OpenAI, optional Tavily/LangSmith), persistent disk at `/app/data`, health check `/api/health`.
- **Action:** After doc reorganization, update **DEPLOY_RENDER.md** path in any “see also” links (e.g. in README, docs/README.md). Then perform the Render deploy steps once.

---

## Part E: Push to a new repository

Interpretation: “push this as branch to a new repository” = have this codebase (with reorganized docs and rebrand) available in a **new Git remote** (new repo).

**Option 1 – New repo from existing (recommended)**  
1. Create a **new repository** on GitHub (e.g. `cloud-migration-command-center`).  
2. In the **current** repo (current folder): add the new repo as a second remote, e.g. `git remote add newrepo https://github.com/<org>/cloud-migration-command-center.git`.  
3. Push the branch you want (e.g. `main` or `release/docs-reorg`) to the new remote: `git push newrepo main`.  
4. All history is in the new repo; you can later make it the primary remote and archive the old repo.

**Option 2 – New branch on current repo, then new repo**  
1. Create a branch, e.g. `feature/docs-reorg-rebrand`.  
2. Do all changes (docs reorg + rebrand) on that branch.  
3. Create the new repo (empty), add it as remote, push this branch as `main`: `git remote add newrepo <url> && git push newrepo feature/docs-reorg-rebrand:main`.

**Action:** You choose Option 1 or 2. Then we execute: add remote, push chosen branch to new repo. No deletion of the current repo or history.

---

## Part F: Order of execution (after your sign-off)

1. **Reorganize docs** (Part A): create dirs, move files, add READMEs, fix all internal and root links, update docs/index.html links.
2. **Rebrand** (Part B): update root README, backend title, frontend title, package name (if desired), docs that say “pinecone-semantic-search” as project name; add Modules section.
3. **CI**: Quick sanity check (run `pytest tests/ -m "not external"` and frontend build); fix any broken paths if needed.
4. **Render**: Deploy per DEPLOY_RENDER (using new doc paths); set env vars and disk.
5. **New repo**: Add new remote, push the branch you want to the new repository.

---

## Summary checklist for your sign-off

- [ ] **Part A** – Agree with the folder structure (Architecture, Wireframes, Modules, Setup-and-Reference, Deployment, Project) and the file mapping. Any file you want in a different folder?
- [ ] **Part B** – Agree with “Cloud Migration Command Center” as project name and the modules list (KB, Assessment, Admin & Diagnostics, Planning, Execution). Any title/name change you don’t want?
- [ ] **Part C** – CI: keep as-is and only fix links, or add a step?
- [ ] **Part D** – Render: proceed with current DEPLOY_RENDER steps after doc move?
- [ ] **Part E** – Confirm Option 1 (new repo + push current/main to it) or Option 2 (branch → push to new repo as main). Confirm new repo name (e.g. `cloud-migration-command-center`).
- [ ] **Part F** – Order of execution (1 → 2 → 3 → 4 → 5) is acceptable.

Once you confirm or adjust the above, the next step is to perform the plan (reorg, rebrand, link fixes, CI check, Render, push to new repo) accordingly.
