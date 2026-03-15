"""Assessment persistence – SQLite store (pluggable)."""

import json
import sqlite3
import uuid
from pathlib import Path

from backend.services.assessment.models import ApplicationProfile, AssessmentState


def _get_db_path() -> Path:
    """Database file path (project root / data dir)."""
    root = Path(__file__).resolve().parent.parent.parent.parent
    data_dir = root / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir / "assessments.db"


def _init_db(conn: sqlite3.Connection) -> None:
    """Create table if not exists; add quality_check_json column if missing."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS assessments (
            id TEXT PRIMARY KEY,
            profile_json TEXT,
            approach_document TEXT,
            report TEXT,
            status TEXT NOT NULL DEFAULT 'draft',
            error_message TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    # Migration: add optional columns if not present
    cur = conn.execute("PRAGMA table_info(assessments)")
    columns = [row[1] for row in cur.fetchall()]
    if "quality_check_json" not in columns:
        conn.execute("ALTER TABLE assessments ADD COLUMN quality_check_json TEXT")
    if "research_details_json" not in columns:
        conn.execute("ALTER TABLE assessments ADD COLUMN research_details_json TEXT")
    conn.commit()


class AssessmentStore:
    """SQLite-backed assessment store. Pluggable: swap for Postgres by implementing same interface."""

    def __init__(self, db_path: Path | None = None):
        self._path = db_path or _get_db_path()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path))
        _init_db(conn)
        return conn

    def create(self) -> str:
        """Create new assessment; returns id."""
        aid = str(uuid.uuid4())
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO assessments (id, status, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (aid, "draft", now, now),
            )
            conn.commit()
        return aid

    def get(self, assessment_id: str) -> AssessmentState | None:
        """Get assessment by id."""
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT id, profile_json, approach_document, report, status, error_message, quality_check_json, research_details_json FROM assessments WHERE id = ?",
                (assessment_id,),
            ).fetchone()
        if not row:
            return None
        profile = None
        if row["profile_json"]:
            try:
                profile = ApplicationProfile.model_validate(json.loads(row["profile_json"]))
            except Exception:
                pass
        quality_check = None
        try:
            qc_json = row["quality_check_json"]
        except (IndexError, KeyError):
            qc_json = None
        if qc_json:
            try:
                quality_check = json.loads(qc_json)
            except Exception:
                pass
        research_details = None
        try:
            rd_json = row["research_details_json"]
        except (IndexError, KeyError):
            rd_json = None
        if rd_json:
            try:
                research_details = json.loads(rd_json)
            except Exception:
                pass
        return AssessmentState(
            id=row["id"],
            profile=profile,
            approach_document=row["approach_document"],
            report=row["report"],
            status=row["status"],
            error_message=row["error_message"],
            quality_check=quality_check,
            research_details=research_details,
        )

    def update_profile(self, assessment_id: str, profile: ApplicationProfile) -> None:
        """Update profile."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                "UPDATE assessments SET profile_json = ?, updated_at = ? WHERE id = ?",
                (profile.model_dump_json(), now, assessment_id),
            )
            conn.commit()

    def update_approach(
        self,
        assessment_id: str,
        approach_document: str,
        research_details: dict | None = None,
    ) -> None:
        """Update approach document and optionally research_details (kb_hits, official_docs) for transparency."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                "UPDATE assessments SET approach_document = ?, status = 'research_done', updated_at = ? WHERE id = ?",
                (approach_document, now, assessment_id),
            )
            conn.commit()
        if research_details is not None:
            with self._conn() as conn:
                conn.execute(
                    "UPDATE assessments SET research_details_json = ?, updated_at = ? WHERE id = ?",
                    (json.dumps(research_details), now, assessment_id),
                )
                conn.commit()

    def update_report(self, assessment_id: str, report: str) -> None:
        """Update report and set status done."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                "UPDATE assessments SET report = ?, status = 'done', updated_at = ? WHERE id = ?",
                (report, now, assessment_id),
            )
            conn.commit()

    def clear_artifacts_for_research(self, assessment_id: str) -> None:
        """
        Clear approach_document, report, quality_check, and research_details so re-run research
        does not show stale content. Call when starting research.
        """
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                """UPDATE assessments SET approach_document = NULL, report = NULL,
                   quality_check_json = NULL, research_details_json = NULL, updated_at = ? WHERE id = ?""",
                (now, assessment_id),
            )
            conn.commit()

    def clear_report_and_quality_check(self, assessment_id: str) -> None:
        """
        Clear report and quality_check only. Call when starting report regeneration (summarize)
        so the UI does not show stale report/QC while the new report is being generated.
        """
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                "UPDATE assessments SET report = NULL, quality_check_json = NULL, updated_at = ? WHERE id = ?",
                (now, assessment_id),
            )
            conn.commit()

    def update_report_body(self, assessment_id: str, report: str) -> None:
        """Update report text only (edit); do not change status."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                "UPDATE assessments SET report = ?, updated_at = ? WHERE id = ?",
                (report, now, assessment_id),
            )
            conn.commit()

    def update_quality_check(self, assessment_id: str, result: dict) -> None:
        """Store quality check result (comprehensive_ok, actionable_ok, useful_ok, overall_pass, suggestions)."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                "UPDATE assessments SET quality_check_json = ?, updated_at = ? WHERE id = ?",
                (json.dumps(result), now, assessment_id),
            )
            conn.commit()

    def update_status(
        self,
        assessment_id: str,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """Update status (e.g. researching, summarizing, error)."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                "UPDATE assessments SET status = ?, error_message = ?, updated_at = ? WHERE id = ?",
                (status, error_message, now, assessment_id),
            )
            conn.commit()

    def delete(self, assessment_id: str) -> bool:
        """Delete one assessment by id. Returns True if deleted, False if not found."""
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM assessments WHERE id = ?", (assessment_id,))
            conn.commit()
            return cur.rowcount > 0

    def delete_by_status(self, status: str, limit: int = 1000) -> int:
        """Delete all assessments with the given status. Returns number deleted. Use for cleanup (e.g. status='draft')."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id FROM assessments WHERE status = ? LIMIT ?",
                (status, limit),
            ).fetchall()
            ids = [r[0] for r in rows]
            for aid in ids:
                conn.execute("DELETE FROM assessments WHERE id = ?", (aid,))
            conn.commit()
            return len(ids)

    def list_all(self, limit: int = 50, status_filter: str | None = None) -> list[dict]:
        """List assessments for admin: id, app_name, status, error_message, updated_at."""
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            if status_filter:
                rows = conn.execute(
                    """SELECT id, profile_json, status, error_message, updated_at
                       FROM assessments WHERE status = ? ORDER BY updated_at DESC LIMIT ?""",
                    (status_filter, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT id, profile_json, status, error_message, updated_at
                       FROM assessments ORDER BY updated_at DESC LIMIT ?""",
                    (limit,),
                ).fetchall()
        result = []
        for row in rows:
            app_name = ""
            if row["profile_json"]:
                try:
                    p = json.loads(row["profile_json"])
                    app_name = p.get("application_name", "") or "(unnamed)"
                except Exception:
                    pass
            result.append({
                "id": row["id"],
                "app_name": app_name,
                "status": row["status"],
                "error_message": row["error_message"],
                "updated_at": row["updated_at"],
            })
        return result

    def get_summary(self) -> dict:
        """Summary counts for admin scorecards: total, submitted, done, in_progress, error."""
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM assessments").fetchone()[0]
            submitted = conn.execute(
                "SELECT COUNT(*) FROM assessments WHERE status = 'submitted'"
            ).fetchone()[0]
            done = conn.execute(
                "SELECT COUNT(*) FROM assessments WHERE status = 'done'"
            ).fetchone()[0]
            in_progress = conn.execute(
                """SELECT COUNT(*) FROM assessments
                   WHERE status IN ('researching', 'summarizing', 'research_done', 'draft')"""
            ).fetchone()[0]
            error = conn.execute(
                "SELECT COUNT(*) FROM assessments WHERE status = 'error'"
            ).fetchone()[0]
        return {
            "total": total,
            "submitted": submitted,
            "done": done,
            "in_progress": in_progress,
            "error": error,
        }
