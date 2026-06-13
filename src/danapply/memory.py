"""SQLite-backed memory layer for DanApply.

Stores parsed jobs (``applications``) and outcome events (``outcomes``).
Future versions add companies (enrichment cache) and tagline_performance
(the learning loop).

The DB lives at ``~/danapply-data/memory.db`` by default. Schema is created
on first use; ``init_db()`` is idempotent.

Concurrency: SQLite handles a single user fine. No connection pool needed.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from danapply import paths
from danapply.models import Job

SCHEMA_VERSION = 4

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
_SCHEMA_SQL = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS applications (
    job_id          TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    company         TEXT NOT NULL,
    location        TEXT,
    posting_date    TEXT,
    deadline        TEXT,
    source          TEXT NOT NULL,
    url             TEXT,
    language        TEXT NOT NULL,
    description_raw TEXT NOT NULL,
    data_confidence TEXT NOT NULL CHECK (data_confidence IN ('high', 'medium', 'low')),
    status          TEXT NOT NULL DEFAULT 'parsed',
    score           INTEGER NOT NULL DEFAULT 0,
    score_breakdown TEXT,
    scored_at       TEXT,
    jobnet_logged_at TEXT,
    requirements    TEXT,
    parsed_at       TEXT NOT NULL,
    last_seen_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_applications_status
    ON applications(status);

CREATE INDEX IF NOT EXISTS idx_applications_posting_date
    ON applications(posting_date);

CREATE INDEX IF NOT EXISTS idx_applications_deadline
    ON applications(deadline);

CREATE TABLE IF NOT EXISTS outcomes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id          TEXT NOT NULL REFERENCES applications(job_id) ON DELETE CASCADE,
    status          TEXT NOT NULL,
    notes           TEXT,
    recorded_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_outcomes_job_id ON outcomes(job_id);
"""


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------
def db_path() -> Path:
    """Where the SQLite file lives."""
    return paths.memory_db_path()


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Open a connection with sensible defaults. Auto-commits on success,
    rolls back on exception, always closes."""
    db = db_path()
    db.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        str(db),
        detect_types=sqlite3.PARSE_DECLTYPES,
        isolation_level=None,  # autocommit; we manage transactions explicitly
    )
    conn.row_factory = sqlite3.Row
    # PRAGMAs are per-connection — the schema script's PRAGMA only applied
    # to the connection that ran init_db.
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema setup
# ---------------------------------------------------------------------------
def init_db() -> Path:
    """Create the database file and tables if they don't exist, and run
    any pending migrations. Idempotent. Returns the path to the DB file."""
    with connect() as conn:
        conn.executescript(_SCHEMA_SQL)

        existing = conn.execute(
            "SELECT version FROM schema_version LIMIT 1"
        ).fetchone()
        if existing is None:
            conn.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,),
            )
        else:
            current = int(existing["version"])
            _run_migrations(conn, from_version=current)
    return db_path()


def _run_migrations(conn: sqlite3.Connection, from_version: int) -> None:
    """Apply any pending schema migrations.

    Each migration block is idempotent — ``ADD COLUMN`` is wrapped in a
    try/except because SQLite has no ``IF NOT EXISTS`` for column adds.
    """
    if from_version < 2:
        # v0.0.3 — add scoring columns
        for stmt in (
            "ALTER TABLE applications ADD COLUMN score INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE applications ADD COLUMN score_breakdown TEXT",
            "ALTER TABLE applications ADD COLUMN scored_at TEXT",
        ):
            try:
                conn.execute(stmt)
            except sqlite3.OperationalError as exc:
                if "duplicate column" not in str(exc).lower():
                    raise
        conn.execute("UPDATE schema_version SET version = 2")

    if from_version < 3:
        # v0.0.9 — track when each application got logged to Jobnet
        try:
            conn.execute(
                "ALTER TABLE applications ADD COLUMN jobnet_logged_at TEXT"
            )
        except sqlite3.OperationalError as exc:
            if "duplicate column" not in str(exc).lower():
                raise
        conn.execute("UPDATE schema_version SET version = 3")

    if from_version < 4:
        # v0.2.0 — persist requirements (JSON list). Claude-extracted
        # requirements drive the sharp skills-match path, so they must
        # survive the memory.db roundtrip.
        try:
            conn.execute(
                "ALTER TABLE applications ADD COLUMN requirements TEXT"
            )
        except sqlite3.OperationalError as exc:
            if "duplicate column" not in str(exc).lower():
                raise
        conn.execute("UPDATE schema_version SET version = 4")


def schema_version() -> int | None:
    """Read the recorded schema version. None means DB doesn't exist yet."""
    if not db_path().exists():
        return None
    with connect() as conn:
        row = conn.execute(
            "SELECT version FROM schema_version LIMIT 1"
        ).fetchone()
        return int(row["version"]) if row else None


# ---------------------------------------------------------------------------
# Applications CRUD
# ---------------------------------------------------------------------------
_CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}


