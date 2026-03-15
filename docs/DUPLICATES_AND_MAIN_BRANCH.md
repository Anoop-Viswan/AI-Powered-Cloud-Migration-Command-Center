# Duplicate docs (root vs subdirs) and creating `main` branch

---

## Duplicate identification logic

**“Duplicate” here does not mean “HTML vs MD.”** It means:

**Same logical document exists in two file paths** because we **copied** (did not move) during the doc reorg:

- **Location A:** `docs/<OldName>.<ext>` (root)
- **Location B:** `docs/<Subdir>/<NewName>.<ext>` (subdir)

**Identification rule:** A file in `docs/` root is a **duplicate** if we created a **copy** of it under a subdir with a new name. Same content (or intended same content), two paths. For example:

- `docs/ARCHITECTURE_DESIGN.md` and `docs/Architecture-and-Design/Architecture.md` → **duplicate** (same doc, two paths)
- `docs/ARCHITECTURE_DESIGN.html` and `docs/Architecture-and-Design/Architecture.html` → **duplicate** (same doc, two paths)
- `docs/WIREFRAMES.html` (root) vs `docs/Architecture-and-Design/Wireframes.html` (subdir) → **duplicate**

So:

- **.md and .html are not duplicates of each other** – they are two formats of the same doc (e.g. Architecture: one .md, one .html). Duplicate = **root copy vs subdir copy** for each of those.
- **HTMLs are required for project information webpages** (e.g. GitHub Pages). `docs/index.html` links to `ARCHITECTURE_DESIGN.html`; the HTMLs in root link to each other and to .md files in the same folder. If we remove root HTMLs, we must update `index.html` and all internal links to point to the subdir paths (e.g. `Architecture-and-Design/Architecture.html`), and the HTMLs in subdirs use **new** filenames (e.g. `Migration-Request-Flow.md`) so those internal links would need updating too.

**Recommendation:** **Keep all HTML files in `docs/` root** for the project webpages so existing links keep working. Treat only the **.md** files in root as candidates for removal (duplicates of the subdir .md copies). If you later want a single location for HTMLs, we can move them to subdirs and update every link in `index.html` and between HTMLs.

---

## 1. Creating an empty `main` branch (new repo)

The new repo **AI-Powered-Cloud-Migration-Command-Center** only has branch **`initial-commit`** right now. To open a PR into `main`:

### Option A – Create `main` on GitHub (simplest)

1. Open: **https://github.com/Anoop-Viswan/AI-Powered-Cloud-Migration-Command-Center**
2. If the default branch is `initial-commit`, go to **Settings → General** and under "Default branch" you may need to add `main` first.
3. **Create `main` from the repo root:**
   - Click the branch dropdown (it may say "initial-commit" or "No branches").
   - Type **`main`** and choose **"Create branch: main from this repository"** or similar.  
   **If the repo is empty except for `initial-commit`:** You can create a new branch named `main` from the first commit:
   - Go to **Code** → switch to branch **`initial-commit`**.
   - Click the branch dropdown → **"New branch"** (or "Create branch").
   - Name it **`main`**, create from `initial-commit`, then create (leave it as-is for now).
   - Go to **Settings → General → Default branch** → switch default to **`main`**.
4. Now open a **Pull request**: base **`main`**, compare **`initial-commit`**. The PR will show all commits from `initial-commit`; merge when ready.

### Option B – Create empty `main` from your machine (orphan branch)

If you want `main` to be an **empty** branch (e.g. one commit with a README) so the PR from `initial-commit` adds all code:

```bash
cd /path/to/your/clone-of-AI-Powered-Cloud-Migration-Command-Center
git fetch origin
git checkout --orphan main
git rm -rf . 2>/dev/null || true
echo "# AI-Powered Cloud Migration Command Center" > README.md
git add README.md
git commit -m "Initial empty main"
git push -u origin main
```

Then in GitHub: **Settings → General → Default branch** → set to **`main`**. After that, open a PR **from `initial-commit` into `main`** to bring in the full codebase.

---

## 2. Old duplicate files (docs root)

These files in **`docs/`** (root) have a **copy** in one of the new subdirs. They are the "old duplicates" you can remove if you want a single source of truth.

### Architecture-and-Design (copies in `docs/Architecture-and-Design/`)

