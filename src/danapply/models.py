"""Core domain models for DanApply.

These pydantic models are the contract between parsers, scorer, renderer,
and memory layer. A parser produces a ``Job``; the memory layer serialises
``Job`` to SQLite; the renderer + scorer consume ``Job`` plus user
``profile.yaml`` data.

The ``job_id`` is deterministic per (company, title, posting-date hint), so
parsing the same posting twice produces the same id — which is how dedup
works downstream.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from slugify import slugify


# ---------------------------------------------------------------------------
# Confidence + status enums (string literals — easier to serialise than enum.Enum)
# ---------------------------------------------------------------------------
DataConfidence = Literal["high", "medium", "low"]

ApplicationStatus = Literal[
    "parsed",
    "tailored",
    "applied",
    "interview_scheduled",
    "interview_completed_advancing",
    "interview_completed_rejected",
    "rejected_pre_interview",
    "ghosted",
    "offer_received",
    "offer_accepted",
    "withdrew",
]


# ---------------------------------------------------------------------------
# Slug helpers
# ---------------------------------------------------------------------------
def pascalcase_slug(value: str, max_words: int = 6) -> str:
    """Convert a free-text label to PascalCase (no spaces, no punctuation).

    Words already containing internal capitals (CamelCase / PascalCase /
    brand names like ``McKinsey`` or ``HelloFresh``) are preserved as-is.
    All-lowercase or all-uppercase words are title-cased.

    Examples:
        "HelloFresh"                                  -> "HelloFresh"
        "McKinsey & Company"                          -> "McKinseyCompany"
        "Junior Business Analyst (Asset Finance)"     -> "JuniorBusinessAnalystAssetFinance"
        "BUSINESS ANALYST"                            -> "BusinessAnalyst"
        "business analyst"                            -> "BusinessAnalyst"
    """
    if not value:
        return ""
    parts = re.split(r"[^a-zA-Z0-9]+", value)
    parts = [p for p in parts if p][:max_words]

    out: list[str] = []
    for p in parts:
        if p.islower() or p.isupper():
            # All same case — title-case it
            out.append(p.capitalize())
        else:
            # Mixed-case (intentional CamelCase / brand) — preserve
            out.append(p)
    return "".join(out)


def _content_hash(text: str, length: int = 8) -> str:
    """Short stable hash of a content blob — last-resort id component."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


# ---------------------------------------------------------------------------
# Job (parser output / memory.db row)
# ---------------------------------------------------------------------------
class Job(BaseModel):
    """A parsed job posting.

    Produced by parsers, scored by the scorer, persisted by the memory layer,
    and used by the renderer + interview_prep + joblog workflows.
    """

    model_config = ConfigDict(extra="forbid")

    # Identity (computed if not provided — see ``ensure_job_id``)
    job_id: str = Field(
        default="",
        description="Deterministic id: {CompanySlug}_{TitleSlug}[_{DateOrHash}].",
    )

    # Core fields (always extracted; may be empty for low-confidence parses)
    title: str = ""
    company: str = ""
    location: str | None = None

    # Date fields
    posting_date: date | None = None
    deadline: date | None = None

    # Source attribution
    source: str = "unknown"  # e.g. "linkedin", "thehub", "jobindex", "pdf:filename.pdf"
    url: str | None = None

    # Content
    language: Literal["EN", "DA", "DE", "HU", "SV", "NO", "FI", "OTHER"] = "EN"
    description_raw: str = ""
    requirements: list[str] = Field(default_factory=list)

    # Quality + lifecycle
    data_confidence: DataConfidence = "medium"
    status: ApplicationStatus = "parsed"

    # Scoring (populated by the scorer; 0 means "unscored")
    score: int = 0
    score_breakdown: dict | None = None
    scored_at: datetime | None = None

    # When this application was logged to Jobnet (None = not yet logged)
    jobnet_logged_at: datetime | None = None

    parsed_at: datetime = Field(default_factory=datetime.now)
    last_seen_at: datetime = Field(default_factory=datetime.now)

    # --- Validators -----------------------------------------------------

    @field_validator("title", "company")
    @classmethod
    def _strip_whitespace(cls, v: str) -> str:
        return v.strip() if v else v

    # --- Convenience ----------------------------------------------------

    def ensure_job_id(self) -> str:
        """Populate ``job_id`` from company/title (and a date or content hash
        as disambiguator). Idempotent — returns the existing id if set."""
        if self.job_id:
            return self.job_id

        company_slug = pascalcase_slug(self.company) or "UnknownCompany"
        title_slug = pascalcase_slug(self.title) or "UntitledRole"
        suffix: str
        if self.posting_date:
            suffix = self.posting_date.isoformat()
        elif self.description_raw:
            suffix = _content_hash(self.description_raw)
        else:
            suffix = _content_hash(f"{company_slug}/{title_slug}")

        self.job_id = f"{company_slug}_{title_slug}_{suffix}"
        return self.job_id

    def to_db_row(self) -> dict:
        """Flat dict for SQLite insertion — dates and datetimes as ISO strings."""
        import json as _json
        self.ensure_job_id()
        return {
            "job_id": self.job_id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "posting_date": self.posting_date.isoformat() if self.posting_date else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "source": self.source,
            "url": self.url,
            "language": self.language,
            "description_raw": self.description_raw,
            "data_confidence": self.data_confidence,
            "status": self.status,
            "score": self.score,
            "score_breakdown": _json.dumps(self.score_breakdown) if self.score_breakdown else None,
            "scored_at": self.scored_at.isoformat() if self.scored_at else None,
            "jobnet_logged_at": self.jobnet_logged_at.isoformat() if self.jobnet_logged_at else None,
            "requirements": _json.dumps(self.requirements) if self.requirements else None,
            "parsed_at": self.parsed_at.isoformat(),
            "last_seen_at": self.last_seen_at.isoformat(),
        }

    @classmethod
    def from_db_row(cls, row: dict) -> Job:
        """Hydrate a Job from a sqlite3 Row (with the schema in memory.py)."""
        import json as _json
        data = dict(row)
        for date_field in ("posting_date", "deadline"):
            v = data.get(date_field)
            if v:
                data[date_field] = date.fromisoformat(v)
        for dt_field in ("parsed_at", "last_seen_at", "scored_at", "jobnet_logged_at"):
            v = data.get(dt_field)
            if v:
                data[dt_field] = datetime.fromisoformat(v)
        if data.get("score_breakdown"):
            try:
                data["score_breakdown"] = _json.loads(data["score_breakdown"])
            except (TypeError, ValueError):
                data["score_breakdown"] = None
        # requirements stored as a JSON list (schema v4+); None for older rows
        raw_requirements = data.get("requirements")
        if isinstance(raw_requirements, str):
            try:
                parsed = _json.loads(raw_requirements)
                data["requirements"] = parsed if isinstance(parsed, list) else []
            except (TypeError, ValueError):
                data["requirements"] = []
        else:
            data["requirements"] = []
        return cls(**data)
