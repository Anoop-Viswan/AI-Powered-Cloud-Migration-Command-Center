# Research flow (final)

How the Assessment research step works: KB lookup with confidence and explainability, optional official-document search when confidence is low, and live updates to the user.

---

## 1. Overview

1. **KB lookup** – Structured queries from the application profile (origin/destination, workload, use case) are run against the knowledge base (Pinecone). Scores and metadata are kept for every hit.
2. **Confidence** – A 0–1 KB confidence score is computed from top-hit score, number of strong hits, and coverage. A configurable low threshold (e.g. `RESEARCH_KB_CONFIDENCE_LOW=0.35`) determines whether official-doc research is triggered.
3. **Explainability** – For each hit we expose source (`file_path`, `application`), score, and a short “why it matches” (origin/destination, features).
4. **Low confidence path** – When confidence is below threshold, the system searches official documentation (e.g. Microsoft, Snowflake) via the Tool Gateway (e.g. Tavily). Findings are summarized with source URLs and rationale.
5. **Approach document** – A single approach document is produced that states KB confidence, whether official-doc research was run, KB section with references and match reasons, and (if any) official-doc section with references and rationale.
6. **Live updates** – Progress is streamed to the Admin UI via Server-Sent Events (SSE): e.g. “Searching KB…”, “KB confidence: X%”, “Searching official docs…”, “Approach document ready.”

---

## 2. KB lookup and confidence

- **Queries** are derived from the profile: origin/destination (e.g. “on-prem to Azure”), workload/stack (tech_stack, database_types, RTO/RPO), and use case (application_name + business_purpose + “migration assessment”).
- **KB search** returns full hits (score, `file_path`, `application`, `category`, `content`).
- **Confidence** is computed from top score, count of hits above a relevance threshold (`RESEARCH_KB_MIN_SCORE`), and coverage. Below `RESEARCH_KB_CONFIDENCE_LOW` → official-doc research is triggered (when `RESEARCH_OFFICIAL_DOCS_ENABLED` is true).

---

## 3. Explainability (why the match)

For each relevant hit we provide:

- **Source:** `file_path`, `application` from metadata.
- **Score:** relevance score.
- **Why it matches:** short rule-based or LLM-generated explanation (origin/destination alignment, stack/features match).

---

## 4. Official-document research (low confidence)

- **Targeting:** e.g. target_environment “Azure” → search Microsoft learn; Snowflake → Snowflake migration guides. Queries are built from the profile and sent to web search via the Tool Gateway.
- **Tool:** Implemented as a direct Tavily tool in the gateway; Research Agent invokes it when confidence is low.
- **Output:** Snippets, source URLs, and (optionally) a short rationale per finding. These feed into the approach document.

---

## 5. Summarization and streaming

- **Approach document** includes KB confidence, whether official-doc research ran, KB section with references and match reasons, and official-doc section with references and rationale when applicable.
- **Streaming:** Backend emits SSE events (phase, kb_results, confidence, match_explanations, official_search_*, approach_section, done, error). The Admin UI shows a live research progress panel and the final approach in the Report area.

---

## 6. Configuration (env)

| Variable | Purpose |
|----------|---------|
| `RESEARCH_KB_MIN_SCORE` | Min relevance score for a “strong” hit (default 0.5). |
| `RESEARCH_KB_CONFIDENCE_LOW` | Below this confidence we trigger official-doc research (default 0.35). |
| `RESEARCH_OFFICIAL_DOCS_ENABLED` | Set to `false` to disable official-doc search. |

All external tools (e.g. Tavily) go through the Tool Gateway; see [Tool-Gateway.md](Tool-Gateway.md) in this directory.
