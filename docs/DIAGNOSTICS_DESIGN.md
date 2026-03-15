# Diagnostics Tab – Design (Killer Feature)

**Status:** Design for review (pre-implementation)  
**Goal:** Make Diagnostics the **killer feature** of the project: full visibility into every external interface (LLM, Tavily, Pinecone), usage, cost, thresholds, alerts, and patterns—so teams never underestimate LLM usage, token limits, or spend.

**Related:** [Admin Command Center Design](./ADMIN_COMMAND_CENTER_DESIGN.md), [ENV_REFERENCE](./ENV_REFERENCE.md)

---

## 1. Why “X-Ray” Diagnostics Matters

### The problem

When using LLMs and external APIs, teams often:

- **Underestimate usage** – One “research” run can trigger many LLM calls (research agent, summarizer, architecture design, Mermaid, quality check). Without visibility, it looks like “one click.”
- **Underestimate cost** – Token counts and pricing vary by model; a few heavy sessions can exceed expectations.
- **Hit limits blindly** – Rate limits (OpenAI, Tavily, etc.) or quota caps appear as opaque errors with no prior warning.
- **Miss patterns** – No view of which flows (research vs. chat vs. report) consume the most, or when usage spikes.

### The solution: X-ray visibility

Diagnostics must provide:

1. **Every external interface tracked** – LLM (by provider/model), Tavily, Pinecone, and (optionally) LangSmith linkage.
2. **Per-interface metrics** – Call count, total duration, success vs. error, and (where applicable) tokens and approximate cost.
3. **Configurable thresholds** – Daily/monthly token limits, cost caps, call limits per service.
4. **Alerts** – When a threshold is **approaching** (e.g. 80%) or **exceeded**, with clear in-app messaging and optional export.
5. **Approximate cost** – Per request, per agent, per day; model-aware so admins see real impact.
6. **Patterns** – Usage over time, top consumers (which agent/flow), error rate trends, peak hours.

This document defines the data model, APIs, thresholds, alerts, and UI so implementation is unambiguous.

---

## 1.1 Why custom Diagnostics instead of LangSmith? (Compare & contrast)

We chose a **custom** in-app Diagnostics dashboard rather than relying on LangSmith to power it. Both can show usage and cost; they solve different problems and work best together.

### What LangSmith provides

| Capability | LangSmith |
|------------|-----------|
| **Traces** | Full trace trees (every LLM call, tool call, chain step) with inputs/outputs. Best-in-class for debugging. |
| **Token usage** | Yes – input/output tokens per span, automatic for LangChain LLM calls. |
| **Cost** | Yes – cost tracking per run and aggregated (project stats, dashboards). Token-based cost calculation; customizable pricing. |
| **Where you see it** | In LangSmith’s UI (smith.langchain.com). You leave your app and open their dashboard. |
| **Thresholds / alerts** | Dashboards and visibility; budget/threshold alerts are not a primary feature (no “alert me at 80% of daily spend” in-app in our product). |
| **Non-LangChain calls** | Only if you manually log or wrap them. Tavily invoked via LangChain is traced; raw Pinecone or other HTTP calls may need extra hooks. |
| **Requires** | `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY`. No tracing if not configured. |
| **Data location** | LangSmith cloud. Retention and access follow their product. |

So **LangSmith does provide** tokens, cost, and rich traces – but in **their** UI, with **their** schema and no first-class “set a daily budget and get alerted in our app.”

### What our custom Diagnostics provides

| Capability | Our custom Diagnostics |
|------------|-------------------------|
| **Traces** | No full tree. We have a **request log** (flat list of calls with operation, tokens, latency, status). For deep traces we **link out** to LangSmith. |
| **Token usage** | Yes – we record per call from our instrumentation (e.g. after each `llm.invoke()`). |
| **Cost** | Yes – approximate cost per request/operation/day from our own model-pricing table. |
| **Where you see it** | **Inside our app** – same Admin Command Center as Assessments and Knowledge Base. One place, no context switch. |
| **Thresholds / alerts** | **Yes** – configurable daily token limit, cost limit, “alert at %”. We compute and show “Approaching limit” / “Limit exceeded” in our UI and can add mute/acknowledge. |
| **Non-LangChain calls** | **Yes** – we instrument every interface we care about: LLM, Tavily (tool gateway), Pinecone. One schema, one store. |
| **Requires** | Nothing external. Works with or without LangSmith. |
| **Data location** | Our SQLite (or our DB). We control retention and who can see it. |

