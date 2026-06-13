"""Tests for the Jobnet joblog prompt generator."""

from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path

import pytest

from danapply.joblog import (
    JoblogEntry,
    generate_joblog_prompt,
    pick_jobs_for_joblog,
    resolve_output_path,
)
from danapply.models import Job


@pytest.fixture(autouse=True)
def _isolated_data_dir(tmp_path: Path):
    os.environ["DANAPPLY_DATA_DIR"] = str(tmp_path)
    yield tmp_path
    os.environ.pop("DANAPPLY_DATA_DIR", None)


def _job(title: str, company: str, score: int = 70, **kwargs) -> Job:
    """Build a Job for tests with a deterministic job_id."""
    j = Job(title=title, company=company, score=score, **kwargs)
    j.ensure_job_id()
    return j


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------
def test_pick_jobs_filters_by_threshold() -> None:
    jobs = [
        _job("Analyst", "A", score=80),
        _job("Engineer", "B", score=40),
        _job("Researcher", "C", score=65),
    ]
    included, excluded = pick_jobs_for_joblog(jobs, threshold=60)
    assert {j.company for j in included} == {"A", "C"}
    assert len(excluded) == 1 and excluded[0][0].company == "B"
    assert "score 40 < threshold 60" in excluded[0][1]


def test_pick_jobs_excludes_already_logged() -> None:
    j1 = _job("Analyst", "A", score=80,
              jobnet_logged_at=datetime(2026, 6, 1, 10, 0))
    j2 = _job("Insights", "B", score=80)
    included, excluded = pick_jobs_for_joblog([j1, j2])
    assert len(included) == 1 and included[0].company == "B"
    assert len(excluded) == 1 and "already logged" in excluded[0][1]


def test_pick_jobs_optional_keep_logged() -> None:
    j = _job("Analyst", "A", score=80,
             jobnet_logged_at=datetime(2026, 6, 1, 10, 0))
    included, excluded = pick_jobs_for_joblog(
        [j], exclude_already_logged=False
    )
    assert len(included) == 1
    assert excluded == []


def test_pick_jobs_empty_input_returns_empty() -> None:
    included, excluded = pick_jobs_for_joblog([])
    assert included == []
    assert excluded == []


# ---------------------------------------------------------------------------
# JoblogEntry
# ---------------------------------------------------------------------------
def test_joblog_entry_from_job_with_deadline() -> None:
    j = _job("Analyst", "Acme", deadline=date(2026, 6, 30),
             url="https://acme.example/job/1")
    e = JoblogEntry.from_job(j)
    assert e.title == "Analyst"
    assert e.company == "Acme"
    assert e.deadline == "2026-06-30"
    assert e.url == "https://acme.example/job/1"
    assert e.country == "Danmark"
    assert e.arbejdstid == "Fuldtid"


def test_joblog_entry_handles_missing_deadline() -> None:
    j = _job("Analyst", "Acme")
    e = JoblogEntry.from_job(j)
    assert "leave blank" in e.deadline.lower()


def test_joblog_entry_handles_missing_url() -> None:
    j = _job("Analyst", "Acme")
    e = JoblogEntry.from_job(j)
    assert "leave blank" in e.url


def test_joblog_entry_uses_placeholder_for_unknown_company() -> None:
    j = Job(title="Analyst", company="", score=70)
    j.ensure_job_id()
    e = JoblogEntry.from_job(j)
    assert e.company == "(no company)"


# ---------------------------------------------------------------------------
# Prompt rendering
# ---------------------------------------------------------------------------
def test_generate_prompt_includes_header_and_entries() -> None:
    jobs = [
        _job("Analyst", "Acme", deadline=date(2026, 7, 1)),
        _job("Researcher", "Beta Co"),
    ]
    prompt = generate_joblog_prompt(jobs)
    assert "create 2 entries" in prompt
    assert "Opret Joblog" in prompt
    assert "ENTRY 1 — Acme" in prompt
    assert "ENTRY 2 — Beta Co" in prompt
    assert "When all are saved" in prompt  # footer present


def test_generate_prompt_with_single_job_uses_singular() -> None:
    jobs = [_job("Analyst", "Acme")]
    prompt = generate_joblog_prompt(jobs)
    assert "create 1 entries" in prompt  # number doesn't pluralize the noun
    assert "ENTRY 1 — Acme" in prompt
    # singular phrasing for "the job" vs "the jobs"
    assert "between the job." in prompt


