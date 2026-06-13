"""The canonical CV + cover letter template (canonical design).

ATS-friendly two-page layout. Dark-teal accent, plain section headers,
▸ bullets, highlighted PORTFOLIO block, circular profile photo top-right
with green ring. All user-specific content (name, contact, languages,
references, photo) comes from the ``Profile`` object passed in — the
template itself is generic.

Per-job tailoring (tagline, summary, skills order, optional bullet
overrides) comes from the ``JobCVData`` dict.
"""

from __future__ import annotations

import io
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image as PILImage
from PIL import ImageDraw
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from danapply.config import Profile

# ---------------------------------------------------------------------------
# Unicode font for the ▸ bullet glyph (built-in Helvetica lacks U+25B8)
# ---------------------------------------------------------------------------
_BULLET_FONT_PATHS = [
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]
_BULLET_FONT: str | None = None
for _p in _BULLET_FONT_PATHS:
    if os.path.exists(_p):
        try:
            pdfmetrics.registerFont(TTFont("ArialUni", _p))
            _BULLET_FONT = "ArialUni"
            break
        except Exception:
            continue
BULLET_GLYPH = "▸" if _BULLET_FONT else "→"


# ---------------------------------------------------------------------------
# Unicode body-font fallback
#
# The built-in Helvetica only covers Latin-1, so names and places like
# "Wrocław" or "Łódź" silently lose glyphs. When any rendered string needs
# more than Latin-1, the whole document switches to a Unicode-capable TTF
# family; Helvetica stays the default otherwise.
# ---------------------------------------------------------------------------
_UNICODE_FONT_CANDIDATES: list[tuple[str, str | None, str | None, str | None]] = [
    # (regular, bold, italic, bold-italic) — first family found wins
    (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Italic.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold Italic.ttf",
    ),
    (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf",
    ),
    # Single-weight last resorts — bold/italic render in the same weight,
    # but every glyph shows.
    ("/Library/Fonts/Arial Unicode.ttf", None, None, None),
    ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", None, None, None),
]

_unicode_font_map: dict[str, str] | None = None
_unicode_font_searched = False


def _unicode_family() -> dict[str, str] | None:
    """Register a Unicode TTF family once; return the Helvetica→TTF name map
    (or None when no candidate font exists on this system)."""
    global _unicode_font_map, _unicode_font_searched
    if _unicode_font_searched:
        return _unicode_font_map
    _unicode_font_searched = True

    for regular, bold, italic, bold_italic in _UNICODE_FONT_CANDIDATES:
        if not os.path.exists(regular):
            continue
        try:
            pdfmetrics.registerFont(TTFont("DAUni", regular))
            bold_name = italic_name = bold_italic_name = "DAUni"
            if bold and os.path.exists(bold):
                pdfmetrics.registerFont(TTFont("DAUni-Bold", bold))
                bold_name = "DAUni-Bold"
            if italic and os.path.exists(italic):
                pdfmetrics.registerFont(TTFont("DAUni-Italic", italic))
                italic_name = "DAUni-Italic"
            if bold_italic and os.path.exists(bold_italic):
                pdfmetrics.registerFont(TTFont("DAUni-BoldItalic", bold_italic))
                bold_italic_name = "DAUni-BoldItalic"
            # Family registration makes <b>/<i> markup inside Paragraphs work
            pdfmetrics.registerFontFamily(
                "DAUni", normal="DAUni", bold=bold_name,
                italic=italic_name, boldItalic=bold_italic_name,
            )
            _unicode_font_map = {
                "Helvetica": "DAUni",
                "Helvetica-Bold": bold_name,
                "Helvetica-Oblique": italic_name,
            }
            return _unicode_font_map
        except Exception:  # corrupt font file — try the next candidate
            continue
    return None


def _collect_strings(obj: Any) -> list[str]:
    """Recursively pull every string out of nested dicts / lists / tuples."""
    out: list[str] = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            out.extend(_collect_strings(v))
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            out.extend(_collect_strings(item))
    return out


