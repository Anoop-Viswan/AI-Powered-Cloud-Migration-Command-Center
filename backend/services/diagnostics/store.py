"""Diagnostics SQLite store: LLM calls, tool calls, and config (thresholds)."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def _get_db_path() -> Path:
    root = Path(__file__).resolve().parent.parent.parent.parent
    data_dir = root / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir / "diagnostics.db"


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS diagnostics_llm_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            operation TEXT NOT NULL,
            model TEXT,
            input_tokens INTEGER,
            output_tokens INTEGER,
            latency_ms INTEGER,
            status TEXT NOT NULL,
            error_message TEXT,
            assessment_id TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS diagnostics_tool_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            latency_ms INTEGER,
            status TEXT NOT NULL,
            error_message TEXT,
            assessment_id TEXT,
            metadata_json TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS diagnostics_config (
            key TEXT PRIMARY KEY,
            value_text TEXT,
            updated_at TEXT NOT NULL
        )
    """)
    # Default thresholds if not set
    conn.execute(
        "INSERT OR IGNORE INTO diagnostics_config (key, value_text, updated_at) VALUES (?, ?, ?)",
        ("daily_token_limit", "500000", _now()),
    )
    conn.execute(
        "INSERT OR IGNORE INTO diagnostics_config (key, value_text, updated_at) VALUES (?, ?, ?)",
        ("daily_cost_limit_usd", "5.0", _now()),
    )
    conn.execute(
        "INSERT OR IGNORE INTO diagnostics_config (key, value_text, updated_at) VALUES (?, ?, ?)",
        ("alert_at_percent", "80", _now()),
    )
    conn.execute(
        "INSERT OR IGNORE INTO diagnostics_config (key, value_text, updated_at) VALUES (?, ?, ?)",
        ("tavily_daily_limit", "100", _now()),
    )
    conn.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_store: "DiagnosticsStore | None" = None


def get_diagnostics_store() -> "DiagnosticsStore":
    global _store
    if _store is None:
        _store = DiagnosticsStore(_get_db_path())
    return _store


