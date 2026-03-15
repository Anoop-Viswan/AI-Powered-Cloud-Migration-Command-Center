# CI/CD pipeline (GitHub Actions + Render)

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
- **Interface checks:** Run **before push** locally: `python scripts/verify_interfaces.py` or `pytest tests/test_interface_connectivity.py -v -m external`. See [INTERFACE_TESTS.md](INTERFACE_TESTS.md). Optional: add API keys as GitHub Secrets and run the same tests in CI to validate deploy env.

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