def _needs_unicode(*sources: Any) -> bool:
    """True when any string in the given objects falls outside cp1252
    (≈ what the built-in Helvetica can display)."""
    for source in sources:
        for s in _collect_strings(source):
            try:
                s.encode("cp1252")
            except UnicodeEncodeError:
                return True
    return False


def _apply_font_map(
    styles: dict[str, ParagraphStyle], font_map: dict[str, str] | None
) -> dict[str, ParagraphStyle]:
    """Swap Helvetica font names for the Unicode family in-place."""
    if font_map:
        for style in styles.values():
            style.fontName = font_map.get(style.fontName, style.fontName)
    return styles


def _profile_strings(profile: Profile) -> list[str]:
    """All renderable strings from a Profile (for font detection)."""
    return _collect_strings(profile.model_dump())


def _resolve_font_map(*content_sources: Any) -> dict[str, str] | None:
    """Pick the font map for a render: the Unicode family when the content
    needs it (and a candidate font exists), otherwise None → Helvetica."""
    if _needs_unicode(*content_sources):
        return _unicode_family()
    return None


# ---------------------------------------------------------------------------
# Skills bucket labels — the text under each label comes from the user's
# ``profile.user_skills`` (or a per-job ``skills_<key>`` override in
# JobCVData). The template ships no career content of its own: experience,
# education, and skills all hydrate from profile.yaml.
# ---------------------------------------------------------------------------
SKILLS_BUCKET_LABELS = {
    "stakeholder": "Stakeholder Engagement & Communication",
    "commercial": "Business & Commercial Insight",
    "research": "Research & Analysis",
}

_MISSING_EXPERIENCE_NOTE = (
    "No experience entries in profile.yaml yet — onboarding (or editing the "
    "file directly) fills this section in."
)
_MISSING_EDUCATION_NOTE = (
    "No education entries in profile.yaml yet — onboarding (or editing the "
    "file directly) fills this section in."
)


# ---------------------------------------------------------------------------
# Style presets — how the CV / cover letter *feels*.
#
# Every preset is ATS-friendly by construction: the document stays a single
# column of real text with standard section headers; presets only vary
# restrained design touches (where the accent colour appears, rule weights,
# name treatment). Nothing here adds graphics, columns, or text-in-images.
# ---------------------------------------------------------------------------
STYLE_PRESETS: dict[str, dict[str, Any]] = {
    # Serious / traditional — the original canonical look.
    "classic": {
        "name_color": "accent", "name_size": 26,
        "tagline_color": "subtle", "tagline_italic": False,
        "header_rule": 1.2,
        "section_color": "accent", "section_rule": True,
        "box_bg": True,
        "cl_bullet_accent": True, "theme_head_color": "accent",
    },
    # Minimalistic — accent only in details (links, photo ring, left border).
    "minimal": {
        "name_color": "black", "name_size": 23,
        "tagline_color": "subtle", "tagline_italic": False,
        "header_rule": 0.7,
        "section_color": "black", "section_rule": False,
        "box_bg": False,
        "cl_bullet_accent": False, "theme_head_color": "black",
    },
    # Smart / contemporary — black name, confident accent rules.
    "modern": {
        "name_color": "black", "name_size": 26,
        "tagline_color": "accent", "tagline_italic": False,
        "header_rule": 2.4,
        "section_color": "accent", "section_rule": True,
        "box_bg": True,
        "cl_bullet_accent": True, "theme_head_color": "accent",
    },
    # Slightly creative — more colour presence, still restrained.
    "creative": {
        "name_color": "accent", "name_size": 27,
        "tagline_color": "accent", "tagline_italic": True,
        "header_rule": 1.8,
        "section_color": "accent", "section_rule": True,
        "box_bg": True,
        "cl_bullet_accent": True, "theme_head_color": "accent",
    },
}


def _strip_title_period(text: str) -> str:
    """Taglines are titles, not sentences — drop a single trailing full
    stop (but leave ellipses alone)."""
    t = text.strip()
    if t.endswith(".") and not t.endswith(".."):
        t = t[:-1]
    return t


