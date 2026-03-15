# Handoff: Render deployment (for tomorrow / next session)

**Date:** When this was written (session before “implement deployment”).  
**Goal:** Deploy the app with Docker on Render. Either the user follows the steps in DEPLOY_RENDER.md, or we add automation (e.g. render.yaml) and verify.

---

## What’s already done

1. **Step-by-step guide:** [docs/DEPLOY_RENDER.md](DEPLOY_RENDER.md)  
   - Sign up, connect repo, set Runtime = Docker.  
   - Add env vars (API keys as secrets): PINECONE_API_KEY, OPENAI_API_KEY, TAVILY_API_KEY, optional LANGCHAIN_*; ALLOWED_ORIGINS = `https://<service-name>.onrender.com`.  
   - Persistent disk (paid): mount path **`/app/data`**.  
   - Health check path: `/api/health`.  
   - Cost: free tier (ephemeral data) vs paid + disk (data persists).  
   - Checklist and troubleshooting.

2. **Dockerfile**  
   - Uses `PORT` when set (Render sets PORT=10000):  
     `CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-7860}"]`  
   - Frontend stage uses `npm ci` (with devDependencies) so the Vite build works.

3. **.dockerignore**  
   - Excludes `.env`, `venv`, `node_modules`, `data`, `*.db` so secrets and local DBs aren’t in the image.

4. **Docs links**  
   - README.md, docs/README.md, and DEPLOYMENT.md point to DEPLOY_RENDER.md.

---

## What “implement that deployment” can mean tomorrow

- **Option A – User deploys:** User (or someone) follows DEPLOY_RENDER.md in the browser (Render dashboard), creates the Web Service, sets env vars, adds disk if paid. No code changes required.

- **Option B – Add Render Blueprint (optional):** Add a `render.yaml` (or `render.yaml` in repo root) so the service and env can be created from the repo. Env secrets still must be set in the dashboard (or via Render API); the blueprint can define the service, disk mount path, health check.

- **Option C – Verify / fix:** After first deploy, if something fails (e.g. port, path, CORS), fix Dockerfile or app config and update DEPLOY_RENDER.md.

---

## Open items / decisions

- [ ] Confirm whether user wants to **manually** follow DEPLOY_RENDER.md or use a **Blueprint** for repeatable deploys.  
- [ ] After first deploy: confirm URL, test Admin, Assessments, Diagnostics, and that data persists (if paid + disk).  
- [ ] If free tier: remind that data is ephemeral; for real use, need paid + disk.

---

## Key file locations

| What | Where |
|------|--------|
| Render step-by-step | `docs/DEPLOY_RENDER.md` |
| General deployment options | `docs/DEPLOYMENT.md` |
| Dockerfile (PORT, CMD) | `Dockerfile` (repo root) |
| Env reference (key names) | `docs/ENV_REFERENCE.md`, `.env.example` |
| Data dir in container | `/app/data` (mount Render disk here for persistence) |

---

## Quick “tomorrow” checklist

1. Open [docs/DEPLOY_RENDER.md](DEPLOY_RENDER.md).  
2. Decide: manual deploy vs add render.yaml.  
3. If manual: follow steps 1–7; add env vars and (if paid) disk at `/app/data`.  
4. If Blueprint: add `render.yaml`, then create the service from the blueprint and set secrets in the dashboard.  
5. After deploy: test `https://<name>.onrender.com`, `/api/health`, and one full flow (assessment + research/report if keys are set).

Nothing else is required for a basic deploy; the app and Dockerfile are ready.
