"""Tests for the interview-prep brief — templated fallback + Claude content path."""

from __future__ import annotations

import pytest

from danapply.config import ContactInfo, Profile, UserSkills
from danapply.interview import (
    brief_from_content,
    build_interview_brief,
    render_brief_markdown,
)
from danapply.models import Job


def _make_profile() -> Profile:
    return Profile(
        name="Test User",
        tagline_default="Tagline",
        contact=ContactInfo(phone="+1", email="t@t.t", location="Aarhus"),
        user_skills=UserSkills(
            tools=["Python", "SQL"], methods=["market research"], domains=["fintech"],
        ),
    )


def _make_job(**kwargs) -> Job:
    j = Job(title=kwargs.get("title", "Business Analyst"),
            company=kwargs.get("company", "Acme"),
            score=kwargs.get("score", 70),
            description_raw=kwargs.get("description_raw", "Some description text."))
    j.ensure_job_id()
    return j


# ---------------------------------------------------------------------------
# Templated fallback (no --content)
# ---------------------------------------------------------------------------
def test_build_brief_is_templated() -> None:
    brief = build_interview_brief(_make_job(), _make_profile())
    assert brief.generation_method == "templated"
    assert len(brief.behavioural_questions) >= 3
    assert len(brief.technical_questions) >= 1
    assert "Templated brief" in brief.notes


def test_templated_short_brief_is_smaller() -> None:
    full = build_interview_brief(_make_job(), _make_profile(), short=False)
    short = build_interview_brief(_make_job(), _make_profile(), short=True)
    assert len(short.behavioural_questions) <= len(full.behavioural_questions)
    assert len(short.technical_questions) <= len(full.technical_questions)


def test_templated_brief_mentions_company() -> None:
    job = _make_job(company="MegaCorp")
    brief = build_interview_brief(job, _make_profile())
    combined = " ".join(brief.behavioural_questions + brief.questions_to_ask)
    assert "MegaCorp" in combined


def test_templated_brief_warns_about_deadline_when_present() -> None:
    from datetime import date
    job = _make_job()
    job.deadline = date(2026, 6, 30)
    brief = build_interview_brief(job, _make_profile())
    combined = " ".join(brief.watch_outs)
    assert "2026-06-30" in combined


# ---------------------------------------------------------------------------
# Claude content path
# ---------------------------------------------------------------------------
def _valid_content() -> dict:
    return {
        "behavioural_questions": ["q1", "q2", "q3"],
        "technical_questions": ["t1", "t2"],
        "watch_outs": ["w1"],
        "questions_to_ask": ["a1", "a2"],
        "notes": "Specific to Acme's analytics team.",
    }


def test_brief_from_content_builds_claude_brief() -> None:
    brief = brief_from_content(_make_job(), _valid_content())
    assert brief.generation_method == "claude"
    assert brief.behavioural_questions == ["q1", "q2", "q3"]
    assert brief.notes == "Specific to Acme's analytics team."


def test_brief_from_content_rejects_non_dict() -> None:
    with pytest.raises(ValueError, match="JSON object"):
        brief_from_content(_make_job(), ["nope"])  # type: ignore[arg-type]


def test_brief_from_content_rejects_missing_section() -> None:
    bad = _valid_content()
    del bad["watch_outs"]
    with pytest.raises(ValueError, match="watch_outs"):
        brief_from_content(_make_job(), bad)


def test_brief_from_content_rejects_empty_list() -> None:
    bad = _valid_content()
    bad["technical_questions"] = []
    with pytest.raises(ValueError, match="technical_questions"):
        brief_from_content(_make_job(), bad)


def test_brief_from_content_strips_blank_entries() -> None:
    content = _valid_content()
    content["questions_to_ask"] = ["  a1  ", "", "a2"]
    brief = brief_from_content(_make_job(), content)
    assert brief.questions_to_ask == ["a1", "a2"]


def test_brief_from_content_notes_optional() -> None:
    content = _valid_content()
    del content["notes"]
    brief = brief_from_content(_make_job(), content)
    assert brief.notes == ""


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------
def test_render_markdown_contains_all_sections() -> None:
    brief = build_interview_brief(_make_job(company="Acme"), _make_profile())
    md = render_brief_markdown(brief)
    assert "# Interview prep" in md
    assert "Acme" in md
    assert "## Snapshot" in md
    assert "## Likely behavioural questions" in md
    assert "## Likely technical / case questions" in md
    assert "## Watch out for" in md
    assert "## Questions to ask them" in md


def test_render_markdown_shows_generation_method() -> None:
    brief = build_interview_brief(_make_job(), _make_profile())
    md = render_brief_markdown(brief)
    assert "**Generation method:** templated" in md


def test_render_markdown_claude_brief_shows_method() -> None:
    brief = brief_from_content(_make_job(), _valid_content())
    md = render_brief_markdown(brief)
    assert "**Generation method:** claude" in md


def test_render_markdown_includes_round_number() -> None:
    brief = build_interview_brief(_make_job(), _make_profile(), round_number=2)
    md = render_brief_markdown(brief, round_number=2)
    assert "**Round:** 2" in md
