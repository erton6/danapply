"""Text + paste parser.

Handles raw pasted job descriptions and ``.txt`` / ``.md`` / ``.eml`` files.
Same heuristic approach as the PDF parser, applied to plain text.
"""

from __future__ import annotations

from pathlib import Path

from danapply.models import Job
from danapply.parse.pdf import (
    _guess_language,
    _guess_location,
    _guess_posting_date,
    _guess_source_from_text,
    _guess_title_and_company,
)


def parse_text_file(path: Path, source_hint: str | None = None) -> Job:
    """Parse a ``.txt`` / ``.md`` / ``.eml`` / ``.html`` file as a single job.

    For HTML, the v0.0.2 implementation reads raw text — it does not strip
    tags. Good enough for plain-text job exports; a proper HTML parser
    lands in v0.0.3.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    return _parse_text_body(
        text,
        filename_stem=path.stem,
        source=source_hint or f"file:{path.name}",
    )


def parse_paste(content: str, source_hint: str = "paste") -> Job:
    """Parse a free-text paste as a single job posting.

    The caller (CLI) supplies ``source_hint`` to attribute the paste
    (e.g. ``"paste:linkedin"`` if the user said "from LinkedIn").
    """
    return _parse_text_body(
        content,
        filename_stem="",
        source=source_hint,
    )


def _parse_text_body(text: str, filename_stem: str, source: str) -> Job:
    title, company, conf = _guess_title_and_company(text, filename_stem)
    location = _guess_location(text)
    posting_date = _guess_posting_date(text)
    language = _guess_language(text)
    auto_source = _guess_source_from_text(text, filename_stem)
    chosen_source = source if source != "paste" else auto_source

    return Job(
        title=title,
        company=company,
        location=location,
        posting_date=posting_date,
        source=chosen_source,
        url=None,
        language=language,  # type: ignore[arg-type]
        description_raw=text,
        data_confidence=conf,
    )
