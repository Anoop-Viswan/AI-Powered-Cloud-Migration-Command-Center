# Pinecone guide (knowledge base)

The app uses **Pinecone** as the vector store for the knowledge base (KB). Only documents under a single project directory are indexed; search is scoped to that directory via a stable namespace.

---

## 1. Prerequisites

- **Pinecone API key** – [Create one at app.pinecone.io](https://app.pinecone.io/)
- **Index** – Create an index named `coe-kb-search` (or set `PINECONE_INDEX_NAME` to your index name). The index must use a compatible embedding model and field mapping (`text` / `content`). See [One-Time-Setup](../Setup-and-Reference/One-Time-Setup.md) for step-by-step index creation (console or CLI).

---

## 2. Configuration

In `.env`:

- `PINECONE_API_KEY` – Your API key (required).
- `PINECONE_PROJECT_DIR` – Path to the directory to index and search (optional; can pass `--project-dir` when using the CLI).
- `PINECONE_INDEX_NAME` – Default `coe-kb-search`; override if you use a different index name.
- `PINECONE_SPEND_LIMIT` – Optional spend guardrail in USD (default 10). The KB CLI and backend will block further usage when estimated spend reaches this unless you set `PINECONE_ALLOW_OVER_LIMIT=yes` or use `--allow-over-limit`.

---

## 3. Seeding the index

From the **project root**:

```bash
python -m backend.semantic_search --project-dir /path/to/your/docs --seed
```

Only files under that directory are scanned and upserted into a project-scoped namespace. Supported extensions include text/code (`.md`, `.txt`, `.py`, `.js`, etc.) and documents (`.pdf`, `.docx`, `.xlsx`, `.csv`, `.pptx`). See `backend/semantic_search.py` (`INCLUDE_EXTENSIONS`) and [Manifest.md](Manifest.md) for metadata.

You can also trigger seeding from the **Admin UI** (Knowledge Base tab) when `PINECONE_PROJECT_DIR` is set.

---

## 4. Search

- **CLI:**  
  `python -m backend.semantic_search --project-dir /path/to/your/docs --query "your question"`  
  Optional: `--category pdf`, `--application MyApp`, `--top-k 5`.

- **API:**  
  `POST /api/search` with `{"query": "...", "category": null, "application": null, "top_k": 5}`.

- **Chat:**  
  The chat endpoint uses the same KB search and then summarizes results with the LLM.

---

## 5. Usage and spend

- Estimated read/write units are tracked in `.pinecone_usage.json` at the project root. When estimated spend reaches `PINECONE_SPEND_LIMIT`, the CLI (and Admin seed) will block unless overridden.
- **Check usage:**  
  `python -m backend.semantic_search --check-usage`

---

## 6. References

- **One-time setup (index, env):** [Setup-and-Reference/One-Time-Setup.md](../Setup-and-Reference/One-Time-Setup.md)
- **Env variables:** [Setup-and-Reference/ENV-Reference.md](../Setup-and-Reference/ENV-Reference.md)
- **Manifest and metadata:** [Manifest.md](Manifest.md)
