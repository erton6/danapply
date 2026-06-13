"""Tests for the dagpenge tracker."""

from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path

import pytest
import yaml

from danapply import memory
from danapply.dagpenge import (
    DagpengeConfig,
    load_dagpenge_config,
    week_bounds,
    weekly_status,
)
from danapply.dagpenge.tracker import weeks_history
from danapply.models import Job


@pytest.fixture(autouse=True)
def _isolated_data_dir(tmp_path: Path):
    os.environ["DANAPPLY_DATA_DIR"] = str(tmp_path)
    yield tmp_path
    os.environ.pop("DANAPPLY_DATA_DIR", None)


def _make_dagpenge_yaml(tmp_path: Path, **fields) -> None:
    pdir = tmp_path / "profile"
    pdir.mkdir(parents=True, exist_ok=True)
    defaults = {
        "on_dagpenge": True,
        "a_kasse": "Test A-kasse",
        "my_plan_field": "Analyst",
        "weekly_threshold": 2,
    }
    defaults.update(fields)
    (pdir / "dagpenge.yaml").write_text(yaml.safe_dump(defaults), encoding="utf-8")


# ---------------------------------------------------------------------------
# Week math
# ---------------------------------------------------------------------------
def test_week_bounds_returns_monday_to_sunday() -> None:
    # 2026-06-10 is a Wednesday
    monday, sunday = week_bounds(date(2026, 6, 10))
    assert monday == date(2026, 6, 8)
    assert sunday == date(2026, 6, 14)


def test_week_bounds_for_monday() -> None:
    monday, sunday = week_bounds(date(2026, 6, 8))
    assert monday == date(2026, 6, 8)
    assert sunday == date(2026, 6, 14)


def test_week_bounds_for_sunday() -> None:
    monday, sunday = week_bounds(date(2026, 6, 14))
    assert monday == date(2026, 6, 8)
    assert sunday == date(2026, 6, 14)


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------
def test_load_dagpenge_config_missing_returns_default() -> None:
    cfg = load_dagpenge_config()
    assert cfg.on_dagpenge is False
    assert cfg.weekly_threshold == 2


def test_load_dagpenge_config_reads_yaml(tmp_path: Path) -> None:
    _make_dagpenge_yaml(tmp_path, weekly_threshold=3, a_kasse="Foo A-kasse")
    cfg = load_dagpenge_config()
    assert cfg.on_dagpenge is True
    assert cfg.weekly_threshold == 3
    assert cfg.a_kasse == "Foo A-kasse"


def test_load_dagpenge_config_malformed_returns_default(tmp_path: Path) -> None:
    pdir = tmp_path / "profile"
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / "dagpenge.yaml").write_text("not: valid: yaml: [", encoding="utf-8")
    cfg = load_dagpenge_config()
    assert cfg.on_dagpenge is False


# ---------------------------------------------------------------------------
# Weekly status — DB integration
# ---------------------------------------------------------------------------
def _insert_logged_jobs(when: datetime, count: int) -> None:
    """Insert ``count`` jobs all logged at ``when``."""
    memory.init_db()
    for i in range(count):
        j = Job(
            title=f"Analyst {i}",
            company=f"Corp {i}",
            jobnet_logged_at=when,
        )
        j.ensure_job_id()
        memory.upsert_job(j)


def test_weekly_status_zero_when_nothing_logged() -> None:
    cfg = DagpengeConfig(on_dagpenge=True, weekly_threshold=2)
    status = weekly_status(reference=date(2026, 6, 10), config=cfg)
    assert status.logged_count == 0
    assert status.is_compliant is False
    assert status.shortfall == 2


def test_weekly_status_counts_jobs_in_window() -> None:
    cfg = DagpengeConfig(on_dagpenge=True, weekly_threshold=2)
    # 2026-06-10 = Wednesday
    _insert_logged_jobs(datetime(2026, 6, 10, 14, 30), count=3)
    status = weekly_status(reference=date(2026, 6, 10), config=cfg)
    assert status.logged_count == 3
    assert status.is_compliant is True
    assert status.shortfall == 0


def test_weekly_status_excludes_jobs_outside_window() -> None:
    cfg = DagpengeConfig(on_dagpenge=True, weekly_threshold=2)
    # Insert one job last week + two this week
    _insert_logged_jobs(datetime(2026, 6, 2, 10, 0), count=1)  # last week
    _insert_logged_jobs(datetime(2026, 6, 9, 10, 0), count=2)  # this week (Mon)
    status = weekly_status(reference=date(2026, 6, 10), config=cfg)
    assert status.logged_count == 2  # only this week's


def test_weekly_status_summary_line_includes_marker() -> None:
    cfg = DagpengeConfig(on_dagpenge=True, weekly_threshold=2)
    status = weekly_status(reference=date(2026, 6, 10), config=cfg)
    line = status.summary_line()
    assert "Week 2026-06-08" in line
    assert "0/2 logged" in line


def test_weekly_status_days_remaining_decreases_through_week() -> None:
    cfg = DagpengeConfig(on_dagpenge=True, weekly_threshold=2)
    mon = weekly_status(reference=date(2026, 6, 8), config=cfg)  # Monday
    wed = weekly_status(reference=date(2026, 6, 10), config=cfg)  # Wednesday
    sun = weekly_status(reference=date(2026, 6, 14), config=cfg)  # Sunday
    assert mon.days_remaining_in_week == 7
    assert wed.days_remaining_in_week == 5
    assert sun.days_remaining_in_week == 1


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------
def test_weeks_history_returns_requested_count() -> None:
    cfg = DagpengeConfig(on_dagpenge=True, weekly_threshold=2)
    results = weeks_history(weeks_back=4, config=cfg)
    assert len(results) == 4
    # Oldest first, most recent last
    assert results[-1].week_start >= results[0].week_start
