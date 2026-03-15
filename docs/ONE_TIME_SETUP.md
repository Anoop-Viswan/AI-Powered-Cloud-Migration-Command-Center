# One-time setup (new environment / open-source users)

Follow these steps **once** when you clone this repo or deploy to a **brand new environment**. At the end, run the **setup verification** so the app can tell you exactly what is correct and what to fix (and why).

---

## 1. Clone and install

```bash
git clone <this-repo-url>
cd pinecone-semantic-search
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your favourite editor and add the keys below.
```

---

## 3. Required: Pinecone (knowledge base search)

The app uses Pinecone for semantic search and the assessment knowledge base. You need an **API key** and an **index**.

### 3.1 Get a Pinecone API key

1. Sign up at **[https://app.pinecone.io/](https://app.pinecone.io/)**.
2. Create or open a project.
3. Go to **API Keys** and create a key (or use the default).
4. In `.env` set:
   ```bash
   PINECONE_API_KEY=your-api-key-here
   ```

### 3.2 Create the index (one-time)

The app expects an index named **`coe-kb-search`** (or set `PINECONE_INDEX_NAME` to your index name).

**Option A – Pinecone console**

1. In [app.pinecone.io](https://app.pinecone.io/), click **Create index**.
2. **Name:** `coe-kb-search`.
3. **Embedding model:** Inference → **llama-text-embed-v2** (or compatible).
4. **Similarity:** Cosine.
5. **Field to embed:** record field **`content`** (model input `text` ← `content`).
6. Create and wait until status is **Ready**.

**Option B – Pinecone CLI**

```bash
# Install CLI (e.g. macOS: brew tap pinecone-io/tap && brew install pinecone-io/tap/pinecone)
export PINECONE_API_KEY=your-key
pc index create -n coe-kb-search -m cosine -c aws -r us-east-1 --model llama-text-embed-v2 --field_map text=content
pc index list   # verify when Ready
```

More detail: see the main **[README](../README.md)** (Pinecone index section).

---

## 4. Required: LLM (research, reports, chat)

The assessment flow (research, report, quality check) and chat summarization need an LLM. Choose **one** provider and set the matching key(s).

### 4.1 OpenAI (default)

1. Get an API key from **[https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)**.
2. In `.env`:
   ```bash
   LLM_PROVIDER=openai
   OPENAI_API_KEY=sk-...
   OPENAI_MODEL=gpt-4o-mini
   ```
   - 401 = invalid key; 429 = rate limit or quota (check [usage](https://platform.openai.com/usage)).

### 4.2 Anthropic

1. Get an API key from **[https://console.anthropic.com/](https://console.anthropic.com/)**.
2. In `.env`:
   ```bash
   LLM_PROVIDER=anthropic
   ANTHROPIC_API_KEY=sk-ant-...
   ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
   ```
3. Install: `pip install langchain-anthropic` (if not in requirements).

### 4.3 Azure OpenAI

1. Create a resource in Azure and deploy a model (e.g. gpt-4o-mini).
2. In `.env`:
   ```bash
   LLM_PROVIDER=azure_openai
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_API_KEY=...
   AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
   ```

---

## 5. Optional: Tavily (official-documentation search)

When KB confidence is low, the app can search official docs (e.g. Microsoft Learn) via Tavily. If you skip this, research still works using only the knowledge base.

1. Get a key at **[https://app.tavily.com/](https://app.tavily.com/)**.
2. In `.env`:
   ```bash
   TAVILY_API_KEY=tvly-...
   ```

---

## 6. Optional: LangSmith (tracing)

For trace trees and token usage in [LangSmith](https://smith.langchain.com/):

1. Sign up at **https://smith.langchain.com/** and create an API key.
2. In `.env`:
   ```bash
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=lsv2_pt_...
   LANGCHAIN_PROJECT=assessment
   ```

---

## 7. Optional: Project directory (for KB seed/search)

For local CLI seed and search, set a project directory (or pass `--project-dir`):

```bash
PINECONE_PROJECT_DIR=/path/to/your/docs
```

Not required for the web app if you only use the Assessment/Admin UI without seeding from this machine.

---

## 8. Run setup verification

After editing `.env`, run the verification script. It checks **all** interfaces (Pinecone, LLM, optional Tavily, LangSmith, Mermaid.ink) and tells you **what passed**, **what failed**, and **why** (with step-by-step fix instructions).

From the **project root**:

```bash
python scripts/verify_setup.py
```

- **Exit 0:** All required checks passed. You can start the app.
- **Exit 1:** One or more required checks failed. The script prints each failure and **what to do** (e.g. “Add PINECONE_API_KEY”, “Create index coe-kb-search”, “OpenAI: 401 – get a new key from …”).

Optional (same checks, via pytest):

```bash
pytest tests/test_interface_connectivity.py -v -m external
```

Fix any reported issue and run verification again until it passes.

---

## 9. Start the app

```bash
# Backend
uvicorn backend.main:app --reload --port 8000

# Frontend (another terminal)
cd frontend && npm install && npm run dev
```

Open [http://localhost:5173](http://localhost:5173). For deployment (e.g. Docker, Render), see **[DEPLOYMENT.md](DEPLOYMENT.md)** and **[DEPLOY_RENDER.md](DEPLOY_RENDER.md)**.

---

## Quick checklist

| Step | What | Required? |
|------|------|-----------|
| Copy `.env.example` → `.env` | Yes | Yes |
| Pinecone: API key + index `coe-kb-search` | [app.pinecone.io](https://app.pinecone.io/) | Yes |
| LLM: one of OpenAI / Anthropic / Azure | Set provider and key(s) in `.env` | Yes |
| Tavily | [app.tavily.com](https://app.tavily.com/) – for official-doc search | No |
| LangSmith | [smith.langchain.com](https://smith.langchain.com/) – for tracing | No |
| Run `python scripts/verify_setup.py` | Confirm everything is correct | Yes (before first run / deploy) |