def _tint(hex_color: str, whiteness: float) -> colors.Color:
    """Mix the accent colour toward white (0.0 = accent, 1.0 = white).

    Soft rules and the portfolio-box background derive from the user's
    ``accent_color`` instead of fixed greens, so a colour change in
    profile.yaml propagates to every tinted element.
    """
    r, g, b = _hex_to_rgb(hex_color)
    return colors.Color(
        (r + (255 - r) * whiteness) / 255,
        (g + (255 - g) * whiteness) / 255,
        (b + (255 - b) * whiteness) / 255,
    )


@dataclass
class _Theme:
    """Resolved design tokens for one render: accent + style preset."""

    accent_hex: str
    preset: dict[str, Any] = field(default_factory=lambda: STYLE_PRESETS["classic"])

    @property
    def accent(self) -> colors.Color:
        return colors.HexColor(self.accent_hex)

    @property
    def soft_rule(self) -> colors.Color:
        return _tint(self.accent_hex, 0.62)

    @property
    def box_bg(self) -> colors.Color:
        return _tint(self.accent_hex, 0.93)


def _resolve_theme(profile: Profile, style: str | None, *, cover_letter: bool = False) -> _Theme:
    """Pick the theme for a render: explicit ``style`` arg wins, then the
    profile's ``cv_style`` / resolved cover-letter style, then classic."""
    if style is None:
        if cover_letter:
            style = getattr(profile, "cover_letter_style", None) or getattr(
                profile, "cv_style", "classic"
            )
        else:
            style = getattr(profile, "cv_style", "classic")
    preset = STYLE_PRESETS.get(style, STYLE_PRESETS["classic"])
    return _Theme(accent_hex=profile.accent_color, preset=preset)


# ---------------------------------------------------------------------------
# Style factory
# ---------------------------------------------------------------------------
def _styles(theme: _Theme, scale: float = 1.0) -> dict[str, ParagraphStyle]:
    """Paragraph styles. Calibrated for a relaxed two-page CV.

    ``scale`` (the profile's ``cv_font_scale``) shrinks every font size,
    leading, and vertical space uniformly — the fix for a CV that spills
    a line or two onto an extra page."""
    def s(x: float) -> float:
        return x * scale

    accent = theme.accent
    preset = theme.preset
    subtle = colors.HexColor("#4A4A4A")
    name_color = accent if preset["name_color"] == "accent" else colors.black
    tagline_color = accent if preset["tagline_color"] == "accent" else subtle
    tagline_font = "Helvetica-Oblique" if preset["tagline_italic"] else "Helvetica"
    section_color = accent if preset["section_color"] == "accent" else colors.black
    base = ParagraphStyle(
        name="Body", fontName="Helvetica", fontSize=s(10), leading=s(14),
        textColor=colors.black, alignment=TA_LEFT, spaceAfter=s(3),
    )
    return {
        "name": ParagraphStyle("Name", parent=base, fontName="Helvetica-Bold",
                               fontSize=s(preset["name_size"]),
                               leading=s(preset["name_size"] + 4),
                               textColor=name_color, spaceAfter=s(3)),
        "tagline": ParagraphStyle("Tagline", parent=base, fontName=tagline_font,
                                  fontSize=s(11), leading=s(14),
                                  textColor=tagline_color, spaceAfter=s(4)),
        "contact": ParagraphStyle("Contact", parent=base, fontSize=s(9.5), leading=s(12),
                                  textColor=colors.black, spaceAfter=s(4)),
        "portfolio_label": ParagraphStyle("PortfolioLabel", parent=base, fontSize=s(9.5),
                                          textColor=accent, fontName="Helvetica-Bold"),
        "portfolio_url": ParagraphStyle("PortfolioUrl", parent=base, fontSize=s(12),
                                        textColor=accent, fontName="Helvetica-Bold"),
        "summary": ParagraphStyle("Summary", parent=base, fontSize=s(10), leading=s(14),
                                  textColor=colors.black, spaceBefore=s(10),
                                  spaceAfter=s(8)),
        "section": ParagraphStyle("Section", parent=base, fontName="Helvetica-Bold",
                                  fontSize=s(13), leading=s(16), textColor=section_color,
                                  spaceBefore=s(14), spaceAfter=s(6)),
        "role": ParagraphStyle("Role", parent=base, fontName="Helvetica-Bold",
                               fontSize=s(11.5), leading=s(14.5), textColor=colors.black,
                               spaceBefore=s(8), spaceAfter=s(2)),
        "meta": ParagraphStyle("Meta", parent=base, fontSize=s(9.5), leading=s(12),
                               textColor=subtle, spaceAfter=s(2.5)),
        "descriptor": ParagraphStyle("Descriptor", parent=base, fontSize=s(9.5),
                                     leading=s(12), textColor=subtle,
                                     fontName="Helvetica-Oblique", spaceAfter=s(3)),
        "bullet": ParagraphStyle("Bullet", parent=base, fontSize=s(10), leading=s(13.5),
                                 leftIndent=14, firstLineIndent=-14, spaceAfter=s(2.5)),
        "kvline": ParagraphStyle("KVLine", parent=base, fontSize=s(10), leading=s(14),
                                 spaceAfter=s(4)),
    }


