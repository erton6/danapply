"""Tests for the Job pydantic model + slug helpers."""

from __future__ import annotations

from datetime import date

from danapply.models import Job, pascalcase_slug


# ---------------------------------------------------------------------------
# Slug helper
# ---------------------------------------------------------------------------
def test_pascalcase_slug_simple() -> None:
    assert pascalcase_slug("HelloFresh") == "HelloFresh"


def test_pascalcase_slug_strips_punctuation() -> None:
    assert pascalcase_slug("McKinsey & Company") == "McKinseyCompany"


def test_pascalcase_slug_handles_long_titles() -> None:
    out = pascalcase_slug("Junior Business Analyst (Asset Finance Tribe)")
    assert out == "JuniorBusinessAnalystAssetFinanceTribe"


def test_pascalcase_slug_empty() -> None:
    assert pascalcase_slug("") == ""


# ---------------------------------------------------------------------------
# Job model
# ---------------------------------------------------------------------------
def test_job_default_values() -> None:
    job = Job()
    assert job.title == ""
    assert job.company == ""
    assert job.data_confidence == "medium"
    assert job.status == "parsed"
    assert job.language == "EN"


def test_ensure_job_id_with_company_title_date() -> None:
    job = Job(
        title="Business Analyst",
        company="McKinsey & Company",
        posting_date=date(2026, 5, 17),
    )
    assert job.ensure_job_id() == "McKinseyCompany_BusinessAnalyst_2026-05-17"


def test_ensure_job_id_falls_back_to_hash() -> None:
    job = Job(title="X", company="Y", description_raw="some unique description text")
    job_id = job.ensure_job_id()
    assert job_id.startswith("Y_X_")
    assert len(job_id.split("_")[-1]) == 8  # hash component


def test_ensure_job_id_idempotent() -> None:
    job = Job(title="A", company="B", posting_date=date(2026, 1, 1))
    first = job.ensure_job_id()
    second = job.ensure_job_id()
    assert first == second


def test_to_db_row_serialises_dates() -> None:
    job = Job(
        title="X", company="Y",
        posting_date=date(2026, 6, 1),
        deadline=date(2026, 6, 15),
    )
    row = job.to_db_row()
    assert row["posting_date"] == "2026-06-01"
    assert row["deadline"] == "2026-06-15"
    assert isinstance(row["parsed_at"], str)