def test_generate_prompt_includes_audit_footer_with_excluded() -> None:
    jobs = [_job("Analyst", "Acme")]
    excluded = [(_job("Eng", "BadCo", score=40), "score 40 < threshold 60")]
    prompt = generate_joblog_prompt(jobs, excluded=excluded)
    assert "Footer — jobs excluded" in prompt
    assert "BadCo" in prompt
    assert "score 40" in prompt


def test_generate_prompt_with_zero_jobs_returns_empty_prompt() -> None:
    prompt = generate_joblog_prompt([])
    assert "No entries to log" in prompt
    assert "danapply parse" in prompt  # suggested next step


def test_generate_prompt_with_zero_jobs_lists_excluded_reasons() -> None:
    excluded = [(_job("X", "Y", score=20), "score too low")]
    prompt = generate_joblog_prompt([], excluded=excluded)
    assert "No entries to log" in prompt
    assert "Y" in prompt
    assert "score too low" in prompt


def test_entry_block_field_order_matches_jobnet_form() -> None:
    jobs = [_job("Analyst", "Acme")]
    prompt = generate_joblog_prompt(jobs)
    # Field order matters for the Claude-in-Chrome flow
    field_order = [
        "Stilling:",
        "Ansøgningsfrist:",
        "Arbejdstid:",
        "Virksomhedens navn:",
        "Adresse:",
        "Land:",
        "Postnummer og by:",
        "Kontaktperson:",
        "Telefonnummer:",
        "E-mail:",
        "Link til jobannonce:",
    ]
    positions = [prompt.find(f) for f in field_order]
    assert positions == sorted(positions), "Field order mismatch"


# ---------------------------------------------------------------------------
# Output path resolution — supplement files
# ---------------------------------------------------------------------------
def test_first_resolve_returns_dated_filename() -> None:
    path = resolve_output_path(when=date(2026, 6, 9))
    assert path.name == "jobnet_joblog_2026-06-09.md"


def test_second_resolve_returns_supplement() -> None:
    primary = resolve_output_path(when=date(2026, 6, 9))
    primary.touch()
    second = resolve_output_path(when=date(2026, 6, 9))
    assert second.name == "jobnet_joblog_2026-06-09_supplement_1.md"


def test_resolve_increments_supplement_number() -> None:
    primary = resolve_output_path(when=date(2026, 6, 9))
    primary.touch()
    second = resolve_output_path(when=date(2026, 6, 9))
    second.touch()
    third = resolve_output_path(when=date(2026, 6, 9))
    assert third.name == "jobnet_joblog_2026-06-09_supplement_2.md"


# ---------------------------------------------------------------------------
# CLI: --mark-logged stamps without generating a prompt file
# ---------------------------------------------------------------------------
def test_cli_mark_logged_writes_no_prompt_file(tmp_path, monkeypatch) -> None:

    from typer.testing import CliRunner

    from danapply import memory
    from danapply.cli import app

    monkeypatch.setenv("DANAPPLY_DATA_DIR", str(tmp_path / "data"))
    memory.init_db()
    job = Job(title="Analyst", company="Acme", description_raw="d", score=80)
    saved, _ = memory.upsert_job(job)

    runner = CliRunner()
    result = runner.invoke(
        app, ["joblog", "--mark-logged", "--job-ids", saved.job_id]
    )
    assert result.exit_code == 0, result.output
    assert "Marked 1 job(s)" in result.output

    prompts_dir = tmp_path / "data" / "joblog_prompts"
    written = list(prompts_dir.glob("*.md")) if prompts_dir.exists() else []
    assert written == [], f"--mark-logged must not generate prompt files: {written}"

    after = memory.get_job(saved.job_id)
    assert after is not None
    assert after.jobnet_logged_at is not None
    assert after.status == "applied"


def test_cli_mark_logged_requires_job_ids(tmp_path, monkeypatch) -> None:
    from typer.testing import CliRunner

    from danapply.cli import app

    monkeypatch.setenv("DANAPPLY_DATA_DIR", str(tmp_path / "data"))
    runner = CliRunner()
    result = runner.invoke(app, ["joblog", "--mark-logged"])
    assert result.exit_code == 2