# ---------------------------------------------------------------------------
# Circular profile photo with accent-coloured ring
# ---------------------------------------------------------------------------
_CIRCLE_PHOTO_CACHE: dict[tuple, io.BytesIO] = {}


def _circular_photo(
    path: str,
    px: int = 500,
    border_px: int = 14,
    border_rgb: tuple[int, int, int] = (31, 71, 55),
) -> io.BytesIO:
    """Square-crop, circle-mask, accent-ring border. Cached per source path."""
    cache_key = (path, px, border_px, border_rgb)
    if cache_key in _CIRCLE_PHOTO_CACHE:
        buf = _CIRCLE_PHOTO_CACHE[cache_key]
        buf.seek(0)
        return buf

    im = PILImage.open(path).convert("RGBA")
    w, h = im.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    inner = im.crop((left, top, left + side, top + side)).resize((px, px), PILImage.LANCZOS)

    canvas_px = px + 2 * border_px
    out = PILImage.new("RGBA", (canvas_px, canvas_px), (255, 255, 255, 0))
    draw = ImageDraw.Draw(out)
    draw.ellipse((0, 0, canvas_px - 1, canvas_px - 1), fill=border_rgb + (255,))

    mask = PILImage.new("L", (px, px), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, px - 1, px - 1), fill=255)
    out.paste(inner, (border_px, border_px), mask=mask)

    buf = io.BytesIO()
    out.save(buf, format="PNG")
    buf.seek(0)
    _CIRCLE_PHOTO_CACHE[cache_key] = buf
    return buf


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


# ---------------------------------------------------------------------------
# Composable blocks
# ---------------------------------------------------------------------------
def _bullet_para(text: str, style: ParagraphStyle) -> Paragraph:
    if _BULLET_FONT:
        prefix = f'<font name="{_BULLET_FONT}">{BULLET_GLYPH}</font>'
    else:
        prefix = BULLET_GLYPH
    return Paragraph(f"{prefix}&nbsp;&nbsp;{text}", style)


def _section_rule_items(title: str, styles: dict[str, ParagraphStyle], theme: _Theme) -> list:
    items: list = [Paragraph(title, styles["section"])]
    if theme.preset["section_rule"]:
        items.append(HRFlowable(
            width="100%", thickness=0.6, color=theme.soft_rule,
            spaceBefore=1, spaceAfter=4,
        ))
    return items


def _section_header(
    title: str, styles: dict[str, ParagraphStyle], theme: _Theme
) -> KeepTogether:
    return KeepTogether(_section_rule_items(title, styles, theme))


def _section_with_first(
    title: str, first_block: list, styles: dict[str, ParagraphStyle], theme: _Theme
) -> KeepTogether:
    return KeepTogether(_section_rule_items(title, styles, theme) + list(first_block))


