"""Skills matching — Job.requirements vs the user's curated user_skills.

Heuristic substring + lemma-style matching of requirement strings against
the user's keyword library. Deterministic, no network. Returns a
``SkillsMatchResult`` with a 0–25 score, a per-requirement match status
(``matched`` / ``partial`` / ``missing``), and a rationale string
suitable for the scorer's breakdown.

Semantic matching (e.g. "is 'ML experience' covered by 'machine
learning'?") is Claude Code's job in-conversation — it reads the
rationale in the score breakdown and refines the requirements list via
``danapply ingest`` when the heuristic gets it wrong.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from danapply.config import Profile
from danapply.models import Job

MatchStatus = Literal["matched", "partial", "missing"]


@dataclass
class RequirementMatch:
    """How well one job requirement maps to the user's skills."""

    requirement: str
    status: MatchStatus
    matched_against: list[str] = field(default_factory=list)
    """The user-skill keywords that produced the match (if any)."""


@dataclass
class SkillsMatchResult:
    """Aggregate result from matching a job's requirements to user skills."""

    score: int  # 0–25
    score_max: int = 25
    matches: list[RequirementMatch] = field(default_factory=list)
    rationale: str = ""
    method: Literal["heuristic", "llm"] = "heuristic"


# ---------------------------------------------------------------------------
# Heuristic matcher (no API key)
# ---------------------------------------------------------------------------
def _normalise(text: str) -> str:
    """Lowercase + strip non-alphanumeric → for fuzzy contains-check."""
    return "".join(c.lower() if c.isalnum() or c == " " else " " for c in text).strip()


def _requirement_matches(requirement: str, keyword: str) -> bool:
    """Cheap fuzzy match — does the user's keyword appear in the requirement,
    or does any substantial part of the requirement appear in the keyword?
    Both directions help: 'Python expert' matches keyword 'Python', and
    keyword 'machine learning' matches requirement 'ML experience preferred'.
    """
    req_norm = _normalise(requirement)
    kw_norm = _normalise(keyword)
    if not kw_norm or not req_norm:
        return False
    if kw_norm in req_norm:
        return True
    # Multi-word keyword: match if any of its words >= 4 chars appears
    for word in kw_norm.split():
        if len(word) >= 4 and word in req_norm:
            return True
    return False


def match_skills_heuristic(
    job: Job, profile: Profile, *, fallback_to_description: bool = True
) -> SkillsMatchResult:
    """Match job requirements against the user's curated keywords.

    If ``job.requirements`` is empty and ``fallback_to_description=True``,
    falls back to scanning ``job.description_raw`` for keyword presence
    (degraded mode — flagged in the rationale).
    """
    user_keywords = profile.user_skills.all_keywords()

    if not user_keywords:
        return SkillsMatchResult(
            score=0,
            rationale=(
                "user_skills in profile.yaml is empty — skills match cannot be "
                "computed. Add tools/methods/domains/soft_skills to enable "
                "scoring."
            ),
            method="heuristic",
        )

    # Branch 1: requirements present — match each one against user keywords
    if job.requirements:
        matches: list[RequirementMatch] = []
        for req in job.requirements:
            hits = [kw for kw in user_keywords if _requirement_matches(req, kw)]
            if hits:
                status: MatchStatus = "matched"
            elif any(_requirement_matches(req, kw) for kw in user_keywords):
                status = "partial"
            else:
                status = "missing"
            matches.append(RequirementMatch(req, status, hits))

        matched = sum(1 for m in matches if m.status == "matched")
        partial = sum(1 for m in matches if m.status == "partial")
        missing = sum(1 for m in matches if m.status == "missing")

        # Score: ratio of matched + half-credit for partial, scaled to 25.
        total = len(matches)
        credit = matched + 0.5 * partial
        ratio = credit / total if total else 0.0
        score = max(0, min(25, round(25 * ratio)))

        rationale = (
            f"Per-requirement match: {matched}/{total} matched, "
            f"{partial} partial, {missing} missing → {score}/25."
        )
        return SkillsMatchResult(
            score=score, matches=matches, rationale=rationale, method="heuristic"
        )

    # Branch 2: no requirements list — fall back to description text scanning
    if not fallback_to_description:
        return SkillsMatchResult(
            score=0,
            rationale=(
                "No job.requirements extracted; ask Claude to extract them "
                "from the posting and refresh via `danapply ingest`."
            ),
            method="heuristic",
        )

    text = (job.description_raw or "") + " " + (job.title or "")
    matched_kws = [kw for kw in user_keywords if _requirement_matches(text, kw)]
    # Rough scaling: more matches → higher score, capped at 25
    score = min(25, len(matched_kws) * 2)
    rationale = (
        f"Description scan (no extracted requirements): "
        f"matched {len(matched_kws)}/{len(user_keywords)} user keywords → {score}/25. "
        f"Ask Claude to extract structured requirements from the posting "
        f"(`danapply ingest`) for sharper matching."
    )
    return SkillsMatchResult(
        score=score,
        matches=[RequirementMatch(kw, "matched", [kw]) for kw in matched_kws],
        rationale=rationale,
        method="heuristic",
    )


# ---------------------------------------------------------------------------
# Public router
# ---------------------------------------------------------------------------
def match_skills(job: Job, profile: Profile) -> SkillsMatchResult:
    """Match a job's requirements against the user's skills (heuristic).

    Semantic judgment calls (e.g. "is R close enough to Python?") belong
    to Claude Code in-conversation — when match quality matters, Claude
    reviews the rationale strings in the score breakdown and can refine
    the job's requirements list via `danapply ingest`.
    """
    return match_skills_heuristic(job, profile)
