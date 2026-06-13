"""Tests for `render-base`, `render-letter`, and the visual style system.

These cover the v0.3.1 fixes: the base CV renders the user's REAL summary
from cv_content.md (not placeholder text), standalone cover letters always
ship as PDFs, and the style presets / accent colour propagate.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from danapply.cli import _extract_cv_summary, app
from danapply.config import CV_STYLES, Profile
from danapply.render.tailoring import validate_letter_content
from danapply.render.templates.canonical import STYLE_PRESETS

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolated_data_dir(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DANAPPLY_DATA_DIR", str(tmp_path / "data"))
    yield tmp_path / "data"


def _letter_payload(**overrides) -> dict:
    payload = {
        "role_title": "Data Analyst",
        "company_name": "Test ApS",
        "opening_paragraph": "Why I am applying to Test ApS.",
        "key_strengths": ["One.", "Two.", "Three.", "Four."],
        "themes": [
            {"heading": "A", "paragraph": "First theme."},
            {"heading": "B", "paragraph": "Second theme."},
            {"heading": "C", "paragraph": "Third theme."},
        ],
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# Summary extraction from cv_content.md
# ---------------------------------------------------------------------------
def test_extract_summary_pulls_section_text() -> None:
    text = (
        "# CV\n\n## Summary\n\nAnalyst with five years of experience.\n"
        "Works with SQL.\n\n## Skills\n\nstuff"
    )
    assert _extract_cv_summary(text) == (
        "Analyst with five years of experience. Works with SQL."
    )


def test_extract_summary_strips_placeholder_comments() -> None:
    text = "## Summary\n\n<!-- 3-5 sentences: who you are. -->\n\n## Skills\n"
    assert _extract_cv_summary(text) == ""


def test_extract_summary_missing_section() -> None:
    assert _extract_cv_summary("# CV\n\n## Skills\n\nthings") == ""


# ---------------------------------------------------------------------------
# render-base
# ---------------------------------------------------------------------------
def test_render_base_uses_real_summary(_isolated_data_dir: Path) -> None:
    runner.invoke(app, ["init", "--example"])
    result = runner.invoke(app, ["render-base"])
    assert result.exit_code == 0, result.output
    cv = _isolated_data_dir / "resume_drafts" / "base_cv.pdf"
    assert cv.exists() and cv.stat().st_size > 1000


def test_render_base_fails_without_summary(_isolated_data_dir: Path) -> None:
    runner.invoke(app, ["init"])  # blank scaffold: summary is only a comment
    result = runner.invoke(app, ["render-base"])
    assert result.exit_code == 1
    assert "no summary found" in result.output


def test_render_base_warns_when_no_photo(_isolated_data_dir: Path) -> None:
    runner.invoke(app, ["init"])
    cv_content = _isolated_data_dir / "profile" / "cv_content.md"
    text = cv_content.read_text(encoding="utf-8").replace(
        "## Summary", "## Summary\n\nA real summary sentence.", 1
    )
    cv_content.write_text(text, encoding="utf-8")
    result = runner.invoke(app, ["render-base"])
    assert result.exit_code == 0, result.output
    assert "No profile photo" in result.output


def test_render_base_rejects_unknown_style(_isolated_data_dir: Path) -> None:
    runner.invoke(app, ["init", "--example"])
    result = runner.invoke(app, ["render-base", "--style", "baroque"])
    assert result.exit_code == 2
    assert "baroque" in result.output


def test_render_base_all_styles(_isolated_data_dir: Path) -> None:
    runner.invoke(app, ["init", "--example"])
    for style in CV_STYLES:
        result = runner.invoke(app, ["render-base", "--style", style])
        assert result.exit_code == 0, result.output
        assert f"style: {style}" in result.output


# ---------------------------------------------------------------------------
# render-letter
# ---------------------------------------------------------------------------
def test_render_letter_produces_pdf(_isolated_data_dir: Path, tmp_path: Path) -> None:
    runner.invoke(app, ["init", "--example"])
    payload_file = tmp_path / "letter.json"
    payload_file.write_text(json.dumps(_letter_payload()), encoding="utf-8")
    result = runner.invoke(app, ["render-letter", str(payload_file)])
    assert result.exit_code == 0, result.output
    pdf = _isolated_data_dir / "cover_letters" / "test_aps_data_analyst_cover.pdf"
    assert pdf.exists() and pdf.stat().st_size > 1000


def test_render_letter_rejects_missing_role(_isolated_data_dir: Path, tmp_path: Path) -> None:
    runner.invoke(app, ["init", "--example"])
    payload = _letter_payload()
    del payload["role_title"]
    payload_file = tmp_path / "letter.json"
    payload_file.write_text(json.dumps(payload), encoding="utf-8")
    result = runner.invoke(app, ["render-letter", str(payload_file)])
    assert result.exit_code == 1
    assert "role_title" in result.output


def test_render_letter_danish_and_explicit_output(
    _isolated_data_dir: Path, tmp_path: Path
) -> None:
    runner.invoke(app, ["init", "--example"])
    payload_file = tmp_path / "letter.json"
    payload_file.write_text(json.dumps(_letter_payload()), encoding="utf-8")
    out = tmp_path / "first_letter.pdf"
    result = runner.invoke(
        app, ["render-letter", str(payload_file), "--language", "DA", "-o", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert out.exists()


# ---------------------------------------------------------------------------
# validate_letter_content
# ---------------------------------------------------------------------------
def test_validate_letter_content_happy_path() -> None:
    validated = validate_letter_content(_letter_payload(tagline="Custom | Line"))
    assert validated["role_title"] == "Data Analyst"
    assert validated["company_name"] == "Test ApS"
    assert validated["tagline"] == "Custom | Line"
    assert "summary" not in validated


def test_validate_letter_content_requires_four_strengths() -> None:
    with pytest.raises(ValueError, match="key_strengths"):
        validate_letter_content(_letter_payload(key_strengths=["only", "two"]))


# ---------------------------------------------------------------------------
# Style fields on Profile
# ---------------------------------------------------------------------------
def _minimal_profile(**overrides) -> Profile:
    data = {
        "name": "TEST PERSON",
        "tagline_default": "Analyst | Evidence",
        "contact": {"phone": "12345678", "email": "t@example.com", "location": "Aarhus"},
    }
    data.update(overrides)
    return Profile.model_validate(data)


def test_profile_style_defaults() -> None:
    p = _minimal_profile()
    assert p.cv_style == "classic"
    assert p.cover_letter_style is None
    assert p.resolved_cover_letter_style() == "classic"


def test_profile_cover_letter_matches_cv_by_default() -> None:
    p = _minimal_profile(cv_style="minimal")
    assert p.resolved_cover_letter_style() == "minimal"


def test_profile_cover_letter_style_can_diverge() -> None:
    p = _minimal_profile(cv_style="creative", cover_letter_style="classic")
    assert p.resolved_cover_letter_style() == "classic"


def test_profile_rejects_unknown_style() -> None:
    with pytest.raises(Exception, match="cv_style"):
        _minimal_profile(cv_style="baroque")


def test_every_cv_style_has_a_preset() -> None:
    for style in CV_STYLES:
        assert style in STYLE_PRESETS


# ---------------------------------------------------------------------------
# cv_font_scale — the one-line fix for a CV spilling onto an extra page
# ---------------------------------------------------------------------------
def test_font_scale_default_and_bounds() -> None:
    assert _minimal_profile().cv_font_scale == 1.0
    assert _minimal_profile(cv_font_scale=0.95).cv_font_scale == 0.95
    with pytest.raises(Exception, match="cv_font_scale"):
        _minimal_profile(cv_font_scale=0.5)
    with pytest.raises(Exception, match="cv_font_scale"):
        _minimal_profile(cv_font_scale=1.5)


def test_scaled_cv_renders(tmp_path: Path) -> None:
    from danapply.render.templates.canonical import build_cv_pdf

    profile = _minimal_profile(cv_font_scale=0.9)
    out = tmp_path / "cv.pdf"
    build_cv_pdf({"tagline": "T", "summary": "S."}, out, profile)
    assert out.exists() and "S." in _pdf_text(out)


def test_cv_page_report_no_hint_for_single_page(tmp_path: Path) -> None:
    from danapply.cli import _cv_page_report
    from danapply.render.templates.canonical import build_cv_pdf

    profile = _minimal_profile()
    out = tmp_path / "cv.pdf"
    build_cv_pdf({"tagline": "T", "summary": "Short."}, out, profile)
    pages, hint = _cv_page_report(out)
    assert pages == 1 and hint is None


def test_cv_page_report_flags_thin_last_page(tmp_path: Path) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rl_canvas

    from danapply.cli import _cv_page_report

    # Hand-built two-pager: page 2 holds a single lonely line.
    out = tmp_path / "two_pages.pdf"
    c = rl_canvas.Canvas(str(out), pagesize=A4)
    for i in range(40):
        c.drawString(72, 800 - i * 18, f"Page one line {i} with plenty of content")
    c.showPage()
    c.drawString(72, 800, "Lonely line")
    c.showPage()
    c.save()

    pages, hint = _cv_page_report(out)
    assert pages == 2
    assert hint is not None and "cv_font_scale" in hint


# ---------------------------------------------------------------------------
# Taglines are titles — trailing full stop stripped at render time
# ---------------------------------------------------------------------------
def test_strip_title_period() -> None:
    from danapply.render.templates.canonical import _strip_title_period

    assert _strip_title_period("Evidence over opinion.") == "Evidence over opinion"
    assert _strip_title_period("Evidence over opinion") == "Evidence over opinion"
    assert _strip_title_period("To be continued...") == "To be continued..."
    assert _strip_title_period("  Padded. ") == "Padded"


def test_closing_tagline_renders_without_period(tmp_path: Path) -> None:
    from danapply.render.templates.canonical import build_cover_letter_pdf

    profile = _minimal_profile()
    data = {
        "tagline": "Analyst | Evidence",
        "closing_tagline": "Evidence over opinion.",
        "role_title": "Analyst",
        "company_name": "Test ApS",
        "opening_paragraph": "Hello.",
        "key_strengths": ["a", "b", "c", "d"],
        "themes": [("H1", "P1"), ("H2", "P2"), ("H3", "P3")],
        "lang": "EN",
    }
    out = tmp_path / "cl.pdf"
    build_cover_letter_pdf(data, out, profile)
    text = _pdf_text(out)
    assert "Evidence over opinion" in text
    assert "Evidence over opinion." not in text


# ---------------------------------------------------------------------------
# Portfolio section — present with a link, absent entirely without one
# ---------------------------------------------------------------------------
def _pdf_text(path: Path) -> str:
    from pypdf import PdfReader

    return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)


def test_empty_portfolio_block_normalises_to_none() -> None:
    p = _minimal_profile(portfolio={"display": "", "href": ""})
    assert p.portfolio is None


def test_blank_strings_portfolio_normalises_to_none() -> None:
    p = _minimal_profile(portfolio={"display": "  ", "href": ""})
    assert p.portfolio is None


def test_real_portfolio_survives_validation() -> None:
    p = _minimal_profile(portfolio={"display": "me.com", "href": "https://me.com"})
    assert p.portfolio is not None and p.portfolio.display == "me.com"


def test_cv_without_portfolio_has_no_portfolio_section(tmp_path: Path) -> None:
    from danapply.render.templates.canonical import build_cv_pdf

    profile = _minimal_profile()
    out = tmp_path / "cv.pdf"
    build_cv_pdf({"tagline": "T", "summary": "S."}, out, profile)
    assert "PORTFOLIO" not in _pdf_text(out)


def test_cv_with_portfolio_shows_section(tmp_path: Path) -> None:
    from danapply.render.templates.canonical import build_cv_pdf

    profile = _minimal_profile(
        portfolio={"display": "example.dev", "href": "https://example.dev"}
    )
    out = tmp_path / "cv.pdf"
    build_cv_pdf({"tagline": "T", "summary": "S."}, out, profile)
    text = _pdf_text(out)
    assert "PORTFOLIO" in text and "example.dev" in text


def test_cover_letter_without_portfolio_has_no_portfolio_section(
    tmp_path: Path,
) -> None:
    from danapply.render.templates.canonical import build_cover_letter_pdf

    profile = _minimal_profile()
    data = {
        "tagline": "T",
        "closing_tagline": "",
        "role_title": "Analyst",
        "company_name": "Test ApS",
        "opening_paragraph": "Hello.",
        "key_strengths": ["a", "b", "c", "d"],
        "themes": [("H1", "P1"), ("H2", "P2"), ("H3", "P3")],
        "lang": "EN",
    }
    out = tmp_path / "cl.pdf"
    build_cover_letter_pdf(data, out, profile)
    assert "PORTFOLIO" not in _pdf_text(out)
