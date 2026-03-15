# Deployment

How to deploy the app and run CI/CD.

| Document | Description |
|----------|-------------|
| [Deployment.md](Deployment.md) | Overview: packaging, env, persistence, port; comparison of deployment options (Render, Cloud Run, VPS, etc.). |
| [Deploy-Render.md](Deploy-Render.md) | Step-by-step: Docker on Render, API keys, persistent disk, health check. |
| [CICD-Pipeline.md](CICD-Pipeline.md) | CI with GitHub Actions (tests, frontend build); CD with Render. |
| [Viewing-CI-Logs-and-Errors.md](Viewing-CI-Logs-and-Errors.md) | Where to see what checks ran and full error messages (Actions tab, job steps, tracebacks). |
| [Secrets-in-Cloud.md](Secrets-in-Cloud.md) | Where secrets live: local `.env`, Render/GitHub env, and how to use Azure Key Vault or AWS Secrets Manager. |

**CI workflow (code review):** The GitHub Actions workflow lives in ** [.github/workflows/ci.yml](../../.github/workflows/ci.yml)** (repo root). It runs on push and pull_request to `main`/`master`. Jobs: `backend-tests` (pytest, excluding `external`), `frontend-build` (npm ci + build), and optional `interface-checks` (runs only when `PINECONE_API_KEY` secret is set; runs `verify_setup.py`). See [CICD-Pipeline.md](CICD-Pipeline.md) for behavior and branch protection.
