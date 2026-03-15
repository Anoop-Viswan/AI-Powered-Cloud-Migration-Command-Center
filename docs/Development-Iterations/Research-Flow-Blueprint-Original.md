# Research Flow – Blueprint (Explainability, Confidence, Official Docs, Live Updates)

**Status:** Design for sign-off  
**Purpose:** Define how the Research step works today, the intended flow (KB → confidence → explainability → official-doc research when low confidence), live updates to the user, and tool integration (Tavily/MCP). This document is the **blueprint** for implementation; no code changes until approved.

---

## 1. Current State (As-Is)

### 1.1 How research is done today

| Step | What happens | Gaps |
|------|----------------|------|
| 1 | **Query build** – A single search query is built from profile: `application_name`, `business_purpose`, `description`, `tech_stack`, `database_types`, `target_environment`, plus the word "migration". | No structured queries (e.g. separate “origin”, “destination”, “workload type”). No explainability. |
| 2 | **KB search** – `semantic_search.search_knowledge_base()` is called with that query, `top_k=8`. Pinecone returns **hits with `_score` and metadata** (`file_path`, `category`, `application`, `content`). | The Research Agent **discards scores and metadata** and only passes **raw content chunks** to the LLM. No confidence score, no “why this match,” no source/origin/destination. |
| 3 | **LLM synthesis** – All chunks are concatenated into one context string. A single LLM call (system + user message) produces one **approach document** (markdown: strategy, steps, best practices, pitfalls, references). | No staged reasoning. No “we matched because …”. No distinction between “from KB” vs “from official docs.” No streaming; user sees nothing until the full response is done. |
| 4 | **Output** – The approach document is stored and shown in the Admin UI as one block of text. | No live updates. No references to specific KB documents or official guides. |

### 1.2 Where scores and metadata exist but are unused

- **Pinecone** returns `_score` (relevance) and fields: `file_path`, `category`, `application`, `content`.
- **Research Agent** (`research_agent.py`) today does:  
  `[h.fields.get("content", "") for h in results.result.hits]`  
  So **scores and metadata are not used**.
- The **Search API** (`/api/search`) already returns `score`, `file_path`, `category`, `application` per hit; the Research Agent does not use that API and instead calls `_search_kb()` which strips that information.

### 1.3 Web search / official docs

- **Tavily (or other web search) is not implemented.** The Tool Gateway design exists (see [TOOL_GATEWAY_DESIGN.md](./TOOL_GATEWAY_DESIGN.md)) and the extension guide describes how to add Tavily as a direct tool or via MCP. No code yet.
- There is **no “official documentation” path** (e.g. “if target is Azure → search Microsoft official migration guide”; “if Snowflake → Snowflake migration guides”). That would be implemented via the same Tool Gateway (e.g. Tavily with targeted queries, or a dedicated “official docs” tool).

---

## 2. Intended Research Flow (To-Be)

High-level flow that you described:

1. **First: look at the KB** with a **clear confidence score**.
2. **If we hit a match:** explain **why** (e.g. origin/destination same, which features match the incoming request).
3. **If confidence is below a low threshold:** inform the Architect and **do research from official documents** (e.g. Azure → Microsoft official guide; Snowflake → Snowflake migration guides).
4. **Bring research findings**, summarize with **reference to official documentation and rationale** (why this step should be followed).
5. **Show all of this as live updates** to the user (like Cursor’s plan/thinking).

Below is the same flow in concrete, implementable form.

---

### 2.1 Phase A: KB lookup and confidence

- **Structured query(ies)**  
  Instead of one free-text query, we derive one or more queries from the profile, e.g.:
  - **Origin/destination:** e.g. “on-prem to Azure migration”, “Oracle to Snowflake”.
  - **Workload/stack:** tech_stack, database_types, data volume, RTO/RPO.
  - **Use case:** application_name + business_purpose + “migration assessment”.
- **KB search**  
  Call the same Pinecone search but **keep scores and metadata** for every hit.
- **Confidence score (KB)**  
  A single **0–1 (or 0–100%) “KB confidence”** that answers: “How well does the KB support this request?”
  - **Proposed formula (for sign-off):**
    - If no hits or all scores below a minimum relevance threshold → **0** (or “no match”).
    - Otherwise: combine **top-hit score**, **number of strong hits** (e.g. score > threshold), and **coverage** (do we have hits for both “origin/destination” and “workload” queries?). Exact formula can be:  
      `confidence = f(top_score, count_above_threshold, coverage_flags)`  
      e.g. weighted average of normalized top score and a “coverage” factor.  
  - **Configurable low threshold** (e.g. `RESEARCH_KB_CONFIDENCE_LOW = 0.35`). Below that → “low confidence”; we inform the Architect and trigger official-doc research.

---

### 2.2 Phase B: Explainability (why the match)

When we have KB hits, we must **explain why** they are relevant to this request.

