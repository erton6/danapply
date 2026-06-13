"""Profile / targets configuration models.

Profile is the user's identity (name, contact, languages, references) plus
display preferences (tagline default, photo path, accent colour). Targets is
the scoring rubric weights and the role/geography hunting parameters.

Both load from YAML and are validated by pydantic. Loading failures surface
clear errors with field paths.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------- Profile ----------


class ContactInfo(BaseModel):
    phone: str
    email: str
    linkedin_url: str | None = None
    location: str  # e.g. "Copenhagen, Denmark"


class Portfolio(BaseModel):
    display: str  # e.g. "yourname.com"
    href: str  # full URL with protocol


class LanguageEntry(BaseModel):
    name: str
    level: str  # free-form, e.g. "Native (mother tongue)", "Intermediate"


class ReferenceEntry(BaseModel):
    name: str
    email: str


class ExperienceEntry(BaseModel):
    """One CV experience entry. Rendered top-to-bottom in list order."""

    model_config = ConfigDict(extra="forbid")

    role: str
    company: str
    dates: str  # free-form, e.g. "2020–2022" or "2024"
    location: str = ""
    descriptor: str | None = None  # optional one-line italic context
    bullets: list[str] = Field(default_factory=list)


class EducationEntry(BaseModel):
    """One CV education entry. Rendered top-to-bottom in list order."""

    model_config = ConfigDict(extra="forbid")

    degree: str
    school: str
    dates: str
    extra: str | None = None  # optional meta suffix, e.g. a specialisation
    bullets: list[str] = Field(default_factory=list)


class UserSkills(BaseModel):
    """User-curated skill keywords used by the scorer and tailoring layer.

    All lists are optional and default to empty. When empty, the scorer falls
    back to substring matching against the job description (less precise).
    """

    model_config = ConfigDict(extra="forbid")

    tools: list[str] = Field(default_factory=list)
    """Software / platforms the user is comfortable with."""

    methods: list[str] = Field(default_factory=list)
    """Research and analytical methods."""

    domains: list[str] = Field(default_factory=list)
    """Industry or subject-matter expertise."""

    soft_skills: list[str] = Field(default_factory=list)
    """Communication, facilitation, stakeholder skills."""

    def all_keywords(self) -> list[str]:
        """Flat list of all skill keywords for quick matching."""
        return [*self.tools, *self.methods, *self.domains, *self.soft_skills]

    def is_empty(self) -> bool:
        return not (self.tools or self.methods or self.domains or self.soft_skills)


# Visual style presets for the rendered CV / cover letter. Every preset is
# ATS-friendly by construction: single column, real text, standard section
# headers — the presets only vary restrained design touches (where the accent
# colour appears, rule weights, header treatment). Nothing overdecorated.
CV_STYLES = ("classic", "minimal", "modern", "creative")


class Profile(BaseModel):
    """The user identity that drives every rendered artefact."""

    model_config = ConfigDict(extra="forbid")

    # Identity
    name: str  # e.g. "SOFIA ALMEIDA" — used in CV header as-is, so caps controlled here
    tagline_default: str

    contact: ContactInfo
    portfolio: Portfolio | None = None

    # Optional profile photo (top-right of CV with green ring).
    # Path is resolved relative to the profile directory if not absolute.
    photo_path: str | None = None

    languages: list[LanguageEntry] = Field(default_factory=list)
    references: list[ReferenceEntry] = Field(default_factory=list)

    # CV body content — every rendered experience/education line comes from
    # here. Empty lists render an explicit placeholder, never invented
    # content (onboarding / the CV session fills these in).
    experience: list[ExperienceEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)

    # Curated skill keywords (used by scoring + tailoring; safe to be empty)
    user_skills: UserSkills = Field(default_factory=UserSkills)

    # Design tokens — sensible defaults match the canonical template.
    accent_color: str = "#1F4737"

    cv_style: str = "classic"
    """One of ``CV_STYLES``: how the CV should feel — ``minimal``
    (minimalistic, accent only in details), ``classic`` (serious,
    traditional), ``modern`` (smart, confident accent use), ``creative``
    (slightly creative, more colour presence). All ATS-friendly."""

    cover_letter_style: str | None = None
    """Style for the cover letter. ``None`` (default) means match
    ``cv_style`` — set explicitly only when the user wants them to differ."""

    cv_font_scale: float = 1.0
    """Uniform font/spacing scale for the rendered CV (and the shared
    header on the cover letter). Drop to e.g. 0.95 when the CV spills a
    line or two onto an extra page. Sane range enforced: 0.8–1.05."""

    @field_validator("accent_color")
    @classmethod
    def _validate_hex(cls, v: str) -> str:
        if not (v.startswith("#") and len(v) in {4, 7}):
            raise ValueError(f"accent_color must be a hex string like '#1F4737', got {v!r}")
        return v

    @field_validator("cv_style")
    @classmethod
    def _validate_cv_style(cls, v: str) -> str:
        if v not in CV_STYLES:
            raise ValueError(f"cv_style must be one of {CV_STYLES}, got {v!r}")
        return v

    @field_validator("cover_letter_style")
    @classmethod
    def _validate_cl_style(cls, v: str | None) -> str | None:
        if v is not None and v not in CV_STYLES:
            raise ValueError(f"cover_letter_style must be one of {CV_STYLES}, got {v!r}")
        return v

    @field_validator("cv_font_scale")
    @classmethod
    def _validate_font_scale(cls, v: float) -> float:
        if not (0.8 <= v <= 1.05):
            raise ValueError(
                f"cv_font_scale must be between 0.8 and 1.05 (1.0 = default), got {v!r}"
            )
        return v

    def resolved_cover_letter_style(self) -> str:
        """The style the cover letter actually renders with."""
        return self.cover_letter_style or self.cv_style

    @model_validator(mode="after")
    def _empty_portfolio_is_none(self) -> Profile:
        """A portfolio block with blank display/href means *no portfolio*.

        The blank scaffold ships ``portfolio: {display: "", href: ""}`` as a
        fill-in template; until the user actually provides a link, the
        renderers must treat the profile as having no portfolio at all —
        the section is omitted entirely, never rendered as an empty box.
        """
        if self.portfolio is not None and not (
            self.portfolio.display.strip() and self.portfolio.href.strip()
        ):
            self.portfolio = None
        return self


# ---------- Targets (scoring rubric weights + filters) ----------


class TargetRoles(BaseModel):
    tier_a_titles: list[str] = Field(default_factory=list)
    tier_b_titles: list[str] = Field(default_factory=list)


class GeographyFilter(BaseModel):
    primary: list[str] = Field(default_factory=list)
    acceptable: list[str] = Field(default_factory=list)
    remote_ok: bool = True


class TargetConstraints(BaseModel):
    excluded_industries: list[str] = Field(default_factory=list)
    excluded_companies: list[str] = Field(default_factory=list)
    max_commute_minutes_one_way: int | None = None


class Targets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    roles: TargetRoles = Field(default_factory=TargetRoles)
    geography: GeographyFilter = Field(default_factory=GeographyFilter)
    arrangement: str = "hybrid"  # office | hybrid | remote
    seniority: str = "early_career"  # entry | junior | mid | senior | flexible
    salary_floor_monthly_dkk: int | None = None
    salary_target_monthly_dkk: int | None = None
    constraints: TargetConstraints = Field(default_factory=TargetConstraints)


# ---------- Loaders ----------


class ConfigLoadError(Exception):
    """Raised when a profile or targets file is missing or invalid."""


def load_profile(path: Path) -> Profile:
    """Load and validate ``profile.yaml``.

    Resolves a relative ``photo_path`` to absolute (relative to the profile
    directory, so users can write ``photo_path: photo.jpeg`` in YAML).
    """
    if not path.exists():
        raise ConfigLoadError(f"Profile not found at {path}. Run `danapply init` first.")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        profile = Profile.model_validate(raw)
    except Exception as exc:
        raise ConfigLoadError(f"Failed to load profile from {path}: {exc}") from exc

    if profile.photo_path:
        photo = Path(profile.photo_path).expanduser()
        if not photo.is_absolute():
            photo = (path.parent / photo).resolve()
        profile.photo_path = str(photo)

    return profile


def load_targets(path: Path) -> Targets:
    if not path.exists():
        raise ConfigLoadError(f"Targets not found at {path}. Run `danapply init` first.")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return Targets.model_validate(raw)
    except Exception as exc:
        raise ConfigLoadError(f"Failed to load targets from {path}: {exc}") from exc
