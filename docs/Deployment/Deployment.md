# Deployment guide (V0.1 → cloud or non-local)

This document lists **all changes needed** to deploy the app beyond local, then compares **deployment options** with pros and cons so you can pick one.

---

## Part 1: Changes needed for deployment

### 1.1 Environment and secrets

| Item | Current | Change for deployment |
|------|--------|------------------------|
| **API keys** | In `.env` on disk | Never commit `.env`. In cloud: use the platform’s **secrets / env vars** (e.g. Railway “Variables”, Render “Environment”, AWS Secrets Manager) for `PINECONE_API_KEY`, `OPENAI_API_KEY`, `TAVILY_API_KEY`, `LANGCHAIN_API_KEY`, etc. |
| **`.env` location** | Loaded from project root | In Docker, project root is `/app`. Either (a) build-time or runtime env vars set by the platform, or (b) mount a secret file at `/app/.env` if the platform supports it. Prefer platform env vars so secrets aren’t in the image. |
| **`ALLOWED_ORIGINS`** | Optional; defaults include localhost | Set to your deployed frontend origin(s), e.g. `https://your-app.fly.dev` or `https://your-app.onrender.com`. Comma-separated if multiple. |

### 1.2 Data persistence

| Item | Current | Change for deployment |
|------|--------|------------------------|
| **SQLite files** | `data/assessments.db`, `data/diagnostics.db` under project root | In Docker, project root is `/app`, so data is `/app/data/`. **Persist** `/app/data` via a **volume** (or cloud disk) so restarts don’t wipe assessments and diagnostics. |
| **Uploads & diagrams** | `data/assessment_uploads/`, `data/assessment_diagrams/` | Same as above: under `data/`. As long as `data/` is on a persistent volume, uploads and diagram artifacts persist. |
| **Optional: configurable data dir** | Paths hardcoded as `root / "data"` | For flexibility (e.g. external NFS or different paths per env), introduce a `DATA_DIR` env var and refactor stores to use it (see “Optional code changes” below). |

### 1.3 Dockerfile

- The frontend build stage uses `npm ci` (with devDependencies) so that `vite` and other build tools are available for `npm run build`. The final image only copies the built `dist/` into `static/`, so no Node or dev deps are in the running container.
- Add a **`.dockerignore`** (if not present) with at least: `venv`, `.env`, `__pycache__`, `node_modules`, `.git`, `*.db`, so the build is fast and secrets aren’t copied.

### 1.4 Port and process

| Item | Current | Change for deployment |
|------|--------|------------------------|
| **Port** | Local: 8000 (uvicorn). Dockerfile: **7860** (Hugging Face Spaces) | Decide one: either keep **7860** and set the platform’s “port” to 7860, or change Dockerfile to **8000** and use that everywhere. Document the chosen port. |
| **Bind** | Dockerfile already uses `--host 0.0.0.0` | No change; required for cloud. |
| **Health check** | `GET /api/health` exists | Configure the platform’s health check to call `GET /api/health` (and optionally `GET /` for “app up”). |

### 1.5 Frontend and static

| Item | Current | Change for deployment |
|------|--------|------------------------|
| **Build** | `npm run build` in Dockerfile (frontend stage) | No change; Dockerfile already builds and copies `dist` to `static/`. |
| **API base** | Frontend uses relative `/api` (proxy in dev) | In production the same origin serves the app and API, so relative `/api` is correct. No change if you serve the app from the same host (single container). |
| **SPA fallback** | FastAPI mounts `StaticFiles` with `html=True` | Ensures `/admin`, `/assessment/...` etc. serve `index.html`. Already in place. |

### 1.6 Optional code changes (for flexibility)

- **`DATA_DIR` env**: Add `get_data_dir() -> Path` in `backend/config.py` (e.g. `os.getenv("DATA_DIR")` or default `root / "data"`). Refactor `assessment/store.py`, `diagnostics/store.py`, `diagram_export.py`, and `assessment.py` upload path to use it. Useful if different environments use different mount points.
- **Port from env**: Use `PORT` env in Dockerfile CMD (e.g. `--port ${PORT:-8000}`) so platforms that inject `PORT` work without rebuilding.
- **`.env` in Docker**: If you don’t use platform env vars, ensure `.env` is not in the image (add to `.dockerignore`); inject at runtime via volume or secret.

### 1.7 Checklist summary

- [ ] All secrets in platform env vars (no `.env` in repo/image).
- [ ] `ALLOWED_ORIGINS` set to deployed frontend URL(s).
- [ ] Persistent volume (or disk) for `data/` (or `DATA_DIR`).
- [ ] Port: 7860 or 8000, consistent and set in platform.
- [ ] Health check: `GET /api/health`.
- [ ] (Optional) `DATA_DIR` and/or `PORT` from env for portability.