- **Per hit (or per “match group”), expose:**
  - **Source:** `file_path`, `application` (from metadata).
  - **Score:** raw relevance score (and optionally normalized).
  - **Why it matches:** short, structured explanation, e.g.:
    - **Origin/destination:** “Same pattern: on-prem → Azure” (from profile + hit content or metadata).
    - **Features:** “Matches: tech stack (e.g. Java, Spring), database (PostgreSQL), RTO/RPO in range.”
  - This “why” can be:
    - **Rule-based:** compare profile fields to metadata and a short summary of the chunk (e.g. “contains ‘Azure’ and ‘PostgreSQL’”).  
    - **LLM-generated:** one short LLM call per top hit (or per group): “Given this request profile and this KB chunk, in 1–2 sentences explain why it’s relevant (origin/destination, features).”
- **Aggregate “KB summary” for the Architect:**  
  “We found N hits. Confidence: X%. Top sources: [file1, file2]. Main match reasons: origin/destination alignment, stack match, …”

All of this is part of the **research payload** we can stream and show in the UI (see 2.5).

---

### 2.3 Phase C: Low confidence → inform Architect + official-doc research

- **When KB confidence &lt; low threshold:**
  - **Notify:** “KB confidence is below threshold (X%). Informing Architect and running research from official documentation.”
  - **Official-doc targeting:**
    - **Target platform rules (examples):**
      - `target_environment == "azure"` → search “site:learn.microsoft.com migration guide” (or curated Microsoft official URLs).
      - Snowflake (from profile or tech stack) → “Snowflake migration guide”, “Snowflake best practices”.
      - AWS / GCP → analogous official sources.
    - Queries are **generated from profile** (e.g. “Azure SQL migration”, “Azure Kubernetes migration”) and passed to **web search**.
- **Web search**  
  Implemented via **Tool Gateway**:
  - **Preferred:** One **direct tool** (e.g. Tavily) registered in the gateway; Research Agent calls `gateway.invoke("web_search", { "query": "...", "max_results": 5 })` (and optionally `sources: ["learn.microsoft.com"]` or similar).
  - **Alternative:** MCP server that exposes a search tool; gateway discovers and invokes it (same interface from the agent’s perspective).
- **Findings**  
  For each (or grouped) official-doc result:
  - **Snippet/summary** (from Tavily or MCP response).
  - **Source URL** (and preferably title).
  - **Rationale:** “Why this step should be followed” – can be one short LLM call: “Given this snippet and the application profile, in one sentence why should the Architect follow this recommendation?”

---

### 2.4 Phase D: Summarize with references and rationale

- **Single “approach document” (or equivalent)** that:
  - States **KB confidence** and **whether official-doc research was run** (and why: low confidence).
  - **KB section:** “From your knowledge base: …” with **references** (file_path, application) and **why matched** (origin/destination, features).
  - **Official-doc section (if any):** “From official documentation: …” with **reference to doc/source** and **rationale** for each (or grouped) recommendation.
- **Traceability:** Every recommendation should be traceable to either a KB source or an official URL (and ideally a short rationale).

---

### 2.5 Phase E: Live updates (streaming) to the user

- **Goal:** Show the Architect **live progress**, similar to Cursor’s plan/thinking (incremental updates, not one block at the end).
- **Proposed mechanism:**
  - **Backend:** Research run is **staged** and emits **events** (or chunks) as it progresses, e.g.:
    1. “Searching knowledge base…”
    2. “KB search done. Confidence: X%. Top sources: …”
    3. “Explaining matches…”
    4. “Match explanations done. [summary]”
    5. (If low confidence) “Confidence below threshold. Searching official documentation (e.g. Microsoft / Snowflake)…”
    6. “Official-doc search done. [N results]”
    7. “Summarizing with references and rationale…”
    8. “Approach document ready.”
  - **Transport:** Either **Server-Sent Events (SSE)** or **WebSocket** from backend to frontend. Recommendation: **SSE** for simplicity (one-way server→client), unless we need bidirectional control (e.g. “cancel research”) in the same channel, in which case WebSocket is an option.
- **API shape (conceptual):**
  - **Start research (streaming):** e.g. `POST /api/assessment/{id}/research/stream` that returns a **stream** (SSE or chunked JSON).
  - **Event types (examples):**  
    `phase`, `kb_results`, `confidence`, `match_explanations`, `official_search_start`, `official_search_results`, `rationale`, `approach_section`, `done`, `error`.
- **Frontend:** Admin “Run research” triggers the streaming endpoint and **appends** each event to a **live log/panel** (e.g. “Research progress” with timestamps and expandable sections for KB hits, confidence, official-doc results, and final approach). Final approach document is still shown in the existing “Approach document” / “Report” area.

---

## 3. Tool Integration (Tavily / MCP)

