"""Tests for the tailoring orchestration (render/tailoring.py)."""

from __future__ import annotations

from pathlib import Path

import pytest

from danapply.config import (
    ContactInfo,
    EducationEntry,
    ExperienceEntry,
    LanguageEntry,
    Portfolio,
    Profile,
    ReferenceEntry,
    UserSkills,
)
from danapply.models import Job
from danapply.render.tailoring import (
    SKILLS_ORDER_PRESETS,
    build_cover_letter_data,
    build_summary,
    detect_role_character,
    tailor_job,
)


@pytest.fixture
def example_profile(tmp_path: Path) -> Profile:
    """A minimal Profile sufficient for the renderer."""
    return Profile(
        name="TEST USER",
        tagline_default="Test Default Tagline",
        contact=ContactInfo(
            phone="+45 12 34 56 78",
            email="test@test.com",
            location="Aarhus, Denmark",
        ),
        portfolio=Portfolio(display="test.com", href="https://test.com/"),
        languages=[LanguageEntry(name="English", level="Fluent")],
        references=[ReferenceEntry(name="Reference One", email="ref1@x.com")],
        user_skills=UserSkills(
            tools=["Python", "SQL"],
            methods=["survey design"],
            domains=["retail"],
            soft_skills=["stakeholder engagement"],
        ),
        experience=[
            ExperienceEntry(
                role="Data Analyst",
                company="FixtureCorp",
                dates="2023–2024",
                location="Aarhus, Denmark",
                bullets=["Did analysis work for the fixture."],
            ),
        ],
        education=[
            EducationEntry(
                degree="MSc in Testing",
                school="Test University",
                dates="2018–2020",
                bullets=["Studied test methods."],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Role-character detection
# ---------------------------------------------------------------------------
def test_detect_research_character_from_title() -> None:
    job = Job(title="Market Research Analyst", description_raw="")
    assert detect_role_character(job) == "research"


def test_detect_strategy_character_from_description() -> None:
    job = Job(
        title="Associate",
        description_raw="Strategy consulting work. Due diligence on M&A. Advisory.",
    )
    assert detect_role_character(job) == "strategy"


def test_detect_content_character() -> None:
    job = Job(
        title="Content Marketing Lead",
        description_raw="Editorial, communications, storytelling, copywriting.",
    )
    assert detect_role_character(job) == "content"


def test_unknown_role_returns_default() -> None:
    job = Job(title="Software Developer", description_raw="Build a frontend app.")
    assert detect_role_character(job) == "default"


# ---------------------------------------------------------------------------
# Skills-order presets are complete and valid
# ---------------------------------------------------------------------------
def test_skills_order_presets_use_known_buckets() -> None:
    valid = {"research", "commercial", "stakeholder"}
    for key, order in SKILLS_ORDER_PRESETS.items():
        assert set(order) == valid
        assert len(order) == 3  # no dupes


# ---------------------------------------------------------------------------
# Summary + cover-letter content builders
# ---------------------------------------------------------------------------
def test_build_summary_en_contains_role_facet(example_profile: Profile) -> None:
    job = Job(title="Senior Researcher", description_raw="Research, analysis.")
    s = build_summary(job, example_profile, language="EN")
    assert "research" in s.lower()
    # Built strictly from profile facts — latest experience and tools appear
    assert "FixtureCorp" in s
    assert "Python" in s
    assert len(s) > 50


def test_build_summary_da_is_in_danish(example_profile: Profile) -> None:
    job = Job(title="Senior Researcher", description_raw="Research.")
    s = build_summary(job, example_profile, language="DA")
    assert "FixtureCorp" in s
    assert "fundament" in s.lower()  # Danish content marker


def test_build_summary_never_invents_career_facts(example_profile: Profile) -> None:
    """The templated fallback must only state what profile.yaml contains."""
    job = Job(title="Senior Researcher", description_raw="Research.")
    for lang in ("EN", "DA"):
        s = build_summary(job, example_profile, language=lang)
        assert "Copenhagen Business School" not in s
        assert "NordRetail" not in s


def test_build_cover_letter_data_returns_expected_shape(example_profile: Profile) -> None:
    job = Job(
        title="Strategy Consultant",
        company="Acme Inc",
        description_raw="Strategy consulting work.",
    )
    data = build_cover_letter_data(job, example_profile, language="EN")
    assert data["role_title"] == "Strategy Consultant"
    assert data["company_name"] == "Acme Inc"
    assert data["lang"] == "EN"
    assert len(data["key_strengths"]) == 4
    assert len(data["themes"]) == 3
    assert data["tagline"] == example_profile.tagline_default
    # Opening paragraph weaves the role + company
    assert "Acme Inc" in data["opening_paragraph"]
    assert "Strategy Consultant" in data["opening_paragraph"]


def test_build_cover_letter_data_danish(example_profile: Profile) -> None:
    job = Job(title="Analytiker", company="Dansk Firma", description_raw="Research.")
    data = build_cover_letter_data(job, example_profile, language="DA")
    assert data["lang"] == "DA"
    # First theme cites the latest experience from profile.yaml + the company
    assert "FixtureCorp" in data["themes"][0][1]
    assert "Dansk Firma" in data["themes"][0][1]


# ---------------------------------------------------------------------------
# End-to-end tailor_job
# ---------------------------------------------------------------------------
def test_tailor_job_produces_all_three_files(
    example_profile: Profile,
    tmp_path: Path,
) -> None:
    job = Job(
        title="Senior Business Analyst",
        company="TestCo",
        description_raw="Research-heavy analyst role.",
        score=72,
    )
    cv_dir = tmp_path / "cv"
    cl_dir = tmp_path / "cl"
    result = tailor_job(job, example_profile, cv_dir, cl_dir)

    assert result.cv_path.exists()
    assert result.cover_letter_path.exists()
    assert result.notes_path.exists()
    assert result.cv_path.stat().st_size > 2_000  # real PDF, not empty
    assert result.cover_letter_path.stat().st_size > 2_000
    assert result.notes_path.stat().st_size > 100


def test_tailor_job_rank_prefix_in_filename(
    example_profile: Profile,
    tmp_path: Path,
) -> None:
    job = Job(title="X", company="Y", description_raw="z")
    result = tailor_job(
        job, example_profile,
        output_dir_cv=tmp_path / "cv", output_dir_cl=tmp_path / "cl",
        rank=3,
    )
    assert result.cv_path.name.startswith("03_")
    assert result.cover_letter_path.name.startswith("03_")
    assert result.notes_path.name.startswith("03_")


def test_tailor_job_language_override_takes_precedence(
    example_profile: Profile,
    tmp_path: Path,
) -> None:
    job = Job(
        title="Analytiker",
        company="Firma",
        description_raw="Research.",
        language="DA",
    )
    result = tailor_job(
        job, example_profile,
        output_dir_cv=tmp_path / "cv", output_dir_cl=tmp_path / "cl",
        language="EN",
    )
    assert result.language == "EN"


def test_tailor_job_falls_back_to_en_for_unsupported_language(
    example_profile: Profile,
    tmp_path: Path,
) -> None:
    job = Job(
        title="X", company="Y", description_raw="z",
        language="HU",  # not EN/DA — templates only support those
    )
    result = tailor_job(
        job, example_profile,
        output_dir_cv=tmp_path / "cv", output_dir_cl=tmp_path / "cl",
    )
    assert result.language == "EN"


def test_tailor_job_writes_notes_with_score_breakdown(
    example_profile: Profile,
    tmp_path: Path,
) -> None:
    job = Job(
        title="Analyst",
        company="C",
        description_raw="x",
        score=72,
        score_breakdown={
            "total": 72,
            "role_fit": {"score": 35, "max": 45, "rationale": "Tier A title."},
            "skills_match": {"score": 18, "max": 25, "rationale": "Heuristic match."},
            "company_fit": {"score": 10, "max": 20, "rationale": "Some signals."},
            "freshness": {"score": 9, "max": 10, "rationale": "Posted 2 days ago."},
        },
    )
    result = tailor_job(
        job, example_profile,
        output_dir_cv=tmp_path / "cv", output_dir_cl=tmp_path / "cl",
    )
    notes_text = result.notes_path.read_text(encoding="utf-8")
    assert "72/100" in notes_text or "Score: 72" in notes_text
    assert "Role Fit" in notes_text
    assert "Tier A title" in notes_text


def test_tailor_job_notes_includes_tailoring_choices(
    example_profile: Profile,
    tmp_path: Path,
) -> None:
    job = Job(title="Senior Researcher", company="C", description_raw="research")
    result = tailor_job(
        job, example_profile,
        output_dir_cv=tmp_path / "cv", output_dir_cl=tmp_path / "cl",
    )
    notes_text = result.notes_path.read_text(encoding="utf-8")
    assert "research" in notes_text.lower()  # tagline key
    assert "Research" in notes_text  # skills order entry


# ---------------------------------------------------------------------------
# Claude content path through tailor_job()
# ---------------------------------------------------------------------------
def _valid_content() -> dict:
    return {
        "summary": "Claude-written summary that matches the user's voice.",
        "opening_paragraph": "Claude-written opening that respects the voice.",
        "key_strengths": ["Strength 1.", "Strength 2.", "Strength 3.", "Strength 4."],
        "themes": [
            {"heading": "T1", "paragraph": "T1 body."},
            {"heading": "T2", "paragraph": "T2 body."},
            {"heading": "T3", "paragraph": "T3 body."},
        ],
    }


def test_validate_tailor_content_accepts_valid_payload() -> None:
    from danapply.render.tailoring import validate_tailor_content

    validated = validate_tailor_content(_valid_content())
    assert validated["summary"].startswith("Claude-written")
    assert len(validated["key_strengths"]) == 4
    assert validated["themes"][0] == ("T1", "T1 body.")


def test_validate_tailor_content_accepts_pair_lists_for_themes() -> None:
    from danapply.render.tailoring import validate_tailor_content

    content = _valid_content()
    content["themes"] = [["H1", "P1"], ["H2", "P2"], ["H3", "P3"]]
    validated = validate_tailor_content(content)
    assert validated["themes"][2] == ("H3", "P3")


def test_validate_tailor_content_rejects_wrong_strength_count() -> None:
    from danapply.render.tailoring import validate_tailor_content

    content = _valid_content()
    content["key_strengths"] = content["key_strengths"][:3]
    with pytest.raises(ValueError, match="key_strengths"):
        validate_tailor_content(content)


def test_validate_tailor_content_rejects_missing_summary() -> None:
    from danapply.render.tailoring import validate_tailor_content

    content = _valid_content()
    del content["summary"]
    with pytest.raises(ValueError, match="summary"):
        validate_tailor_content(content)


def test_validate_tailor_content_rejects_malformed_theme() -> None:
    from danapply.render.tailoring import validate_tailor_content

    content = _valid_content()
    content["themes"][1] = {"heading": "only-heading"}
    with pytest.raises(ValueError, match="themes"):
        validate_tailor_content(content)


def test_tailor_job_uses_claude_content_when_provided(
    example_profile: Profile,
    tmp_path: Path,
) -> None:
    """Content supplied → generation_method == 'claude', register filter skipped."""
    job = Job(
        title="Market Research Analyst", company="ACME A/S",
        description_raw="Research role.", language="EN",
    )
    result = tailor_job(
        job, example_profile,
        output_dir_cv=tmp_path / "cv", output_dir_cl=tmp_path / "cl",
        content=_valid_content(),
    )
    assert result.generation_method == "claude"
    # Claude content already followed the register guide — filter must not run
    assert result.register_applied is False
    notes_text = result.notes_path.read_text(encoding="utf-8")
    assert "Claude Code" in notes_text
    assert result.cv_path.exists()
    assert result.cover_letter_path.exists()


def test_tailor_job_templated_without_content(
    example_profile: Profile,
    tmp_path: Path,
) -> None:
    job = Job(title="Senior Researcher", company="ACME", description_raw="Research.", language="EN")
    result = tailor_job(
        job, example_profile,
        output_dir_cv=tmp_path / "cv", output_dir_cl=tmp_path / "cl",
    )
    assert result.generation_method == "templated"
    assert result.register_applied is True


def test_tailor_job_raises_on_malformed_content(
    example_profile: Profile,
    tmp_path: Path,
) -> None:
    job = Job(title="X", company="Y", description_raw="z", language="EN")
    bad = _valid_content()
    bad["themes"] = []
    with pytest.raises(ValueError, match="themes"):
        tailor_job(
            job, example_profile,
            output_dir_cv=tmp_path / "cv", output_dir_cl=tmp_path / "cl",
            content=bad,
        )


# ---------------------------------------------------------------------------
# Per-job taglines (no baked-in library)
# ---------------------------------------------------------------------------
def test_templated_fallback_uses_profile_tagline(example_profile: Profile) -> None:
    job = Job(title="Analyst", company="Acme", description_raw="research")
    data = build_cover_letter_data(job, example_profile, language="EN")
    assert data["tagline"] == example_profile.tagline_default
    assert data["closing_tagline"] == ""


def test_claude_content_taglines_flow_into_outputs(
    example_profile: Profile, tmp_path: Path,
) -> None:
    job = Job(title="Analyst", company="Acme", description_raw="r", language="EN")
    content = _valid_content()
    content["tagline"] = "Custom Headline | For This Job Only"
    content["closing_tagline"] = "A Custom Closing Line."
    result = tailor_job(
        job, example_profile,
        output_dir_cv=tmp_path / "cv", output_dir_cl=tmp_path / "cl",
        content=content,
    )
    notes = result.notes_path.read_text(encoding="utf-8")
    assert "Custom Headline | For This Job Only" in notes
    assert "A Custom Closing Line." in notes


def test_claude_content_without_taglines_falls_back_to_profile(
    example_profile: Profile, tmp_path: Path,
) -> None:
    job = Job(title="Analyst", company="Acme", description_raw="r", language="EN")
    result = tailor_job(
        job, example_profile,
        output_dir_cv=tmp_path / "cv", output_dir_cl=tmp_path / "cl",
        content=_valid_content(),
    )
    notes = result.notes_path.read_text(encoding="utf-8")
    assert example_profile.tagline_default in notes


def test_validate_rejects_blank_tagline() -> None:
    from danapply.render.tailoring import validate_tailor_content

    content = _valid_content()
    content["tagline"] = "   "
    with pytest.raises(ValueError, match="tagline"):
        validate_tailor_content(content)
