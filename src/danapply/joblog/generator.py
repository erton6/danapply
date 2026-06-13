"""Jobnet prompt generator.

Format mirrors the working prompts in ``automated_job_search/joblog_prompts/``
(see ``docs/workflows/joblog_prompt.md`` for the canonical spec).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from danapply import paths
from danapply.config import Profile
from danapply.models import Job


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------
def pick_jobs_for_joblog(
    jobs: list[Job],
    threshold: int = 60,
    exclude_already_logged: bool = True,
) -> tuple[list[Job], list[tuple[Job, str]]]:
    """Pick jobs to include + record which were excluded with reasons.

    Returns ``(included, excluded_with_reason)``.
    """
    included: list[Job] = []
    excluded: list[tuple[Job, str]] = []

    for j in jobs:
        if exclude_already_logged and j.jobnet_logged_at is not None:
            excluded.append((j, "already logged to Jobnet"))
            continue
        if j.score < threshold:
            excluded.append((j, f"score {j.score} < threshold {threshold}"))
            continue
        included.append(j)

    return included, excluded


# ---------------------------------------------------------------------------
# Entry data structure
# ---------------------------------------------------------------------------
@dataclass
class JoblogEntry:
    """One Jobnet form entry's worth of fields."""

    company: str
    title: str
    deadline: str  # YYYY-MM-DD or "leave blank (rolling)"
    arbejdstid: str  # "Fuldtid" / "Deltid" / "Tidsbegrænset (N md)"
    address: str  # or "leave blank"
    country: str  # default "Danmark"
    postnummer_by: str  # NNNN City or "leave blank — ..."
    contact_person: str
    phone: str
    email: str
    url: str

    @classmethod
    def from_job(cls, job: Job) -> JoblogEntry:
        """Translate a Job → JoblogEntry, using conservative defaults
        when fields are missing. Address/postal are never invented —
        they stay 'leave blank' when not in the job data."""
        deadline = (
            job.deadline.isoformat() if job.deadline else "leave blank (rolling)"
        )
        return cls(
            company=job.company or "(no company)",
            title=job.title or "(no title)",
            deadline=deadline,
            arbejdstid="Fuldtid",
            address="leave blank",
            country="Danmark",
            postnummer_by=(
                "leave blank — tick \"Jeg kender hverken postnummer eller by\""
            ),
            contact_person="leave blank",
            phone="leave blank",
            email="leave blank",
            url=job.url or "leave blank",
        )


# ---------------------------------------------------------------------------
# Prompt rendering
# ---------------------------------------------------------------------------
def generate_joblog_prompt(
    jobs: list[Job],
    excluded: list[tuple[Job, str]] | None = None,
    profile: Profile | None = None,  # noqa: ARG001 — kept for future alignment checks
) -> str:
    """Render the full prompt as a markdown string."""
    n = len(jobs)
    if n == 0:
        return _empty_prompt(excluded or [])

    entries = [JoblogEntry.from_job(j) for j in jobs]
    parts = [_header(n)]
    for i, e in enumerate(entries, start=1):
        parts.append(_entry_block(i, e))
    parts.append(_footer())

    if excluded:
        parts.append("")
        parts.append("---")
        parts.append("")
        parts.append("## Footer — jobs excluded from this prompt (audit trail)")
        parts.append("")
        for job, reason in excluded:
            company = job.company or "(no company)"
            title = job.title or "(no title)"
            parts.append(f"- **{company}** — {title} (score {job.score}) — {reason}")

    return "\n".join(parts) + "\n"


def _header(n: int) -> str:
    return (
        f"You are going to create {n} entries in the Jobnet \"Opret Joblog\" "
        f"form that is currently open in this tab. I am giving you blanket "
        f"permission upfront for this session: you may click \"Gem\" to save "
        f"each joblog and reopen \"Opret Joblog\" between entries — do NOT "
        f"pause to ask for confirmation between fields or between the "
        f"{'job' if n == 1 else 'jobs'}. Only stop and ask if a field is "
        f"genuinely ambiguous or the page throws a validation error you "
        f"can't resolve.\n\n"
        f"Do NOT upload any files. Skip the \"Upload jobansøgning\", "
        f"\"Upload CV\", and \"Upload jobannonce\" sections entirely — leave "
        f"them empty.\n\n"
        f"For every entry:\n"
        f"- Skip the \"Skriv evt. noter om jobbet\" notes section — leave it empty.\n"
        f"- \"Hvor langt er du med at søge dette job?\" → Søgt\n"
        f"- \"Hvordan fandt du jobbet?\" → Opslået stilling\n"
        f"- \"Hvordan søger du jobbet?\" → Digitalt\n"
        f"- Arbejdstid → Fuldtid (unless I note otherwise below)\n"
        f"- After filling everything, click \"Gem\" to save. Then click "
        f"\"Opret Joblog\" again (or reopen it from the menu) and start the "
        f"next entry.\n"
    )


def _entry_block(n: int, e: JoblogEntry) -> str:
    return (
        f"\nENTRY {n} — {e.company}\n"
        f"- Stilling: {e.title}\n"
        f"- Ansøgningsfrist: {e.deadline}\n"
        f"- Arbejdstid: {e.arbejdstid}\n"
        f"- Virksomhedens navn: {e.company}\n"
        f"- Adresse: {e.address}\n"
        f"- Land: {e.country}\n"
        f"- Postnummer og by: {e.postnummer_by}\n"
        f"- Kontaktperson: {e.contact_person}\n"
        f"- Telefonnummer: {e.phone}\n"
        f"- E-mail: {e.email}\n"
        f"- Link til jobannonce: {e.url}\n"
    )


def _footer() -> str:
    return (
        "\nWhen all are saved, give me a short summary of what was created "
        "and flag anything you had to skip or guess.\n"
    )


def _empty_prompt(excluded: list[tuple[Job, str]]) -> str:
    parts = [
        "# No entries to log\n",
        "DanApply selected zero jobs for this prompt. Reasons:\n",
    ]
    if excluded:
        for job, reason in excluded:
            company = job.company or "(no company)"
            title = job.title or "(no title)"
            parts.append(
                f"- **{company}** — {title} (score {job.score}) — {reason}"
            )
    else:
        parts.append("- No scored jobs in your memory.db.")
    parts.append("")
    parts.append(
        "Run `danapply parse ...` + `danapply score` first, then re-run "
        "`danapply joblog`."
    )
    return "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Output path resolution — supplement-file pattern
# ---------------------------------------------------------------------------
def resolve_output_path(when: date | None = None) -> Path:
    """Pick the next unused filename for ``today``.

    First call returns ``jobnet_joblog_YYYY-MM-DD.md``. Subsequent calls
    on the same date return ``jobnet_joblog_YYYY-MM-DD_supplement_1.md``,
    ``..._supplement_2.md``, etc. Never overwrites.
    """
    d = when or date.today()
    base = paths.joblog_prompts_dir()
    base.mkdir(parents=True, exist_ok=True)
    primary = base / f"jobnet_joblog_{d.isoformat()}.md"
    if not primary.exists():
        return primary

    n = 1
    while True:
        candidate = base / f"jobnet_joblog_{d.isoformat()}_supplement_{n}.md"
        if not candidate.exists():
            return candidate
        n += 1
