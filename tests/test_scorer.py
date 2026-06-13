"""Tests for the scoring rubric."""

from __future__ import annotations

from datetime import date, timedelta

from danapply.config import GeographyFilter, TargetConstraints, TargetRoles, Targets
from danapply.models import Job
from danapply.scorer import apply_score, score_job


def _default_targets() -> Targets:
    return Targets(
        roles=TargetRoles(
            tier_a_titles=["Business Analyst", "Insights Analyst", "Market Intelligence Analyst"],
            tier_b_titles=["Associate Consultant", "Product Analyst"],
        ),
        geography=GeographyFilter(primary=["Aarhus", "Copenhagen"], remote_ok=True),
        constraints=TargetConstraints(),
    )


# ---------------------------------------------------------------------------
# Role Fit
# ---------------------------------------------------------------------------
def test_tier_a_title_with_analyst_description() -> None:
    job = Job(
        title="Business Analyst",
        company="TestCorp",
        description_raw="We need someone to do market research and produce reports and analysis.",
    )
    breakdown = score_job(job, _default_targets())
    assert breakdown.role_fit >= 35


def test_tier_a_title_with_weak_description() -> None:
    job = Job(
        title="Business Analyst",
        company="TestCorp",
        description_raw="Sales role with quota targets.",
    )
    breakdown = score_job(job, _default_targets())
    # Tier A title without analyst-like description verbs → 30 pts
    assert 25 <= breakdown.role_fit <= 32


def test_tier_b_title() -> None:
    job = Job(
        title="Associate Consultant",
        company="TestCorp",
        description_raw="Consulting work for clients.",
    )
    breakdown = score_job(job, _default_targets())
    assert 20 <= breakdown.role_fit <= 30


def test_clear_miss_returns_zero() -> None:
    job = Job(
        title="Software Engineer",
        company="TestCorp",
        description_raw="We need a senior engineer.",
    )
    breakdown = score_job(job, _default_targets())
    assert breakdown.role_fit == 0


def test_tier_c_loose_match() -> None:
    job = Job(
        title="Research Coordinator",
        company="TestCorp",
        description_raw="Various coordination duties.",
    )
    breakdown = score_job(job, _default_targets())
    assert 15 <= breakdown.role_fit <= 25


# ---------------------------------------------------------------------------
# Skills Match
# ---------------------------------------------------------------------------
def test_skills_match_with_strong_signals() -> None:
    job = Job(
        title="Business Analyst",
        description_raw=(
            "We need Python, SQL, Power BI, Excel, Tableau, and statistics skills. "
            "Experience with market research, qualitative research, "
            "stakeholder interview, competitive analysis, and a/b test. "
            "Domains: digital transformation, fintech, banking, payments, sustainability. "
            "Strong stakeholder, communication, writing, and facilitation skills required."
        ),
    )
    breakdown = score_job(job, _default_targets())
    # Should hit all 5 buckets at the cap
    assert breakdown.skills_match >= 22


def test_skills_match_5plus_years_deduction() -> None:
    job = Job(
        title="Business Analyst",
        description_raw="Python and SQL required. Minimum 5 years experience.",
    )
    breakdown = score_job(job, _default_targets())
    assert "−8" in breakdown.skills_match_rationale or "5+ yrs" in breakdown.skills_match_rationale


def test_skills_match_native_danish_deduction() -> None:
    job = Job(
        title="Business Analyst",
        description_raw="Native Danish required. Some Python and SQL skills.",
    )
    breakdown = score_job(job, _default_targets())
    assert "native Danish" in breakdown.skills_match_rationale


# ---------------------------------------------------------------------------
# Freshness
# ---------------------------------------------------------------------------
def test_freshness_fresh_posting() -> None:
    today = date.today()
    job = Job(title="X", company="Y", posting_date=today - timedelta(days=2))
    breakdown = score_job(job, _default_targets(), today=today)
    assert breakdown.freshness == 10


def test_freshness_recent_posting() -> None:
    today = date.today()
    job = Job(title="X", company="Y", posting_date=today - timedelta(days=6))
    breakdown = score_job(job, _default_targets(), today=today)
    assert breakdown.freshness == 7


def test_freshness_aging_posting() -> None:
    today = date.today()
    job = Job(title="X", company="Y", posting_date=today - timedelta(days=12))
    breakdown = score_job(job, _default_targets(), today=today)
    assert breakdown.freshness == 4


def test_freshness_stale_posting() -> None:
    today = date.today()
    job = Job(title="X", company="Y", posting_date=today - timedelta(days=25))
    breakdown = score_job(job, _default_targets(), today=today)
    assert breakdown.freshness == 2


def test_freshness_no_date_neutral() -> None:
    job = Job(title="X", company="Y")
    breakdown = score_job(job, _default_targets())
    assert breakdown.freshness == 4


def test_freshness_future_posting() -> None:
    today = date.today()
    job = Job(title="X", company="Y", posting_date=today + timedelta(days=5))
    breakdown = score_job(job, _default_targets(), today=today)
    assert breakdown.freshness == 10


# ---------------------------------------------------------------------------
# Company Fit
# ---------------------------------------------------------------------------
def test_company_fit_scale_up_signals() -> None:
    job = Job(
        title="Analyst",
        description_raw="Join our fast-growing scale-up on our exciting growth journey.",
        language="EN",
    )
    breakdown = score_job(job, _default_targets())
    assert breakdown.company_fit >= 5


def test_company_fit_red_flags_deducted() -> None:
    job = Job(
        title="Analyst",
        description_raw="We are restructuring after recent layoffs.",
        language="EN",
    )
    breakdown = score_job(job, _default_targets())
    # Even with EN +5, the −5 red flag should reduce the score
    assert breakdown.company_fit <= 5


# ---------------------------------------------------------------------------
# End-to-end + apply_score
# ---------------------------------------------------------------------------
def test_total_equals_sum_of_components() -> None:
    job = Job(
        title="Business Analyst",
        description_raw="Python, SQL, market research, stakeholder engagement.",
        posting_date=date.today(),
    )
    breakdown = score_job(job, _default_targets())
    assert breakdown.total == (
        breakdown.role_fit + breakdown.skills_match
        + breakdown.company_fit + breakdown.freshness
    )


def test_apply_score_mutates_job() -> None:
    job = Job(title="Insights Analyst", description_raw="Research and Python.")
    breakdown = score_job(job, _default_targets())
    apply_score(job, breakdown)
    assert job.score == breakdown.total
    assert job.score_breakdown is not None
    assert job.scored_at is not None


def test_total_score_bounded_0_to_100() -> None:
    targets = _default_targets()
    for desc in (
        "",
        "Random text",
        "Python SQL Power BI Excel market research stakeholder digital transformation banking",
        "Some 5+ years required; native Danish required.",
    ):
        job = Job(title="Business Analyst", company="X", description_raw=desc)
        breakdown = score_job(job, targets)
        assert 0 <= breakdown.total <= 100
