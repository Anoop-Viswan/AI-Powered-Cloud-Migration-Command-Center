# Secrets and environment variables: local vs cloud

The app reads **all configuration from the process environment** (`os.getenv(...)`). Locally we use a `.env` file; in the cloud you use the platform’s secret or env mechanism. The same variable names apply everywhere.

---

## 1. Local development

- **Use:** A **`.env`** file in the project root (copy from `.env.example`). Never commit `.env` (it’s in `.gitignore`).
- **Loading:** The backend and scripts load `.env` via `python-dotenv` at startup. See [ENV-Reference](../Setup-and-Reference/ENV-Reference.md) and [Config-and-Env](../Setup-and-Reference/Config-and-Env.md).

---

## 2. Cloud: where secrets come from

| Environment | Where secrets live | How the app gets them |
|-------------|--------------------|------------------------|
| **Render** | Render dashboard → your Web Service → **Environment**: add key/value; mark API keys as **Secret**. | Render injects them as **environment variables** at container start. The app reads `os.environ`; no `.env` file in the image. |
| **GitHub Actions (CI)** | Repo → **Settings → Secrets and variables → Actions**: add e.g. `PINECONE_API_KEY`, `OPENAI_API_KEY`. | The workflow passes them into the job with `env: PINECONE_API_KEY: ${{ secrets.PINECONE_API_KEY }}`. Used only for the optional `interface-checks` job. |
| **Other clouds (ECS, Cloud Run, etc.)** | Each platform has its own “environment variables” or “secrets” UI (e.g. AWS ECS task definition, Cloud Run env vars). | You set the same variable names there; the platform injects them into the process. |

So: **locally = `.env`**; **in the cloud = platform env vars** (Render dashboard, GitHub Secrets for CI, etc.). No `.env` file is deployed.

---

## 3. Using Azure Key Vault or AWS Secrets Manager (future)

The app does **not** talk to Key Vault or Secrets Manager directly. It only reads **environment variables**. So any secret store is supported as long as you **fill the environment before the app process starts**.

### Pattern: fetch secrets at startup, then start the app

1. **Before** starting `uvicorn` (or the Docker `CMD`), run a small script or one-off step that:
   - Calls **Azure Key Vault** or **AWS Secrets Manager** (using that platform’s SDK or CLI),
   - Reads the secret values (e.g. `PINECONE_API_KEY`, `OPENAI_API_KEY`),
   - **Exports them as environment variables** (e.g. `export PINECONE_API_KEY=...`), or writes a temporary `.env` that you then `source` or load.
2. **Then** start the app in the same process (or child process that inherits the env). The app sees `os.environ` and works as usual.

### Example: Render with a custom start command

Instead of the default Docker `CMD`, you can set a **custom start command** that:

1. Fetches secrets from Azure or AWS (e.g. a script that uses `azure-keyvault-secrets` or `boto3` and exports env vars),
2. Starts the app in the same shell so it inherits those vars.

Example (conceptual):

```bash
# Example: fetch from Azure Key Vault and export, then start app
# (You’d install azure-identity + azure-keyvault-secrets in the image or a prior step.)
python -c "
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import os
cred = DefaultAzureCredential()
client = SecretClient(vault_url=os.environ['AZURE_KEY_VAULT_URL'], credential=cred)
os.environ['PINECONE_API_KEY'] = client.get_secret('PINECONE-API-KEY').value
os.environ['OPENAI_API_KEY'] = client.get_secret('OPENAI-API-KEY').value
# ... export other keys ...
"
export PINECONE_API_KEY OPENAI_API_KEY  # if your script wrote them to a file or you need to re-export
uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-7860}
```

In practice you’d use a small wrapper script (or Render’s “Pre-Deploy Command” if it runs in the same env as the service). The important point: **the app never needs to know about Key Vault or AWS SM**; it only sees `os.environ` after you’ve populated it.

### Example: AWS (ECS, Lambda, or EC2)

- **ECS:** Use [AWS Secrets Manager integration with ECS](https://docs.aws.amazon.com/AmazonECS/latest/userguide/specifying-sensitive-data-secrets.html): you reference secrets in the task definition; ECS injects them as env vars. No code change in the app.
- **EC2 / custom AMI:** In user data or a start script, fetch secrets (e.g. `aws secretsmanager get-secret-value`) and export them before starting the app.
- **Lambda:** Use Lambda environment variables (which can be populated from Secrets Manager via template or IaC).

### Summary

| Store | How it’s used with this app |
|-------|-----------------------------|
| **Render env vars** | Set in dashboard; Render injects as env. No extra work. |
| **GitHub Secrets** | In CI only; workflow passes them to the job. |
| **Azure Key Vault** | Add a startup step that fetches secrets and sets `os.environ` (or a temp `.env`), then start the app. App code unchanged. |
| **AWS Secrets Manager** | Use ECS secrets injection, or a startup script that fetches and exports env vars, then start the app. App code unchanged. |

The app stays **env-only**; you choose how to fill that env in each environment (local `.env`, Render env, Key Vault at startup, AWS SM, etc.). No special “Key Vault” or “Secrets Manager” integration is required inside the app.

---

## 4. Reference

- **Variable list and defaults:** [Setup-and-Reference/ENV-Reference.md](../Setup-and-Reference/ENV-Reference.md)
- **Render step-by-step (including env):** [Deploy-Render.md](Deploy-Render.md)
- **CI and GitHub Secrets:** [CICD-Pipeline.md](CICD-Pipeline.md)