### Why we use custom (advantages)

1. **In-app experience** – Admins see Diagnostics next to Assessments and KB. No “go to LangSmith” for day-to-day usage and cost control.
2. **Thresholds and alerts** – We need “alert when daily cost or tokens approach/exceed limit.” That’s first-class in our design; in LangSmith it’s not the main offering. We can also later enforce soft blocks (e.g. warn or block when over limit).
3. **Works without LangSmith** – No API key required. Works in air-gapped or “no external tracing” environments. Cost visibility doesn’t depend on a third-party service.
4. **One place for all interfaces** – We record LLM, Tavily, and Pinecone in one store with one schema. LangSmith is strongest for LangChain traces; we guarantee coverage for every call we care about.
5. **Data ownership** – Usage and cost data stay in our system. Some orgs prefer that for compliance or policy.
6. **Tailored to our product** – Aggregations (“by operation,” “top consumers,” “per assessment”), time ranges, and export are exactly what we need, without depending on LangSmith’s API or roadmap.

### When LangSmith is better

- **Debugging a single run** – Trace tree, inputs/outputs, step-by-step latency. We don’t replicate that; we link to LangSmith.
- **Zero instrumentation** – Turning on tracing is just env vars; they capture LangChain calls automatically. We have to add `record_llm_call` etc. (one-time cost).
- **No ops on our side** – They handle storage, retention, and scaling for traces.

### Summary

| | Custom Diagnostics | LangSmith |
|--|--------------------|-----------|
| **Powers our dashboard?** | Yes – our UI reads our store. | No – we don’t call their API to render our dashboard. |
| **Tokens, cost, request log?** | Yes (our store). | Yes (their UI). |
| **Thresholds & in-app alerts?** | Yes. | Not as a built-in, in-our-app feature. |
| **Works without LangSmith?** | Yes. | N/A. |
| **Deep trace debugging?** | Link to LangSmith. | Yes – their strength. |

So: **custom** = in-app control, thresholds, alerts, and coverage of all our interfaces; **LangSmith** = optional, for deep traces and debugging. We use custom for the “killer” dashboard; we use LangSmith as an optional complement and link out to it from Diagnostics.

---

## 2. External Interfaces to Track

| Interface | What we track | Units | Cost / limits |
|-----------|----------------|-------|----------------|
| **LLM** (OpenAI / Anthropic / Azure) | Invocations, tokens in/out, latency, model, agent/operation name, success/error | Calls, tokens, ms | Approx. cost per request; provider rate limits |
| **Tavily** (web search) | API calls, latency, success/error, queries count | Calls, ms | Per-query cost / plan limits |
| **Pinecone** (KB) | Query count, vectors read, latency | Queries, read units | Usage vs. plan / spend limit |
| **LangSmith** (optional) | Link-out to trace; we don’t duplicate full trace data | — | N/A (we surface link + high-level counts if available) |

### 2.1 LLM (primary cost driver)

- **Per call:** `operation` (e.g. `research`, `summarize`, `chat`, `quality_check`, `architecture_design`, `mermaid_from_design`, `profile_validation`), `model`, `input_tokens`, `output_tokens`, `latency_ms`, `status` (ok / error), `error_message` (if any), `timestamp`.
- **Derived:** Total tokens (in/out), **approximate cost** using model-specific pricing (e.g. GPT-4o-mini $0.15/1M in, $0.60/1M out; document in config).
- **Aggregates:** Calls per operation, tokens per operation, cost per operation, p50/p95 latency per operation.

### 2.2 Tavily

- **Per call:** `query`, `result_count`, `latency_ms`, `status`, `timestamp`.
- **Aggregates:** Total calls, success/error count, total latency, approximate cost if plan is known.

### 2.3 Pinecone

- **Per query (when we have it):** `operation` (e.g. `research_kb`), `latency_ms`, `results_count` (or read units if API exposes), `status`.
- **Aggregates:** Query count, read units (if available), latency p95.

