"""Onboarding state — answer storage + pause/resume support.

Lives at ``~/danapply-data/sessions/onboarding_state.yaml``. Saved after
each chapter completes, so the user can ``Ctrl+C`` mid-interview and
``danapply onboard --resume`` later.

State shape::

    started_at: 2026-06-09T14:23:11
    last_updated_at: 2026-06-09T14:35:02
    answers:
      welcome:
        ready: true
      situation:
        name: "Sofia Almeida"
        ...
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from danapply import paths


STATE_FILENAME = "onboarding_state.yaml"


def state_path() -> Path:
    return paths.sessions_dir() / STATE_FILENAME


@dataclass
class OnboardingState:
    started_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    last_updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    answers: dict[str, dict[str, Any]] = field(default_factory=dict)
    """{chapter_id: {question_id: answer}}"""

    def chapter_completed(self, chapter_id: str) -> bool:
        return chapter_id in self.answers

    def record(self, chapter_id: str, answers: dict[str, Any]) -> None:
        self.answers[chapter_id] = answers
        self.last_updated_at = datetime.now().isoformat(timespec="seconds")

    def get_answer(self, chapter_id: str, question_id: str) -> Any:
        return self.answers.get(chapter_id, {}).get(question_id)

    def completed_chapters(self) -> list[str]:
        return list(self.answers.keys())


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def state_exists() -> bool:
    return state_path().exists()


def load_state() -> OnboardingState | None:
    """Load state from disk. Returns None if no state file exists or it's malformed."""
    p = state_path()
    if not p.exists():
        return None
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    return OnboardingState(
        started_at=data.get("started_at") or datetime.now().isoformat(timespec="seconds"),
        last_updated_at=data.get("last_updated_at") or datetime.now().isoformat(timespec="seconds"),
        answers=data.get("answers") or {},
    )


def save_state(state: OnboardingState) -> Path:
    """Write state to disk. Returns the path."""
    p = state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        yaml.safe_dump(asdict(state), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return p


def clear_state() -> None:
    """Delete the state file. Idempotent."""
    p = state_path()
    if p.exists():
        p.unlink()
