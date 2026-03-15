# Final steps – implement reorg, rebrand, CI, push to new repo

**After you say "yes"** we execute in this order. You run tests / open PR in the new repo and merge to main when ready.

---

## What I need from you (if not already decided)

1. **New repo:** Create the new GitHub repository (e.g. `cloud-migration-command-center`) and either:
   - Tell me the clone URL (e.g. `https://github.com/<org>/cloud-migration-command-center.git`), or
   - Confirm org + repo name so we use the right remote.
2. **Branch name:** Push to a branch called `initial-commit` in the new repo (then open PR `initial-commit` → main; CI runs on the PR; merge when ready).

---

## STEPS (execution order)

### 1. Reorganize docs (per DOCS_REORGANIZATION_PLAN.md)

- Create directories: `docs/Architecture-and-Design/`, `docs/Setup-and-Reference/`, `docs/Deployment/`, `docs/Guides/`, `docs/Development-Iterations/`.
- Rework **Research-Flow**: create `docs/Architecture-and-Design/Research-Flow.md` with final flow only (from RESEARCH_FLOW_BLUEPRINT); optionally keep original in `docs/Development-Iterations/`.
- Move and optionally rename files into the right folders; add README.md in each subdir.
- Fix all internal doc links (and root → docs links) to use new paths.
- Update `docs/index.html` links to point to new paths.

### 2. Guides

- Move SQLite, Pydantic, Tool Extension, Manifest, Code Review into `docs/Guides/` (with names from the plan).
- Create `docs/Guides/Pinecone-Guide.md` (index, seeding, usage; consolidate from README + .agents if needed).
- Add `docs/Guides/README.md` index.

### 3. Development-Iterations

- Move AI-Assisted-Development-Narrative, phase plans, design checklist, and original research-flow blueprint (or link) into `docs/Development-Iterations/`.
- Add README explaining purpose (transparency / how the project was built).

### 4. Root README as roadmap

- Rewrite root `README.md`: title **Cloud Migration Command Center**, short intro, quick start, **documentation map** (Architecture & Design, Setup, Deployment, Guides, Development Iterations), modules list. No “current vs new” in README; point to the right doc folders.

### 5. Rebrand

- Replace “Pinecone Semantic Search” with “Cloud Migration Command Center” in user-facing places (README, backend API title, frontend page title).
- Path examples: “project root” or new repo name.

### 6. CI check (local)

- Run `pytest tests/ -m "not external"` and frontend `npm run build`; fix any broken paths or references.

### 7. Push to new repo

- Add new remote: `git remote add newrepo <new-repo-url>`.
- Push branch: `git push newrepo <current-branch>:initial-commit`.
- You then open a PR in the new repo (`initial-commit` → main); CI runs; you run any extra tests; merge when satisfied.

---

## Summary

| Step | Action |
|------|--------|
| 1 | Reorganize docs (dirs, move files, rework Research-Flow to final only, fix links) |
| 2 | Populate Guides (SQLite, Pinecone, Pydantic, etc.) |
| 3 | Populate Development-Iterations |
| 4 | Root README = roadmap |
| 5 | Rebrand (Cloud Migration Command Center) |
| 6 | Run CI locally (pytest + frontend build) |
| 7 | Add remote, push to new repo (branch initial-commit) |

Once you say **yes** and (if needed) provide the new repo URL and branch preference, we proceed in this order.