---

## 3. Data Model (metrics store)

We need a **local metrics store** (in addition to LangSmith) so the dashboard works without depending on LangSmith and so we can enforce thresholds and alerts.

### 3.1 Option A: SQLite tables (recommended)

- **`diagnostics_llm_calls`**  
  `id`, `timestamp`, `operation`, `model`, `input_tokens`, `output_tokens`, `latency_ms`, `status`, `error_message`, `assessment_id` (nullable)

- **`diagnostics_tool_calls`**  
  `id`, `timestamp`, `tool_name` (e.g. `tavily_search`), `params_hash` (optional), `latency_ms`, `status`, `error_message`, `assessment_id` (nullable), `metadata` (JSON: result_count, etc.)

- **`diagnostics_pinecone_queries`** (optional, if we instrument)  
  `id`, `timestamp`, `operation`, `latency_ms`, `results_count`, `status`, `assessment_id` (nullable)

- **`diagnostics_config`** (key-value or single row)  
  Thresholds and alert settings (see §5).

### 3.2 Retention

- **Raw events:** Configurable retention (e.g. 7 days default; keep last N rows or by date). Older data can be aggregated then pruned.
- **Aggregates:** Precomputed daily (or rolling 24h) for summary and patterns; retain longer (e.g. 30 days) for trend charts.

---

## 4. Instrumentation Points

| Where | What to record |
|-------|----------------|
| **LLM (all agents)** | After each `llm.invoke()`: operation name, model, `usage.prompt_tokens` / `usage.completion_tokens` (from response or callback), latency, status. If provider doesn’t return usage, estimate or leave null and still count call. |
| **Tool Gateway – Tavily** | In `tavily_search` wrapper: before/after call, record to `diagnostics_tool_calls` (tool_name=`tavily_search`, latency, status, result_count). |
| **Pinecone** (search) | Wherever we call Pinecone search: record query count and latency (and read units if available) to `diagnostics_pinecone_queries` or a generic tool call. |
| **Research / Summarize flow** | Tag records with `assessment_id` when available so we can show “per assessment” breakdown. |

Implementation detail: a small **diagnostics service** (e.g. `record_llm_call(...)`, `record_tool_call(...)`) that all agents and the Tool Gateway call. This keeps instrumentation in one place and makes it easy to add new interfaces.

---

## 5. Thresholds and Configuration

### 5.1 Configurable thresholds (stored in `diagnostics_config` or .env)

| Key | Description | Default | Unit |
|-----|-------------|--------|------|
| **Daily token limit** | Soft cap for total LLM tokens (in+out) per calendar day | e.g. 500_000 | tokens |
| **Daily cost limit (USD)** | Soft cap for estimated LLM (+ optional Tavily) cost per day | e.g. 5.00 | USD |
| **Alert at %** | Alert when usage reaches this % of a limit (e.g. 80%) | 80 | % |
| **Tavily daily call limit** | Max Tavily API calls per day (if plan has a cap) | e.g. 100 | calls |
| **Pinecone daily query limit** | Max KB queries per day (optional) | e.g. 1000 | queries |

Thresholds should be **editable in the Diagnostics UI** (form that PATCHes config) and optionally overridable via env (e.g. `DIAGNOSTICS_DAILY_TOKEN_LIMIT`). UI wins over env for operator convenience.

### 5.2 Model-specific pricing (for cost estimation)

Stored in config or code; used only for **approximate** cost.

| Provider | Model | Input (per 1M tokens) | Output (per 1M tokens) |
|----------|--------|------------------------|------------------------|
| OpenAI | gpt-4o-mini | $0.15 | $0.60 |
| OpenAI | gpt-4o | $2.50 | $10.00 |
| Anthropic | claude-3-5-sonnet | ~$3.00 | ~$15.00 |
| Azure | (deployment-based) | Configurable in UI | Configurable in UI |

We document that these are approximate and may lag provider pricing; admins can override per-model in a “Cost model” subsection of Diagnostics config.

---

## 6. Alerts

### 6.1 When to alert

- **Approaching limit:** When daily tokens, daily cost, or daily Tavily/Pinecone usage crosses the “alert at %” threshold (e.g. 80% of limit).
- **Limit exceeded:** When any limit is exceeded (e.g. 100% or more).

