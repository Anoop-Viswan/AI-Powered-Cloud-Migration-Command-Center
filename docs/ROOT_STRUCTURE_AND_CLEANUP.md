# Root structure and cleanup

Current root layout and what should stay vs move. Goal: **root has only README, config/dirs, and entrypoints; no application modules at top level.**

---

## 1. Current root (files and directories)

```
<repo-root>/
├── .DS_Store                 # macOS – ignore (gitignore)
├── .dockerignore             # Keep at root (Docker)
├── .env                      # Keep at root (local secrets, not committed)
├── .env.example              # Keep at root (template for setup)
├── .git/                     # Git
├── .github/                  # Keep at root (CI workflows)
├── .gitignore                # Keep at root
├── .pinecone_usage.json      # Runtime – add to gitignore if not already
├── .pytest_cache/            # Pytest – ignore
├── .seed_status.json         # Runtime – add to gitignore if not already
├── __pycache__/               # Python – ignore
├── Dockerfile                # Keep at root (deploy)
├── README.md                 # Keep at root (main roadmap)
├── backend/                  # Keep at root (app)
├── data/                     # Keep at root (runtime DBs, generated)
├── docs/                     # Keep at root (documentation)
├── document_extractors.py    # ⚠️ APPLICATION – move into backend
├── frontend/                 # Keep at root (app)
├── manifest.json.example     # Keep at root (or move to docs/Guides/samples)
├── pytest.ini                 # Keep at root (test config)
├── requirements.txt          # Keep at root (Python deps)
├── sample_docs/               # Keep at root (sample content for KB)
├── scripts/                  # Keep at root (verify_setup, etc.)
├── semantic_search.py        # ⚠️ APPLICATION – move into backend
├── tests/                    # Keep at root (tests)
├── usage_tracker.py          # ⚠️ APPLICATION – move into backend
└── venv/                     # Ignore (local env)
```

---

## 2. What should stay at root (recommended)

| Item | Reason |
|------|--------|
| **README.md** | Main project roadmap and entry. |
| **.gitignore** | Git. |
| **.dockerignore** | Docker build. |
| **.env.example** | Setup template (required at root for `cp .env.example .env`). |
| **.github/** | CI (GitHub Actions). |
| **Dockerfile** | Deploy. |
| **pytest.ini** | Pytest config. |
| **requirements.txt** | Python deps. |
| **backend/** | Application backend. |
| **frontend/** | Application frontend. |
| **docs/** | Documentation. |
| **scripts/** | Utility scripts (verify_setup, etc.). |
| **tests/** | Tests. |
| **data/** | Runtime data (DBs, generated); often in .gitignore. |
| **sample_docs/** | Sample content. |
| **manifest.json.example** | Optional at root for visibility; or move to `docs/Guides/` or `sample_docs/`. |

**.env** stays at root locally but is not committed.

---

## 3. What to move (application code at root → backend)

| Current (root) | Move to | Notes |
|----------------|---------|--------|
| **semantic_search.py** | **backend/semantic_search.py** | KB search, indexing, CLI. Backend and tests import it; update imports to `backend.semantic_search`. CLI: `python -m backend.semantic_search` or a thin `scripts/run_kb.py`. |
| **document_extractors.py** | **backend/document_extractors.py** | Used by semantic_search and tests. Update imports to `backend.document_extractors`. |
| **usage_tracker.py** | **backend/usage_tracker.py** | Pinecone usage tracking. Used by semantic_search, admin, feature_status. Update imports to `backend.usage_tracker`. |

After the move, **backend/main.py** no longer needs to add project root to `sys.path` for these three; it can rely on `backend` package imports.

---

## 4. Target root layout (after cleanup)

```
<repo-root>/
├── .dockerignore
├── .env.example
├── .github/
├── .gitignore
├── Dockerfile
├── README.md
├── backend/              # includes semantic_search, document_extractors, usage_tracker
├── data/
├── docs/
├── frontend/
├── manifest.json.example  # or docs/Guides/ or sample_docs/
├── pytest.ini
├── requirements.txt
├── sample_docs/
├── scripts/
├── tests/
└── (venv, .env, .pytest_cache, __pycache__, .pinecone_usage.json, .seed_status.json – local/ignore)
```

No **document_extractors.py**, **semantic_search.py**, or **usage_tracker.py** at root.

---

## 5. Import and CLI updates required

- **backend/main.py:** Remove root from `sys.path`; no direct import of `semantic_search`/`usage_tracker` from root (they live in backend).
- **backend/routers/admin.py:** `from backend import semantic_search` (or `from backend.semantic_search import ...`), `from backend import usage_tracker`.
- **backend/routers/chat.py:** `from backend.semantic_search import ...`.
- **backend/routers/search.py:** `from backend.semantic_search import ...`.
- **backend/services/feature_status.py:** `from backend.usage_tracker import ...`.
- **backend/services/assessment/research_agent.py:** `from backend.semantic_search import ...`.
- **backend/semantic_search.py:** `from backend.document_extractors import ...`, `from backend.usage_tracker import ...`.
- **tests:** Update imports to `backend.semantic_search`, `backend.document_extractors`, `backend.usage_tracker`.
- **scripts:** If any script runs `semantic_search` as script, use `python -m backend.semantic_search` or a small wrapper under `scripts/`.

---

## 6. Optional

- **manifest.json.example:** Move to `docs/Guides/` or `sample_docs/` and link from README/Guides if you want root even leaner.
- **.pinecone_usage.json / .seed_status.json:** Ensure both are in `.gitignore` so they never get committed.

---

## 7. Order relative to doc reorg and push

1. Move the three Python modules into **backend/** and fix all imports and CLI.
2. Run tests and fix any breakage.
3. Proceed with doc reorg, rebrand, then push to the new repo on branch **initial-commit**.

If you want, we can do root cleanup first (steps above), then doc reorg + rebrand, then push; or do doc reorg + rebrand first and include root cleanup in the same branch before push.
