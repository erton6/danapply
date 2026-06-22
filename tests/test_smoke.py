"""Smoke tests — confirm the package imports and the renderer produces a PDF.

Heavier tests (parser fixtures, scorer rubric, memory layer) come with the
features that need them in later versions.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from danapply import __version__, paths


def test_version_is_set() -> None:
    assert __version__ == "0.5.4"


def test_default_data_dir_under_home() -> None:
    # Default is ~/danapply-data when no env override
    os.environ.pop("DANAPPLY_DATA_DIR", None)
    assert paths.data_dir() == Path.home() / "danapply-data"


def test_env_override_data_dir(tmp_path: Path) -> None:
    os.environ["DANAPPLY_DATA_DIR"] = str(tmp_path)
    try:
        assert paths.data_dir() == tmp_path.resolve()
    finally:
        os.environ.pop("DANAPPLY_DATA_DIR", None)


def test_init_creates_expected_files(tmp_path: Path) -> None:
    """`danapply init` should create the directory + example files."""
    from danapply.scaffolding.init_data_dir import init_data_dir

    os.environ["DANAPPLY_DATA_DIR"] = str(tmp_path)
    try:
        report = init_data_dir(force=False)
        assert any(s == "created" for s in report.values())
        assert (tmp_path / "profile" / "profile.yaml").exists()
        assert (tmp_path / "profile" / "targets.yaml").exists()
        # Blank init deliberately ships NO photo — the CV session asks for one
        assert not (tmp_path / "profile" / "photo.jpeg").exists()
        assert (tmp_path / "raw_searches").is_dir()
        assert (tmp_path / "research_notes").is_dir()
    finally:
        os.environ.pop("DANAPPLY_DATA_DIR", None)


def test_renderer_produces_cv_pdf(tmp_path: Path) -> None:
    """End-to-end smoke: init -> load profile -> render CV -> PDF exists and is non-empty."""
    from danapply.config import load_profile
    from danapply.render.templates import canonical
    from danapply.scaffolding.init_data_dir import init_data_dir

    os.environ["DANAPPLY_DATA_DIR"] = str(tmp_path)
    try:
        init_data_dir(force=False)
        profile = load_profile(tmp_path / "profile" / "profile.yaml")

        cv_path = tmp_path / "test_cv.pdf"
        canonical.build_cv_pdf(
            {
                "tagline": "Test Tagline | Smoke Test",
                "summary": "Test summary paragraph for the smoke test.",
                "skills_order": ["research", "commercial", "stakeholder"],
            },
            cv_path,
            profile,
        )
        assert cv_path.exists()
        # Blank profile renders photo-less and content-light — small but real
        assert cv_path.stat().st_size > 1_500
    finally:
        os.environ.pop("DANAPPLY_DATA_DIR", None)


def test_renderer_produces_cover_letter_pdf(tmp_path: Path) -> None:
    """End-to-end smoke for the cover letter builder."""
    from danapply.config import load_profile
    from danapply.render.templates import canonical
    from danapply.scaffolding.init_data_dir import init_data_dir

    os.environ["DANAPPLY_DATA_DIR"] = str(tmp_path)
    try:
        init_data_dir(force=False)
        profile = load_profile(tmp_path / "profile" / "profile.yaml")

        cl_path = tmp_path / "test_cover.pdf"
        canonical.build_cover_letter_pdf(
            {
                "tagline": "Test Tagline | Smoke Test",
                "closing_tagline": "Test Closing Line.",
                "role_title": "Test Role",
                "company_name": "Test Company",
                "opening_paragraph": "Test opening paragraph.",
                "key_strengths": ["a", "b", "c", "d"],
                "themes": [("h1", "p1"), ("h2", "p2"), ("h3", "p3")],
                "lang": "EN",
            },
            cl_path,
            profile,
        )
        assert cl_path.exists()
        assert cl_path.stat().st_size > 1_500
    finally:
        os.environ.pop("DANAPPLY_DATA_DIR", None)


def test_cover_letter_fits_one_page(tmp_path: Path) -> None:
    """The cover letter must always be a single page, even with long content."""
    from danapply.config import load_profile
    from danapply.render.templates import canonical
    from danapply.scaffolding.init_data_dir import init_data_dir

    os.environ["DANAPPLY_DATA_DIR"] = str(tmp_path)
    try:
        init_data_dir(force=False, example=True)
        profile = load_profile(tmp_path / "profile" / "profile.yaml")

        cl_path = tmp_path / "long_cover.pdf"
        canonical.build_cover_letter_pdf(
            {
                "tagline": "Analyst & Communicator | Clear Decisions",
                "closing_tagline": "Evidence into Decisions.",
                "role_title": "Commercial Analyst",
                "company_name": "Acme A/S",
                "opening_paragraph": "A very long opening paragraph. " * 20,
                "key_strengths": [
                    "A long strength bullet with metrics and detail. " * 3
                ] * 4,
                "themes": [
                    (f"A longer heading number {i}",
                     "A long theme paragraph with lots of detail. " * 16)
                    for i in range(1, 4)
                ],
                "lang": "EN",
            },
            cl_path,
            profile,
        )
        data = cl_path.read_bytes()
        page_count = data.count(b"/Type /Page") - data.count(b"/Type /Pages")
        assert page_count == 1, f"cover letter ran to {page_count} pages"
    finally:
        os.environ.pop("DANAPPLY_DATA_DIR", None)


def test_load_profile_fails_helpfully_when_missing(tmp_path: Path) -> None:
    from danapply.config import ConfigLoadError, load_profile

    missing = tmp_path / "no_such_profile.yaml"
    with pytest.raises(ConfigLoadError) as exc:
        load_profile(missing)
    assert "Profile not found" in str(exc.value)
    assert "danapply init" in str(exc.value)


def test_cv_renders_non_latin1_characters(tmp_path: Path) -> None:
    """Regression: Helvetica dropped Polish glyphs (Wrocław → Wroc aw).
    The renderer must switch to a Unicode font when content needs it."""
    from pypdf import PdfReader

    from danapply.config import ContactInfo, ExperienceEntry, Profile
    from danapply.render.templates import canonical

    profile = Profile(
        name="AGNIESZKA TEST",
        tagline_default="Analityk — Wrocław & Łódź",
        contact=ContactInfo(phone="+48 1", email="a@x.pl", location="Wrocław, Poland"),
        experience=[ExperienceEntry(role="Analityk", company="Społem", dates="2024",
                                    location="Łódź", bullets=["Analiza ąćęłńóśźż."])],
    )
    out = tmp_path / "unicode_cv.pdf"
    canonical.build_cv_pdf(
        {"tagline": profile.tagline_default, "summary": "Wrocław summary."},
        out, profile,
    )
    text = PdfReader(str(out)).pages[0].extract_text()
    assert "Wrocław" in text
    assert "Łódź" in text