def _portfolio_box(profile: Profile, styles: dict[str, ParagraphStyle], theme: _Theme) -> Table:
    """The highlighted PORTFOLIO block with a clickable link.

    Only called when ``profile.portfolio`` is set — a profile without a
    portfolio renders no trace of this section (callers must guard)."""
    assert profile.portfolio is not None
    box_bg = theme.box_bg if theme.preset["box_bg"] else colors.white
    accent = theme.accent
    inner = [[
        Paragraph("PORTFOLIO", styles["portfolio_label"]),
        Paragraph(
            f'<link href="{profile.portfolio.href}">'
            f'<font color="{profile.accent_color}"><b>{profile.portfolio.display}</b></font>'
            f'</link>',
            styles["portfolio_url"],
        ),
    ]]
    tbl = Table(inner, colWidths=[3.0 * cm, None], hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), box_bg),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LINEBEFORE", (0, 0), (0, -1), 3, accent),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tbl


def _contact_line(profile: Profile) -> str:
    """Render the contact line as inline HTML for a Paragraph."""
    parts = [profile.contact.phone, profile.contact.email]
    if profile.contact.linkedin_url:
        parts.append(
            f'<link href="{profile.contact.linkedin_url}">'
            f'<font color="{profile.accent_color}">LinkedIn</font>'
            f'</link>'
        )
    parts.append(profile.contact.location)
    return "  ·  ".join(parts)


