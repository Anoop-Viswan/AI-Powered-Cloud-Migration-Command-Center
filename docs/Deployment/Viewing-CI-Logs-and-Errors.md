# Viewing CI runs and detailed errors

Where to see **what checks run** in GitHub Actions and **full error messages** when something fails.

---

## Where to look

1. **Repo on GitHub** → **Actions** tab.
2. Click a **workflow run** (e.g. **CI** with a green ✓ or red ✗ and the commit message).
3. You’ll see the **jobs**: `backend-tests`, `frontend-build`, `interface-checks` (if enabled).
4. **Click a job name** (e.g. **backend-tests**) to open that job’s log.
5. **Expand the step** you care about. Each step shows its full output (stdout/stderr). If a step failed, it’s usually expanded by default; scroll inside that step for the full traceback and error.

---

## What each job runs and where details are

| Job | What it runs | Step to open for details |
|-----|--------------|---------------------------|
| **backend-tests** | Pytest: all tests except those marked `external` (unit + API tests; no real Pinecone/LLM calls). | **List tests that will run (backend)** – list of every test that will run.<br>**Run tests (excluding external API checks)** – full pytest output: each test name, PASSED/FAILED, and on failure a **full traceback** (assertion errors, request/response details, stack traces). |
| **frontend-build** | `npm ci` and `npm run build` in `frontend/`. | **Install and build frontend** – npm install and build logs. |
| **interface-checks** | `scripts/verify_setup.py`: real connectivity checks for Pinecone, LLM, LangSmith, Tavily, Mermaid.ink. | **Run all interface connectivity checks** – pass/fail and messages per interface (e.g. “Pinecone: OK”, “LLM: API key missing”). |

---

## Backend test output (verbose)

- **List tests that will run (backend)** prints the collected tests (one line per test) before they run.
- **Run tests** uses:
  - `-v` – one line per test (name + PASSED/FAILED).
  - `--tb=long` – **full traceback** on failure (file, line, code, assertion message).
  - `-ra` – short summary of all results at the end (passed, failed, skipped).

So when a backend test fails, open **backend-tests** → **Run tests (excluding external API checks)** and scroll to the failure; you’ll see the full traceback and any request/response or assertion details the test prints.

---

## Interface checks output

When **interface-checks** runs, `verify_setup.py` prints for each interface:

- **[PASS]** or **[FAIL]** plus a short message.
- For failures: detail lines and optional **setup_steps** (what to do to fix).

All of that appears in the **Run all interface connectivity checks** step log.

---

## Quick link

- **Workflow file:** [.github/workflows/ci.yml](../../.github/workflows/ci.yml)  
- **Branch protection and requiring checks:** [CICD-Pipeline.md](CICD-Pipeline.md#require-all-tests-green-before-merge-branch-protection)
