"""Interview-prep brief — payload validation + markdown rendering.

Claude Code writes the brief content in-conversation (company-specific
questions grounded in the job description + the user's profile) and hands
it to ``danapply interview-prep --content``. This module validates the
payload and renders the markdown. A templated fallback exists for runs
without ``--content``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from danapply.config import Profile
from danapply.models import Job


@dataclass
class InterviewBrief:
    """Structured interview-prep output."""

    job: Job
    behavioural_questions: list[str] = field(default_factory=list)
    technical_questions: list[str] = field(default_factory=list)
    watch_outs: list[str] = field(default_factory=list)
    questions_to_ask: list[str] = field(default_factory=list)
    notes: str = ""
    generated_at: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )
    generation_method: str = "templated"
    """``claude`` when written by Claude Code in-conversation;
    ``templated`` for the fallback."""


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------
def build_interview_brief(
    job: Job,
    profile: Profile,
    round_number: int = 1,
    short: bool = False,
) -> InterviewBrief:
    """Build the templated fallback brief for one job.

    The real, company-specific brief is written by Claude Code
    in-conversation (see ``workflows/interview_prep.md``) and rendered via
    ``brief_from_content``. This templated version exists so the command
    still produces something useful when invoked without ``--content``.
    """
    return _templated_brief(job, profile, round_number, short)


def brief_from_content(job: Job, content: dict) -> InterviewBrief:
    """Validate a Claude-written brief payload into an ``InterviewBrief``.

    Expected keys: ``behavioural_questions``, ``technical_questions``,
    ``watch_outs``, ``questions_to_ask`` (each a non-empty list of
    strings) and optional ``notes`` (string).

    Raises ``ValueError`` with a readable message on malformed payloads —
    the CLI surfaces it so Claude can fix the JSON and retry.
    """
    if not isinstance(content, dict):
        raise ValueError(f"Brief content must be a JSON object, got {type(content).__name__}.")

    def _str_list(key: str) -> list[str]:
        value = content.get(key)
        if not isinstance(value, list) or not value:
            raise ValueError(f"'{key}' must be a non-empty list of strings.")
        items = [str(v).strip() for v in value if str(v).strip()]
        if not items:
            raise ValueError(f"'{key}' contains no usable entries.")
        return items

    return InterviewBrief(
        job=job,
        behavioural_questions=_str_list("behavioural_questions"),
        technical_questions=_str_list("technical_questions"),
        watch_outs=_str_list("watch_outs"),
        questions_to_ask=_str_list("questions_to_ask"),
        notes=str(content.get("notes") or ""),
        generation_method="claude",
    )


# ---------------------------------------------------------------------------
# Templated fallback (no API key path)
# ---------------------------------------------------------------------------
def _templated_brief(
    job: Job, profile: Profile, round_number: int, short: bool
) -> InterviewBrief:
    """Generic prep when LLM is unavailable. Honest in the notes about it."""
    company = job.company or "the company"
    title = job.title or "this role"

    behavioural = [
        f"Walk us through your background and what drew you to {company}.",
        "Tell me about a time you had to break down an ambiguous problem.",
        f"How would you describe the value you'd bring to the {title} team?",
        "Describe a time you challenged a colleague's assumption — how did you handle it?",
        "Tell me about a failure you learned from.",
    ]

    technical = [
        f"How would you scope a project for the {title} role?",
        "Walk us through how you'd analyse a typical business question.",
        "Walk us through your CV (3-minute version — practice this).",
    ]

    watch_outs = [
        "Templated brief — your real prep needs company-specific research.",
        "Confirm interview format (in-person / Zoom / Teams) and exact location.",
    ]
    if job.deadline:
        watch_outs.append(f"Deadline is {job.deadline}; confirm timeline expectations.")

    questions_to_ask = [
        "What does the first 6 months look like in this role?",
        f"What's the team's current top priority at {company}?",
        "How does success get measured in this position after the first year?",
        "What's the most common reason people leave the firm after the first 2 years?",
    ]

    if short:
        behavioural = behavioural[:3]
        technical = technical[:3]
        watch_outs = watch_outs[:3]
        questions_to_ask = questions_to_ask[:3]

    return InterviewBrief(
        job=job,
        behavioural_questions=behavioural,
        technical_questions=technical,
        watch_outs=watch_outs,
        questions_to_ask=questions_to_ask,
        notes=(
            f"Templated brief for round {round_number}. For a company-specific, "
            f"profile-tailored version, ask Claude Code to write the brief "
            f"(it reads the job + your profile and passes --content)."
        ),
        generation_method="templated",
    )


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------
def render_brief_markdown(brief: InterviewBrief, round_number: int = 1) -> str:
    """Render the brief as a markdown document the user can read offline."""
    job = brief.job
    company = job.company or "(no company)"
    title = job.title or "(no title)"

    parts = [
        f"# Interview prep — {title} at {company}",
        "",
        f"**Round:** {round_number}  ",
        f"**Score:** {job.score}/100  ",
        f"**Posting deadline:** {job.deadline or '(rolling)'}  ",
        f"**Generation method:** {brief.generation_method}  ",
        f"**Generated:** {brief.generated_at}",
        "",
        "## Snapshot",
        f"You applied to {company} for the {title} role.",
        "Use this brief to focus 30–60 minutes of prep. Edit anything that's wrong.",
        "",
        "## Likely behavioural questions",
        "",
    ]
    parts.extend(f"{i}. {q}" for i, q in enumerate(brief.behavioural_questions, start=1))

    parts.extend([
        "",
        "## Likely technical / case questions",
        "",
    ])
    parts.extend(f"{i}. {q}" for i, q in enumerate(brief.technical_questions, start=1))

    parts.extend([
        "",
        "## Watch out for",
        "",
    ])
    parts.extend(f"- {w}" for w in brief.watch_outs)

    parts.extend([
        "",
        "## Questions to ask them",
        "",
    ])
    parts.extend(f"{i}. {q}" for i, q in enumerate(brief.questions_to_ask, start=1))

    if brief.notes:
        parts.extend(["", "## Notes", "", brief.notes])

    return "\n".join(parts) + "\n"