def _name_header(
    profile: Profile,
    tagline: str,
    styles: dict[str, ParagraphStyle],
    theme: _Theme,
    photo_size_cm: float = 2.8,
) -> list:
    """Name + tagline + contact on the left; circular photo on the right (if present)."""
    accent = theme.accent
    rule_thickness = theme.preset["header_rule"]
    text_block = [
        Paragraph(profile.name, styles["name"]),
        Paragraph(_strip_title_period(tagline), styles["tagline"]),
        Paragraph(_contact_line(profile), styles["contact"]),
    ]

    if not profile.photo_path or not os.path.exists(profile.photo_path):
        # Text-only header
        return text_block + [
            HRFlowable(width="100%", thickness=rule_thickness, color=accent,
                       spaceBefore=2, spaceAfter=2),
        ]

    photo_buf = _circular_photo(profile.photo_path, border_rgb=_hex_to_rgb(profile.accent_color))
    img = Image(photo_buf, width=photo_size_cm * cm, height=photo_size_cm * cm)
    tbl = Table(
        [[text_block, img]],
        colWidths=[None, photo_size_cm * cm + 0.1 * cm],
        hAlign="LEFT",
    )
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (0, 0), "TOP"),
        ("VALIGN", (1, 0), (1, 0), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    return [
        tbl,
        HRFlowable(width="100%", thickness=rule_thickness, color=accent,
                   spaceBefore=4, spaceAfter=4),
    ]


def _experience_block(
    role: str,
    company: str,
    dates: str,
    location: str,
    descriptor: str | None,
    bullets: list[str],
    styles: dict[str, ParagraphStyle],
) -> list:
    block: list[Any] = [
        Paragraph(role, styles["role"]),
        Paragraph(
            f"<b>{company}</b> &nbsp;·&nbsp; {dates} &nbsp;·&nbsp; {location}",
            styles["meta"],
        ),
    ]
    if descriptor:
        block.append(Paragraph(descriptor, styles["descriptor"]))
    for b in bullets:
        block.append(_bullet_para(b, styles["bullet"]))
    return block


def _education_block(
    degree: str,
    school: str,
    dates: str,
    extra: str | None,
    bullets: list[str],
    styles: dict[str, ParagraphStyle],
) -> list:
    block: list[Any] = [Paragraph(degree, styles["role"])]
    meta = f"<b>{school}</b> &nbsp;·&nbsp; {dates}"
    if extra:
        meta += f" &nbsp;·&nbsp; {extra}"
    block.append(Paragraph(meta, styles["meta"]))
    for b in bullets:
        block.append(_bullet_para(b, styles["bullet"]))
    return block


def _default_bucket_text(profile: Profile, key: str) -> str:
    """Build the skills paragraph for one bucket from ``profile.user_skills``.

    Only the user's own curated keywords appear — an empty bucket yields an
    empty string (and the bucket is skipped) rather than invented content.
    """
    s = profile.user_skills
    keywords = {
        "stakeholder": s.soft_skills,
        "commercial": s.domains,
        "research": [*s.methods, *s.tools],
    }[key]
    return ", ".join(keywords)


def _skills_block(
    job_data: dict[str, Any], profile: Profile, styles: dict[str, ParagraphStyle]
) -> list[Paragraph]:
    order = job_data.get("skills_order", ["stakeholder", "commercial", "research"])
    paras = []
    for key in order:
        label = SKILLS_BUCKET_LABELS[key]
        text = job_data.get(f"skills_{key}", _default_bucket_text(profile, key))
        if not text:
            continue
        paras.append(Paragraph(f"<b>{label}:</b> {text}", styles["kvline"]))
    return paras


def _languages_line(profile: Profile, styles: dict[str, ParagraphStyle]) -> Paragraph:
    parts = [f"<b>{lang.name}:</b> {lang.level}" for lang in profile.languages]
    return Paragraph("  &nbsp;·&nbsp;  ".join(parts), styles["kvline"])


def _references_line(profile: Profile, styles: dict[str, ParagraphStyle]) -> Paragraph:
    parts = [f"<b>{ref.name}</b> — {ref.email}" for ref in profile.references]
    return Paragraph("&nbsp;&nbsp;|&nbsp;&nbsp;".join(parts), styles["kvline"])


# ---------------------------------------------------------------------------
# Top-level builders
# ---------------------------------------------------------------------------
def build_cv_pdf(
    job_data: dict[str, Any],
    output_path: str | Path,
    profile: Profile,
    style: str | None = None,
) -> Path:
    """Generate a tailored CV PDF.

    Required keys in ``job_data``: ``tagline``, ``summary``.

    Optional: ``skills_order``, ``skills_stakeholder``, ``skills_commercial``,
    ``skills_research``.

    ``style`` picks the visual preset (see ``STYLE_PRESETS``); when None,
    the profile's ``cv_style`` decides.

    Experience and education render from ``profile.experience`` /
    ``profile.education`` — the template carries no career content of its own.
    """
    theme = _resolve_theme(profile, style)
    font_map = _resolve_font_map(_profile_strings(profile), job_data)
    cv_scale = getattr(profile, "cv_font_scale", 1.0)
    styles = _apply_font_map(_styles(theme, cv_scale), font_map)
    story: list = []

    story.extend(_name_header(profile, job_data["tagline"], styles, theme))
    if profile.portfolio is not None:
        story.append(Spacer(1, 8))
        story.append(_portfolio_box(profile, styles, theme))
    story.append(Paragraph(job_data["summary"], styles["summary"]))

    # Experience — straight from profile.yaml
    if profile.experience:
        first, *rest = profile.experience
        first_block = _experience_block(
            first.role, first.company, first.dates, first.location,
            first.descriptor, first.bullets, styles,
        )
        story.append(_section_with_first("EXPERIENCE", first_block, styles, theme))
        for entry in rest:
            story.extend(_experience_block(
                entry.role, entry.company, entry.dates, entry.location,
                entry.descriptor, entry.bullets, styles,
            ))
    else:
        story.append(_section_with_first(
            "EXPERIENCE",
            [Paragraph(_MISSING_EXPERIENCE_NOTE, styles["descriptor"])],
            styles, theme,
        ))

    # Education — straight from profile.yaml
    if profile.education:
        first_ed, *rest_ed = profile.education
        first_block = _education_block(
            first_ed.degree, first_ed.school, first_ed.dates,
            first_ed.extra, first_ed.bullets, styles,
        )
        story.append(_section_with_first("EDUCATION", first_block, styles, theme))
        for entry in rest_ed:
            story.extend(_education_block(
                entry.degree, entry.school, entry.dates,
                entry.extra, entry.bullets, styles,
            ))
    else:
        story.append(_section_with_first(
            "EDUCATION",
            [Paragraph(_MISSING_EDUCATION_NOTE, styles["descriptor"])],
            styles, theme,
        ))

    # Skills
    skill_paragraphs = _skills_block(job_data, profile, styles)
    if skill_paragraphs:
        story.append(_section_with_first("SKILLS", skill_paragraphs[:1], styles, theme))
        story.extend(skill_paragraphs[1:])
    else:
        story.append(_section_header("SKILLS", styles, theme))

    # Languages + References
    if profile.languages:
        story.append(_section_with_first(
            "LANGUAGES", [_languages_line(profile, styles)], styles, theme,
        ))
    if profile.references:
        story.append(_section_with_first(
            "REFERENCES", [_references_line(profile, styles)], styles, theme,
        ))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4,
        leftMargin=1.7 * cm, rightMargin=1.7 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        title=f"{profile.name.title()} — CV", author=profile.name.title(),
    )
    doc.build(story)
    return output_path


