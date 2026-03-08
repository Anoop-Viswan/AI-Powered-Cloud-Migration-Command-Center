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
    """Create table if not exists."""
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
        return aid

    def get(self, assessment_id: str) -> AssessmentState | None:
        """Get assessment by id."""
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT id, profile_json, approach_document, report, status, error_message FROM assessments WHERE id = ?",
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
        return AssessmentState(
            id=row["id"],
            profile=profile,
            approach_document=row["approach_document"],
            report=row["report"],
            status=row["status"],
            error_message=row["error_message"],
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

    def update_approach(self, assessment_id: str, approach_document: str) -> None:
        """Update approach document."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                "UPDATE assessments SET approach_document = ?, status = 'research_done', updated_at = ? WHERE id = ?",
                (approach_document, now, assessment_id),
            )

    def update_report(self, assessment_id: str, report: str) -> None:
        """Update report and set status done."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                "UPDATE assessments SET report = ?, status = 'done', updated_at = ? WHERE id = ?",
                (report, now, assessment_id),
            )

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
        """Summary counts for admin scorecards: total, done, in_progress, error."""
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM assessments").fetchone()[0]
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
            "done": done,
            "in_progress": in_progress,
            "error": error,
        }
