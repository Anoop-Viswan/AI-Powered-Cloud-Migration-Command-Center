# SQLite in this project: is it enough? How to query

## Is SQLite enough for this app?

**Yes.** For this small app (single team, internal/demo, low concurrency), SQLite is a good fit.

| Use case | SQLite | Consider another DB when |
|----------|--------|---------------------------|
| **Assessments** (migration requests, profiles, reports) | One writer at a time is fine; typical volume is tens to hundreds of rows. | You run **multiple app instances** (load-balanced) that must share the same data, or you need **hundreds of concurrent writers**. |
| **Diagnostics** (LLM/tool call logs, thresholds) | Append-heavy, read for dashboards; SQLite handles this well. | You need **centralized logging** across many instances or **very high** write throughput. |
| **Deployment** | Single container + one volume for `data/` is simple. | You explicitly want managed DB (backups, replication, point-in-time recovery) or multi-region. |

**Summary:** Stay on SQLite for V0.1. Revisit Postgres (or similar) only if you add multi-instance deployment, need shared DB across replicas, or want managed backups/replication.

---

## Where are the SQLite files?

Both databases live under the project **data** directory:

- **Assessments:** `data/assessments.db`
- **Diagnostics:** `data/diagnostics.db`

From the project root:

```bash
ls -la data/
# assessments.db   diagnostics.db   (and subdirs: assessment_diagrams/, assessment_uploads/)
```

---

## How to query SQLite

### Option 1: Command line (`sqlite3`)

macOS often has `sqlite3` installed; Linux: `apt install sqlite3` / `yum install sqlite`.

```bash
cd /path/to/pinecone-semantic-search

# Open assessments DB
sqlite3 data/assessments.db

# Inside sqlite3:
.tables
.schema assessments
SELECT id, status, created_at FROM assessments ORDER BY updated_at DESC LIMIT 10;
.quit
```

```bash
# Open diagnostics DB
sqlite3 data/diagnostics.db

.tables
.schema diagnostics_llm_calls
SELECT timestamp, operation, status, latency_ms FROM diagnostics_llm_calls ORDER BY timestamp DESC LIMIT 20;
.quit
```

**One-liners (no interactive shell):**

```bash
sqlite3 data/assessments.db "SELECT id, status, created_at FROM assessments;"
sqlite3 data/diagnostics.db "SELECT COUNT(*) FROM diagnostics_llm_calls WHERE date(timestamp) = date('now');"
```

### Option 2: GUI tools

- **[DB Browser for SQLite](https://sqlitebrowser.org/)** (free): Open `data/assessments.db` or `data/diagnostics.db`, browse tables, run SQL, export CSV.
- **VS Code / Cursor:** Extensions like “SQLite” or “SQLite Viewer” let you open `.db` files and run queries in the editor.

### Option 3: Python (one-off script)

```python
import sqlite3
conn = sqlite3.connect("data/assessments.db")
conn.row_factory = sqlite3.Row  # so columns are by name
for row in conn.execute("SELECT id, status, created_at FROM assessments"):
    print(dict(row))
conn.close()
```

---

## Table reference (quick lookup)

### `data/assessments.db` → table `assessments`

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | UUID of the assessment |
| profile_json | TEXT | JSON: application profile (overview, architecture, data, etc.) |
| approach_document | TEXT | Research/approach text (after “Run research”) |
| report | TEXT | Final report markdown (after “Generate report”) |
| status | TEXT | draft, submitted, researching, research_done, summarizing, done, error |
| error_message | TEXT | Last error if status = error |
| created_at | TEXT | ISO timestamp |
| updated_at | TEXT | ISO timestamp |
| quality_check_json | TEXT | JSON: quality check scores and reasons |
| research_details_json | TEXT | JSON: KB hits, Tavily results, confidence |

**Example queries:**

```sql
-- Count by status
SELECT status, COUNT(*) FROM assessments GROUP BY status;

-- Last 5 assessments with app name from profile JSON
SELECT id, status, json_extract(profile_json, '$.application_name') AS app_name, updated_at
FROM assessments ORDER BY updated_at DESC LIMIT 5;
```

### `data/diagnostics.db`

**Table: `diagnostics_llm_calls`**  
(id, timestamp, operation, model, input_tokens, output_tokens, latency_ms, status, error_message, assessment_id)

**Table: `diagnostics_tool_calls`**  
(id, timestamp, tool_name, latency_ms, status, error_message, assessment_id, metadata_json)

**Table: `diagnostics_config`**  
(key, value_text, updated_at) — e.g. daily_token_limit, daily_cost_limit_usd, alert_at_percent, tavily_daily_limit

**Example queries:**

```sql
-- Token usage today
SELECT SUM(input_tokens + output_tokens) AS tokens_today
FROM diagnostics_llm_calls WHERE date(timestamp) = date('now');

-- Calls by operation (last 7 days)
SELECT operation, COUNT(*), SUM(input_tokens + output_tokens) AS tokens
FROM diagnostics_llm_calls
WHERE timestamp >= datetime('now', '-7 days')
GROUP BY operation;

-- Current thresholds
SELECT * FROM diagnostics_config;
```

---

## Backup

SQLite is a single file per DB. To backup:

```bash
cp data/assessments.db data/assessments.db.bak
cp data/diagnostics.db data/diagnostics.db.bak
```

Or use `sqlite3 data/assessments.db ".backup backup.db"` for a consistent snapshot while the app might be running.