# ---------------------------------------------------------------------------
# Cover-letter builder
# ---------------------------------------------------------------------------
def _cl_styles(theme: _Theme, scale: float = 1.0) -> dict[str, ParagraphStyle]:
    """Cover-letter paragraph styles.

    ``scale`` (<= 1.0) shrinks every font size, leading, and vertical space by
    the same factor — used by the one-page fit pass in
    ``build_cover_letter_pdf`` to compress overflowing letters onto a single
    page without changing the layout structure.
    """
    def s(x: float) -> float:
        return x * scale

    accent = theme.accent
    theme_head_color = (
        accent if theme.preset["theme_head_color"] == "accent" else colors.black
    )
    subtle = colors.HexColor("#4A4A4A")
    base = ParagraphStyle(
        name="Body", fontName="Helvetica", fontSize=s(10), leading=s(14),
        textColor=colors.black, alignment=TA_LEFT, spaceAfter=s(3),
    )
    return {
        "closing_title": ParagraphStyle(
            "ClosingTitle", parent=base, fontName="Helvetica-Bold",
            fontSize=s(15), leading=s(18), textColor=accent, alignment=TA_CENTER,
            spaceBefore=s(8), spaceAfter=s(4),
        ),
        "application_line": ParagraphStyle(
            "ApplicationLine", parent=base, fontName="Helvetica-Oblique",
            fontSize=s(9.5), leading=s(12), textColor=subtle,
            alignment=TA_RIGHT, spaceBefore=s(14), spaceAfter=s(14),
        ),
        "body": ParagraphStyle(
            "BodyP", parent=base, fontSize=s(10), leading=s(14.5),
            spaceBefore=0, spaceAfter=s(10),
        ),
        "intro": ParagraphStyle(
            "Intro", parent=base, fontSize=s(10), leading=s(14.5),
            spaceBefore=s(2), spaceAfter=s(4),
        ),
        "bullet": ParagraphStyle(
            "Bullet", parent=base, fontSize=s(10), leading=s(13.8),
            leftIndent=14, firstLineIndent=-14, spaceAfter=s(3),
        ),
        "theme_head": ParagraphStyle(
            "ThemeHead", parent=base, fontName="Helvetica-Bold",
            fontSize=s(11), leading=s(14), textColor=theme_head_color,
            spaceBefore=s(10), spaceAfter=s(3),
        ),
        "theme_para": ParagraphStyle(
            "ThemePara", parent=base, fontSize=s(10), leading=s(14.5),
            spaceAfter=s(8),
        ),
        "signoff": ParagraphStyle(
            "Signoff", parent=base, fontSize=s(10), leading=s(14),
            spaceBefore=s(10), spaceAfter=s(1),
        ),
        "signoff_name": ParagraphStyle(
            "SignoffName", parent=base, fontName="Helvetica-Oblique",
            fontSize=s(10), leading=s(13), textColor=colors.black,
            spaceAfter=0,
        ),
    }


def _cl_bullet(text: str, style: ParagraphStyle, accent_hex: str) -> Paragraph:
    if _BULLET_FONT:
        prefix = f'<font name="{_BULLET_FONT}" color="{accent_hex}">{BULLET_GLYPH}</font>'
    else:
        prefix = f'<font color="{accent_hex}">{BULLET_GLYPH}</font>'
    return Paragraph(f"{prefix}&nbsp;&nbsp;{text}", style)


