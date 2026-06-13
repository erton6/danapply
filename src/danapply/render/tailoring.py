"""Tailoring orchestration: scored Job + Profile (+ Claude prose) → PDFs.

Sits between the scorer / memory layer (which produce ``Job`` records) and
the canonical template (which renders the PDFs). Encodes the per-job
tailoring decisions documented in ``workflows/tailor.md``:

  - Tagline picked from a canonical library based on the role's character
    (research-heavy / strategy / content / default)
  - Skills bucket order reordered for the role
  - Summary, cover-letter opener, four strengths bullets, and three themes
    written by **Claude Code in-conversation** (voice-matched, Danish-mode,
    grounded in cv_content.md) and passed in via ``content`` — with a
    templated default when no content is supplied
  - Notes markdown documents every tailoring decision for the audit trail
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from danapply.config import Profile
from danapply.extract.register import apply_register
from danapply.extract.voice import VoiceProfile, load_voice_profile
from danapply.models import Job
from danapply.render.templates import canonical

# ---------------------------------------------------------------------------
# Per-job tailoring decisions
#
# Taglines are PER-USER, PER-JOB content: the headline tagline defaults to
# the user's ``profile.tagline_default`` and the closing tagline to none.
# Claude Code writes job-specific ones via the ``--content`` payload
# (``tagline`` / ``closing_tagline`` fields) — there is no baked-in tagline
# library, because any library is somebody else's CV.
# ---------------------------------------------------------------------------
TaglineKey = Literal["research", "strategy", "content", "default"]

# Skills bucket order presets per role character.
# Reuses the keys understood by the canonical CV template's _skills_block.
SKILLS_ORDER_PRESETS: dict[TaglineKey, list[str]] = {
    "research":  ["research", "commercial", "stakeholder"],
    "strategy":  ["research", "stakeholder", "commercial"],
    "content":   ["stakeholder", "commercial", "research"],
    "default":   ["research", "commercial", "stakeholder"],
}


def detect_role_character(job: Job) -> TaglineKey:
    """Inspect the job title + description to pick a tagline category.

    Cheap heuristic. The CLI ``--tagline-override`` (future) lets users
    short-circuit this when needed.
    """
    haystack = ((job.title or "") + " " + (job.description_raw or "")[:2000]).lower()

    research_signals = ("research", "insights", "data analysis", "analytical",
                        "investigation", "intelligence", "market analyst")
    strategy_signals = ("strategy", "consulting", "advisory", "transformation",
                        "due diligence", "consultant")
    content_signals = ("content", "communications", "storytelling",
                       "thought leadership", "editorial", "copywriting")

    research_hits = sum(1 for s in research_signals if s in haystack)
    strategy_hits = sum(1 for s in strategy_signals if s in haystack)
    content_hits = sum(1 for s in content_signals if s in haystack)

    top = max(research_hits, strategy_hits, content_hits)
    if top == 0:
        return "default"
    if research_hits == top:
        return "research"
    if strategy_hits == top:
        return "strategy"
    return "content"


# ---------------------------------------------------------------------------
# Templated summary + cover letter content — the fallback when no
# Claude-written ``--content`` is supplied. Every sentence is built strictly
# from profile.yaml facts (user_skills, languages, experience); the template
# never invents employers, degrees, or achievements.
# ---------------------------------------------------------------------------
def build_summary(job: Job, profile: Profile, language: str) -> str:
    """Build the templated CV summary paragraph from profile.yaml facts only.

    The real flow is Claude-written prose via ``--content`` — this fallback
    exists so batch runs and smoke tests produce something honest.
    """
    character = detect_role_character(job)
    facet_phrase = {
        "research":  "research and analytical methods",
        "strategy":  "strategy consulting and stakeholder advisory work",
        "content":   "narrative development and stakeholder communication",
        "default":   "evidence-based analysis and stakeholder communication",
    }[character]
    facet_phrase_da = {
        "research":  "research og analytiske metoder",
        "strategy":  "strategisk rådgivning og interessentarbejde",
        "content":   "formidling og interessentkommunikation",
        "default":   "evidensbaseret analyse og interessentkommunikation",
    }[character]

    tools = ", ".join(profile.user_skills.tools[:5])
    methods = ", ".join(profile.user_skills.methods[:3])
    latest = profile.experience[0] if profile.experience else None

    if language == "DA":
        parts = []
        if latest:
            parts.append(
                f"Senest {latest.role} hos {latest.company} ({latest.dates})."
            )
        if tools:
            parts.append(f"Arbejder med {tools}.")
        if methods:
            parts.append(f"Metodeerfaring inden for {methods}.")
        parts.append(f"Et relevant fundament for {facet_phrase_da}.")
        return " ".join(parts)

    parts = []
    if latest:
        parts.append(
            f"Most recently {latest.role} at {latest.company} ({latest.dates})."
        )
    if tools:
        parts.append(f"Works hands-on with {tools}.")
    if methods:
        parts.append(f"Method experience spans {methods}.")
    parts.append(f"A relevant foundation for {facet_phrase}.")
    return " ".join(parts)


def build_cover_letter_data(
    job: Job, profile: Profile, language: str,
) -> dict:
    """Build the templated cover-letter data dict from profile.yaml facts only.

    The opening and theme headings are generic framing (opinion, not claims);
    every factual statement comes from ``profile.user_skills``,
    ``profile.languages``, or ``profile.experience``. The real flow is
    Claude-written prose via ``--content`` — which also carries the per-job
    ``tagline`` / ``closing_tagline``. The fallback uses the user's own
    default tagline and no closing tagline.
    """
    tagline = profile.tagline_default
    closing = ""

    company = job.company or "your company"
    role = job.title or "this role"

    s = profile.user_skills
    tools = ", ".join(s.tools[:5])
    methods = ", ".join(s.methods[:4])
    soft = ", ".join(s.soft_skills[:4])
    langs = "; ".join(f"{lan.name} ({lan.level})" for lan in profile.languages[:3])
    latest = profile.experience[0] if profile.experience else None

    if language == "DA":
        opening = (
            f"Efter min opfattelse er den største barriere for at realisere "
            f"potentialet i digitalisering og organisatoriske initiativer ofte "
            f"ikke mangel på idéer, men vanskeligheden ved at oversætte "
            f"komplekse systemer og data til overbevisende fortællinger. "
            f"Dette er kerneopgaven i den {role}-rolle, jeg søger hos {company}."
        )
        strengths = []
        if tools:
            strengths.append(f"Kvantitativ analyse med {tools}.")
        if methods:
            strengths.append(f"Metodeerfaring: {methods}.")
        if soft:
            strengths.append(f"Samarbejds- og formidlingskompetencer: {soft}.")
        if langs:
            strengths.append(f"Professionel kommunikation på {langs}.")
        if not strengths:
            strengths = [
                "(Ingen user_skills i profile.yaml endnu — kør onboarding, "
                "eller bed Claude Code om at skræddersy dette brev.)"
            ]
        themes = [
            (
                "Omsætter kompleks analyse til klare fortællinger",
                (f"Jeg arbejder med {tools or 'analyse'} for at omsætte data til "
                 f"anbefalinger, beslutningstagere kan handle på"
                 + (f" — senest som {latest.role} hos {latest.company}" if latest else "")
                 + f". Det vil jeg bringe til {company}."),
            ),
            (
                "Samler forskellige interessenter omkring fælles beslutninger",
                (f"Mine kompetencer inden for {soft or 'kommunikation'} bruger jeg "
                 f"til at samle bidragydere med forskellige prioriteter omkring "
                 f"fælles beslutninger."),
            ),
            (
                "Nysgerrighed, struktur og motivation for reel effekt",
                (f"Jeg ser frem til at bidrage med disse egenskaber til {company} "
                 f"og diskutere, hvordan min baggrund passer til jeres "
                 f"{role}-arbejde."),
            ),
        ]
    else:
        opening = (
            f"In my view, the greatest barrier to realising the potential of "
            f"digitalisation and organisational initiatives is rarely a lack of "
            f"ideas — it is the difficulty of translating complex systems and "
            f"data into compelling narratives that mobilise people to act. "
            f"That is the work at the heart of the {role} position, and the "
            f"reason I am applying to {company}."
        )
        strengths = []
        if tools:
            strengths.append(f"Quantitative analysis using {tools}.")
        if methods:
            strengths.append(f"Method experience: {methods}.")
        if soft:
            strengths.append(f"Collaboration and communication: {soft}.")
        if langs:
            strengths.append(f"Professional communication in {langs}.")
        if not strengths:
            strengths = [
                "(No user_skills in profile.yaml yet — run onboarding, or ask "
                "Claude Code to tailor this letter.)"
            ]
        themes = [
            (
                "Translating complex analysis into clear narratives",
                (f"I work with {tools or 'analysis'} to turn data into "
                 f"recommendations decision-makers can act on"
                 + (f" — most recently as {latest.role} at {latest.company}" if latest else "")
                 + f". I would bring this to {company}."),
            ),
            (
                "Bringing diverse stakeholders together",
                (f"I use my {soft or 'communication'} skills to align "
                 f"contributors with different priorities around shared "
                 f"decisions."),
            ),
            (
                "Curiosity, structure, and motivation to drive real-world impact",
                (f"I would welcome the opportunity to contribute these "
                 f"qualities to {company} and to discuss how my background "
                 f"aligns with your {role} work."),
            ),
        ]

    return {
        "tagline": tagline,
        "closing_tagline": closing,
        "role_title": role,
        "company_name": company,
        "opening_paragraph": opening,
        "key_strengths": strengths,
        "themes": themes,
        "lang": language,
    }


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------
@dataclass
class TailorResult:
    job_id: str
    cv_path: Path
    cover_letter_path: Path
    notes_path: Path
    tagline_key: TaglineKey
    skills_order: list[str]
    language: str
    voice_applied: bool = False
    register_applied: bool = False
    register_score: float = 0.0
    generation_method: Literal["claude", "templated"] = "templated"
    """``claude`` when Claude Code wrote the summary + cover letter prose
    in-conversation and passed it via ``content``; ``templated`` when the
    static defaults were used."""


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def validate_tailor_content(content: dict) -> dict:
    """Validate a Claude-written tailor payload.

    Expected shape (see ``workflows/tailor.md`` for writing instructions):

    .. code-block:: json

        {
          "summary":           "CV summary paragraph, 60-100 words",
          "opening_paragraph": "cover letter opening, 80-130 words",
          "key_strengths":     ["four strength statements"],
          "themes":            [{"heading": "...", "paragraph": "..."}]
        }

    ``themes`` must have exactly 3 entries; ``key_strengths`` exactly 4.
    Two optional fields carry the per-job taglines: ``tagline`` (headline
    under the name, CV + cover letter) and ``closing_tagline`` (under the
    cover-letter signature). When omitted, the headline falls back to
    ``profile.tagline_default`` and the closing tagline is left out.

    Returns a normalised dict (themes as ``(heading, paragraph)`` tuples).
    Raises ``ValueError`` with a readable message — the CLI surfaces it so
    Claude can fix the JSON and retry.
    """
    if not isinstance(content, dict):
        raise ValueError(f"Tailor content must be a JSON object, got {type(content).__name__}.")

    summary = content.get("summary")
    if not (isinstance(summary, str) and summary.strip()):
        raise ValueError("'summary' must be a non-empty string.")

    opening = content.get("opening_paragraph")
    if not (isinstance(opening, str) and opening.strip()):
        raise ValueError("'opening_paragraph' must be a non-empty string.")

    strengths = content.get("key_strengths")
    if not (isinstance(strengths, list) and len(strengths) == 4):
        raise ValueError("'key_strengths' must be a list of exactly 4 strings.")
    strengths = [str(s).strip() for s in strengths]
    if not all(strengths):
        raise ValueError("'key_strengths' entries must be non-empty strings.")

    themes_raw = content.get("themes")
    if not (isinstance(themes_raw, list) and len(themes_raw) == 3):
        raise ValueError("'themes' must be a list of exactly 3 objects.")
    themes: list[tuple[str, str]] = []
    for i, t in enumerate(themes_raw):
        if isinstance(t, dict):
            heading, paragraph = t.get("heading"), t.get("paragraph")
        elif isinstance(t, (list, tuple)) and len(t) == 2:
            heading, paragraph = t
        else:
            raise ValueError(
                f"'themes[{i}]' must be an object with 'heading' and 'paragraph'."
            )
        if not (isinstance(heading, str) and heading.strip()
                and isinstance(paragraph, str) and paragraph.strip()):
            raise ValueError(
                f"'themes[{i}]' needs non-empty string 'heading' and 'paragraph'."
            )
        themes.append((heading.strip(), paragraph.strip()))

    tagline = content.get("tagline")
    if tagline is not None and not (isinstance(tagline, str) and tagline.strip()):
        raise ValueError("'tagline' must be a non-empty string when provided.")
    closing_tagline = content.get("closing_tagline")
    if closing_tagline is not None and not (
        isinstance(closing_tagline, str) and closing_tagline.strip()
    ):
        raise ValueError("'closing_tagline' must be a non-empty string when provided.")

    return {
        "summary": summary.strip(),
        "opening_paragraph": opening.strip(),
        "key_strengths": strengths,
        "themes": themes,
        "tagline": tagline.strip() if tagline else None,
        "closing_tagline": closing_tagline.strip() if closing_tagline else None,
    }


def validate_letter_content(content: dict) -> dict:
    """Validate a Claude-written payload for a **standalone** cover letter
    (``danapply render-letter``) — a letter with no Job record behind it,
    e.g. the first letter written during onboarding.

    Same shape as ``validate_tailor_content`` minus the CV ``summary``,
    plus ``role_title`` and ``company_name`` carried in the payload itself
    (since there is no job to take them from).
    """
    if not isinstance(content, dict):
        raise ValueError(f"Letter content must be a JSON object, got {type(content).__name__}.")

    full = dict(content)
    full.setdefault("summary", "(unused)")
    validated = validate_tailor_content(full)
    validated.pop("summary", None)

    role_title = content.get("role_title")
    company_name = content.get("company_name")
    if not (isinstance(role_title, str) and role_title.strip()):
        raise ValueError(
            "'role_title' must be a non-empty string (no job record to take it from)."
        )
    if not (isinstance(company_name, str) and company_name.strip()):
        raise ValueError(
            "'company_name' must be a non-empty string (no job record to take it from)."
        )

    validated["role_title"] = role_title.strip()
    validated["company_name"] = company_name.strip()
    return validated


def tailor_job(
    job: Job,
    profile: Profile,
    output_dir_cv: Path,
    output_dir_cl: Path,
    rank: int | None = None,
    language: str | None = None,
    voice_profile_dir: Path | None = None,
    apply_dk_register: bool = True,
    content: dict | None = None,
) -> TailorResult:
    """Generate CV PDF + cover letter PDF + notes markdown for one job.

    Args:
        job: The scored Job to tailor for. Must have ``job_id`` set.
        profile: The user's profile.
        output_dir_cv: Where to write the CV PDF.
        output_dir_cl: Where to write the cover letter PDF and notes md.
        rank: Optional rank prefix for filenames (e.g. ``01_…``).
        language: ``"EN"`` or ``"DA"``. Defaults to the job's posting language.
        voice_profile_dir: Where to look for ``voice_profile.yaml``.
            Defaults to the user's profile directory. Pass an explicit
            value to test alternate voice profiles.
        apply_dk_register: When True (default), runs the Danish-mode
            register filter over the generated summary + cover letter
            body. Set False for international (non-DK) employers. Only
            used on the templated path — Claude-written content already
            followed ``danish_register_guide.md``.
        content: Claude-written prose (see ``validate_tailor_content``).
            When provided, the summary / opening / strengths / themes come
            from Claude Code's in-conversation writing instead of the
            templates. Raises ``ValueError`` if malformed.

    Returns:
        ``TailorResult`` with all the output paths and tailoring decisions.
    """
    job.ensure_job_id()
    lang = language or job.language
    # Templates only know EN and DA; fall back to EN for other postings.
    if lang not in ("EN", "DA"):
        lang = "EN"

    character = detect_role_character(job)
    skills_order = SKILLS_ORDER_PRESETS[character]

    # Load voice profile if available (None if user hasn't captured one)
    voice: VoiceProfile | None = None
    if voice_profile_dir is not None:
        voice = load_voice_profile(voice_profile_dir)

    prefix = f"{rank:02d}_" if rank is not None else ""
    base = f"{prefix}{job.job_id}"

    output_dir_cv.mkdir(parents=True, exist_ok=True)
    output_dir_cl.mkdir(parents=True, exist_ok=True)

    cv_path = output_dir_cv / f"{base}_cv.pdf"
    cover_letter_path = output_dir_cl / f"{base}_cover.pdf"
    notes_path = output_dir_cl / f"{base}_notes.md"

    generation_method: Literal["claude", "templated"] = "templated"
    if content is not None:
        validated = validate_tailor_content(content)
        summary = validated["summary"]
        tagline = validated["tagline"] or profile.tagline_default
        closing_tagline = validated["closing_tagline"] or ""
        cl_data = {
            "tagline": tagline,
            "closing_tagline": closing_tagline,
            "role_title": job.title or "this role",
            "company_name": job.company or "your company",
            "opening_paragraph": validated["opening_paragraph"],
            "key_strengths": validated["key_strengths"],
            "themes": validated["themes"],
            "lang": lang,
        }
        generation_method = "claude"
    else:
        summary = build_summary(job, profile, lang)
        cl_data = build_cover_letter_data(job, profile, lang)
        tagline = cl_data["tagline"]
        closing_tagline = cl_data["closing_tagline"]

    # Danish-mode register filter — templated path only. Claude-written
    # content followed the register guide at writing time; re-running
    # rule-based swaps over it would sandpaper the voice.
    register_applied = False
    register_score = 0.0
    if apply_dk_register and generation_method == "templated":
        summary_result = apply_register(summary, voice_profile=voice)
        summary = summary_result.calibrated
        register_applied = True
        register_score = summary_result.register_score

        # Also calibrate the cover letter opening, themes, and strengths
        cl_data["opening_paragraph"] = apply_register(
            cl_data["opening_paragraph"], voice_profile=voice
        ).calibrated
        cl_data["key_strengths"] = [
            apply_register(s, voice_profile=voice).calibrated
            for s in cl_data["key_strengths"]
        ]
        cl_data["themes"] = [
            (h, apply_register(p, voice_profile=voice).calibrated)
            for h, p in cl_data["themes"]
        ]

    # Build CV
    cv_data = {
        "tagline": tagline,
        "summary": summary,
        "skills_order": skills_order,
    }
    canonical.build_cv_pdf(cv_data, cv_path, profile)

    # Render cover letter PDF with the (possibly register-calibrated) data
    canonical.build_cover_letter_pdf(cl_data, cover_letter_path, profile)

    # Write notes — includes voice + register + generation-method info
    notes_text = _build_notes(
        job, character, skills_order, lang, cv_path, cover_letter_path,
        tagline=tagline, closing_tagline=closing_tagline,
        voice=voice, register_score=register_score,
        generation_method=generation_method,
    )
    notes_path.write_text(notes_text, encoding="utf-8")

    return TailorResult(
        job_id=job.job_id,
        cv_path=cv_path,
        cover_letter_path=cover_letter_path,
        notes_path=notes_path,
        tagline_key=character,
        skills_order=skills_order,
        language=lang,
        voice_applied=(voice is not None),
        register_applied=register_applied,
        register_score=register_score,
        generation_method=generation_method,
    )


def _build_notes(
    job: Job,
    character: TaglineKey,
    skills_order: list[str],
    language: str,
    cv_path: Path,
    cl_path: Path,
    tagline: str = "",
    closing_tagline: str = "",
    voice: VoiceProfile | None = None,
    register_score: float = 0.0,
    generation_method: Literal["claude", "templated"] = "templated",
) -> str:
    """Audit-trail markdown documenting tailoring decisions."""
    score_line = f"Score: {job.score}/100" if job.score else "Score: not computed"
    deadline = job.deadline.isoformat() if job.deadline else "(rolling / unspecified)"

    voice_line = (
        f"- Voice profile: **applied** ({voice.extraction_method}, "
        f"captured {voice.extracted_at})"
        if voice
        else "- Voice profile: not captured. Share a writing sample with "
        "Claude Code to capture your voice (`danapply voice set`)."
    )
    if generation_method == "claude":
        gen_line = (
            "- Generation: **Claude Code (voice-matched, Danish-mode at "
            "writing time)** — no rule-based register filter applied."
        )
    else:
        gen_line = (
            "- Generation: templated defaults. Ask Claude Code to tailor "
            "this job for voice-matched, role-specific prose."
        )
    register_line = (
        f"- Danish-mode register filter: applied (score {register_score:.1f}/10)"
        if register_score > 0
        else "- Danish-mode register filter: not applied"
    )

    parts = [
        f"# {job.title or '(no title)'} — {job.company or '(no company)'}",
        "",
        "## Snapshot",
        f"- {score_line}",
        f"- Posting language: {job.language}",
        f"- Tailored output language: {language}",
        f"- Deadline: {deadline}",
        f"- Source: {job.source}",
        f"- URL: {job.url or '(none)'}",
        "",
        "## Tailoring choices",
        f"- Detected role character: **{character}**",
        f"- Tagline: \"{tagline}\""
        + (" *(profile default — ask Claude Code for a job-specific one)*"
           if generation_method == "templated" else ""),
        f"- Skills order: {' → '.join(s.capitalize() for s in skills_order)}",
        (f"- Closing tagline: \"{closing_tagline}\"" if closing_tagline
         else "- Closing tagline: (none — Claude Code writes one per job)"),
        voice_line,
        gen_line,
        register_line,
        "",
        "## Score breakdown",
    ]
    if job.score_breakdown:
        for key in ("role_fit", "skills_match", "company_fit", "freshness"):
            block = job.score_breakdown.get(key, {})
            parts.append(
                f"- **{key.replace('_', ' ').title()}** "
                f"{block.get('score', '?')}/{block.get('max', '?')} — "
                f"{block.get('rationale', '(no rationale)')}"
            )
    else:
        parts.append("- (No score breakdown available — run `danapply score` first.)")

    parts.extend([
        "",
        "## Files",
        f"- CV: `{cv_path}`",
        f"- Cover letter: `{cl_path}`",
        "",
        "## Notes",
        "- Read the generated cover letter carefully and edit anything that",
        "  doesn't sound like you. The CV is fully driven by your profile.yaml.",
        "",
        f"_Generated: {datetime.now().isoformat(timespec='seconds')}_",
    ])
    return "\n".join(parts) + "\n"
