# Deploy with Docker on Render – step-by-step

This guide walks through deploying this app to [Render](https://render.com) using the existing Dockerfile. It covers cost, API key storage, persistent data, and every step from signup to a working URL.

---

## Cost

| Plan | Cost | Limits | Data persistence |
|------|------|--------|------------------|
| **Free** | $0 | 750 instance hours/month, 100 GB bandwidth; service spins down after 15 min idle; **ephemeral disk** (data lost on restart/redeploy) | No |
| **Starter** | ~\$7/month (usage-based) | No spin-down; **persistent disk** available (paid add-on) | Yes, with a disk |

- **To try the app with no cost:** Use the **Free** tier. Your SQLite DB and uploads will be **wiped** on each redeploy or when the service restarts; use only for a quick demo.
- **To keep assessments and diagnostics:** Use a **paid** Web Service (e.g. Starter) and add a **Persistent Disk** mounted at `/app/data`. Disk pricing is on [Render Pricing](https://render.com/pricing).

---

## CI/CD

We recommend **turning on CI before the first deploy**: see [CICD_PIPELINE.md](CICD_PIPELINE.md). The repo includes `.github/workflows/ci.yml` (tests + frontend build). After that, connect this repo to Render so only green builds get deployed.

---

## Prerequisites

- A [GitHub](https://github.com) (or GitLab) account.
- This repo pushed to a GitHub/GitLab repository (Render deploys from Git).
- Your API keys ready (Pinecone, OpenAI, etc.) – you will paste them in Render’s dashboard; do not commit them to the repo.

---

## Step 1: Sign up and connect the repo

1. Go to [render.com](https://render.com) and sign up (e.g. with GitHub).
2. In the Render dashboard, click **New +** → **Web Service**.
3. Connect your Git provider if asked, then select the **repository** that contains this project.
4. Choose the **branch** to deploy (e.g. `main`).

---

## Step 2: Configure as a Docker service

1. **Name:** Set a name (e.g. `coe-migration-app`). This will be part of the URL: `https://<name>.onrender.com`.
2. **Region:** Pick the region closest to you or your users.
3. **Runtime:** Set **Docker** (not Python or Node). Render will use the Dockerfile in the repo root.
4. **Dockerfile path:** Leave blank if the Dockerfile is in the repo root; otherwise set e.g. `./Dockerfile`.
5. **Docker Command:** Leave blank so the image uses its default `CMD` (uvicorn). The Dockerfile is set up to use the `PORT` variable Render provides (default 10000).

---

## Step 3: Add environment variables (API keys and config)

In the same screen, open the **Environment** section and add variables. Render injects these at **runtime** (they are not baked into the image). For secrets, use **Secret Files** or mark values as **Secret** so they are masked in the UI.

**Local vs cloud:** Locally you use a `.env` file; on Render you use the dashboard env vars (no `.env` in the image). For Azure Key Vault or AWS Secrets Manager, see [Secrets-in-Cloud.md](Secrets-in-Cloud.md).

Add every key your app needs. Example (adjust names to match your `.env`):

| Key | Value | Secret? |
|-----|--------|--------|
| `PINECONE_API_KEY` | Your Pinecone API key | Yes |
| `OPENAI_API_KEY` | Your OpenAI API key | Yes |
| `TAVILY_API_KEY` | Your Tavily API key (if you use research/Tavily) | Yes |
| `LANGCHAIN_TRACING_V2` | `true` (optional, for LangSmith) | No |
| `LANGCHAIN_API_KEY` | Your LangSmith API key (optional) | Yes |
| `LANGCHAIN_PROJECT` | `assessment` (optional) | No |
| `ALLOWED_ORIGINS` | `https://<your-service-name>.onrender.com` | No |

- **ALLOWED_ORIGINS:** Replace `<your-service-name>` with the exact name you gave the service (e.g. `https://coe-migration-app.onrender.com`). Add more origins separated by commas if you use a custom domain later.
- **Optional (e.g. Azure/Anthropic):** Add `LLM_PROVIDER`, `ANTHROPIC_API_KEY`, `AZURE_OPENAI_*`, etc., if you use them locally.

To add a variable: click **Add Environment Variable**, enter the key, paste the value, and turn **Secret** on for API keys and tokens.

---

## Step 4: Persistent data (paid plan only)

If you are on a **paid** plan and want assessments and diagnostics to survive restarts and redeploys:

1. In the service creation form, open **Advanced** (at the bottom).
2. Under **Persistent Disks**, click **Add Disk**.
3. **Mount path:** Set **`/app/data`**. The app writes SQLite files and uploads under `data/`; in the container the project root is `/app`, so the data directory is `/app/data`.
4. **Size:** Choose the smallest size that fits your needs (e.g. 1 GB). You can increase it later; you cannot decrease it.

If you skip this (e.g. on the free tier), the app will run but **all data will be lost** on each redeploy or restart.

---

## Step 5: Health check (optional but recommended)

Under **Advanced**:

- **Health Check Path:** Set **`/api/health`**. Render will call this to decide if the service is up.

---

## Step 6: Deploy

1. Click **Create Web Service**. Render will clone the repo, build the Docker image (frontend + backend), and start the container.
2. Watch the **Logs** tab. The first deploy can take a few minutes (build + install). When you see something like “Listening on 0.0.0.0:10000”, the app is running.
3. Open **`https://<your-service-name>.onrender.com`**. You should see the app; use **Admin** and **Diagnostics** as usual.

---

## Step 7: After the first deploy

- **Change env vars or secrets:** Dashboard → your service → **Environment** → edit → **Save Changes**. Render will redeploy.
- **View logs:** **Logs** tab. Use for debugging API key or startup errors.
- **Custom domain:** **Settings** → **Custom Domain** (supported on paid plans).
- **Free tier:** The service will spin down after ~15 minutes of no traffic; the next request may take ~1 minute to wake it up.

---

## Checklist

- [ ] Repo connected; branch selected.
- [ ] Runtime = **Docker**; Dockerfile path correct (or blank if at root).
- [ ] All required env vars added (Pinecone, OpenAI, optional Tavily/LangSmith); API keys marked **Secret**.
- [ ] `ALLOWED_ORIGINS` set to `https://<your-service-name>.onrender.com`.
- [ ] (Paid) Persistent disk added with mount path **`/app/data`**.
- [ ] Health check path **`/api/health`** (optional).
- [ ] First deploy succeeded; app loads at `https://<name>.onrender.com`.

---

## Troubleshooting

- **Blank page or 502:** Wait 1–2 minutes after deploy; on free tier, the instance may be spinning up. Check **Logs** for Python/uvicorn errors.
- **CORS errors:** Ensure `ALLOWED_ORIGINS` exactly matches the URL you use (including `https://`, no trailing slash).
- **“Project dir not configured” or search/KB not working:** Set `PINECONE_PROJECT_DIR` to `/data` if you use the default; for KB you also need a Pinecone index and `PINECONE_API_KEY`. The app does not index local files on Render unless you seed from elsewhere; KB search still works if the index is populated.
- **Data gone after redeploy:** On the free tier the filesystem is ephemeral. Use a paid plan and a persistent disk at `/app/data` to keep data.