---

## Part 2: Deployment options (pros & cons)

### Option A: Docker on a managed “single app” platform (Railway, Render, Fly.io)

**Idea:** Build the existing Dockerfile; platform runs the container and gives you a URL. You attach a volume for `data/`.

| Pros | Cons |
|------|------|
| Minimal change: existing Dockerfile works. | SQLite + single instance only; not ideal for horizontal scaling. |
| One dashboard: build, env, logs, volume. | Volume persistence and backup are platform-dependent (e.g. Render free tier ephemeral disk). |
| Usually free or low-cost tier to try. | You must set env vars and (if needed) port (7860 vs 8000). |
| Good fit for V0.1 and internal/demo. | |

**Best for:** Fastest path to “running in cloud”, demos, small teams.  
**Example platforms:** Railway, Render, Fly.io.

---

### Option B: Docker on “serverless” containers (GCP Cloud Run, AWS App Runner)

**Idea:** Push the same Docker image to Cloud Run or App Runner; they run it as a container and scale (including to zero) and handle HTTPS.

| Pros | Cons |
|------|------|
| Auto-scaling and HTTPS out of the box. | **Ephemeral filesystem**: container restarts can wipe local `data/`. You must either (1) use a **volume mount** (Cloud Run supports this; App Runner has limits) or (2) move DB and files to external storage (e.g. Cloud SQL + GCS, or RDS + S3). |
| Pay-per-request possible (scale to zero). | More setup if you move off SQLite (migrations, connection strings). |
| Good for production patterns (GCP/AWS). | Cold starts on first request. |

**Best for:** Production on GCP/AWS when you’re ready to use managed DB and object storage, or when you can attach a persistent volume (e.g. Cloud Run with volume).  
**Examples:** GCP Cloud Run (with volume or Cloud SQL), AWS App Runner.

---

### Option C: Single VPS (DigitalOcean Droplet, EC2, etc.) + Docker Compose

**Idea:** Rent one VM; run Docker Compose that starts the app container and a volume for `data/`. Optionally add Nginx for TLS and a single domain.

| Pros | Cons |
|------|------|
| Full control; one place for app + data. | You manage OS, updates, TLS (e.g. Let’s Encrypt), backups. |
| SQLite and file storage are simple (bind mount or named volume). | No auto-scaling; single point of failure. |
| No need to change to Postgres/S3 for V0.1. | Slightly more ops than Option A. |

**Best for:** Simple production or staging where one server is enough and you’re fine with a single instance.  
**Examples:** DigitalOcean Droplet, AWS EC2, Linode.

---

### Option D: PaaS without Docker (e.g. Heroku, older PaaS)

**Idea:** Deploy via buildpack (Python + Node) or a manifest; platform runs the process(es). No Docker.

| Pros | Cons |
|------|------|
| No Docker to maintain if you prefer buildpacks. | Requires adapting to platform (e.g. `PORT` from env, possibly separate frontend build step). |
| Managed runtimes and scaling. | Many PaaS options prefer or require Postgres and external storage for uploads; SQLite on ephemeral disk is not durable. |
| | Our app is already container-ready; adding a non-Docker path is extra work. |

**Best for:** Teams already on a specific PaaS. Less ideal for this repo as-is because we’re Docker-first and use SQLite + local files.

---

### Option E: Kubernetes (EKS, GKE, AKS)

**Idea:** Run the app as a Deployment with a persistent volume; optionally Ingress and TLS.

| Pros | Cons |
|------|------|
| Strong production and scaling story. | Overkill for V0.1; more YAML and concepts (PV/PVC, Ingress, secrets). |
| Fits existing enterprise K8s. | Same as Option B: for multi-replica you’d move off SQLite to a shared DB and object storage. |

**Best for:** Later when you need multi-replica, high availability, or are already on K8s. Not recommended for first cloud deploy of V0.1.

---

## Recommendation for V0.1

- **Fastest and simplest:** **Option A** (Railway, Render, or Fly.io) with the existing Dockerfile, one persistent volume for `data/`, and env vars for secrets and `ALLOWED_ORIGINS`.
- **If you prefer a VPS and full control:** **Option C** (single VPS + Docker Compose).
- **If you’re on GCP/AWS and want “serverless” containers:** **Option B**, with a plan to attach a volume or migrate to managed DB + object storage so data survives restarts.

Once you pick an option, the next step is to apply the checklist in Part 1 and (if needed) add a small `docker-compose.yml` and/or platform-specific notes. **For Render:** see **[DEPLOY_RENDER.md](DEPLOY_RENDER.md)** for step-by-step instructions (API keys, persistent disk, cost).
