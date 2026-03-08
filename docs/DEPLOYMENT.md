# Deployment options

You have two main paths: **Hugging Face Spaces (Docker)** or **any cloud** (AWS, GCP, Azure, etc.). Both use the **same container**—you only need to containerize once.

---

## Do you need to containerize?

**Yes.** This app is a full-stack service (FastAPI + React). To run it on Hugging Face or in the cloud you need a single **Docker image** that:

1. Builds the React frontend.
2. Runs the FastAPI backend and serves the built frontend on the same port.

The repo includes a **Dockerfile** and **.dockerignore** for that. The same image works for Hugging Face Spaces and for cloud container platforms.

---

## Option 1: Hugging Face Spaces (Docker Space)

Hugging Face Spaces can run **Docker** apps. You don’t need a separate cloud account; you containerize and deploy the image to a **Docker Space**.

### Steps

1. **Create a new Space**
   - Go to [huggingface.co/spaces](https://huggingface.co/spaces).
   - Click **Create new Space**.
   - Choose **Docker** as the SDK (not Gradio/Streamlit).
   - Name the Space and set visibility (public/private).

2. **Push your code (with Dockerfile)**
   - Clone the Space repo and copy in this project (or push from this repo).
   - Ensure the **Dockerfile** is at the root of the Space repo (same as in this project).
   - Commit and push. HF will build the image and run it. The Space expects the app to listen on **port 7860** (the Dockerfile already uses this).

3. **Configure secrets**
   - In the Space → **Settings** → **Repository secrets**, add:
     - `PINECONE_API_KEY` – required for search and indexing.
     - `OPENAI_API_KEY` – optional; for LLM-summarized chat.
   - You can also set **Variables** (non-secret): e.g. `PINECONE_PROJECT_DIR`, `OPENAI_MODEL`, `OPENAI_TEMPERATURE`.

4. **Project directory (documents)**
   - The app expects a **directory path** where your migration documents live (`PINECONE_PROJECT_DIR`). In a Space you don’t have a long-lived filesystem by default.
   - Options:
     - **Use a Hugging Face Dataset:** Download or mount your docs into a path (e.g. `/data`) and set `PINECONE_PROJECT_DIR=/data`. You’d need a small entrypoint or init step that fetches the dataset into `/data` before starting the app (or use a Space with a persistent volume if available).
     - **Demo without docs:** Leave `PINECONE_PROJECT_DIR` unset. The UI will load; search/chat will return a “project dir not configured” style message until you point it at a directory with indexed documents.
   - For a quick **public demo**, you can index a small set of documents once (e.g. from a dataset) into Pinecone and set the project dir to that path in the Space.

5. **Pinecone index**
   - Create the index **`coe-kb-search`** in the Pinecone console (or via CLI) as in the main README. The Space uses the same Pinecone index; only the app is hosted on HF.

### Summary (HF)

| Item        | Action |
|------------|--------|
| Container  | Use the project **Dockerfile** (already uses port 7860). |
| Secrets     | `PINECONE_API_KEY`; optionally `OPENAI_API_KEY`. |
| Variables   | `PINECONE_PROJECT_DIR` (if you have a path with docs), `OPENAI_MODEL`, etc. |
| Documents   | Provide a dir (e.g. via dataset or volume) or run in “no project dir” mode for UI-only demo. |

---

## Option 2: Cloud (AWS, GCP, Azure, etc.)

Use the **same Docker image** on any container platform.

1. **Build the image**
   ```bash
   docker build -t migration-command-center:latest .
   ```

2. **Run locally (test)**
   ```bash
   docker run -p 7860:7860 \
     -e PINECONE_API_KEY=your-key \
     -e PINECONE_PROJECT_DIR=/data \
     -v /path/to/your/docs:/data \
     migration-command-center:latest
   ```
   Open `http://localhost:7860`. Set `OPENAI_API_KEY` if you want chat summarization.

3. **Deploy to cloud**
   - **AWS:** Push image to ECR, run on ECS (Fargate) or EKS. Set env vars and mount a volume or use S3 + init for document directory if needed.
   - **GCP:** Push to Artifact Registry, run on **Cloud Run** (`gcloud run deploy --image=...`) or GKE. Use env vars and optionally Cloud Storage + startup script for docs.
   - **Azure:** Push to ACR, run on **Container Apps** or AKS. Same idea: env vars and optional volume/Storage for documents.

4. **Production details**
   - **Secrets:** Prefer the platform’s secret manager (e.g. AWS Secrets Manager, GCP Secret Manager) and inject as env vars.
   - **Project directory:** For a persistent document set, use a volume or object storage and sync to a local path at startup (or run indexing as a separate job and only run the app with `PINECONE_PROJECT_DIR` pointing at a pre-filled volume).
   - **Scaling:** Scale the container as needed; Pinecone and OpenAI are external and stateless.

---

## Comparison

|                         | Hugging Face Spaces (Docker)     | Cloud (ECS, Cloud Run, etc.)   |
|-------------------------|----------------------------------|---------------------------------|
| **Containerize?**       | Yes (same Dockerfile)            | Yes (same image)                |
| **Cost**                | Free tier available              | Pay for compute + Pinecone/OpenAI |
| **Secrets**             | Space secrets + variables       | Platform secret manager        |
| **Documents / project dir** | Dataset or volume; or UI-only   | Volume or object storage       |
| **Best for**            | Demos, sharing, quick public app  | Production, full control, scale |

**Bottom line:** You do need to containerize. Once you have the Docker image, you can deploy it on **Hugging Face** (Docker Space) or **any cloud** without changing the app code.
