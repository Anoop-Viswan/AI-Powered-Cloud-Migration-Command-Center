# Cloud Migration Command Center

AI-powered migration command center: **Knowledge Base** (semantic search over migration docs), **Assessment** (profile → research → report), and **Admin & Diagnostics** (run research, view reports, monitor LLM/tool usage). The KB uses Pinecone for vector search; other modules use LLM, optional Tavily for official-doc search, and optional LangSmith for tracing.

**First time here (new environment / open-source user)?**  
Follow **[docs/Setup-and-Reference/One-Time-Setup.md](docs/Setup-and-Reference/One-Time-Setup.md)** for step-by-step setup (Pinecone, LLM, optional Tavily/LangSmith). Then run **`python scripts/verify_setup.py`** to confirm everything is correct; it will tell you what passed, what failed, and **what to do** for each failure.

---

## Quick start

```bash
git clone <this-repo>
cd <repo-dir>
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: PINECONE_API_KEY, PINECONE_PROJECT_DIR (optional), OPENAI_API_KEY (or other LLM), etc.
python scripts/verify_setup.py
```

Create the Pinecone index `coe-kb-search` once (see [One-Time-Setup](docs/Setup-and-Reference/One-Time-Setup.md)). Then:

```bash
# Terminal 1 – API
uvicorn backend.main:app --reload --port 8000

# Terminal 2 – Frontend
cd frontend && npm install && npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Seed the KB from Admin → Knowledge Base, or:  
`python -m backend.semantic_search --project-dir /path/to/docs --seed`

---

## Documentation (where to look)

| Area | Location | Description |
|------|----------|-------------|
| **Architecture & design** | [docs/Architecture-and-Design/](docs/Architecture-and-Design/) | System architecture, research flow, wireframes, diagnostics design. |
| **Setup & reference** | [docs/Setup-and-Reference/](docs/Setup-and-Reference/) | One-time setup, env variables, config, interface tests. |
| **Deployment** | [docs/Deployment/](docs/Deployment/) | Cloud deploy, Render step-by-step, CI/CD. |
| **Guides** | [docs/Guides/](docs/Guides/) | SQLite, Pinecone, Pydantic, tool extension, manifest, code review. |
| **Development iterations** | [docs/Development-Iterations/](docs/Development-Iterations/) | How the project was built (AI-assisted narrative, phase plans). |

---

## Modules

- **Knowledge Base (KB)** – Semantic search over a single project directory; indexing and search via Pinecone (`backend.semantic_search`). Optional `manifest.json` for metadata.
- **Assessment** – Application profile → validation → submit (app user); research → report → quality check (admin). Uses KB, LLM, optional Tavily for official-doc search.
- **Admin & Diagnostics** – Admin command center: assessments list, KB config, Diagnostics tab (LLM/Tavily/Pinecone usage, thresholds, request log).
- **Planning** *(placeholder)* – Future runbooks, checklists.
- **Execution** *(placeholder)* – Future post-migration artifacts.

---

## Prerequisites

- **Pinecone API key** – [app.pinecone.io](https://app.pinecone.io/); create index `coe-kb-search` once (see [One-Time-Setup](docs/Setup-and-Reference/One-Time-Setup.md)).
- **Python 3.8+**
- **LLM** – OpenAI (default), Anthropic, or Azure OpenAI; set the corresponding API key in `.env` (see [ENV-Reference](docs/Setup-and-Reference/ENV-Reference.md)).

---

## KB CLI (seed & search)

From project root:

```bash
python -m backend.semantic_search --project-dir /path/to/docs --seed
python -m backend.semantic_search --project-dir /path/to/docs --query "your question"
python -m backend.semantic_search --check-usage
```

If `PINECONE_PROJECT_DIR` is set in `.env`, you can omit `--project-dir`. See [Guides/Pinecone-Guide.md](docs/Guides/Pinecone-Guide.md).

---

## Optional features

| Feature | Purpose | Env |
|--------|---------|-----|
| **Tavily** | Official-doc web search when KB confidence is low | `TAVILY_API_KEY` |
| **LangSmith** | Tracing for LangChain/LangGraph | `LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_API_KEY` |

Admin → Knowledge Base shows **Feature status** for each; missing keys show clear instructions. Full list: [ENV-Reference](docs/Setup-and-Reference/ENV-Reference.md).

---

## Deployment

- **Render (Docker):** [docs/Deployment/Deploy-Render.md](docs/Deployment/Deploy-Render.md)
- **Other cloud:** [docs/Deployment/Deployment.md](docs/Deployment/Deployment.md)

```bash
docker build -t cloud-migration-command-center .
docker run -p 7860:7860 -e PINECONE_API_KEY=your-key -v /path/to/docs:/data cloud-migration-command-center
```

---

## Tests

```bash
pytest tests/ -m "not external" -v
```

Interface connectivity tests (Pinecone, LLM, Tavily, etc.) are marked `external`; run `python scripts/verify_setup.py` for full checks. See [Setup-and-Reference/Interface-Tests.md](docs/Setup-and-Reference/Interface-Tests.md).

---

## Project layout

- **backend/** – API, KB (`semantic_search`, `document_extractors`, `usage_tracker`), assessment, diagnostics, tool gateway.
- **frontend/** – React app (Assessment, Admin, Chat, Home).
- **docs/** – Architecture, setup, deployment, guides, development iterations (see [Documentation](#documentation-where-to-look) above).
- **scripts/** – `verify_setup.py`, `verify_interfaces.py`.
- **tests/** – Pytest suite.
