"""Onboarding interview orchestration.

Walks the user through the 10-chapter interview script from
``docs/workflows/onboarding.md`` and builds their ``profile.yaml`` +
``targets.yaml`` (+ optional ``dagpenge.yaml``) from scratch.

Design notes:

  - Pure CLI flow. ``input()`` for prompts, ``yaml`` for state.
  - Each chapter is a discrete step; state saves after every chapter so
    the user can ``Ctrl+C`` and ``danapply onboard --resume`` later.
  - Push-back logic is concentrated in Chapter 6 (reality-check synthesis)
    rather than scattered through each chapter — keeps the per-chapter
    flow tight and the contradictions surface once, where the user can
    deal with them.
  - Voice capture (Chapter 9) defers to ``extract/voice.py``. CV calibration
    (Chapter 8) defers to ``extract/register.py``.

Public API:

    from danapply.onboarding import run_onboarding, reset_onboarding
"""

from danapply.onboarding.runner import run_onboarding
from danapply.onboarding.state import (
    clear_state,
    load_state,
    save_state,
    state_exists,
)

__all__ = [
    "clear_state",
    "load_state",
    "run_onboarding",
    "save_state",
    "state_exists",
]


def reset_onboarding() -> None:
    """Delete any saved onboarding state. Idempotent."""
    clear_state()
