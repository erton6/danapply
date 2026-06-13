"""Parser tests.

The PDF fixture is a real Fertin Pharma posting saved from the Aspeya
salesforce-sites portal in 2026-05. It exercises:
  - filename heuristic with " _ " separator and generic "Job Details" suffix
  - location detection (Vejle, Denmark)
  - language detection (English, with some Danish markers in URLs)
  - source detection (salesforce-sites)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from danapply.models import Job
from danapply.parse import parse_batch, parse_file, parse_paste

FIXTURE_DIR = Path(__file__).parent / "fixtures"
FERTIN_PDF = FIXTURE_DIR / "Sustainability Data Analyst _ Job Details.pdf"


# ---------------------------------------------------------------------------
# PDF parser
# ---------------------------------------------------------------------------
def test_parse_fertin_pdf_extracts_title() -> None:
    job = parse_file(FERTIN_PDF)
    assert isinstance(job, Job)
    assert "Sustainability Data Analyst" in job.title


def test_parse_fertin_pdf_extracts_location() -> None:
    job = parse_file(FERTIN_PDF)
    assert job.location is not None
    assert "Vejle" in job.location


def test_parse_fertin_pdf_has_non_empty_description() -> None:
    job = parse_file(FERTIN_PDF)
    assert len(job.description_raw) > 200
    assert "ESG" in job.description_raw or "sustainability" in job.description_raw.lower()


def test_parse_fertin_pdf_detects_source() -> None:
    job = parse_file(FERTIN_PDF)
    # The Aspeya/Fertin portal lives at *.my.salesforce-sites.com
    assert job.source == "salesforce-sites"


def test_parse_fertin_pdf_detects_english_language() -> None:
    job = parse_file(FERTIN_PDF)
    assert job.language == "EN"


def test_parse_fertin_pdf_strips_generic_title_prefix() -> None:
    job = parse_file(FERTIN_PDF)
    # The PDF text starts with "Job Details: Sustainability Data Analyst";
    # the parser should strip the generic "Job Details:" prefix.
    assert not job.title.lower().startswith("job details")
    assert "Sustainability Data Analyst" in job.title


def test_parse_fertin_pdf_gets_a_job_id() -> None:
    job = parse_file(FERTIN_PDF)
    job_id = job.ensure_job_id()
    assert len(job_id) > 0
    assert "_" in job_id


def test_parse_file_raises_for_missing() -> None:
    with pytest.raises(FileNotFoundError):
        parse_file(FIXTURE_DIR / "does_not_exist.pdf")


def test_parse_file_raises_for_unknown_extension(tmp_path: Path) -> None:
    weird = tmp_path / "thing.xyz"
    weird.write_text("hello", encoding="utf-8")
    with pytest.raises(ValueError, match="No parser registered"):
        parse_file(weird)


# ---------------------------------------------------------------------------
# Text + paste parser
# ---------------------------------------------------------------------------
SAMPLE_PASTE = """\
Business Analyst – AI & Automation
TDC NET · København, Denmark · 3 days ago

Do you want to turn AI opportunities into tangible products and business value?

We are looking for an experienced Business Analyst to be a part of our
accelerated AI enablement journey in TDC NET.

In this role as a Business Analyst with an AI & automation focus, you will be
responsible for identifying, describing, and driving AI relevant improvement
opportunities across business areas.

Your responsibilities will include:
- Analyzing processes and data to identify relevant AI use cases
- Preparing use case descriptions and AI specific requirements
- Working closely with developers, architects, and data specialists
"""


def test_parse_paste_extracts_title_from_first_line() -> None:
    job = parse_paste(SAMPLE_PASTE)
    assert "Business Analyst" in job.title


def test_parse_paste_preserves_full_content() -> None:
    job = parse_paste(SAMPLE_PASTE)
    assert "AI use cases" in job.description_raw


def test_parse_paste_default_source() -> None:
    job = parse_paste(SAMPLE_PASTE)
    # No filename hints; source falls back to "paste" or "pdf:" based on routing
    assert job.source != ""


# ---------------------------------------------------------------------------
# Batch parser
# ---------------------------------------------------------------------------
def test_parse_batch_processes_fixture_dir() -> None:
    jobs = parse_batch(FIXTURE_DIR)
    assert len(jobs) >= 1
    assert any("Sustainability" in (j.title or "") for j in jobs)


def test_parse_batch_raises_for_non_directory(tmp_path: Path) -> None:
    not_a_dir = tmp_path / "missing"
    with pytest.raises(NotADirectoryError):
        parse_batch(not_a_dir)


def test_parse_batch_skips_hidden_files(tmp_path: Path) -> None:
    (tmp_path / ".DS_Store").write_text("junk", encoding="utf-8")
    (tmp_path / "real.txt").write_text("Business Analyst\nFor TestCorp", encoding="utf-8")
    jobs = parse_batch(tmp_path)
    assert len(jobs) == 1
    assert "Business Analyst" in jobs[0].title


def test_parse_batch_continues_after_unsupported(tmp_path: Path) -> None:
    (tmp_path / "weird.xyz").write_text("ignored", encoding="utf-8")
    (tmp_path / "real.txt").write_text(
        "Insights Analyst\nFor SomeCo\nCopenhagen, Denmark", encoding="utf-8",
    )
    jobs = parse_batch(tmp_path)
    assert len(jobs) == 1


# ---------------------------------------------------------------------------
# Integration: parse → upsert → roundtrip
# ---------------------------------------------------------------------------
def test_parser_to_memory_roundtrip(tmp_path: Path) -> None:
    import os

    from danapply import memory

    os.environ["DANAPPLY_DATA_DIR"] = str(tmp_path)
    try:
        memory.init_db()
        parsed = parse_file(FERTIN_PDF)
        saved, is_new = memory.upsert_job(parsed)
        assert is_new is True
        retrieved = memory.get_job(saved.job_id)
        assert retrieved is not None
        assert retrieved.title == saved.title
        assert len(retrieved.description_raw) > 200
    finally:
        os.environ.pop("DANAPPLY_DATA_DIR", None)