class DiagnosticsStore:
    def __init__(self, db_path: Path):
        self._path = db_path

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path))
        _init_db(conn)
        return conn

    def record_llm(
        self,
        operation: str,
        model: str | None,
        input_tokens: int | None,
        output_tokens: int | None,
        latency_ms: int | None,
        status: str,
        error_message: str | None = None,
        assessment_id: str | None = None,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO diagnostics_llm_calls
                   (timestamp, operation, model, input_tokens, output_tokens, latency_ms, status, error_message, assessment_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    _now(),
                    operation,
                    model or "",
                    input_tokens,
                    output_tokens,
                    latency_ms,
                    status,
                    error_message,
                    assessment_id,
                ),
            )
            conn.commit()

    def record_tool(
        self,
        tool_name: str,
        latency_ms: int | None,
        status: str,
        error_message: str | None = None,
        assessment_id: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO diagnostics_tool_calls
                   (timestamp, tool_name, latency_ms, status, error_message, assessment_id, metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    _now(),
                    tool_name,
                    latency_ms,
                    status,
                    error_message,
                    assessment_id,
                    json.dumps(metadata) if metadata else None,
                ),
            )
            conn.commit()

    def get_summary(self, period: str = "24h") -> dict:
        """Aggregate counts and tokens for the given period (24h, 7d, 30d)."""
        since = _since_iso(period)
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            # LLM
            rows = conn.execute(
                """SELECT operation, COUNT(*) as calls,
                   COALESCE(SUM(input_tokens), 0) as ti, COALESCE(SUM(output_tokens), 0) as to_
                   FROM diagnostics_llm_calls WHERE timestamp >= ? AND status = 'ok'
                   GROUP BY operation""",
                (since,),
            ).fetchall()
            by_op = [
                {
                    "operation": r["operation"],
                    "calls": r["calls"],
                    "input_tokens": r["ti"],
                    "output_tokens": r["to_"],
                }
                for r in rows
            ]
            total_llm = conn.execute(
                """SELECT COUNT(*) as c, COALESCE(SUM(input_tokens), 0) as ti, COALESCE(SUM(output_tokens), 0) as to_
                   FROM diagnostics_llm_calls WHERE timestamp >= ?""",
                (since,),
            ).fetchone()
            llm_errors = conn.execute(
                """SELECT COUNT(*) as c FROM diagnostics_llm_calls WHERE timestamp >= ? AND status != 'ok'""",
                (since,),
            ).fetchone()["c"]
            # Tool (Tavily)
            tool_rows = conn.execute(
                """SELECT tool_name, COUNT(*) as c FROM diagnostics_tool_calls WHERE timestamp >= ?
                   GROUP BY tool_name""",
                (since,),
            ).fetchall()
            tavily_calls = sum(r["c"] for r in tool_rows if r["tool_name"] == "tavily_search")
            tool_errors = conn.execute(
                """SELECT COUNT(*) as c FROM diagnostics_tool_calls WHERE timestamp >= ? AND status != 'ok'""",
                (since,),
            ).fetchone()["c"]
        total_input = total_llm["ti"] or 0
        total_output = total_llm["to_"] or 0
        return {
            "period": period,
            "from": since,
            "llm": {
                "total_calls": total_llm["c"] or 0,
                "total_input_tokens": total_input,
                "total_output_tokens": total_output,
                "by_operation": by_op,
                "errors": llm_errors,
            },
            "tavily": {"total_calls": tavily_calls, "errors": tool_errors},
        }

    def get_requests(self, limit: int = 50, offset: int = 0, interface: str | None = None) -> list[dict]:
        """Request log: LLM and tool events combined, newest first."""
        since = _since_iso("7d")  # last 7 days
        out = []
        fetch_limit = limit + offset + 100  # fetch extra so we can merge and paginate
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            if interface != "tool":
                rows = conn.execute(
                    """SELECT id, timestamp, operation, model, input_tokens, output_tokens, latency_ms, status, error_message, assessment_id
                       FROM diagnostics_llm_calls WHERE timestamp >= ?
                       ORDER BY timestamp DESC LIMIT ?""",
                    (since, fetch_limit),
                ).fetchall()
                for r in rows:
                    out.append({
                        "id": f"llm_{r['id']}",
                        "timestamp": r["timestamp"],
                        "interface": "llm",
                        "operation": r["operation"],
                        "model": r["model"],
                        "tokens_in": r["input_tokens"],
                        "tokens_out": r["output_tokens"],
                        "latency_ms": r["latency_ms"],
                        "status": r["status"],
                        "error_message": r["error_message"],
                        "assessment_id": r["assessment_id"],
                        "metadata": None,
                    })
            if interface != "llm":
                rows = conn.execute(
                    """SELECT id, timestamp, tool_name, latency_ms, status, error_message, assessment_id, metadata_json
                       FROM diagnostics_tool_calls WHERE timestamp >= ?
                       ORDER BY timestamp DESC LIMIT ?""",
                    (since, fetch_limit),
                ).fetchall()
                for r in rows:
                    meta = None
                    if r["metadata_json"]:
                        try:
                            meta = json.loads(r["metadata_json"])
                        except Exception:
                            meta = {"raw": r["metadata_json"]}
                    out.append({
                        "id": f"tool_{r['id']}",
                        "timestamp": r["timestamp"],
                        "interface": "tool",
                        "operation": r["tool_name"],
                        "model": None,
                        "tokens_in": None,
                        "tokens_out": None,
                        "latency_ms": r["latency_ms"],
                        "status": r["status"],
                        "error_message": r["error_message"],
                        "assessment_id": r["assessment_id"],
                        "metadata": meta,
                    })
        out.sort(key=lambda x: x["timestamp"], reverse=True)
        return out[offset : offset + limit]

    def get_interface_stats(self, period: str) -> dict:
        """Per-interface stats including latency (p95 for LLM, avg for tools) for External interfaces section."""
        since = _since_iso(period)
        result = {"llm": {"calls": 0, "errors": 0, "approx_cost_usd": 0, "p95_latency_ms": None, "total_input_tokens": 0, "total_output_tokens": 0}, "tavily": {"calls": 0, "errors": 0, "avg_latency_ms": None}, "pinecone": {"queries": 0, "errors": 0}}
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            # LLM: count, errors, tokens, p95 latency
            row = conn.execute(
                """SELECT COUNT(*) as c, SUM(CASE WHEN status != 'ok' THEN 1 ELSE 0 END) as errs,
                   COALESCE(SUM(input_tokens), 0) as ti, COALESCE(SUM(output_tokens), 0) as to_
                   FROM diagnostics_llm_calls WHERE timestamp >= ?""",
                (since,),
            ).fetchone()
            result["llm"]["calls"] = row["c"] or 0
            result["llm"]["errors"] = row["errs"] or 0
            result["llm"]["total_input_tokens"] = row["ti"] or 0
            result["llm"]["total_output_tokens"] = row["to_"] or 0
            latencies = conn.execute(
                """SELECT latency_ms FROM diagnostics_llm_calls WHERE timestamp >= ? AND latency_ms IS NOT NULL""",
                (since,),
            ).fetchall()
            if latencies:
                vals = sorted([r["latency_ms"] for r in latencies])
                idx = max(0, int(len(vals) * 0.95) - 1)
                result["llm"]["p95_latency_ms"] = vals[idx]
            latest = conn.execute(
                """SELECT model FROM diagnostics_llm_calls WHERE timestamp >= ? AND model IS NOT NULL AND model != '' ORDER BY timestamp DESC LIMIT 1""",
                (since,),
            ).fetchone()
            result["llm"]["model"] = latest["model"] if latest else None
            # Tavily (tool_calls with tool_name = tavily_search)
            row = conn.execute(
                """SELECT COUNT(*) as c, SUM(CASE WHEN status != 'ok' THEN 1 ELSE 0 END) as errs, AVG(latency_ms) as avg_ms
                   FROM diagnostics_tool_calls WHERE timestamp >= ? AND tool_name = 'tavily_search'""",
                (since,),
            ).fetchone()
            result["tavily"]["calls"] = row["c"] or 0
            result["tavily"]["errors"] = row["errs"] or 0
            if row["avg_ms"] is not None:
                result["tavily"]["avg_latency_ms"] = round(row["avg_ms"], 0)
        return result

    def get_usage_by_day(self, period: str) -> list[dict]:
        """Usage by calendar day for the chart: date, input_tokens, output_tokens, calls."""
        since = _since_iso(period)
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            # SQLite: date(timestamp) gives YYYY-MM-DD for ISO strings
            rows = conn.execute(
                """SELECT date(timestamp) as d, COALESCE(SUM(input_tokens), 0) as ti, COALESCE(SUM(output_tokens), 0) as to_, COUNT(*) as c
                   FROM diagnostics_llm_calls WHERE timestamp >= ? GROUP BY date(timestamp) ORDER BY d""",
                (since,),
            ).fetchall()
        return [{"date": r["d"], "input_tokens": r["ti"], "output_tokens": r["to_"], "calls": r["c"]} for r in rows]

    def get_config(self) -> dict:
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT key, value_text FROM diagnostics_config").fetchall()
        return {r["key"]: r["value_text"] for r in rows}

    def update_config(self, updates: dict) -> None:
        now = _now()
        with self._conn() as conn:
            for k, v in updates.items():
                conn.execute(
                    "INSERT OR REPLACE INTO diagnostics_config (key, value_text, updated_at) VALUES (?, ?, ?)",
                    (k, str(v), now),
                )
            conn.commit()


def _since_iso(period: str) -> str:
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    if period == "24h":
        delta = timedelta(hours=24)
    elif period == "7d":
        delta = timedelta(days=7)
    elif period == "30d":
        delta = timedelta(days=30)
    else:
        delta = timedelta(hours=24)
    return (now - delta).isoformat()
