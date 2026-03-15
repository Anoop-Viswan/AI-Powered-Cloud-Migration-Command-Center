# Environment variables (.env)

Copy `.env.example` to `.env` and fill in your keys. **Do not commit `.env`** (it is in `.gitignore`).

**Cloud and other secret stores:** For Render, GitHub Actions, and using Azure Key Vault or AWS Secrets Manager, see [Deployment/Secrets-in-Cloud.md](../Deployment/Secrets-in-Cloud.md). **CI (GitHub Actions):** API keys from Secrets; optional config (e.g. OPENAI_MODEL, LLM_PROVIDER) from Variables or defaults — see [Deployment/CI-Config-and-Rerun.md](../Deployment/CI-Config-and-Rerun.md).

**When is .env loaded?** The backend loads `.env` once at startup. If you change `.env` later, either restart the server or use **Admin → Knowledge Base → “Reload .env”** (or `POST /api/admin/reload-env`) to re-read it once. See [CONFIG_AND_ENV.md](CONFIG_AND_ENV.md) for the full architecture.

| Variable | Required | Description |
|----------|----------|-------------|
| **ADMIN_USERNAME** | When protecting Admin | Username for Admin login. When both ADMIN_USERNAME and ADMIN_PASSWORD are set, the Admin area requires sign-in. |
| **ADMIN_PASSWORD** | When protecting Admin | Password for Admin login. Set in Render as a **Secret**. |
| **PINECONE_API_KEY** | Yes | Pinecone API key from [app.pinecone.io](https://app.pinecone.io/) |
| **PINECONE_PROJECT_DIR** | For search/seed | Project directory to index and search (or pass `--project-dir`) |
| **PINECONE_SPEND_LIMIT** | No | Spend guardrail in USD (default 10). Script blocks when estimated usage reaches this. |
| **PINECONE_ALLOW_OVER_LIMIT** | No | Set to `yes` to allow usage beyond spend limit (explicit permission) |
| **LLM_PROVIDER** | No | `openai` (default), `anthropic`, or `azure_openai` |
| **OPENAI_API_KEY** | When LLM=openai | OpenAI API key from [platform.openai.com](https://platform.openai.com/) |
| **OPENAI_MODEL** | No | e.g. `gpt-4o-mini` (default), `gpt-4o` |
| **OPENAI_TEMPERATURE** | No | Default 0.3 |
| **OPENAI_MAX_TOKENS** | No | Default 4096 |
| **ANTHROPIC_API_KEY** | When LLM=anthropic | From [console.anthropic.com](https://console.anthropic.com/) |
| **ANTHROPIC_MODEL** | No | e.g. `claude-3-5-sonnet-20241022` |
| **AZURE_OPENAI_ENDPOINT** | When LLM=azure_openai | Azure OpenAI endpoint URL |
| **AZURE_OPENAI_API_KEY** | When LLM=azure_openai | Azure OpenAI API key |
| **AZURE_OPENAI_DEPLOYMENT** | When LLM=azure_openai | Deployment name (e.g. `gpt-4o-mini`) |
| **LANGCHAIN_TRACING_V2** | No | Set to `true` to enable LangSmith tracing (see below) |
| **LANGCHAIN_API_KEY** | When tracing | LangSmith API key from [smith.langchain.com](https://smith.langchain.com/) |
| **LANGCHAIN_PROJECT** | No | LangSmith project name (e.g. `assessment`); traces show under this project |
| **PROFILE_VALIDATION_USE_LLM** | No | `yes` to use LLM for profile validation (extra API call) |
| **PROFILE_CONTENT_VALIDATION_USE_LLM** | No | `true` (default) to use LLM to flag placeholder/nonsense content |
| **RESEARCH_KB_MIN_SCORE** | No | Min Pinecone score for “strong” hit (default 0.5) |
| **RESEARCH_KB_CONFIDENCE_LOW** | No | Below this (0–1) we run official-doc search (default 0.35) |
| **RESEARCH_OFFICIAL_DOCS_ENABLED** | No | `true` (default) or `false` to disable official-doc search |
| **TAVILY_API_KEY** | For official-doc search | Tavily API key from [app.tavily.com](https://app.tavily.com/). If unset, official-doc step is skipped. |

See `.env.example` in the project root for commented examples.

---

## Enabling LangSmith traces

To turn on tracing so every LangChain/LangGraph run (research, summarize, chat, etc.) is sent to LangSmith:

1. **Get an API key:** Sign up at [smith.langchain.com](https://smith.langchain.com/) and create an API key (e.g. under Settings → API Keys).
2. **Add to `.env`:**
   ```bash
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=lsv2_pt_...   # your key
   LANGCHAIN_PROJECT=assessment    # optional; default project name for traces
   ```
3. **Restart the backend** (or use Admin → “Reload .env”) so the new variables are loaded.

After that, runs appear in the LangSmith dashboard under the project name. You can inspect trace trees, token usage, cost, and latency per step. The app works normally if these variables are not set; tracing is simply off.

**Check status:** Admin → Knowledge Base tab → Feature status panel shows whether LangSmith is configured and enabled.

---

## LangSmith cost

- **Free (Developer) plan:** $0/month, no credit card; includes a limited number of traces per month (e.g. 5,000 base traces). Enough for development and light use.
- **Paid plans:** For higher volume, LangSmith has Plus and Enterprise plans (see [LangSmith pricing](https://www.langchain.com/pricing-langsmith)). Overage is typically per additional traces (e.g. per 1,000 traces).
- **This project:** We do not call LangSmith’s API from our code; we only send traces when you set the env vars above. So the only cost is what LangSmith charges for your usage (free tier or paid). Check their site for current limits and pricing.
