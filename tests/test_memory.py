"""SQLite memory layer tests."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pytest

from danapply import memory
from danapply.models import Job


@pytest.fixture
def isolated_db(tmp_path: Path):
    """Point DANAPPLY_DATA_DIR at a temp dir for each test."""
    os.environ["DANAPPLY_DATA_DIR"] = str(tmp_path)
    yield tmp_path
    os.environ.pop("DANAPPLY_DATA_DIR", None)


def test_init_db_creates_file(isolated_db: Path) -> None:
    db_path = memory.init_db()
    assert db_path.exists()
    assert memory.schema_version() == memory.SCHEMA_VERSION


def test_init_db_idempotent(isolated_db: Path) -> None:
    memory.init_db()
    memory.init_db()  # should not raise
    assert memory.schema_version() == memory.SCHEMA_VERSION


def test_schema_version_none_when_not_initialised(isolated_db: Path) -> None:
    assert memory.schema_version() is None


def test_upsert_new_job(isolated_db: Path) -> None:
    memory.init_db()
    job = Job(title="Business Analyst", company="TestCorp", posting_date=date(2026, 6, 1))
    saved, is_new = memory.upsert_job(job)
    assert is_new is True
    assert saved.job_id == "TestCorp_BusinessAnalyst_2026-06-01"
    assert memory.count_jobs() == 1


def test_upsert_existing_job_not_new(isolated_db: Path) -> None:
    memory.init_db()
    job = Job(title="X", company="Y", posting_date=date(2026, 1, 1))
    memory.upsert_job(job)
    _, is_new = memory.upsert_job(job)
    assert is_new is False
    assert memory.count_jobs() == 1


def test_get_job_roundtrip(isolated_db: Path) -> None:
    memory.init_db()
    original = Job(
        title="Insights Analyst",
        company="Telenor",
        location="Copenhagen",
        posting_date=date(2026, 5, 27),
        source="linkedin",
        language="DA",
        description_raw="Some description.",
        data_confidence="high",
    )
    memory.upsert_job(original)
    retrieved = memory.get_job(original.job_id)
    assert retrieved is not None
    assert retrieved.title == "Insights Analyst"
    assert retrieved.company == "Telenor"
    assert retrieved.posting_date == date(2026, 5, 27)
    assert retrieved.language == "DA"


def test_list_jobs_orders_by_recent_first(isolated_db: Path) -> None:
    memory.init_db()
    memory.upsert_job(Job(title="A", company="C1", posting_date=date(2026, 1, 1)))
    memory.upsert_job(Job(title="B", company="C2", posting_date=date(2026, 2, 1)))
    jobs = memory.list_jobs()
    assert len(jobs) == 2


def test_log_outcome_updates_status(isolated_db: Path) -> None:
    memory.init_db()
    job = Job(title="X", company="Y", posting_date=date(2026, 1, 1))
    saved, _ = memory.upsert_job(job)
    memory.log_outcome(saved.job_id, "interview_scheduled", notes="First round next week")
    fetched = memory.get_job(saved.job_id)
    assert fetched is not None
    assert fetched.status == "interview_scheduled"


# ---------------------------------------------------------------------------
# Lifecycle guards — a re-parse must never reset pipeline state
# ---------------------------------------------------------------------------
def test_reparse_does_not_reset_score_or_status(isolated_db: Path) -> None:
    """Regression: re-parsing an already-tracked posting used to clobber
    score (back to 0) and status (back to 'parsed')."""
    memory.init_db()
    job = Job(title="Business Analyst", company="Acme",
              description_raw="data analysis")
    memory.upsert_job(job)
    job.score = 78
    from datetime import datetime
    job.scored_at = datetime.now()
    job.score_breakdown = {"total": 78}
    memory.upsert_job(job)
    memory.log_outcome(job.job_id, "interview_scheduled")

    # Same posting parsed again next week — fresh defaults
    reparsed = Job(title="Business Analyst", company="Acme",
                   description_raw="data analysis")
    _, is_new = memory.upsert_job(reparsed)
    assert is_new is False

    after = memory.get_job(job.job_id)
    assert after is not None
    assert after.score == 78
    assert after.status == "interview_scheduled"
    assert after.score_breakdown == {"total": 78}


def test_reparse_does_not_downgrade_confidence(isolated_db: Path) -> None:
    memory.init_db()
    job = Job(title="X", company="Y", description_raw="d",
              data_confidence="high")
    memory.upsert_job(job)
    weaker = Job(title="X", company="Y", description_raw="d",
                 data_confidence="medium")
    memory.upsert_job(weaker)
    after = memory.get_job(job.job_id)
    assert after is not None
    assert after.data_confidence == "high"


def test_explicit_status_transition_still_wins(isolated_db: Path) -> None:
    memory.init_db()
    job = Job(title="X", company="Y", description_raw="d")
    saved, _ = memory.upsert_job(job)
    saved.status = "tailored"
    memory.upsert_job(saved)
    after = memory.get_job(saved.job_id)
    assert after is not None
    assert after.status == "tailored"


def test_mark_jobnet_logged_advances_status_to_applied(isolated_db: Path) -> None:
    memory.init_db()
    job = Job(title="X", company="Y", description_raw="d")
    saved, _ = memory.upsert_job(job)
    count = memory.mark_jobnet_logged([saved.job_id])
    assert count == 1
    after = memory.get_job(saved.job_id)
    assert after is not None
    assert after.status == "applied"
    assert after.jobnet_logged_at is not None


def test_mark_jobnet_logged_keeps_outcome_status(isolated_db: Path) -> None:
    memory.init_db()
    job = Job(title="X", company="Y", description_raw="d")
    saved, _ = memory.upsert_job(job)
    memory.log_outcome(saved.job_id, "interview_scheduled")
    memory.mark_jobnet_logged([saved.job_id])
    after = memory.get_job(saved.job_id)
    assert after is not None
    assert after.status == "interview_scheduled"