| In docs/ root | Copy in subdir |
|---------------|----------------|
| `ARCHITECTURE_DESIGN.md` | `Architecture-and-Design/Architecture.md` |
| `ARCHITECTURE_DESIGN.html` | `Architecture-and-Design/Architecture.html` |
| `DECISION_MATRIX.md` | `Architecture-and-Design/Decision-Matrix.md` |
| `DECISION_MATRIX.html` | `Architecture-and-Design/Decision-Matrix.html` |
| `TARGET_ARCHITECTURE_DIAGRAM_DESIGN.md` | `Architecture-and-Design/Target-Architecture-Diagram.md` |
| `DATAFLOW_LLM.md` | `Architecture-and-Design/Dataflow-LLM.md` |
| `TOOL_GATEWAY_DESIGN.md` | `Architecture-and-Design/Tool-Gateway.md` |
| `ASSESSMENT_MODULE_DESIGN.md` | `Architecture-and-Design/Assessment-Module.md` |
| `ASSESSMENT_PROFILE_DESIGN.md` | `Architecture-and-Design/Assessment-Profile.md` |
| `PROFILE_VALIDATION.md` | `Architecture-and-Design/Profile-Validation.md` |
| `MIGRATION_REQUEST_FLOW.md` | `Architecture-and-Design/Migration-Request-Flow.md` |
| `DIAGNOSTICS_DESIGN.md` | `Architecture-and-Design/Diagnostics-Design.md` |
| `ADMIN_COMMAND_CENTER_DESIGN.md` | `Architecture-and-Design/Admin-Command-Center-Design.md` |
| `ADMIN_COMMAND_CENTER_DESIGN.html` | `Architecture-and-Design/Admin-Command-Center-Design.html` |
| `WIREFRAMES.html` | `Architecture-and-Design/Wireframes.html` |
| `ASSESSMENT_DESIGN.html` | `Architecture-and-Design/Assessment-Design.html` |
| `DIAGNOSTICS_WIREFRAMES.html` | `Architecture-and-Design/Diagnostics-Wireframes.html` |

### Setup-and-Reference (copies in `docs/Setup-and-Reference/`)

| In docs/ root | Copy in subdir |
|---------------|----------------|
| `ONE_TIME_SETUP.md` | `Setup-and-Reference/One-Time-Setup.md` |
| `ENV_REFERENCE.md` | `Setup-and-Reference/ENV-Reference.md` |
| `CONFIG_AND_ENV.md` | `Setup-and-Reference/Config-and-Env.md` |
| `INTERFACE_TESTS.md` | `Setup-and-Reference/Interface-Tests.md` |

### Deployment (copies in `docs/Deployment/`)

| In docs/ root | Copy in subdir |
|---------------|----------------|
| `DEPLOYMENT.md` | `Deployment/Deployment.md` |
| `DEPLOY_RENDER.md` | `Deployment/Deploy-Render.md` |
| `CICD_PIPELINE.md` | `Deployment/CICD-Pipeline.md` |
| `HANDOFF_DEPLOY_RENDER.md` | `Deployment/HANDOFF_Deploy-Render.md` |

### Guides (copies in `docs/Guides/`)

| In docs/ root | Copy in subdir |
|---------------|----------------|
| `SQLITE_GUIDE.md` | `Guides/SQLite-Guide.md` |
| `PYDANTIC_MODELS.md` | `Guides/Pydantic-Models.md` |
| `TOOL_EXTENSION_GUIDE.md` | `Guides/Tool-Extension-Guide.md` |
| `MANIFEST.md` | `Guides/Manifest.md` |
| `CODE_REVIEW_GUIDE.md` | `Guides/Code-Review-Guide.md` |

### Development-Iterations (copies in `docs/Development-Iterations/`)

| In docs/ root | Copy in subdir |
|---------------|----------------|
| `AI_ASSISTED_DEVELOPMENT_NARRATIVE.md` | `Development-Iterations/AI-Assisted-Development-Narrative.md` |
| `RESEARCH_FLOW_BLUEPRINT.md` | `Development-Iterations/Research-Flow-Blueprint-Original.md` |
| `DESIGN_REVIEW_CHECKLIST.md` | `Development-Iterations/Design-Review-Checklist.md` |
| `PHASE2_IMPLEMENTATION_PLAN.md` | `Development-Iterations/Phase2-Implementation-Plan.md` |
| `REPORT_TRANSPARENCY_AND_DIAGRAM_PLAN.md` | `Development-Iterations/Report-Transparency-Plan.md` |

---

## 3. Files to KEEP in docs/ root (do not remove)

| File | Reason |
|------|--------|
| **`README.md`** | Master index for the docs folder; points to all sections. |
| **`index.html`** | GitHub Pages landing page. |

---

## 4. Files only in docs/ root (no copy in subdirs yet)

These were **not** copied into the new structure. You can move them later or leave them.

| File | Suggestion |
|------|------------|
| `ASSESSMENT_PROFILE_PILLARS.md` | Move to `Architecture-and-Design/` if you want it with other assessment docs. |
| `DOCS_REORGANIZATION_PLAN.md` | Planning doc; keep in root or move to `Development-Iterations/`. |
| `FINAL_STEPS_IMPLEMENTATION.md` | Planning doc; keep or move to `Development-Iterations/`. |
| `PLAN_REORGANIZE_AND_DEPLOY.md` | Planning doc; keep or move to `Development-Iterations/`. |
| `ROOT_STRUCTURE_AND_CLEANUP.md` | Planning doc; keep or move to `Development-Iterations/`. |
| `RECOMMENDATIONS_MIXED_DOCUMENTS.md` | Could move to `Development-Iterations/` or `Guides/`. |
| `RUN_STEPS.md` | Could move to `Development-Iterations/` or remove if obsolete. |

