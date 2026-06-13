"""Dagpenge weekly compliance tracking."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

import yaml

from danapply import memory, paths
from danapply.models import Job


@dataclass
class DagpengeConfig:
    """User-curated dagpenge state loaded from ``dagpenge.yaml``."""

    on_dagpenge: bool = False
    a_kasse: str = ""
    my_plan_field: str = ""
    weekly_threshold: int = 2
    joblog_auto_generate: bool = True


@dataclass
class DagpengeStatus:
    """Snapshot of the current week's compliance state."""

    week_start: date
    week_end: date
    threshold: int
    logged_count: int
    logged_jobs: list[Job]
    days_remaining_in_week: int
    is_compliant: bool
    config: DagpengeConfig

    @property
    def shortfall(self) -> int:
        return max(0, self.threshold - self.logged_count)

    def summary_line(self) -> str:
        """One-line human summary."""
        prefix = "✓" if self.is_compliant else ("⚠" if self.shortfall > 0 else "·")
        return (
            f"{prefix} Week {self.week_start.isoformat()}–"
            f"{self.week_end.isoformat()}: "
            f"{self.logged_count}/{self.threshold} logged, "
            f"{self.days_remaining_in_week} days remaining"
        )


def load_dagpenge_config(profile_dir: Path | None = None) -> DagpengeConfig:
    """Load dagpenge.yaml. Returns a default (off-dagpenge) config when missing."""
    pdir = profile_dir or paths.profile_dir()
    path = pdir / "dagpenge.yaml"
    if not path.exists():
        return DagpengeConfig()
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return DagpengeConfig()
    if not isinstance(data, dict):
        return DagpengeConfig()
    return DagpengeConfig(
        on_dagpenge=bool(data.get("on_dagpenge", False)),
        a_kasse=str(data.get("a_kasse", "")),
        my_plan_field=str(data.get("my_plan_field", "")),
        weekly_threshold=int(data.get("weekly_threshold", 2)),
        joblog_auto_generate=bool(data.get("joblog_auto_generate", True)),
    )


def week_bounds(reference: date | None = None) -> tuple[date, date]:
    """Return (Monday, Sunday) for the week containing ``reference``.

    Defaults to today. Always returns dates, not datetimes — callers
    that need exact instants use ``datetime.combine`` themselves.
    """
    ref = reference or date.today()
    weekday = ref.weekday()  # Monday=0
    monday = ref - timedelta(days=weekday)
    sunday = monday + timedelta(days=6)
    return monday, sunday


def weekly_status(
    reference: date | None = None,
    config: DagpengeConfig | None = None,
) -> DagpengeStatus:
    """Compute compliance status for the week containing ``reference``."""
    ref = reference or date.today()
    config = config or load_dagpenge_config()
    monday, sunday = week_bounds(ref)

    start_dt = datetime.combine(monday, time.min)
    end_dt = datetime.combine(sunday, time.max)

    memory.init_db()
    logged = memory.list_jobnet_logged_in_window(
        start_dt.isoformat(timespec="seconds"),
        end_dt.isoformat(timespec="seconds"),
    )

    days_remaining = max(0, (sunday - ref).days + 1)

    return DagpengeStatus(
        week_start=monday,
        week_end=sunday,
        threshold=config.weekly_threshold,
        logged_count=len(logged),
        logged_jobs=logged,
        days_remaining_in_week=days_remaining,
        is_compliant=len(logged) >= config.weekly_threshold,
        config=config,
    )


def weeks_history(
    weeks_back: int = 8, config: DagpengeConfig | None = None
) -> list[DagpengeStatus]:
    """Compliance status for the last ``weeks_back`` weeks (oldest first)."""
    config = config or load_dagpenge_config()
    today = date.today()
    results: list[DagpengeStatus] = []
    for offset in range(weeks_back - 1, -1, -1):
        ref = today - timedelta(weeks=offset)
        results.append(weekly_status(ref, config))
    return results