def build_cover_letter_pdf(
    data: dict[str, Any],
    output_path: str | Path,
    profile: Profile,
    style: str | None = None,
) -> Path:
    """Generate a tailored cover-letter PDF.

    Required keys in ``data``: ``tagline``, ``closing_tagline``, ``role_title``,
    ``company_name``, ``opening_paragraph``, ``key_strengths`` (list of 4 strings),
    ``themes`` (list of 3 (heading, paragraph) tuples).

    Optional: ``signoff`` (default "Best regards," or "De bedste hilsner,"
    if ``lang == "DA"``), ``lang`` ("EN" or "DA").

    ``style`` picks the visual preset; when None, the profile's
    ``cover_letter_style`` (falling back to ``cv_style``) decides — so the
    letter matches the CV unless the user chose otherwise.
    """
    theme = _resolve_theme(profile, style, cover_letter=True)
    lang = data.get("lang", "EN")
    font_map = _resolve_font_map(_profile_strings(profile), data)

    def _story(scale: float) -> list:
        """Build the flowable story at a given shrink ``scale``.

        Flowables are consumed on build, so a fresh story is needed per attempt.
        """
        # The shared header follows the profile's cv_font_scale so CV and
        # letter stay visually consistent; the letter body uses the
        # one-page fit pass's own scale.
        cv_styles = _apply_font_map(
            _styles(theme, getattr(profile, "cv_font_scale", 1.0)), font_map
        )
        cl_styles = _apply_font_map(_cl_styles(theme, scale), font_map)
        story: list = []

        # Shared header + portfolio (section omitted entirely when the
        # profile has no portfolio link)
        story.extend(_name_header(profile, data["tagline"], cv_styles, theme))
        if profile.portfolio is not None:
            story.append(Spacer(1, 6 * scale))
            story.append(_portfolio_box(profile, cv_styles, theme))

        # Centred closing tagline (skipped when empty) + right-aligned
        # application subtitle
        story.append(Spacer(1, 6 * scale))
        header_bits: list = []
        if data.get("closing_tagline"):
            # A title, not a sentence: no trailing full stop, no underline.
            header_bits.append(Paragraph(
                _strip_title_period(data["closing_tagline"]),
                cl_styles["closing_title"],
            ))
        header_bits.append(Paragraph(
            f"<i>Application — {data['role_title']}, {data['company_name']}</i>",
            cl_styles["application_line"],
        ))
        story.append(KeepTogether(header_bits))

        # Body
        story.append(Paragraph(data["opening_paragraph"], cl_styles["body"]))

        intro_text = (
            "Nøglekompetencer jeg vil bringe til rollen omfatter:" if lang == "DA"
            else "Key strengths I would bring to the role include:"
        )
        story.append(Paragraph(intro_text, cl_styles["intro"]))
        bullet_hex = (
            theme.accent_hex if theme.preset["cl_bullet_accent"] else "#000000"
        )
        for strength in data["key_strengths"]:
            story.append(_cl_bullet(strength, cl_styles["bullet"], bullet_hex))

        # Themes
        for heading, paragraph in data["themes"]:
            story.append(KeepTogether([
                Paragraph(heading, cl_styles["theme_head"]),
                Paragraph(paragraph, cl_styles["theme_para"]),
            ]))

        # Sign-off
        signoff = data.get("signoff",
                           "De bedste hilsner," if lang == "DA" else "Best regards,")
        story.append(Paragraph(signoff, cl_styles["signoff"]))
        story.append(Paragraph(profile.name.title(), cl_styles["signoff_name"]))
        return story

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # One-page fit: render at full size, and if it overflows onto a second page
    # shrink fonts/spacing a notch and re-render until it fits (or we hit the
    # readability floor). The cover letter is always a single page.
    for scale in (1.0, 0.96, 0.92, 0.88, 0.84, 0.80):
        doc = SimpleDocTemplate(
            str(output_path), pagesize=A4,
            leftMargin=1.7 * cm, rightMargin=1.7 * cm,
            topMargin=1.5 * cm, bottomMargin=1.4 * cm,
            title=f"{profile.name.title()} — Cover Letter",
            author=profile.name.title(),
        )
        doc.build(_story(scale))
        if doc.page <= 1:
            break
    return output_path
