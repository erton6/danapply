"""Jobnet 'Opret Joblog' automation-prompt generator.

Produces a ready-to-paste markdown prompt for Claude in Chrome that fills
the Jobnet form. Generated file naming follows the supplement-file pattern
documented in ``docs/workflows/joblog_prompt.md``: the first call on a
given date writes ``jobnet_joblog_YYYY-MM-DD.md``; subsequent calls write
``jobnet_joblog_YYYY-MM-DD_supplement_N.md``.

Once entries are saved to Jobnet (the user pastes the prompt into Claude
in Chrome, reviews, and clicks Gem), they should be marked as logged via
``memory.mark_jobnet_logged()`` so subsequent runs don't re-include them.
"""

from danapply.joblog.generator import (
    JoblogEntry,
    generate_joblog_prompt,
    pick_jobs_for_joblog,
    resolve_output_path,
)

__all__ = [
    "JoblogEntry",
    "generate_joblog_prompt",
    "pick_jobs_for_joblog",
    "resolve_output_path",
]