- **Standard interface:** All external tools (Tavily, future Teams/email, etc.) go through the **Tool Gateway** ([TOOL_GATEWAY_DESIGN.md](./TOOL_GATEWAY_DESIGN.md)).
- **Web search:**
  - **Option A – Direct tool:** Implement a Tavily client (REST) in `backend/services/tool_gateway/direct_tools/tavily_search.py`; register it as `web_search` (or `tavily_search`); Research Agent calls `gateway.invoke("web_search", {"query": "...", "max_results": 5, "sources": ["learn.microsoft.com"]})` when confidence is low.
  - **Option B – MCP:** Run or connect to an MCP server that exposes a search tool (e.g. Tavily MCP). Gateway acts as MCP client; Research Agent still calls `gateway.invoke("web_search", {...})`; the gateway routes to the MCP server. Same agent code, different backend.
- **Recommendation:** Start with **Option A (direct Tavily)** for speed and clarity; add MCP later if we want to plug in multiple search providers or Cursor-style tools without changing agent logic.
- **Official-doc targeting:** Implemented as **query construction** in the Research Agent (e.g. “Azure migration guide site:learn.microsoft.com”) and/or as parameters to the tool (e.g. `sources: ["learn.microsoft.com"]` if Tavily supports it). No separate “official docs tool” required if web_search is flexible enough.

---

## 4. Data Structures (Summary)

| Concept | Shape (for API / streaming) |
|--------|-----------------------------|
| **KB hit** | `{ "score", "file_path", "application", "category", "content_preview", "why_match" }` |
| **KB confidence** | `{ "value": 0.0–1.0, "label": "high" \| "medium" \| "low", "below_threshold": bool }` |
| **Match explanation** | `{ "hit_id_or_index", "source", "reason": "origin/destination" \| "features" \| "both", "summary": "…" }` |
| **Official-doc result** | `{ "title", "url", "snippet", "rationale": "…" }` |
| **Stream event** | `{ "type": "phase" \| "kb_results" \| "confidence" \| … , "payload": { … }, "ts": "ISO8601" }` |

(Exact field names can be refined in implementation; this is the intended semantics.)

---

## 5. Configuration and thresholds

- **KB confidence low threshold:** e.g. `RESEARCH_KB_CONFIDENCE_LOW=0.35` (env). Below this → run official-doc research.
- **Minimum relevance score:** Hits below this Pinecone score are ignored for confidence (e.g. `RESEARCH_KB_MIN_SCORE=0.5` or similar, depending on Pinecone’s scale).
- **Web search:** Only when KB confidence &lt; threshold; optional kill switch: `RESEARCH_OFFICIAL_DOCS_ENABLED=true/false`.
- **Tavily:** `TAVILY_API_KEY`; if missing, official-doc step can log “Tavily not configured” and still produce KB-only output with a clear message.

---

## 6. Implementation Order (Proposed)

| Phase | Deliverable | Notes |
|-------|-------------|--------|
| **1** | **KB confidence + structured hits** | Research Agent uses full hit payload (score, file_path, application). Compute KB confidence; expose in response (and later in stream). No UI streaming yet. |
| **2** | **Explainability (why match)** | Per top hit (or group), add “why_match” (rule-based or one short LLM call). Include in API response. |
| **3** | **Tool Gateway + Tavily** | Implement Tool Gateway (registry + invoke); add Tavily as `web_search`. Research Agent calls it when confidence &lt; threshold. |
| **4** | **Official-doc targeting + rationale** | Query construction for Azure/Microsoft, Snowflake, etc.; store results with URL and rationale; append to approach document with references. |
| **5** | **Streaming API + live updates** | `POST /api/assessment/{id}/research/stream` (SSE); emit phase, kb_results, confidence, match_explanations, official_search_*, approach_section, done. Frontend consumes stream and shows live “Research progress” panel. |
| **6** | **Polish** | Thresholds in .env; “Inform Architect” messaging; optional MCP adapter for web search. |

---

## 7. Out of scope (for this blueprint)

- **Authentication / authorization** for Admin vs Application User (unchanged).
- **Summarizer Agent** changes (still consumes approach document; could later consume structured KB + official-doc sections).
- **Notifications** (e.g. email to Architect when confidence is low) – can be a later addition via Tool Gateway.
- **Multiple KB namespaces** or multi-tenant search (current single project namespace remains).

---

## 8. Sign-off

This blueprint describes:

1. **Current state:** Research = one query → KB chunks (no scores/metadata) → one LLM call → one approach doc; no confidence, no explainability, no web search, no streaming.
2. **Intended flow:** KB with confidence → explain why match (origin/destination, features) → if low confidence, inform Architect and run official-doc research (Azure/Snowflake/…) via Tool Gateway (Tavily or MCP) → summarize with references and rationale → **live updates** to the user (streaming).
3. **Tool integration:** Via Tool Gateway; Tavily as first web search (direct tool); MCP optional.
4. **Data structures and streaming** for explainability and live UX.

If this matches your intent, we can treat it as the **signed-off design** and implement in the order of §6. Any changes you want (e.g. confidence formula, threshold defaults, or event names) can be noted here before implementation.
