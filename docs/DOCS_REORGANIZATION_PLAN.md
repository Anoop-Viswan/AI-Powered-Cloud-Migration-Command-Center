# Documentation reorganization – final plan

**Rebrand:** Cloud Migration Command Center (approved).  
**Goal:** Clean, intuitive doc layout; root README as the main roadmap; design docs show **final state** only; guides and development-iteration narrative in dedicated areas.

---

## 1. Principles

- **Root README.md** = main entry and **roadmap** for the whole project and docs (where to look for what). New readers start here.
- **Architecture & design** = one directory, **latest and relevant only**; content reworked to describe the **final** flows/design (no “current vs new” in the main docs—that learning stays in Development Iterations).
- **Guides** = learning material for new readers (SQLite, Pinecone, Pydantic, tool extension, etc.) in one place.
- **Development Iterations** = transparency on how this project was built (steps, iterations, what was tried, what worked). Keeps the “current vs intended” and narrative in one place.

---

## 2. Target directory layout

```
<repo-root>/
├── README.md                    # ★ Main roadmap: project name, quick start, doc map (see section 3)
├── DOCUMENTATION.md             # Optional: extended doc index only; or fold into README
│
├── docs/
│   ├── index.html               # GitHub Pages landing (Cloud Migration Command Center)
│   │
│   ├── Architecture-and-Design/ # Single dir: final architecture & design only
│   │   ├── README.md            # Short index of what’s here
│   │   ├── Architecture.md      # Final system architecture (rework from ARCHITECTURE_DESIGN)
│   │   ├── Architecture.html
│   │   ├── Decision-Matrix.md
│   │   ├── Decision-Matrix.html
│   │   ├── Research-Flow.md     # ★ Final research flow only (rework from RESEARCH_FLOW_BLUEPRINT)
│   │   ├── Migration-Request-Flow.md
│   │   ├── Tool-Gateway.md
│   │   ├── Target-Architecture-Diagram.md
│   │   ├── Dataflow-LLM.md
│   │   ├── Assessment-Module.md
│   │   ├── Assessment-Profile-and-Validation.md
│   │   ├── Diagnostics-Design.md
│   │   ├── Admin-Command-Center-Design.md
│   │   ├── Admin-Command-Center-Design.html
│   │   ├── Wireframes.html      # Main app wireframes
│   │   ├── Assessment-Design.html
│   │   └── Diagnostics-Wireframes.html
│   │
│   ├── Setup-and-Reference/     # How to run and configure
│   │   ├── README.md
│   │   ├── One-Time-Setup.md
│   │   ├── ENV-Reference.md
│   │   ├── Config-and-Env.md
│   │   └── Interface-Tests.md
│   │
│   ├── Deployment/               # Deploy and CI/CD
│   │   ├── README.md
│   │   ├── Deployment.md
│   │   ├── Deploy-Render.md
│   │   └── CICD-Pipeline.md
│   │
│   ├── Guides/                  # Learning for new readers (SQLite, Pinecone, etc.)
│   │   ├── README.md            # Index: what each guide covers
│   │   ├── SQLite-Guide.md
│   │   ├── Pinecone-Guide.md    # Extract/create: KB index, seeding, usage (from README + .agents)
│   │   ├── Pydantic-Models.md
│   │   ├── Tool-Extension-Guide.md
│   │   ├── Manifest.md
│   │   └── Code-Review-Guide.md
│   │
│   └── Development-Iterations/  # How this project was built (transparency)
│       ├── README.md            # Purpose: iterations, decisions, what worked
│       ├── AI-Assisted-Development-Narrative.md
│       ├── Phase-Plans.md       # Optional: merge PHASE2, REPORT_TRANSPARENCY, etc.
│       ├── Design-Review-Checklist.md
│       └── Research-Flow-Blueprint-Original.md  # Keep “current vs new” here as learning
│       # Optional: HANDOFF_DEPLOY_RENDER, RUN_STEPS, RECOMMENDATIONS_MIXED_DOCUMENTS
```

**Naming:** Use consistent kebab-case for new filenames (e.g. `Research-Flow.md`, `One-Time-Setup.md`) so URLs and links stay readable. Existing filenames can be moved and optionally renamed in one pass.

---

## 3. Root README.md – main roadmap

**Content to include:**

