"""Canonical filesystem paths for DanApply.

The data directory is overridable via the ``DANAPPLY_DATA_DIR`` env var,
otherwise defaults to ``~/danapply-data``. Never put user data inside the
package directory — the package is read-only OSS, user data is local-first.
"""

from __future__ import annotations

import os
from pathlib import Path


def data_dir() -> Path:
    """Return the root directory for the user's DanApply data."""
    env = os.environ.get("DANAPPLY_DATA_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return Path.home() / "danapply-data"


def profile_dir() -> Path:
    return data_dir() / "profile"


def raw_searches_dir() -> Path:
    return data_dir() / "raw_searches"


def research_notes_dir() -> Path:
    return data_dir() / "research_notes"


def resume_drafts_dir() -> Path:
    return data_dir() / "resume_drafts"


def cover_letters_dir() -> Path:
    return data_dir() / "cover_letters"


def joblog_prompts_dir() -> Path:
    return data_dir() / "joblog_prompts"


def interview_prep_dir() -> Path:
    return data_dir() / "interview_prep"


def prioritized_lists_dir() -> Path:
    return data_dir() / "prioritized_lists"


def sessions_dir() -> Path:
    return data_dir() / "sessions"


def memory_db_path() -> Path:
    return data_dir() / "memory.db"


def profile_yaml_path() -> Path:
    return profile_dir() / "profile.yaml"


def targets_yaml_path() -> Path:
    return profile_dir() / "targets.yaml"


def cv_content_path() -> Path:
    return profile_dir() / "cv_content.md"


def voice_profile_path() -> Path:
    """Legacy path — kept for backwards compatibility with v0.0.6 scaffolding.
    New code should use ``voice_profile_yaml_path`` (the structured source of
    truth) and ``voice_profile_md_path`` (human-readable companion)."""
    return profile_dir() / "voice_profile.md"


def voice_profile_yaml_path() -> Path:
    """The structured voice profile — read by the tailoring code."""
    return profile_dir() / "voice_profile.yaml"


def voice_profile_md_path() -> Path:
    """The human-readable voice profile companion — for the user to review."""
    return profile_dir() / "voice_profile.md"


def all_data_subdirs() -> list[Path]:
    """All subdirectories that ``danapply init`` should create."""
    return [
        profile_dir(),
        raw_searches_dir(),
        research_notes_dir(),
        resume_drafts_dir(),
        cover_letters_dir(),
        joblog_prompts_dir(),
        interview_prep_dir(),
        prioritized_lists_dir(),
        sessions_dir(),
    ]
