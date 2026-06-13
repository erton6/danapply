"""Schema for chapters + questions + answers in the onboarding flow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

AnswerType = Literal["text", "long_text", "choice", "multi_choice", "number", "bool", "file_path"]


@dataclass
class Question:
    """A single prompt the runner asks the user."""

    id: str
    prompt: str
    answer_type: AnswerType = "text"
    choices: list[str] | None = None
    """For ``choice`` and ``multi_choice``. Otherwise ignored."""
    required: bool = True
    help_text: str | None = None
    """Optional one-line hint shown below the prompt."""
    default: Any = None


@dataclass
class Chapter:
    """A discrete onboarding section."""

    id: str
    title: str
    intent: str
    """One-line summary shown at the start of the chapter."""
    questions: list[Question] = field(default_factory=list)
    pre_amble: str | None = None
    """Optional multi-paragraph intro text printed before the first question."""
    post_amble: str | None = None
    """Optional text printed after the last question."""
    optional: bool = False
    """If True, the chapter can be skipped without breaking the profile."""

    def question(self, qid: str) -> Question | None:
        for q in self.questions:
            if q.id == qid:
                return q
        return None