1. **Title:** `# Cloud Migration Command Center`
2. **One paragraph:** What the project is (modules: KB, Assessment, Admin & Diagnostics; Pinecone as KB implementation detail).
3. **Quick start:** Clone, venv, `.env`, `verify_setup.py`, run backend + frontend (with links to `docs/Setup-and-Reference/One-Time-Setup.md`).
4. **Documentation map (where to look for what):**
   - **Architecture & design** → `docs/Architecture-and-Design/` – system design, research flow, wireframes, diagnostics.
   - **Setup & reference** → `docs/Setup-and-Reference/` – one-time setup, env, config, interface tests.
   - **Deployment** → `docs/Deployment/` – cloud deploy, Render, CI/CD.
   - **Guides** → `docs/Guides/` – SQLite, Pinecone, Pydantic, tool extension, manifest, code review.
   - **Development iterations** → `docs/Development-Iterations/` – how the project was iterated and built (AI-assisted narrative, phase plans).
5. **Modules** (short list): KB, Assessment, Admin & Diagnostics; placeholders for Planning, Execution.
6. **Optional:** Prerequisites, index creation (Pinecone), deploy links (Render, Docker). Keep concise; link to the doc dirs above for detail.

So the **final README does not** repeat “current vs new” or long design history; it points to the right places.

---

## 4. Architecture-and-Design – final state only

- **Research flow:** Turn `RESEARCH_FLOW_BLUEPRINT.md` into **`Research-Flow.md`** that describes only the **final** flow:
  - KB lookup → confidence → explainability;
  - when low confidence → official-doc research (e.g. Tavily);
  - live updates (SSE);
  - no “current state vs intended” table; just “how it works today.”
- **Other design docs:** Similarly rework or trim to “final” version (architecture, assessment module, diagnostics, admin, tool gateway). Remove historical “as-is vs to-be” from the main Architecture-and-Design dir.
- **Wireframes:** Keep as-is (they describe the final UI). Place in same directory so architecture and wireframes live together.

The **“current vs new” and learning steps** stay in **Development-Iterations** (e.g. keep original blueprint there as `Research-Flow-Blueprint-Original.md` or merge into the narrative).

---

## 5. Guides (under docs/Guides/)

- **SQLite:** Move/rename `SQLITE_GUIDE.md` → `Guides/SQLite-Guide.md`.
- **Pinecone:** Add **`Guides/Pinecone-Guide.md`** – index creation, seeding, usage, field mapping (consolidate from root README and any .agents/Pinecone content) for new readers.
- **Pydantic, Tool extension, Manifest, Code review:** Move from current locations into `Guides/` with clear names (e.g. `Pydantic-Models.md`, `Tool-Extension-Guide.md`, `Manifest.md`, `Code-Review-Guide.md`).

Each guide is “how to use / how it works” for that topic, not the iteration history.

---

## 6. Development-Iterations

- **Purpose:** Transparency on how the project was built (steps, iterations, what was tried).
- **Contents:**  
  - `AI-Assisted-Development-Narrative.md` (existing).  
  - Optional: phase plans, design checklist, report-transparency plan.  
  - Optional: original research-flow blueprint (current vs new) as a learning artifact.
- **README:** Short note that this folder is for “how we got here,” not for day-to-day usage.

---

## 7. Rebranding (unchanged)

- Project name: **Cloud Migration Command Center** everywhere user-facing.
- Root README title and intro; backend API title; frontend page title.
- Replace “Pinecone Semantic Search” as product name; keep Pinecone only as KB implementation detail.
- Path examples: “project root” or new repo name.

---

## 8. Execution order (after sign-off)

1. Create new dirs under `docs/`: `Architecture-and-Design/`, `Setup-and-Reference/`, `Deployment/`, `Guides/`, `Development-Iterations/`.
2. **Rework and move** Architecture-and-Design content (final state only); add `Research-Flow.md`; move wireframes and design HTML.
3. **Move** setup/deploy docs; fix internal links.
4. **Create** `Guides/Pinecone-Guide.md`; move SQLite, Pydantic, tool extension, manifest, code-review into `Guides/`.
5. **Move** narrative and iteration artifacts into `Development-Iterations/`.
6. **Rewrite root README.md** as the main roadmap (section 3).
7. **Update** `docs/index.html` and any cross-links to use new paths.
8. **Rebrand** (titles, project name) as in section 7.
9. Run CI; then Render deploy; then push to new repo as agreed.

---

## 9. Summary

| Area | Purpose |
|------|--------|
| **Root README** | Main roadmap: what the project is, quick start, **where to find** architecture, setup, deployment, guides, iterations. |
| **Architecture-and-Design** | Single dir with **final** architecture, research flow, wireframes, diagnostics—no “current vs new” in the main doc. |
| **Guides** | SQLite, Pinecone, Pydantic, tool extension, manifest, code review for new readers. |
| **Development-Iterations** | How the project was built; “current vs new” and narrative live here. |
| **Rebrand** | Cloud Migration Command Center everywhere; Pinecone only as KB detail. |

If this structure and content split look good, next step is to implement: create dirs, rework Research Flow (and any other design docs) to final state, move files, add root README roadmap, then CI and Render.