---

## 5. What to remove (if anything)

### Option A – Remove only root .md duplicates (keep all HTMLs for webpages)

So that **project information webpages (GitHub Pages) keep working**, **do not remove any .html** from root. The HTMLs in `docs/` are what `index.html` and the design pages link to; removing them would break the site unless we change every link to the subdir paths and new filenames.

**Safe to remove:** only the **.md** files in root that have a copy in a subdir (20 files). That way the subdirs are the single source for Markdown, and the root HTMLs (and `index.html`) continue to work as today.

```
docs/ADMIN_COMMAND_CENTER_DESIGN.md
docs/AI_ASSISTED_DEVELOPMENT_NARRATIVE.md
docs/ARCHITECTURE_DESIGN.md
docs/ASSESSMENT_MODULE_DESIGN.md
docs/ASSESSMENT_PROFILE_DESIGN.md
docs/CICD_PIPELINE.md
docs/CODE_REVIEW_GUIDE.md
docs/CONFIG_AND_ENV.md
docs/DATAFLOW_LLM.md
docs/DECISION_MATRIX.md
docs/DEPLOYMENT.md
docs/DEPLOY_RENDER.md
docs/DESIGN_REVIEW_CHECKLIST.md
docs/DIAGNOSTICS_DESIGN.md
docs/ENV_REFERENCE.md
docs/HANDOFF_DEPLOY_RENDER.md
docs/INTERFACE_TESTS.md
docs/MANIFEST.md
docs/MIGRATION_REQUEST_FLOW.md
docs/ONE_TIME_SETUP.md
docs/PHASE2_IMPLEMENTATION_PLAN.md
docs/PROFILE_VALIDATION.md
docs/PYDANTIC_MODELS.md
docs/REPORT_TRANSPARENCY_AND_DIAGRAM_PLAN.md
docs/RESEARCH_FLOW_BLUEPRINT.md
docs/SQLITE_GUIDE.md
docs/TARGET_ARCHITECTURE_DIAGRAM_DESIGN.md
docs/TOOL_EXTENSION_GUIDE.md
docs/TOOL_GATEWAY_DESIGN.md
```

**Do not remove:**  
`docs/README.md`, `docs/index.html`, and **all .html files in docs/ root** (ARCHITECTURE_DESIGN.html, WIREFRAMES.html, ASSESSMENT_DESIGN.html, DECISION_MATRIX.html, ADMIN_COMMAND_CENTER_DESIGN.html, DIAGNOSTICS_WIREFRAMES.html, ADMIN_COMMAND_CENTER_DESIGN.html).

### Option B – Remove both .md and .html duplicates (full cleanup)

Only if you are ready to **update all links** in `index.html` and in every HTML to point to the subdir paths and new filenames (e.g. `Architecture-and-Design/Architecture.html`, `Architecture-and-Design/Migration-Request-Flow.md`). Then you can remove the 35 files (20 .md + 7 .html duplicates) from root. The subdir HTMLs currently link to old filenames (e.g. `MIGRATION_REQUEST_FLOW.md`); those would need to be changed to the new names (e.g. `Migration-Request-Flow.md`) so links work.

**Recommendation:** Use **Option A** (remove only root .md duplicates, keep all root HTMLs) so project webpages keep working with no link changes.

---

## 6. CI without GitHub Secrets (what to expect)

The workflow in `.github/workflows/ci.yml` runs on **push and pull_request to `main` (and `master`)**. When you open a PR from `initial-commit` → `main`, CI will run.

**Without any GitHub Secrets:**

- **Backend tests:** The job runs `pytest tests/ -m "not external"`. That **excludes** all tests marked `@pytest.mark.external` (Pinecone, LLM, LangSmith, Tavily, Mermaid.ink). So **no API keys are used**; those 5 tests are **skipped** (deselected), not run. The remaining ~76 tests (assessment API, store, agents, semantic_search, document_extractors, etc.) run as normal and **should pass**. You will **not** see failures or error messages from missing API keys in CI, because the external tests are never executed there.
- **Frontend build:** `npm ci` and `npm run build` run with no secrets; they **should pass**.

**So:** With no secrets, CI should **pass** (green). You will see something like `76 passed, 5 deselected` in the backend job and a successful frontend build.

**If you want to see the interface-check error messages (e.g. for Pinecone/LLM missing keys):**

- Run **locally** after cloning: `python scripts/verify_setup.py`. That runs all checks and prints detailed failures and setup steps when a key is missing or invalid.
- Or run in CI only when secrets exist: add a separate job that runs `pytest tests/test_interface_connectivity.py -v -m external` and set the job to run only when the needed secrets are present (e.g. `if: ${{ secrets.PINECONE_API_KEY != '' }}`), so the job is skipped when you have no secrets and run (and can fail with clear messages) when you add them later.