def upsert_job(job: Job) -> tuple[Job, bool]:
    """Insert a new job or update an existing one.

    Returns ``(job, is_new)`` where ``is_new`` is ``True`` only on first
    insertion. When the job already exists, the only fields updated are
    ``last_seen_at`` and any non-empty new fields (won't overwrite an
    existing title/company with empty strings from a later weak parse).
    """
    job.ensure_job_id()
    row = job.to_db_row()

    with connect() as conn:
        existing = conn.execute(
            "SELECT * FROM applications WHERE job_id = ?",
            (job.job_id,),
        ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO applications (
                    job_id, title, company, location, posting_date, deadline,
                    source, url, language, description_raw,
                    data_confidence, status,
                    score, score_breakdown, scored_at,
                    jobnet_logged_at, requirements,
                    parsed_at, last_seen_at
                ) VALUES (
                    :job_id, :title, :company, :location, :posting_date, :deadline,
                    :source, :url, :language, :description_raw,
                    :data_confidence, :status,
                    :score, :score_breakdown, :scored_at,
                    :jobnet_logged_at, :requirements,
                    :parsed_at, :last_seen_at
                )
                """,
                row,
            )
            return job, True

        # Update path — only refresh last_seen_at and any non-empty new fields
        merged = dict(existing)
        for key, value in row.items():
            if value not in (None, "") or key in ("last_seen_at",):
                merged[key] = value

        # Lifecycle guards: a fresh parse of an already-tracked posting must
        # never reset pipeline state. "parsed" is the parser default, not a
        # transition; an unscored row (scored_at NULL) carries score=0 as a
        # default, not a result; and confidence only ever upgrades.
        if row["status"] == "parsed":
            merged["status"] = existing["status"]
        if row["scored_at"] is None:
            merged["score"] = existing["score"]
            merged["score_breakdown"] = existing["score_breakdown"]
            merged["scored_at"] = existing["scored_at"]
        if (_CONFIDENCE_RANK[row["data_confidence"]]
                < _CONFIDENCE_RANK[existing["data_confidence"]]):
            merged["data_confidence"] = existing["data_confidence"]
        conn.execute(
            """
            UPDATE applications SET
                title = :title,
                company = :company,
                location = :location,
                posting_date = :posting_date,
                deadline = :deadline,
                source = :source,
                url = :url,
                language = :language,
                description_raw = :description_raw,
                data_confidence = :data_confidence,
                status = :status,
                score = :score,
                score_breakdown = :score_breakdown,
                scored_at = :scored_at,
                jobnet_logged_at = :jobnet_logged_at,
                requirements = :requirements,
                last_seen_at = :last_seen_at
            WHERE job_id = :job_id
            """,
            merged,
        )
        return Job.from_db_row(merged), False


def get_job(job_id: str) -> Job | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM applications WHERE job_id = ?",
            (job_id,),
        ).fetchone()
    return Job.from_db_row(dict(row)) if row else None


def list_jobs(
    status: str | None = None,
    limit: int = 100,
) -> list[Job]:
    sql = "SELECT * FROM applications"
    params: list = []
    if status:
        sql += " WHERE status = ?"
        params.append(status)
    sql += " ORDER BY parsed_at DESC LIMIT ?"
    params.append(limit)
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [Job.from_db_row(dict(r)) for r in rows]


def count_jobs() -> int:
    with connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM applications").fetchone()
    return int(row["n"]) if row else 0


# ---------------------------------------------------------------------------
# Outcomes (minimal v0.0.2 stub — full workflow in a later version)
# ---------------------------------------------------------------------------
def log_outcome(job_id: str, status: str, notes: str | None = None) -> int:
    """Record an outcome event. Returns the new outcomes.id."""
    ts = _now_iso()
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO outcomes (job_id, status, notes, recorded_at) "
            "VALUES (?, ?, ?, ?)",
            (job_id, status, notes, ts),
        )
        conn.execute(
            "UPDATE applications SET status = ?, last_seen_at = ? "
            "WHERE job_id = ?",
            (status, ts, job_id),
        )
        return int(cursor.lastrowid)


def mark_jobnet_logged(job_ids: list[str], when: str | None = None) -> int:
    """Stamp ``jobnet_logged_at`` on each given job and advance early-stage
    statuses to ``applied`` (outcome statuses are left untouched).
    Returns rows updated."""
    if not job_ids:
        return 0
    ts = when or _now_iso()
    placeholders = ",".join("?" for _ in job_ids)
    with connect() as conn:
        cursor = conn.execute(
            f"UPDATE applications "
            f"SET jobnet_logged_at = ?, last_seen_at = ?, "
            f"    status = CASE WHEN status IN ('parsed', 'tailored') "
            f"             THEN 'applied' ELSE status END "
            f"WHERE job_id IN ({placeholders})",
            (ts, ts, *job_ids),
        )
        return cursor.rowcount


def list_outcomes(job_id: str | None = None, limit: int = 100) -> list[dict]:
    """Return outcomes ordered most-recent-first."""
    sql = (
        "SELECT id, job_id, status, notes, recorded_at FROM outcomes"
    )
    params: list = []
    if job_id:
        sql += " WHERE job_id = ?"
        params.append(job_id)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def list_jobnet_logged_in_window(
    start_iso: str, end_iso: str
) -> list[Job]:
    """Return jobs whose ``jobnet_logged_at`` falls inside [start, end] (inclusive)."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM applications "
            "WHERE jobnet_logged_at IS NOT NULL "
            "AND jobnet_logged_at >= ? AND jobnet_logged_at <= ? "
            "ORDER BY jobnet_logged_at DESC",
            (start_iso, end_iso),
        ).fetchall()
    return [Job.from_db_row(dict(r)) for r in rows]


def _now_iso() -> str:
    from datetime import datetime as _dt
    return _dt.now().isoformat(timespec="seconds")