### 6.2 How to surface

- **In-app:** Diagnostics tab shows an **Alerts** panel at the top: “Warning: daily token usage at 85% of limit (425K / 500K).” and “Critical: daily cost limit exceeded ($5.02 / $5.00).”
- **State:** Store last alert timestamps and “acknowledged” flag so we can show “Acknowledged at …” and avoid alert fatigue. Optionally: “Mute for 1 hour” or “Mute until tomorrow.”
- **Optional later:** Webhook or email (out of scope for v1; design so we can add a webhook URL and “Send test” later).

### 6.3 Alert content

Each alert includes: **type** (approaching / exceeded), **metric** (tokens, cost, Tavily calls, etc.), **current value**, **limit**, **period** (e.g. “today”), and **timestamp**.

---

## 7. Approximate Cost

- **Per request:** For each LLM call, `cost_approx = (input_tokens/1e6 * price_in + output_tokens/1e6 * price_out)` using the model table.
- **Per operation:** Sum of cost_approx for that operation (research, summarizer, chat, …).
- **Per day:** Sum of all cost_approx for the selected day.
- **Display:** “Approximate cost (LLM): $X.XX (24h)” with a tooltip: “Based on model pricing; actual bill may differ.”

Tavily and Pinecone: if we have plan/cost info, show “Tavily: ~$X” / “Pinecone: usage Y” in the same cost section.

---

## 8. Patterns and Trends

- **Usage over time:** Line or bar chart (or table): tokens / cost / calls per day (or per hour for “last 24h”). Time range selector: Last 24h, Last 7 days, Last 30 days.
- **Top consumers:** Table: “By operation” (research, summarizer, chat, …) with total calls, total tokens, total cost, share of cost %. So admins see “Research is 60% of cost.”
- **Error rate:** Success vs. error count per interface (LLM, Tavily, Pinecone) and over time; highlight spikes.
- **Latency:** p50 / p95 per operation (and per interface for tools) so performance regressions are visible.

Data source: aggregates from the metrics store (daily rollups recommended for 7d/30d to keep queries fast).

---

## 9. API Design

### 9.1 Summary (for overview cards and alerts)

```
GET /api/admin/diagnostics/summary?period=24h
```

**Query:** `period` = `24h` | `7d` | `30d` (default 24h).

**Response:**

- `period`, `from`, `to`
- `llm`: `{ total_calls, total_input_tokens, total_output_tokens, approx_cost_usd, by_operation: [ { operation, calls, tokens_in, tokens_out, cost_usd } ], errors }`
- `tavily`: `{ total_calls, errors, approx_cost_usd }` (if available)
- `pinecone`: `{ total_queries, errors }`
- `alerts`: `[ { type: "approaching"|"exceeded", metric, current, limit, unit, period } ]`
- `thresholds`: current limits (so UI can show “X / Y tokens”)

### 9.2 External interfaces (detailed)

```
GET /api/admin/diagnostics/interfaces?period=24h
```

**Response:** One object per interface (llm, tavily, pinecone) with:

- Name, display label
- Calls/queries count, errors, total duration (ms), approximate cost (if applicable)
- Optional: breakdown by operation (LLM) or by tool (Tavily)

### 9.3 Request log (drill-down)

```
GET /api/admin/diagnostics/requests?limit=50&offset=0&interface=llm&operation=research
```

**Query:** `limit`, `offset`, optional `interface` (llm | tavily | pinecone), optional `operation`, optional `since` (ISO datetime).

**Response:** List of events: `timestamp`, `interface`, `operation` (or tool), `tokens_in`, `tokens_out`, `latency_ms`, `status`, `assessment_id`, `error_message` (if any). Sorted by timestamp desc.

### 9.4 Patterns (for charts / tables)

```
GET /api/admin/diagnostics/patterns?period=7d&granularity=day
```

**Query:** `period` = 24h | 7d | 30d, `granularity` = hour | day.

**Response:** Time series: `[ { bucket (e.g. date or hour), tokens, cost_usd, llm_calls, tavily_calls, errors } ]` and/or `by_operation: [ { operation, total_calls, total_tokens, total_cost_usd } ]` for “top consumers.”

