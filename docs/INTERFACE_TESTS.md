# Interface connectivity tests

Tests that verify **external dependencies** (Pinecone, LLM, Tavily, Mermaid.ink) so deployment in a new environment (e.g. Render) doesn’t fail silently. Each check returns **very detailed error messages** for easy debugging. When something is wrong, checks also return **setup_steps** (numbered “what to do”) so open-source users can fix config. For a single entry point, run **`python scripts/verify_setup.py`** after one-time setup; see **[ONE_TIME_SETUP.md](ONE_TIME_SETUP.md)**.

---

## What is checked

| Interface      | What we verify | When it runs |
|----------------|----------------|--------------|
| **Pinecone**   | `PINECONE_API_KEY` valid; index `coe-kb-search` (or `PINECONE_INDEX_NAME`) exists | When key is set |
| **LLM**        | Configured provider (OpenAI / Anthropic / Azure) and one minimal invoke | When that provider’s key is set |
| **LangSmith**  | If tracing on, `LANGCHAIN_API_KEY` is set | When tracing enabled |
| **Tavily**     | `TAVILY_API_KEY` valid and one search works | When key is set (optional) |
| **Mermaid.ink**| Service reachable (diagram images in reports) | Always (no key) |

On failure you get a short **message** plus **detail** (which env var to check, link to docs, or response snippet).

---

## Run after one-time setup (recommended)

From project root, with `.env` loaded:

```bash
python scripts/verify_setup.py
```

- **Exit 0:** All required checks (Pinecone, LLM) passed. You can start the app or deploy.
- **Exit 1:** One or more required checks failed. The script prints **why** and **what to do** (numbered steps) for each failure. Fix and run again.

Alternatively, same checks with simpler output: `python scripts/verify_interfaces.py`.

Or run the same checks via pytest:

```bash
pytest tests/test_interface_connectivity.py -v -m external
```

---

## Run in CI

- **Default:** CI runs `pytest tests/ -m "not external"` so interface tests are **skipped** and no API keys are needed. CI stays green without secrets.
- **With secrets:** To run interface tests in CI (e.g. to validate Render env), add your API keys as [GitHub Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets) and add an optional job that runs:
  ```yaml
  pytest tests/test_interface_connectivity.py -v -m external
  ```
  with env set from secrets. If a check fails, the job fails with the same detailed message (e.g. "Pinecone: Index 'coe-kb-search' not found...") so you can fix the env or the new environment.

---

## Where the logic lives

- **Checks:** `tests/interface_checks.py` – each `check_*()` returns `{ "name", "ok", "message", "detail" }`.
- **Pytest:** `tests/test_interface_connectivity.py` – one test per interface; skipped when the relevant key is not set; on failure, asserts with the full message + detail.
- **Script:** `scripts/verify_interfaces.py` – runs all checks and prints a report; use before push or before deploy.
- **Marker:** `pytest.ini` – marker `external` so you can run `pytest -m "not external"` to exclude these tests.

---

## Example failure output

```
AssertionError: Pinecone: Index 'coe-kb-search' not found. Your key works but the app expects this index.
Detail: Existing indexes: []. Create index 'coe-kb-search' in Pinecone console or set PINECONE_INDEX_NAME to an existing index. See README.
```

```
AssertionError: OpenAI: 401 – Incorrect API key provided.
Detail: OPENAI_API_KEY is invalid or revoked. Get a new key from https://platform.openai.com/api-keys
```

This makes it clear what broke and how to fix it in the new environment.
