"""Input parsers + smart-paste router.

Each parser converts a specific input shape (PDF file, pasted text,
.txt / .md / .eml file) into a ``Job`` model heuristically. DanApply
never fetches websites — postings arrive as pastes or files. Images and
messy pastes are Claude Code's job — it extracts the fields
in-conversation and stores them via ``danapply ingest``.
"""

from __future__ import annotations

from pathlib import Path

from danapply.models import Job
from danapply.parse import pdf as pdf_parser
from danapply.parse import text as text_parser

__all__ = [
    "parse_batch",
    "parse_file",
    "parse_paste",
]


def parse_file(path: str | Path) -> Job:
    """Dispatch a file to the right parser by extension."""
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"No such file: {p}")

    suffix = p.suffix.lower()
    if suffix == ".pdf":
        return pdf_parser.parse_pdf(p)
    if suffix in {".txt", ".md", ".eml"}:
        return text_parser.parse_text_file(p)
    if suffix in {".html", ".htm"}:
        # Not implemented in v0.0.2 — read as plain text and let user know.
        return text_parser.parse_text_file(p, source_hint=f"html:{p.name}")
    raise ValueError(
        f"No parser registered for extension '{suffix}'. "
        f"Supported in v0.0.2: .pdf, .txt, .md, .eml, .html (degraded)."
    )


def parse_batch(directory: str | Path) -> list[Job]:
    """Parse every supported file in a directory. Skips unsupported files
    silently — pipeline never halts on a single bad file."""
    d = Path(directory).expanduser().resolve()
    if not d.is_dir():
        raise NotADirectoryError(f"Not a directory: {d}")

    results: list[Job] = []
    for entry in sorted(d.iterdir()):
        if not entry.is_file():
            continue
        if entry.name.startswith("."):
            continue  # .DS_Store etc.
        try:
            results.append(parse_file(entry))
        except (ValueError, FileNotFoundError):
            # Unsupported or unreadable — log and continue. Surface in CLI.
            continue
    return results


def parse_paste(content: str, source_hint: str = "paste") -> Job:
    """Parse raw pasted text as a single job posting.

    Screenshots / images of postings are handled by Claude Code directly
    (it reads the image in-conversation, extracts the fields, and stores
    the result via ``danapply ingest``) — there is no image parser here.
    """
    return text_parser.parse_paste(content, source_hint=source_hint)
