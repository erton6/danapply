"""Tests for the skills matcher (extract/skills.py)."""

from __future__ import annotations

from danapply.config import (
    ContactInfo,
    Profile,
    UserSkills,
)
from danapply.extract.skills import (
    _requirement_matches,
    match_skills,
    match_skills_heuristic,
)
from danapply.models import Job


def _make_profile(**skills_kwargs) -> Profile:
    return Profile(
        name="Test User",
        tagline_default="Default Tagline",
        contact=ContactInfo(phone="+1", email="t@t.t", location="X"),
        user_skills=UserSkills(**skills_kwargs),
    )


# ---------------------------------------------------------------------------
# _requirement_matches — fuzzy keyword matcher
# ---------------------------------------------------------------------------
def test_keyword_substring_match() -> None:
    assert _requirement_matches("Python expert needed", "Python")


def test_multi_word_keyword_matches_via_significant_word() -> None:
    assert _requirement_matches("ML experience preferred", "machine learning") is False
    # Now requirement has the keyword's significant word
    assert _requirement_matches("Experience with learning algorithms", "machine learning")


def test_case_insensitive_match() -> None:
    assert _requirement_matches("python", "PYTHON")
    assert _requirement_matches("PYTHON", "python")


def test_no_match() -> None:
    assert _requirement_matches("Java background required", "Python") is False


def test_empty_inputs_dont_match() -> None:
    assert _requirement_matches("", "Python") is False
    assert _requirement_matches("anything", "") is False


# ---------------------------------------------------------------------------
# Heuristic matcher — empty user_skills
# ---------------------------------------------------------------------------
def test_empty_user_skills_returns_zero_with_message() -> None:
    profile = _make_profile()  # empty skills
    job = Job(title="X", company="Y", requirements=["Python", "SQL"])
    result = match_skills_heuristic(job, profile)
    assert result.score == 0
    assert "user_skills" in result.rationale
    assert "empty" in result.rationale


# ---------------------------------------------------------------------------
# Heuristic matcher — requirements present
# ---------------------------------------------------------------------------
def test_all_requirements_matched_gives_full_score() -> None:
    profile = _make_profile(tools=["Python", "SQL", "Excel"])
    job = Job(
        title="X", company="Y",
        requirements=["Python expert", "SQL queries", "Excel modelling"],
    )
    result = match_skills_heuristic(job, profile)
    assert result.score == 25
    assert all(m.status == "matched" for m in result.matches)


def test_half_requirements_matched_gives_half_score() -> None:
    profile = _make_profile(tools=["Python", "SQL"])
    job = Job(
        title="X", company="Y",
        requirements=["Python", "SQL", "Java", "C++"],
    )
    result = match_skills_heuristic(job, profile)
    # 2 matched + 0 partial out of 4 → 50% → 13/25 (rounded from 12.5)
    assert 12 <= result.score <= 13
    matched = [m for m in result.matches if m.status == "matched"]
    missing = [m for m in result.matches if m.status == "missing"]
    assert len(matched) == 2
    assert len(missing) == 2


def test_zero_matches_gives_zero_score() -> None:
    profile = _make_profile(tools=["Python", "SQL"])
    job = Job(title="X", company="Y", requirements=["COBOL", "Fortran", "Lisp"])
    result = match_skills_heuristic(job, profile)
    assert result.score == 0
    assert all(m.status == "missing" for m in result.matches)


def test_matched_against_records_user_keywords() -> None:
    profile = _make_profile(tools=["Python", "SQL"], methods=["regression"])
    job = Job(title="X", company="Y", requirements=["Python and regression"])
    result = match_skills_heuristic(job, profile)
    assert len(result.matches) == 1
    matched = result.matches[0]
    assert matched.status == "matched"
    assert "Python" in matched.matched_against
    assert "regression" in matched.matched_against


# ---------------------------------------------------------------------------
# Heuristic matcher — fallback to description text
# ---------------------------------------------------------------------------
def test_no_requirements_falls_back_to_description() -> None:
    profile = _make_profile(tools=["Python", "SQL"], methods=["market research"])
    job = Job(
        title="Analyst",
        description_raw="We need someone with Python skills for market research.",
    )
    result = match_skills_heuristic(job, profile)
    assert result.score > 0
    assert "Description scan" in result.rationale
    assert "ingest" in result.rationale  # nudges toward Claude-extracted requirements


def test_fallback_can_be_disabled() -> None:
    profile = _make_profile(tools=["Python"])
    job = Job(title="X", description_raw="Python required.")
    result = match_skills_heuristic(job, profile, fallback_to_description=False)
    assert result.score == 0


# ---------------------------------------------------------------------------
# match_skills router
# ---------------------------------------------------------------------------
def test_router_uses_heuristic() -> None:
    profile = _make_profile(tools=["Python"])
    job = Job(title="X", requirements=["Python"])
    result = match_skills(job, profile)
    assert result.method == "heuristic"
