# CI/CD pipeline (GitHub Actions + Render)

## Main branch and interface verification (cloud-first)

**Intent:** This project is meant to run mainly in the cloud (e.g. Render). **Main should hold code that works when API keys are present**—otherwise a deploy to Render can go live and then fail at runtime when Pinecone, LLM, or Tavily are missing or invalid.

**Industry best practice:** One of the two approaches below.

### Recommended: Verify interfaces in CI when secrets exist

- **Add GitHub Secrets** for the services you use in deploy (e.g. `PINECONE_API_KEY`, `OPENAI_API_KEY`, optionally `TAVILY_API_KEY`). Use **test** or **CI-only** keys if you don’t want production keys in GitHub.
- **Run interface checks in CI** (e.g. a job that runs `pytest tests/test_interface_connectivity.py -v -m external`, or `python scripts/verify_setup.py`) so that every PR and push to `main` is verified against real APIs.
- **Result:** Only code that passes both unit tests and interface checks can merge to `main`. When you deploy from `main` to Render (with the same or production keys in Render env), the app is already known to work with valid config. No “green CI then deploy fails.”

Optional: run the interface job only when secrets are present (e.g. `if: ${{ secrets.PINECONE_API_KEY != '' }}`) so open-source contributors without keys still get a green CI for non-external tests.

### Alternative: Verify at deploy time (Render)

- Keep CI as today (no secrets; external tests skipped).
- In Render, add a **build or start command** that runs `python scripts/verify_setup.py` and **exits non-zero if any required check fails**. Render will mark the deploy as failed, so the app never starts with missing or invalid keys.
- **Result:** Main is not “verified” in CI, but no broken config reaches a running deployment. You find misconfiguration at deploy time instead of in CI.

**Summary:** For a cloud-first, “main = deploy-ready” stance, **run interface verification in CI with secrets** (recommended). If you prefer not to store any keys in GitHub, use **deploy-time verification** so Render fails fast when keys are wrong.

**What we ship:** The workflow includes an optional job `interface-checks` that runs **only when** the secret `PINECONE_API_KEY` is set. Once you add that (and optionally `OPENAI_API_KEY`, `TAVILY_API_KEY`, `LANGCHAIN_API_KEY`) in GitHub → Settings → Secrets, the job runs on every PR/push and fails with the same detailed messages as `verify_setup.py` if a required interface is missing or invalid. You can then add **interface-checks** as a required status for `main` in branch protection so main stays deploy-ready.

---

## Logical sequence (recommended)

1. **CI first** – Add the GitHub Actions workflow so every push/PR runs tests (and frontend build). Protects `main` from broken code.
2. **Render deploy** – Connect the repo to Render and do the first deploy (manual or auto). Render can auto-deploy on push to `main`.
3. **Branch protection (optional)** – In GitHub repo Settings → Branches, require “CI” status check to pass before merging to `main`. Then only green builds get deployed.

Doing CI before deploy avoids shipping a broken build and then having to fix the pipeline later.

---

## What’s in place

### CI (`.github/workflows/ci.yml`)

- **Triggers:** Push and pull requests to `main` (and `master`).
- **Jobs:**
  - **backend-tests:** Python 3.11, install from `requirements.txt`, run `pytest tests/ -m "not external"`. Skips interface connectivity tests (Pinecone, LLM, Tavily, Mermaid.ink) so no API keys are needed. `LANGCHAIN_TRACING_V2=false` so no LangSmith in CI.
  - **frontend-build:** Node 20, `npm ci` + `npm run build` in `frontend/` so the same steps as the Dockerfile succeed.
- **No secrets required** for CI; tests use mocks and in-memory SQLite.
- **Interface checks:** Run **before push** locally: `python scripts/verify_setup.py` or `pytest tests/test_interface_connectivity.py -v -m external`. See [Setup-and-Reference/Interface-Tests.md](../Setup-and-Reference/Interface-Tests.md). With GitHub Secrets set, the optional `interface-checks` job runs in CI (see “Main branch and interface verification” above).

### CD (Render)

- **Option A – Render auto-deploy:** In Render dashboard, connect the GitHub repo and set “Auto-Deploy” on for the branch you use (e.g. `main`). Every push to `main` triggers a new deploy. If you add branch protection and require the “CI” check, only merges that pass CI will deploy.
- **Option B – Manual deploy:** Deploy from the Render dashboard (Deploy → Deploy latest commit) or follow [DEPLOY_RENDER.md](DEPLOY_RENDER.md) for the first time.
- **Option C – Deploy via Actions (optional):** You can add a job that calls [Render’s Deploy Hook](https://render.com/docs/deploy-hooks) after CI passes (e.g. on push to `main`). Useful if you want deploy only from a specific branch or with a manual workflow_dispatch. Not required if Render is already connected and auto-deploys.

---

## Enforcing “deploy only when CI passes”

1. GitHub repo → **Settings** → **Branches** → Add rule for `main`.
2. Enable **Require status checks to pass before merging** and select **backend-tests** and **frontend-build** (or the “CI” workflow).
3. Save. Then merges to `main` only succeed when CI is green; Render will only receive pushes that passed CI (if you merge via PR).

---

## Optional: deploy hook from Actions

If you prefer to trigger Render deploy explicitly from Actions (e.g. after tests pass on `main`):

1. In Render dashboard: your service → **Settings** → **Deploy Hook** → copy the URL.
2. Add it as a GitHub secret, e.g. `RENDER_DEPLOY_HOOK`.
3. Add a job to `.github/workflows/ci.yml` (or a separate `deploy.yml`) that runs after `backend-tests` and `frontend-build`, only on `main`, and calls the hook:

```yaml
deploy:
  needs: [backend-tests, frontend-build]
  if: github.ref == 'refs/heads/main' && github.event_name == 'push'
  runs-on: ubuntu-latest
  steps:
    - name: Trigger Render deploy
      run: curl -X POST "${{ secrets.RENDER_DEPLOY_HOOK }}"
```

Then Render builds from the same commit that passed CI. Many teams skip this and rely on Render’s native “Deploy on push” plus branch protection.
