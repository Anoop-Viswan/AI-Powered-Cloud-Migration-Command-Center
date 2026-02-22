# Pinecone Semantic Search (Python)

Semantic search **restricted to a single project directory**. Only files under that directory are indexed; search returns only those documents. Other folders on your machine are never included.

## Prerequisites

- **Pinecone API key** – [Create one at app.pinecone.io](https://app.pinecone.io/)
- **Python 3.8+**
- **Pinecone CLI** – required **once** to create the index (see below). Without this step, search/seed will return **404 Resource not found**.

## 1. First-time setup: create the Pinecone index (required once)

The app uses an index named **`coe-kb-search`**. If you see a 404 like `Resource coe-kb-search not found`, the index does not exist yet. Create it once (see below).

**Why an index is needed:** In Pinecone, an **index** is the place where your vectors (embeddings) are stored. This app sends document text to Pinecone; Pinecone uses a **hosted embedding model** on the index to turn that text into vectors and store them. When you search or use the chat, the app sends your query text; Pinecone embeds the query with the same model and runs similarity search over those vectors. So you need one index per “knowledge base” (or one index with namespaces—this app uses one index and one namespace per project directory). The index must be created with the right **embedding model** and **field mapping** (`text` → `content`) so that the API knows which field to embed.

**Option A – Create the index in the Pinecone console (recommended)**

1. Go to [app.pinecone.io](https://app.pinecone.io/) and sign in.
2. Open your project (or create one), then click **Create index**.
3. Set:
   - **Name:** `coe-kb-search` (must match exactly).
   - **Embedding model:** Choose **Inference** (integrated embedding) and select **llama-text-embed-v2** (or the model you want; the app assumes this model).
   - **Similarity:** **Cosine**.
   - **Cloud & region:** e.g. **AWS** / **us-east-1** (or your preferred region).
   - **Field mapping:** See **Field map** below — you must set the **record field** used for embedding to **`content`**.
4. Create the index and wait until its status is **Ready** (usually 1–2 minutes).

**Field map (what to set in the console)**  
The app sends each record with **both** **`text`** and **`content`** (same chunk value) so indexes that expect a **`text`** field for embedding (e.g. mapping `text=content`) work. Query is sent as **`inputs: { "text": "<query>" }`**.

- **When we index (e.g. the SuperNova docx):** Each record has a field **`content`** — that’s the text chunk we want Pinecone to embed. So the “field to embed” / “source field” / “record field for embedding” in the console must be **`content`**.
- **When we search/chat:** The app sends the query under **`inputs: { "text": "<query>" }`**. So the query side uses the name **`text`** (that’s the model’s input parameter; the console may show this as default).
- **What to set:** If the UI shows **“text”** as default, that’s the *model input* name. You need to tell Pinecone: “when embedding a record, use the value from the record field **content**.” So set the **record field** (or “source field” / “field to embed”) to **`content`**. The mapping is: model input **text** ← record field **content**. In the CLI this is `--field_map text=content`.

**Option B – Create the index with the Pinecone CLI**

```bash
# Install CLI (macOS)
brew tap pinecone-io/tap && brew install pinecone-io/tap/pinecone
pc version

# Create index (use same API key as in .env)
cd /path/to/pinecone-semantic-search
export PINECONE_API_KEY=your-api-key   # or: source .env
pc index create -n coe-kb-search -m cosine -c aws -r us-east-1 --model llama-text-embed-v2 --field_map text=content

# Verify when ready
pc index list
pc index describe --name coe-kb-search
```

After the index is **Ready**, run the app again (seed from UI or CLI, then search).

## 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set:
#   PINECONE_API_KEY=your-api-key          # from https://app.pinecone.io/
#   PINECONE_PROJECT_DIR=/path/to/project  # optional; you can pass --project-dir instead
#   PINECONE_SPEND_LIMIT=10                # optional; default 10 (dollars). Script blocks when estimated usage reaches this.
```

**Adding your API key:** Paste your key only into the `.env` file on your machine. Do not share it in chat or commit `.env` to version control.

## 3. Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 4. Index your project directory (one-time)

Only the directory you pass is scanned and sent to Pinecone. Everything else is ignored.

```bash
# Use --project-dir (required)
python semantic_search.py --project-dir /path/to/your/project --seed
```

Or set the path in `.env` and run:

```bash
python semantic_search.py --seed
```

**Included:** Text/code (`.md`, `.txt`, `.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.json`, `.yml`, `.yaml`, `.toml`, `.rst`, `.sh`, etc.) and documents: **`.pdf`**, **`.doc`**, **`.docx`**, **`.xls`**, **`.xlsx`**, **`.csv`**, **`.pptx`** (see `INCLUDE_EXTENSIONS` in `semantic_search.py`).

**Excluded:** `.git`, `node_modules`, `venv`, `.venv`, `__pycache__`, `dist`, `build`, `.next`, and other hidden or build dirs.

Large files are split into chunks so they stay within Pinecone limits. Each chunk has metadata: `file_path`, `category` (extension), `application` (first folder under project dir), `content_type` (prose/table/slide), and any fields from a **manifest** (see below).

**Application folders and manifest:** You can organize files under **application folders** (e.g. `MyApp/reports/doc.pdf`). The indexer derives **application name** from the first path segment. Optionally add a **`manifest.json`** in the project directory to attach extra metadata (e.g. `technology`, `tools`, `description`) per application. See `docs/MANIFEST.md` and copy `manifest.json.example` into your project directory as `manifest.json`.

## 5. Search (only in that project)

Searches run only over the namespace for that project directory. No other documents are searched.

```bash
python semantic_search.py --project-dir /path/to/your/project --query "where is the main entry point?"
```

Filter by file type (extension) or by application (folder name):

```bash
python semantic_search.py --project-dir /path/to/your/project --query "API routes" --category py --top-k 5
python semantic_search.py --project-dir /path/to/your/project --query "deployment" --application FinanceApp
```

If `PINECONE_PROJECT_DIR` is set in `.env`, you can omit `--project-dir`:

```bash
python semantic_search.py --query "configuration options"
```

## Spend guardrail ($10 default)

The script tracks **estimated** Pinecone usage (read units from search responses, write units from upserts) and persists it in `.pinecone_usage.json`. When the estimated spend reaches **PINECONE_SPEND_LIMIT** (default **$10**), the script **blocks** further runs and prints:

- Current estimated usage and your limit  
- Instructions to give **explicit permission** to go over the limit

To allow usage beyond the limit, either:

1. Set in `.env`: `PINECONE_ALLOW_OVER_LIMIT=yes`
2. Or run with: `--allow-over-limit`

Check current estimated usage anytime:

```bash
python semantic_search.py --check-usage
```

Note: Estimation uses this app’s operations only and Pinecone’s approximate serverless pricing. Actual billing may differ; use the [Pinecone console](https://app.pinecone.io/) for official usage.

## Summary

| What | How |
|------|-----|
| Restrict to one directory | Use `--project-dir /path/to/project` (or `PINECONE_PROJECT_DIR`). Only that path is indexed and searched. |
| Index that directory | `python semantic_search.py --project-dir <dir> --seed` |
| Search that directory | `python semantic_search.py --project-dir <dir> --query "..."` |
| Multiple projects | Use a different `--project-dir` for each; each gets its own namespace so they don’t mix. |
| Check estimated spend | `python semantic_search.py --check-usage` |
| Allow usage over limit | Set `PINECONE_ALLOW_OVER_LIMIT=yes` in `.env` or use `--allow-over-limit` |

## Web app (Phase 2)

A React frontend and FastAPI backend provide:

- **Home** – Landing page with Center of Excellence (CoE) info and migration journey tabs: **Assessment** (application info form), **Planning** (timelines, dependencies, WBS), **Migration** and **Support** (placeholders).
- **Ask the KB** – Chat interface: questions are run against the knowledge base and summarized by an LLM (set `OPENAI_API_KEY` in `.env` for summaries).
- **Admin** – View config (project dir, spend limit), usage, run re-index (seed), and view manifest applications.

**Run backend and frontend (from project root):**

```bash
# Terminal 1 – API
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000

# Terminal 2 – Frontend
cd frontend && npm install && npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The frontend proxies `/api` to the backend. Optional: set `OPENAI_API_KEY` (and optionally `OPENAI_MODEL`, default `gpt-4o-mini`) in `.env` for chat summarization.

## Running tests

Unit tests cover document extractors (PDF, DOCX, XLSX, CSV, PPTX, plain text) and semantic search (manifest, application derivation, build_records, search with mocked index). From the project root with the venv activated:

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

## Project layout

- `semantic_search.py` – Scans one project dir, upserts chunks to a project-scoped namespace; supports PDF, DOCX, XLS, XLSX, CSV, PPTX and text files; application name from folder structure; optional `manifest.json` for extra metadata; search with reranking and optional `--category` / `--application`. Enforces spend guardrail unless overridden.
- `document_extractors.py` – Text extraction and chunking for PDF, DOCX, XLS, XLSX, CSV, PPTX.
- `docs/MANIFEST.md` – How to use application folders and `manifest.json`.
- `manifest.json.example` – Example manifest; copy to your project directory as `manifest.json`.
- `usage_tracker.py` – Tracks read/write units and estimated cost; blocks when at or above `PINECONE_SPEND_LIMIT` unless permission given.
- `requirements.txt` – `pinecone`, `python-dotenv`, document libs, `pytest`.
- `tests/` – Unit tests: `test_document_extractors.py`, `test_semantic_search.py`; fixtures in `conftest.py`.
- `.env` – `PINECONE_API_KEY`, optional `PINECONE_PROJECT_DIR`, `PINECONE_SPEND_LIMIT` (default 10), `PINECONE_ALLOW_OVER_LIMIT` (yes to allow over limit).
- `.pinecone_usage.json` – Persisted usage (created automatically; in `.gitignore`).

## Troubleshooting

- **Project directory required** – You must pass `--project-dir` or set `PINECONE_PROJECT_DIR`.
- **No text files found** – Check that the path is correct and that it contains files with extensions listed in `INCLUDE_EXTENSIONS` (e.g. `.md`, `.py`).
- **Index not found** – Create the index with the CLI (step 1) and wait until it’s ready.
- **No results after --seed** – The script waits 10s after upsert; if you run search from another terminal, wait at least 10 seconds after the seed run finishes.
- **Script exits with “PINECONE SPEND GUARDRAIL”** – Estimated usage is at or above `PINECONE_SPEND_LIMIT`. To proceed, set `PINECONE_ALLOW_OVER_LIMIT=yes` in `.env` or run with `--allow-over-limit`. To reset tracked usage, delete `.pinecone_usage.json` (estimation will start from zero again).
