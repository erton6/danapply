"""Dagpenge compliance tracker.

Reads ``profile/dagpenge.yaml`` for the user's weekly application
threshold and queries ``memory.db`` for jobs logged to Jobnet this week.
Reports counts, days remaining, and whether the user is on track.

Week boundaries follow DK convention: Monday 00:00 to Sunday 23:59 in
the local timezone.
"""

from danapply.dagpenge.tracker import (
    DagpengeConfig,
    DagpengeStatus,
    load_dagpenge_config,
    week_bounds,
    weekly_status,
)

__all__ = [
    "DagpengeConfig",
    "DagpengeStatus",
    "load_dagpenge_config",
    "week_bounds",
    "weekly_status",
]
