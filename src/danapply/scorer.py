"""Job scoring — the 0–100 rubric.

Four components, ported from the canonical rubric in PROMPT.md:

  - Role Fit               45 pts  (title match against targets.yaml tiers)
  - Skills Match           25 pts  (keyword overlap with profile/cv_content)
  - Company Fit            20 pts  (scale-up + international + momentum signals)
  - Posting Freshness      10 pts  (age of posting, in days)

The output is a ``ScoreBreakdown`` with per-component scores and short
rationale strings. Honest about its limits: until v0.0.4 LLM extraction
lands, the Skills component uses substring matching against a static
keyword list, and Company Fit uses simple heuristics on the description.
Both components flag their confidence honestly via the rationale strings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from danapply.config import Profile, Targets
from danapply.models import Job

# ---------------------------------------------------------------------------
# Tier-matching for Role Fit
# ---------------------------------------------------------------------------
# Substrings that signal each tier when found in the job title (case-insensitive).
_TIER_C_SIGNALS = (
    "analyst", "consultant", "strategy", "research", "insights",
    "advisor", "associate", "coordinator", "researcher",
)

# Clear misses — titles that should not be scored as analyst roles even if
# they contain weak matches.
_CLEAR_MISS_SIGNALS = (
    "developer", "engineer", "nurse", "driver", "teacher", "accountant",
    "sales rep", "warehouse", "cleaner", "mechanic", "software engineer",
    "carpenter", "electrician", "plumber", "chef",
)


def _title_matches_tier(title: str, tier_titles: list[str]) -> bool:
    """Case-insensitive: does ``title`` contain any of the tier patterns?"""
    if not title:
        return False
    title_lower = title.lower()
    return any(t.lower() in title_lower for t in tier_titles)


# ---------------------------------------------------------------------------
# Skills heuristic keywords — used only when profile.user_skills is empty
# ---------------------------------------------------------------------------
_QUANT_TOOLS = (
    "python", "r", "sql", "power bi", "tableau", "excel",
    "powerpoint", "looker", "powerquery", "vba", "stata", "spss",
    "econometric", "statistics", "regression",
)
_RESEARCH_METHODS = (
    "market research", "industry analysis", "qualitative", "stakeholder interview",
    "a/b test", "causal", "due diligence", "competitive analysis",
    "user research", "survey",
)
_DOMAIN_KEYWORDS = (
    "digital transformation", "fintech", "telecom", "payments", "banking",
    "ai", "genai", "machine learning", "sustainability", "esg", "csrd",
    "consulting", "strategy",
)
_SOFT_SKILLS = (
    "stakeholder", "communication", "writing", "facilitation",
    "presentation", "collaboration", "cross-functional",
)


def _count_matches(text: str, needles: tuple[str, ...]) -> int:
    """Count needles present in the text, on word boundaries.

    Boundary-anchored so short tokens like "r" or "sql" don't match inside
    other words ("for", "mysql"); an optional plural "s"/"es" suffix is
    allowed ("regressions", "econometrics").
    """
    if not text:
        return 0
    haystack = text.lower()
    count = 0
    for n in needles:
        pattern = r"(?<![a-z0-9])" + re.escape(n) + r"(?:e?s)?(?![a-z0-9])"
        if re.search(pattern, haystack):
            count += 1
    return count


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------
@dataclass
class ScoreBreakdown:
    """Per-component scores + per-component rationale strings."""

    role_fit: int
    role_fit_max: int
    role_fit_rationale: str

    skills_match: int
    skills_match_max: int
    skills_match_rationale: str

    company_fit: int
    company_fit_max: int
    company_fit_rationale: str

    freshness: int
    freshness_max: int
    freshness_rationale: str

    @property
    def total(self) -> int:
        return self.role_fit + self.skills_match + self.company_fit + self.freshness

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "role_fit": {
                "score": self.role_fit, "max": self.role_fit_max,
                "rationale": self.role_fit_rationale,
            },
            "skills_match": {
                "score": self.skills_match, "max": self.skills_match_max,
                "rationale": self.skills_match_rationale,
            },
            "company_fit": {
                "score": self.company_fit, "max": self.company_fit_max,
                "rationale": self.company_fit_rationale,
            },
            "freshness": {
                "score": self.freshness, "max": self.freshness_max,
                "rationale": self.freshness_rationale,
            },
        }


# ---------------------------------------------------------------------------
# Component scorers
# ---------------------------------------------------------------------------
def _score_role_fit(job: Job, targets: Targets) -> tuple[int, str]:
    """0–45 pts based on title match against targets.yaml tiers."""
    title = job.title or ""
    title_lower = title.lower()

    if any(miss in title_lower for miss in _CLEAR_MISS_SIGNALS):
        return 0, f"Clear miss: title '{title}' suggests non-analyst role."

    if _title_matches_tier(title, targets.roles.tier_a_titles):
        # Description confirmation: does it talk about real analyst work?
        desc_lower = job.description_raw.lower() if job.description_raw else ""
        confirmed = any(kw in desc_lower for kw in (
            "research", "analysis", "insights", "data", "report",
        ))
        if confirmed:
            return 40, "Tier A title with description confirming analyst work."
        return 30, "Tier A title; description ambiguous on analyst depth."

    if _title_matches_tier(title, targets.roles.tier_b_titles):
        return 25, "Tier B title; adjacent to core analyst roles."

    if any(sig in title_lower for sig in _TIER_C_SIGNALS):
        return 18, "Tier C: title contains analyst-adjacent keyword but no exact tier match."

    if title:
        return 8, f"Loose fit: title '{title}' does not match any tier."
    return 0, "No title extracted."


def _score_skills_match(
    job: Job,
    targets: Targets,
    profile: Profile | None = None,
) -> tuple[int, str]:
    """0–25 pts.

    Routing:
      1. If ``profile.user_skills`` is non-empty → use the requirements-based
         skills matcher from ``extract/skills.py`` (cleaner signal).
      2. Otherwise → fall back to the description-text substring heuristic
         used in v0.0.3.

    The rationale string makes the chosen path explicit so the user knows
    where the score came from.
    """
    # Branch A: use the dedicated skills matcher when we have user_skills
    if profile is not None and not profile.user_skills.is_empty():
        from danapply.extract.skills import match_skills

        result = match_skills(job, profile)
        # Apply description-level deductions (5+ years, native Danish required)
        text = (job.description_raw or "") + " " + (job.title or "")
        deductions = 0
        deduction_notes: list[str] = []
        if "5+ years" in text.lower() or "minimum 5 years" in text.lower():
            deductions += 8
            deduction_notes.append("5+ yrs gate")
        if "native danish" in text.lower() or "fluent danish required" in text.lower():
            deductions += 8
            deduction_notes.append("native Danish gate")
        final = max(0, result.score - deductions)
        rationale = f"{result.method.title()} match: {result.rationale}"
        if deductions:
            rationale += f" −{deductions} ({', '.join(deduction_notes)}) = {final}/25."
        return final, rationale

    # Branch B: legacy description-text fallback (no user_skills configured)
    text = (job.description_raw or "") + " " + (job.title or "")
    quant = _count_matches(text, _QUANT_TOOLS)
    research = _count_matches(text, _RESEARCH_METHODS)
    domain = _count_matches(text, _DOMAIN_KEYWORDS)
    soft = _count_matches(text, _SOFT_SKILLS)

    quant_pts = min(5, quant)
    research_pts = min(5, research)
    domain_pts = min(5, domain)
    soft_pts = min(5, soft)
    english_pts = 5 if job.language == "EN" else 3

    deductions = 0
    deduction_notes: list[str] = []
    if "5+ years" in text.lower() or "minimum 5 years" in text.lower():
        deductions += 8
        deduction_notes.append("5+ yrs gate")
    if "native danish" in text.lower() or "fluent danish required" in text.lower():
        deductions += 8
        deduction_notes.append("native Danish gate")

    raw = quant_pts + research_pts + domain_pts + soft_pts + english_pts
    final = max(0, raw - deductions)

    rationale_parts = [f"quant {quant_pts}", f"research {research_pts}",
                       f"domain {domain_pts}", f"soft {soft_pts}",
                       f"lang {english_pts}"]
    if deductions:
        rationale_parts.append(f"−{deductions} ({', '.join(deduction_notes)})")
    rationale = "Description-only heuristic (no profile.user_skills configured): " + (
        " + ".join(rationale_parts) + f" = {final}/25."
    )
    return final, rationale


def _score_company_fit(job: Job, targets: Targets) -> tuple[int, str]:
    """0–20 pts. Simple v0.0.3 heuristic; richer signals come with CVR
    enrichment in a later version."""
    text_lower = (job.description_raw or "").lower()

    pts = 0
    signals: list[str] = []

    # International / English signal
    if job.language == "EN":
        pts += 5
        signals.append("EN posting (+5)")
    if any(kw in text_lower for kw in ("international", "global", "across countries", "multinational")):
        pts += 3
        signals.append("international markers (+3)")

    # Scale-up / growth signal
    if any(kw in text_lower for kw in ("scale-up", "scaleup", "startup", "growth journey", "series a", "series b", "series c")):
        pts += 4
        signals.append("scale-up signals (+4)")

    # Momentum
    if any(kw in text_lower for kw in ("expanding", "growing", "new product", "launched", "transformation programme")):
        pts += 3
        signals.append("momentum signals (+3)")

    # Red flags
    if any(kw in text_lower for kw in ("layoff", "restructur", "financial distress")):
        pts -= 5
        signals.append("red flags (−5)")

    pts = max(0, min(20, pts))
    rationale = "Heuristic: " + (
        ", ".join(signals) if signals else "no notable signals"
    ) + f" → {pts}/20."
    return pts, rationale


def _score_freshness(job: Job, today: date | None = None) -> tuple[int, str]:
    """0–10 pts based on posting age."""
    today = today or date.today()
    if not job.posting_date:
        return 4, "No posting date — neutral 4/10."

    age_days = (today - job.posting_date).days
    if age_days < 0:
        # Posting opens in the future
        return 10, f"Posting opens {abs(age_days)} day(s) in the future — 10/10."
    if age_days <= 3:
        return 10, f"Posted {age_days} day(s) ago — fresh (10/10)."
    if age_days <= 7:
        return 7, f"Posted {age_days} day(s) ago — recent (7/10)."
    if age_days <= 14:
        return 4, f"Posted {age_days} day(s) ago — aging (4/10)."
    if age_days <= 30:
        return 2, f"Posted {age_days} day(s) ago — stale (2/10)."
    return 0, f"Posted {age_days} day(s) ago — very stale (0/10)."


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def score_job(
    job: Job,
    targets: Targets,
    profile: Profile | None = None,
    today: date | None = None,
) -> ScoreBreakdown:
    """Score a Job and return the full breakdown.

    Does NOT mutate the Job — the caller decides whether to persist.

    When ``profile`` is provided and has a populated ``user_skills``,
    the skills component uses the requirements-aware matcher (better
    signal). Otherwise the legacy description-text heuristic is used.
    """
    rf, rf_note = _score_role_fit(job, targets)
    sm, sm_note = _score_skills_match(job, targets, profile=profile)
    cf, cf_note = _score_company_fit(job, targets)
    fr, fr_note = _score_freshness(job, today=today)

    return ScoreBreakdown(
        role_fit=rf, role_fit_max=45, role_fit_rationale=rf_note,
        skills_match=sm, skills_match_max=25, skills_match_rationale=sm_note,
        company_fit=cf, company_fit_max=20, company_fit_rationale=cf_note,
        freshness=fr, freshness_max=10, freshness_rationale=fr_note,
    )


def apply_score(job: Job, breakdown: ScoreBreakdown) -> Job:
    """Set the score fields on a Job (returns the same instance for chaining)."""
    job.score = breakdown.total
    job.score_breakdown = breakdown.to_dict()
    job.scored_at = datetime.now()
    return job
