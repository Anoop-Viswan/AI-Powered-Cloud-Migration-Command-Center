# CI: re-running tests and where config comes from

---

## 1. How to run the tests again (no code change)

You added or changed **Secrets** or **Variables** and want CI to run again without pushing new code.

### Option A: Re-run from the GitHub Actions UI (simplest)

1. Open your repo on GitHub → **Actions** tab.
2. Click the **workflow run** you want to re-run (e.g. the latest "CI" run for your branch).
3. On the run summary page, click **Re-run all jobs** (or **Re-run failed jobs** if only some failed).

The same commit is re-run with the **current** Secrets and Variables. No push needed.

### Option B: Push an empty commit

From your repo root:

```bash
git commit --allow-empty -m "ci: re-run tests (e.g. after adding secrets)"
git push origin <your-branch>
```

This triggers a new workflow run. Use Option A if you prefer not to add a commit.

---

## 2. Where CI gets its config (API keys vs OPENAI_MODEL etc.)

The **interface-checks** job (and only that job) needs API keys and optional settings. It does **not** read a `.env` file in CI; there is no `.env` in the repo. It only sees what the workflow passes in the step’s `env:` block.

### API keys → **Secrets**

Put these under **Settings → Secrets and variables → Actions → Secrets**:

- `PINECONE_API_KEY`
- `OPENAI_API_KEY` (or `ANTHROPIC_API_KEY`, or Azure: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`)
- `TAVILY_API_KEY` (optional)
- `LANGCHAIN_API_KEY` (optional)

The workflow passes them into the "Run all interface connectivity checks" step. They **are** read correctly there (the earlier problem was only using `secrets` in the job’s **if** condition, which GitHub does not allow).

### Optional config (OPENAI_MODEL, LLM_PROVIDER, etc.) → **Variables** or defaults

Settings like `OPENAI_MODEL`, `LLM_PROVIDER`, `ANTHROPIC_MODEL` are **not** secrets. In CI you can:

- **Do nothing** – The script and app use **defaults** (e.g. `OPENAI_MODEL` defaults to `gpt-4o-mini`, `LLM_PROVIDER` to `openai`). Interface checks will run with those defaults.
- **Match your .env** – Add them as **Variables** (Settings → Secrets and variables → Actions → **Variables**):
  - `LLM_PROVIDER` (e.g. `openai`, `anthropic`, `azure_openai`)
  - `OPENAI_MODEL` (e.g. `gpt-4o-mini`, `gpt-4o`)
  - `ANTHROPIC_MODEL` (if you use Anthropic)

The workflow passes these into the interface-checks step. If a variable is not set, the value is empty and the script uses its default.

### Summary table

| In your .env | In CI (interface-checks job) |
|--------------|------------------------------|
| API keys (PINECONE_API_KEY, OPENAI_API_KEY, …) | **Secrets** – add under Actions → Secrets. Fetched and passed to the step. |
| RUN_INTERFACE_CHECKS (flag to run the job) | **Variable** – add under Actions → Variables (e.g. `true`). Used in the job `if`. |
| OPENAI_MODEL, LLM_PROVIDER, ANTHROPIC_MODEL | **Variables** (optional) – add under Actions → Variables if you want CI to match your .env; otherwise defaults are used. |

Full list of env vars: [Setup-and-Reference/ENV-Reference.md](../Setup-and-Reference/ENV-Reference.md).  
Secrets and Variables in cloud: [Secrets-in-Cloud.md](Secrets-in-Cloud.md).