### 9.5 Threshold and alert configuration

```
GET  /api/admin/diagnostics/config     → current thresholds and alert-at-% 
PATCH /api/admin/diagnostics/config    → update thresholds (body: { daily_token_limit?, daily_cost_limit_usd?, alert_at_percent?, tavily_daily_limit?, ... })
```

Only admin (or same auth as rest of Admin) can PATCH. Validation: limits must be positive; alert_at_percent in 1–100.

---

## 10. UI Structure (Diagnostics tab)

### 10.1 Tab placement

- Add a third tab: **Assessments | Knowledge Base | Diagnostics** in the Admin Command Center header.

### 10.2 Sections (order and content)

1. **Alerts** (top)  
   - If any alert is active: banner(s) with type (warning/critical), message, current vs limit. Actions: “Acknowledge,” optional “Mute for 1h.”

2. **Time range**  
   - Selector: Last 24h | Last 7 days | Last 30 days. Applies to summary, interfaces, patterns, and request log.

3. **Summary cards**  
   - Row of cards: **LLM** (calls, tokens, approx cost), **Tavily** (calls, errors), **Pinecone** (queries). Optional: **Total approximate cost (24h)**. Each card can link to the detailed view or request log filtered by interface.

4. **External interfaces**  
   - Table or card list: one row/card per interface (LLM, Tavily, Pinecone). Columns: Interface name, Calls (or Queries), Duration (total or avg), Errors, Approx cost (if any), Status (ok / warning / over limit). Expand or link to per-interface breakdown (e.g. LLM by operation).

5. **Thresholds & configuration**  
   - Form: Daily token limit, Daily cost limit (USD), Alert at (%), Tavily daily limit, etc. Save button. Optional: “Cost model” subsection to override per-model pricing (advanced).

6. **Patterns**  
   - “Usage over time” (tokens or cost by day/hour). “Top consumers” table: operation, calls, tokens, cost, % of cost. “Errors over time” or error count by interface.

7. **Request log**  
   - Table: Time, Interface, Operation, Tokens in/out, Latency, Status, Assessment ID (link). Filters: interface, operation, time range. Pagination. Optional: Export CSV.

8. **LangSmith** (optional)  
   - If LangSmith is configured: “View full traces in LangSmith” link (project URL). Short line: “Last 24h: N traces.”

### 10.3 Visual design

- Align with existing Admin Command Center: dark/slate theme, clear typography, status colors (green = ok, amber = warning, red = critical).
- Use numbers and short labels; avoid jargon in default view (“Tokens” not “Input token count” in cards).
- Ensure key numbers (cost, tokens, alerts) are scannable (size, contrast).

---

## 11. Implementation Order

1. **Metrics store** – SQLite tables (or append log) for LLM and Tavily; diagnostics service to record from LLM and Tool Gateway.
2. **Instrumentation** – Add `record_llm_call` at every LLM invoke; add `record_tool_call` in Tavily wrapper (and Pinecone if desired).
3. **GET summary + GET requests** – Implement summary (aggregates) and request log API; no thresholds yet.
4. **Diagnostics tab shell** – New tab in Admin; summary cards and request log table; time range selector.
5. **Thresholds config** – Table and API (GET/PATCH config); persist and use in summary for “current vs limit.”
6. **Alerts** – Compute alerts from thresholds and usage; surface in API and UI (banner + optional acknowledge).
7. **Cost estimation** – Model pricing table; compute and show approx cost in summary, interfaces, and patterns.
8. **Patterns** – Aggregates by day/hour and by operation; patterns API and UI (tables/charts).
9. **External interfaces panel** – Detailed breakdown per interface (and per operation for LLM).
10. **Polish** – Export CSV, LangSmith link, retention/cleanup job.

---

## 12. Open Decisions

- [ ] Retention: 7 days default for raw events? 30 days for daily aggregates?
- [ ] Export: CSV only for request log, or also JSON for patterns/summary?
- [ ] Alert “mute”: 1h vs “until tomorrow” vs “acknowledge and hide until next threshold breach”?
- [ ] Per-model pricing: fully editable in UI or only via env/config file?

---

*Document version: 1.0 | Design for review before implementation*
