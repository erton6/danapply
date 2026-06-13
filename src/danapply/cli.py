"""DanApply command-line interface — the mechanical engine under the
DanApply Claude Code plugin.

Claude Code drives these commands via Bash. The engine owns everything
deterministic: parsing, scoring, SQLite memory, PDF rendering, Jobnet
prompt generation, dagpenge math. Claude Code owns everything that needs
judgment: voice analysis (``voice set``), field extraction from images /
messy pastes (``ingest``), cover-letter prose (``tailor --content``),
and interview briefs (``interview-prep --content``).

Every command works standalone too — without Claude, the generation
commands fall back to honest templated output.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

from danapply import __version__, memory, paths
from danapply.config import ConfigLoadError, load_profile, load_targets

app = typer.Typer(
    name="danapply",
    help="DanApply — job-application co-pilot for the Danish job market.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def version() -> None:
    """Print the installed DanApply version."""
    typer.echo(f"DanApply {__version__}")


# ---------------------------------------------------------------------------
# Status — one screen: profile, pipeline, recent activity, dagpenge
# ---------------------------------------------------------------------------
@app.command(name="status")
def status_cmd() -> None:
    """Show where things stand: profile, pipeline counts, recent activity."""
    data_dir = paths.data_dir()
    typer.echo("")
    typer.echo(f"─── DanApply status ({__version__}) ───")
    typer.echo("")
    typer.echo(f"  Data dir: {data_dir}")

    # Profile
    profile_path = paths.profile_yaml_path()
    if not profile_path.exists():
        typer.echo("  Profile:  none — run onboarding first.")
        typer.echo("")
        return
    try:
        profile = load_profile(profile_path)
        photo_note = ""
        if not (profile.photo_path and Path(profile.photo_path).exists()):
            photo_note = "  (no photo)"
        typer.echo(f"  Profile:  {profile.name}{photo_note}")
    except ConfigLoadError as exc:
        typer.echo(f"  Profile:  INVALID — {exc}")

    voice = paths.voice_profile_yaml_path().exists()
    typer.echo(f"  Voice:    {'captured' if voice else 'not captured'}")

    # Pipeline
    if memory.db_path().exists():
        memory.init_db()
        jobs = memory.list_jobs(limit=10_000)
        by_status: dict[str, int] = {}
        for j in jobs:
            by_status[j.status] = by_status.get(j.status, 0) + 1
        typer.echo("")
        typer.echo(f"  Pipeline: {len(jobs)} job(s)")
        for st, n in sorted(by_status.items(), key=lambda kv: -kv[1]):
            typer.echo(f"    {st:<32} {n}")
        recent = jobs[:5]
        if recent:
            typer.echo("")
            typer.echo("  Most recent:")
            for j in recent:
                score = f"{j.score:>3}" if j.score else "  —"
                typer.echo(f"    {score}  {j.title or '(no title)'} — "
                           f"{j.company or '(no company)'}  [{j.status}]")
    else:
        typer.echo("")
        typer.echo("  Pipeline: empty (no memory.db yet)")

    # Dagpenge one-liner
    from danapply.dagpenge import load_dagpenge_config, weekly_status
    dp = load_dagpenge_config()
    if dp.on_dagpenge:
        ws = weekly_status(config=dp)
        typer.echo("")
        typer.echo(f"  Dagpenge: {ws.logged_count}/{ws.threshold} logged this week, "
                   f"{ws.days_remaining_in_week} day(s) left")
    typer.echo("")


# ---------------------------------------------------------------------------
# Delete — wipe the data directory (profile + memory + generated files)
# ---------------------------------------------------------------------------
@app.command(name="delete")
def delete_cmd(
    force: bool = typer.Option(
        False,
        "--force",
        help="Actually delete. Without it, shows what would be removed.",
    ),
) -> None:
    """Delete ALL DanApply data: profile, memory.db, generated PDFs.

    Removes the entire data directory (default ``~/danapply-data``).
    Irreversible — requires ``--force``.
    """
    import shutil

    data_dir = paths.data_dir()
    if not data_dir.exists():
        typer.echo(f"Nothing to delete — {data_dir} doesn't exist.")
        return

    file_count = sum(1 for p in data_dir.rglob("*") if p.is_file())
    if not force:
        typer.echo(f"This would permanently delete {data_dir}")
        typer.echo(f"  ({file_count} file(s): profile, memory.db, "
                   f"generated CVs and cover letters)")
        typer.echo("")
        typer.echo("Re-run with --force to confirm. There is no undo.")
        raise typer.Exit(code=1)

    shutil.rmtree(data_dir)
    typer.echo(f"Deleted {data_dir} ({file_count} file(s)).")
    typer.echo("Run `danapply init` to start fresh.")


# ---------------------------------------------------------------------------
# Photo — validate + normalise the CV profile photo
# ---------------------------------------------------------------------------
photo_app = typer.Typer(name="photo", help="Manage the CV profile photo.")
app.add_typer(photo_app, name="photo")


@photo_app.command(name="set")
def photo_set_cmd(
    source: Path = typer.Argument(
        ...,
        help="Path to the headshot (JPEG/PNG). Roughly square, face centred, "
             "≥400px on a side gives the best result.",
    ),
) -> None:
    """Centre-crop, resize, and install a headshot as profile/photo.jpeg.

    The CV template circle-crops the photo, so the engine normalises any
    input to a square JPEG at render-optimal resolution. Never upscales —
    a small source is kept at native size and flagged.
    """
    from danapply.render.photo import MIN_SIDE_SHARP, PhotoError, prepare_profile_photo

    dest = paths.profile_dir() / "photo.jpeg"
    try:
        report = prepare_profile_photo(source, dest)
    except PhotoError as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    # Point profile.yaml at the installed photo (line-targeted edit so the
    # user's comments survive).
    import re as _re

    profile_yaml = paths.profile_yaml_path()
    if profile_yaml.exists():
        text = profile_yaml.read_text(encoding="utf-8")
        new_line = 'photo_path: "photo.jpeg"'
        if _re.search(r"(?m)^photo_path:.*$", text):
            text = _re.sub(r"(?m)^photo_path:.*$", new_line, text)
        else:
            text += f"\n{new_line}\n"
        profile_yaml.write_text(text, encoding="utf-8")

    ow, oh = report.original_size
    typer.echo("")
    typer.echo(f"  ✓ {report.dest}")
    if profile_yaml.exists():
        typer.echo("  ✓ profile.yaml photo_path → photo.jpeg")
    typer.echo(f"  Source: {ow}x{oh}  →  saved {report.final_px}x{report.final_px} JPEG")
    if report.too_small_for_print:
        typer.echo("")
        typer.echo(f"  ⚠ The source is small (< {MIN_SIDE_SHARP}px) — it will look "
                   f"soft in print. A larger photo (≥400px square) is recommended.")
    elif report.upscaled_avoided:
        typer.echo("  (kept native resolution — no upscaling)")
    typer.echo("")
    typer.echo("Done. The next rendered CV picks it up automatically.")


@app.command(name="init")
def init_cmd(
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing profile files in the data directory.",
    ),
    example: bool = typer.Option(
        False,
        "--example",
        help="Seed the fictional demo persona instead of a blank profile.",
    ),
) -> None:
    """Create the data directory and seed it with a blank profile.

    Default location: ``~/danapply-data/``. Override with the
    ``DANAPPLY_DATA_DIR`` environment variable.

    By default a blank profile template is created for onboarding to fill in.
    Pass ``--example`` to seed the fictional "Sofia Almeida" demo persona for
    trying the renderer.

    Safe to run multiple times. Existing user files are never replaced
    unless --force is passed.
    """
    from danapply.scaffolding.init_data_dir import init_data_dir

    typer.echo(f"Scaffolding data directory at: {paths.data_dir()}")
    if example:
        typer.echo("--example: seeding the fictional demo persona.")
    if force:
        typer.echo("--force: existing profile files will be overwritten.")
    typer.echo("")

    report = init_data_dir(force=force, example=example)

    created = sum(1 for s in report.values() if s == "created")
    exists = sum(1 for s in report.values() if s == "exists")
    overwritten = sum(1 for s in report.values() if s == "overwritten")

    for path, status in sorted(report.items()):
        symbol = {
            "created": "+",
            "exists": " ",
            "overwritten": "~",
        }[status]
        typer.echo(f"  {symbol} {path}")

    typer.echo("")
    typer.echo(
        f"Done. Created {created}, kept {exists}"
        + (f", overwrote {overwritten}." if overwritten else ".")
    )
    typer.echo("")
    typer.echo("Next steps:")
    if example:
        typer.echo("  1. Run `danapply render-sample` to generate a sample CV + cover letter.")
        typer.echo(f"  2. Inspect {paths.profile_yaml_path()} to see the profile shape.")
    else:
        typer.echo("  1. Run `danapply onboard` to build your profile from an interview.")
        typer.echo(f"  2. Or edit {paths.profile_yaml_path()} directly to make it yours.")
        typer.echo("  3. Add your photo with `danapply photo set <path>` "
                   "(most DK CVs include one).")


@app.command(name="render-sample")
def render_sample_cmd(
    output_dir: Path = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Where to write the sample PDFs. Defaults to ~/danapply-data/resume_drafts/.",
    ),
    tagline: str = typer.Option(
        None,
        "--tagline",
        help="Override the tagline for this sample (defaults to profile's tagline_default).",
    ),
) -> None:
    """Generate a sample CV + cover letter from the user's profile.

    Smoke test for the renderer: confirms the profile loads, the photo is
    found, the LinkedIn link is embedded, and the PDF generation works
    end-to-end. Produces ``sample_cv.pdf`` and ``sample_cover.pdf``.
    """
    from danapply.render.templates import canonical

    # Load the profile
    profile_path = paths.profile_yaml_path()
    typer.echo(f"Loading profile from: {profile_path}")
    try:
        profile = load_profile(profile_path)
    except ConfigLoadError as exc:
        typer.echo(f"\nERROR: {exc}", err=True)
        typer.echo("\nDid you run `danapply init` first?", err=True)
        raise typer.Exit(code=1) from exc

    # Use either user override, the profile default, or a built-in fallback
    chosen_tagline = tagline or profile.tagline_default

    # Sample content is explicit placeholder text — career facts come only
    # from the loaded profile (experience, education, user_skills).
    sample_summary = (
        "This is a sample summary generated by `danapply render-sample` to "
        "smoke-test the renderer. Experience, education, skills, languages, "
        "and references below come from your profile.yaml; in a real run the "
        "summary is written by Claude Code and passed via `danapply tailor "
        "--content`."
    )

    sample_cv_data = {
        "tagline": chosen_tagline,
        "summary": sample_summary,
        "skills_order": ["stakeholder", "commercial", "research"],
    }

    sample_cl_data = {
        "tagline": chosen_tagline,
        "closing_tagline": "Sample Closing Tagline — Sits Under the Signature.",
        "role_title": "Sample Role",
        "company_name": "Sample Company",
        "opening_paragraph": (
            "This is a sample cover letter generated by `danapply render-sample`. "
            "It exists to confirm that the renderer is working end-to-end: profile loads, "
            "photo embeds (if configured), LinkedIn link renders, and the one-page "
            "structure builds correctly. Real letters are written by Claude Code and "
            "passed via `danapply tailor --content`."
        ),
        "key_strengths": [
            "Sample strength bullet 1 — real bullets are grounded in your profile.",
            "Sample strength bullet 2.",
            "Sample strength bullet 3.",
            "Sample strength bullet 4.",
        ],
        "themes": [
            (
                "Sample theme heading 1",
                "Sample theme paragraph. In a real cover letter this would tie the user's "
                "experience to the specific company and role.",
            ),
            (
                "Sample theme heading 2",
                "Sample theme paragraph. Three theme blocks are the canonical structure.",
            ),
            (
                "Sample theme heading 3",
                "Sample theme paragraph. The closing tagline goes under the signature.",
            ),
        ],
        "lang": "EN",
    }

    # Resolve output paths
    out_dir = output_dir or paths.resume_drafts_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    cv_path = out_dir / "sample_cv.pdf"
    cl_path = out_dir / "sample_cover.pdf"

    typer.echo("Rendering sample CV…")
    canonical.build_cv_pdf(sample_cv_data, cv_path, profile)
    typer.echo(f"  wrote {cv_path}")

    typer.echo("Rendering sample cover letter…")
    canonical.build_cover_letter_pdf(sample_cl_data, cl_path, profile)
    typer.echo(f"  wrote {cl_path}")

    typer.echo("")
    typer.echo("Done. Open the PDFs to confirm:")
    typer.echo("  • Name and contact line render correctly")
    typer.echo("  • LinkedIn link is clickable and embedded")
    typer.echo("  • Photo (if configured) shows top-right with accent ring")
    typer.echo("  • Portfolio URL is clickable")
    typer.echo("  • Languages and references appear at the bottom of the CV")


# ---------------------------------------------------------------------------
# Render base CV — the real base CV from cv_content.md + profile.yaml
# ---------------------------------------------------------------------------
def _extract_cv_summary(text: str) -> str:
    """Pull the prose under ``## Summary`` from cv_content.md.

    Strips HTML comments (the blank scaffold's placeholder hints), so an
    untouched template yields an empty string."""
    import re as _re

    m = _re.search(r"(?ms)^##\s*Summary\s*\n(.*?)(?=^##\s|\Z)", text)
    if not m:
        return ""
    body = _re.sub(r"<!--.*?-->", "", m.group(1), flags=_re.S)
    return " ".join(body.split())


def _cv_page_report(pdf_path: Path) -> tuple[int, str | None]:
    """Page count + a layout hint when the last page is nearly empty.

    The canonical CV is two pages max. A spill of a line or two onto an
    extra page is fixable without touching content: suggest a slightly
    smaller ``cv_font_scale`` (profile.yaml) or trimming one bullet."""
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    n = len(reader.pages)
    hint = None
    if n >= 2:
        last_text = (reader.pages[-1].extract_text() or "").strip()
        if len(last_text) < 200:
            hint = (
                f"page {n} holds only a line or two — offer the user a slightly "
                f"smaller font (cv_font_scale: 0.95 in profile.yaml) or trimming "
                f"one bullet, then re-render."
            )
    if n > 2:
        hint = (
            f"CV runs to {n} pages (two is the DK norm) — trim content or lower "
            f"cv_font_scale in profile.yaml."
        )
    return n, hint


def _validate_style_opt(style: str | None) -> None:
    from danapply.config import CV_STYLES

    if style is not None and style not in CV_STYLES:
        typer.echo(
            f"ERROR: --style must be one of {', '.join(CV_STYLES)} — got {style!r}.",
            err=True,
        )
        raise typer.Exit(code=2)


@app.command(name="render-base")
def render_base_cmd(
    output_dir: Path = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Where to write the PDF. Defaults to ~/danapply-data/resume_drafts/.",
    ),
    tagline: str = typer.Option(
        None,
        "--tagline",
        help="Override the tagline (defaults to profile's tagline_default).",
    ),
    style: str = typer.Option(
        None,
        "--style",
        help="Visual preset: classic | minimal | modern | creative. "
             "Defaults to profile.yaml's cv_style.",
    ),
) -> None:
    """Render the user's base CV from their REAL content.

    The summary comes from ``cv_content.md`` (the ``## Summary`` section the
    CV session wrote); everything else from profile.yaml. Use this — not
    ``render-sample`` — when the user wants their actual CV. Produces
    ``base_cv.pdf``.
    """
    from danapply.render.templates import canonical

    _validate_style_opt(style)

    profile_path = paths.profile_yaml_path()
    try:
        profile = load_profile(profile_path)
    except ConfigLoadError as exc:
        typer.echo(f"\nERROR: {exc}", err=True)
        typer.echo("\nDid you run `danapply init` first?", err=True)
        raise typer.Exit(code=1) from exc

    cv_content_file = paths.cv_content_path()
    summary = ""
    if cv_content_file.exists():
        summary = _extract_cv_summary(cv_content_file.read_text(encoding="utf-8"))
    if not summary:
        typer.echo(
            "ERROR: no summary found in cv_content.md (## Summary section is "
            "missing or empty).\n"
            "Write the summary first — the CV session (workflows/cv_session.md) "
            "drafts it with the user — then re-run `danapply render-base`.",
            err=True,
        )
        raise typer.Exit(code=1)

    data = {
        "tagline": tagline or profile.tagline_default,
        "summary": summary,
        "skills_order": ["research", "commercial", "stakeholder"],
    }

    out_dir = output_dir or paths.resume_drafts_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    cv_path = out_dir / "base_cv.pdf"

    typer.echo("Rendering base CV…")
    canonical.build_cv_pdf(data, cv_path, profile, style=style)
    style_used = style or profile.cv_style
    pages, page_hint = _cv_page_report(cv_path)
    typer.echo(
        f"  wrote {cv_path}  "
        f"[style: {style_used} · accent: {profile.accent_color} · {pages} page(s)]"
    )
    if page_hint:
        typer.echo(f"  ⚠ {page_hint}")
    if not (profile.photo_path and Path(profile.photo_path).exists()):
        typer.echo("")
        typer.echo("  ⚠ No profile photo — most DK CVs include one. Ask the user "
                   "for a headshot and run `danapply photo set <path>` (or confirm "
                   "they want a text-only header).")


# ---------------------------------------------------------------------------
# Render standalone cover letter — a letter with no Job record behind it
# ---------------------------------------------------------------------------
@app.command(name="render-letter")
def render_letter_cmd(
    content: Path = typer.Argument(
        ...,
        help="JSON payload with the Claude-written letter prose: role_title, "
             "company_name, opening_paragraph, key_strengths (4), themes (3), "
             "optional tagline / closing_tagline / signoff.",
    ),
    language: str = typer.Option(
        "EN", "--language", "-l", help="EN or DA.",
    ),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Explicit output PDF path. Defaults to "
             "~/danapply-data/cover_letters/<company>_<role>_cover.pdf.",
    ),
    style: str = typer.Option(
        None,
        "--style",
        help="Visual preset: classic | minimal | modern | creative. Defaults to "
             "profile.yaml's cover_letter_style (which falls back to cv_style).",
    ),
) -> None:
    """Render a cover-letter PDF that has no parsed job behind it.

    `danapply tailor` needs a job in memory.db; this command doesn't — use it
    for the first letter written during onboarding, speculative applications,
    or any letter drafted outside the pipeline. The letter must always ship
    as a PDF, never just markdown.
    """
    from slugify import slugify

    from danapply.render.tailoring import validate_letter_content
    from danapply.render.templates import canonical

    _validate_style_opt(style)
    lang = language.upper()
    if lang not in ("EN", "DA"):
        typer.echo(f"ERROR: --language must be EN or DA, got {language!r}.", err=True)
        raise typer.Exit(code=2)

    profile_path = paths.profile_yaml_path()
    try:
        profile = load_profile(profile_path)
    except ConfigLoadError as exc:
        typer.echo(f"\nERROR: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    payload = _read_json_payload(content)
    try:
        validated = validate_letter_content(payload)  # type: ignore[arg-type]
    except ValueError as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    cl_data = {
        "tagline": validated["tagline"] or profile.tagline_default,
        "closing_tagline": validated["closing_tagline"] or "",
        "role_title": validated["role_title"],
        "company_name": validated["company_name"],
        "opening_paragraph": validated["opening_paragraph"],
        "key_strengths": validated["key_strengths"],
        "themes": validated["themes"],
        "lang": lang,
    }
    if isinstance(payload, dict) and payload.get("signoff"):
        cl_data["signoff"] = payload["signoff"]

    if output is None:
        slug = slugify(
            f"{validated['company_name']} {validated['role_title']}",
            separator="_",
        ) or "letter"
        output = paths.cover_letters_dir() / f"{slug}_cover.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)

    typer.echo("Rendering cover letter…")
    canonical.build_cover_letter_pdf(cl_data, output, profile, style=style)
    style_used = style or profile.cover_letter_style or profile.cv_style
    typer.echo(f"  wrote {output}  [style: {style_used} · {lang}]")


# ---------------------------------------------------------------------------
# DB init
# ---------------------------------------------------------------------------
db_app = typer.Typer(name="db", help="Database management.")
app.add_typer(db_app, name="db")


@db_app.command(name="init")
def db_init_cmd() -> None:
    """Initialise the SQLite memory database. Idempotent."""
    db_path = memory.init_db()
    version = memory.schema_version()
    typer.echo(f"Database ready at: {db_path}")
    typer.echo(f"Schema version: {version}")


@db_app.command(name="status")
def db_status_cmd() -> None:
    """Show database state — version, job count, recent jobs."""
    version = memory.schema_version()
    if version is None:
        typer.echo("Database not initialised yet. Run `danapply db init`.")
        raise typer.Exit(code=1)
    count = memory.count_jobs()
    typer.echo(f"Database: {memory.db_path()}")
    typer.echo(f"Schema version: {version}")
    typer.echo(f"Applications: {count}")


# ---------------------------------------------------------------------------
# Parse — turn input into Job records
# ---------------------------------------------------------------------------
@app.command(name="parse")
def parse_cmd(
    batch: Path = typer.Option(
        None,
        "--batch",
        "-b",
        help="Parse every supported file in this directory.",
    ),
    file: Path = typer.Option(
        None,
        "--file",
        "-f",
        help="Parse a single file (PDF / TXT / MD / EML).",
    ),
    paste: str = typer.Option(
        None,
        "--paste",
        "-p",
        help="Parse a free-text paste as a single job posting.",
    ),
    persist: bool = typer.Option(
        True,
        "--persist/--no-persist",
        help="Upsert results into memory.db (default: yes).",
    ),
    output_json: bool = typer.Option(
        False,
        "--json",
        help="Emit machine-readable JSON instead of a human table.",
    ),
) -> None:
    """Parse job postings into ``Job`` records (heuristic extraction).

    Exactly one of ``--batch``, ``--file``, ``--paste`` must be provided.
    Results are persisted to ``memory.db`` by default.

    DanApply never fetches websites. Postings arrive as pasted text or as
    files (PDF / TXT / MD / EML) dropped into a directory. For screenshots,
    messy pastes, or low-confidence parses, Claude Code extracts the fields
    in-conversation and stores them via ``danapply ingest`` instead.
    """
    from danapply import parse as parser_pkg

    modes = [m is not None for m in (batch, file, paste)]
    if sum(modes) != 1:
        typer.echo(
            "ERROR: Provide exactly one of --batch, --file, or --paste.",
            err=True,
        )
        raise typer.Exit(code=2)

    if persist:
        memory.init_db()

    jobs = []
    failures: list[str] = []

    if batch is not None:
        d = batch.expanduser().resolve()
        if not d.is_dir():
            typer.echo(f"ERROR: --batch path is not a directory: {d}", err=True)
            raise typer.Exit(code=2)
        for entry in sorted(d.iterdir()):
            if not entry.is_file() or entry.name.startswith("."):
                continue
            try:
                jobs.append(parser_pkg.parse_file(entry))
            except (ValueError, FileNotFoundError) as exc:
                failures.append(f"{entry.name}: {exc}")
    elif file is not None:
        try:
            jobs.append(parser_pkg.parse_file(file))
        except (ValueError, FileNotFoundError) as exc:
            typer.echo(f"ERROR: {exc}", err=True)
            raise typer.Exit(code=1) from exc
    elif paste is not None:
        jobs.append(parser_pkg.parse_paste(paste))

    new_count = 0
    if persist:
        persisted_jobs = []
        for j in jobs:
            saved, is_new = memory.upsert_job(j)
            persisted_jobs.append(saved)
            if is_new:
                new_count += 1
        jobs = persisted_jobs

    if output_json:
        out = {
            "parsed": len(jobs),
            "new_to_db": new_count if persist else None,
            "failures": failures,
            "jobs": [json.loads(j.model_dump_json()) for j in jobs],
        }
        json.dump(out, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
        return

    # Pretty table output
    if not jobs and not failures:
        typer.echo("Nothing parsed.")
        return

    typer.echo("")
    typer.echo(f"Parsed {len(jobs)} job(s)" + (
        f" — {new_count} new to memory." if persist else "."
    ))
    typer.echo("")
    for j in jobs:
        title = j.title or "(no title)"
        company = j.company or "(no company)"
        loc = j.location or ""
        conf_marker = {"high": "✓", "medium": "·", "low": "?"}[j.data_confidence]
        typer.echo(f"  {conf_marker}  {title}  —  {company}  {loc}")
        typer.echo(f"     job_id={j.job_id}  source={j.source}  lang={j.language}")
    if failures:
        typer.echo("")
        typer.echo(f"⚠️  {len(failures)} failure(s):")
        for f in failures:
            typer.echo(f"     {f}")
    typer.echo("")


# ---------------------------------------------------------------------------
# Ingest — store Claude-extracted Job records
# ---------------------------------------------------------------------------
def _read_json_payload(path: Path) -> object:
    """Read a JSON payload from a file, or stdin when path is ``-``.

    Exits with a readable error on malformed JSON so Claude can fix it.
    """
    try:
        raw = sys.stdin.read() if str(path) == "-" else path.read_text(encoding="utf-8")
    except OSError as exc:
        typer.echo(f"ERROR: Cannot read {path}: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        typer.echo(f"ERROR: Invalid JSON in {path}: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@app.command(name="ingest")
def ingest_cmd(
    payload: Path = typer.Argument(
        ...,
        help="Path to a JSON file holding one Job object or a list of Job "
             "objects. Pass '-' to read from stdin.",
    ),
    output_json: bool = typer.Option(
        False,
        "--json",
        help="Emit machine-readable JSON.",
    ),
) -> None:
    """Store Claude-extracted Job records in memory.db.

    This is the companion to ``parse``: where ``parse`` extracts fields
    heuristically, ``ingest`` accepts records that Claude Code extracted
    in-conversation — from screenshots, messy pastes, or postings whose
    heuristic parse came back medium/low confidence.

    Field semantics match the ``Job`` model (title, company, location,
    posting_date / deadline as YYYY-MM-DD, requirements list, language,
    description_raw, source, url). Records are deduped on job_id like
    every other write path.
    """
    from danapply.models import Job

    data = _read_json_payload(payload)
    records = data if isinstance(data, list) else [data]

    memory.init_db()
    stored = []
    new_count = 0
    for i, record in enumerate(records):
        try:
            job = Job.model_validate(record)
        except Exception as exc:
            typer.echo(f"ERROR: Record {i} failed validation: {exc}", err=True)
            raise typer.Exit(code=1) from exc
        job.ensure_job_id()
        saved, is_new = memory.upsert_job(job)
        stored.append(saved)
        if is_new:
            new_count += 1

    if output_json:
        out = {
            "ingested": len(stored),
            "new_to_db": new_count,
            "jobs": [json.loads(j.model_dump_json()) for j in stored],
        }
        json.dump(out, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
        return

    typer.echo("")
    typer.echo(f"Ingested {len(stored)} job(s) — {new_count} new to memory.")
    for j in stored:
        typer.echo(f"  • {j.title or '(no title)'}  —  {j.company or '(no company)'}")
        typer.echo(f"     job_id={j.job_id}")
    typer.echo("")


# ---------------------------------------------------------------------------
# Show — full record of one job (Claude reads this before writing prose)
# ---------------------------------------------------------------------------
@app.command(name="show")
def show_cmd(
    job_id: str = typer.Option(
        ...,
        "--job-id",
        help="Job to show.",
    ),
) -> None:
    """Dump one job's full record as JSON — including description_raw,
    requirements, and the score breakdown. Claude Code reads this before
    writing tailored cover-letter prose or an interview brief."""
    memory.init_db()
    job = memory.get_job(job_id)
    if not job:
        typer.echo(f"ERROR: No job with id={job_id}", err=True)
        raise typer.Exit(code=1)
    json.dump(json.loads(job.model_dump_json()), sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")


# ---------------------------------------------------------------------------
# Score — apply the 0–100 rubric to parsed jobs
# ---------------------------------------------------------------------------
@app.command(name="score")
def score_cmd(
    job_id: str = typer.Option(
        None,
        "--job-id",
        help="Score a single job by id. If omitted, score all jobs in the DB.",
    ),
    against: Path = typer.Option(
        None,
        "--against",
        help="Path to targets.yaml. Defaults to ~/danapply-data/profile/targets.yaml.",
    ),
    top_n: int = typer.Option(
        10,
        "--top-n",
        "-n",
        help="When scoring all jobs, show the top N in the output.",
    ),
    output_json: bool = typer.Option(
        False,
        "--json",
        help="Emit machine-readable JSON.",
    ),
) -> None:
    """Score parsed jobs against the user's targets and persist the result."""
    from danapply.scorer import apply_score, score_job

    targets_path = against or paths.targets_yaml_path()
    try:
        targets = load_targets(targets_path)
    except ConfigLoadError as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    # Profile is optional — used for the user_skills-aware skills matcher.
    # When missing, scorer falls back to the legacy description-text heuristic.
    profile = None
    try:
        profile = load_profile(paths.profile_yaml_path())
    except ConfigLoadError:
        pass

    memory.init_db()

    if job_id:
        job = memory.get_job(job_id)
        if not job:
            typer.echo(f"ERROR: No job with id={job_id}", err=True)
            raise typer.Exit(code=1)
        jobs = [job]
    else:
        jobs = memory.list_jobs(limit=10_000)

    if not jobs:
        typer.echo("No jobs to score. Run `danapply parse ...` first.")
        return

    scored: list = []
    for j in jobs:
        breakdown = score_job(j, targets, profile=profile)
        apply_score(j, breakdown)
        memory.upsert_job(j)
        scored.append((j, breakdown))

    scored.sort(key=lambda pair: -pair[0].score)

    if output_json:
        out = [
            {
                "job_id": j.job_id,
                "score": j.score,
                "title": j.title,
                "company": j.company,
                "breakdown": b.to_dict(),
            }
            for j, b in scored
        ]
        json.dump(out, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
        return

    typer.echo("")
    typer.echo(f"Scored {len(scored)} job(s). Targets: {targets_path}")
    typer.echo("")
    typer.echo(f"{'#':>3}  {'Score':>5}  {'Title':<40}  {'Company':<25}")
    typer.echo("  " + "-" * 80)
    for i, (j, _) in enumerate(scored[:top_n], start=1):
        title = (j.title or "(no title)")[:40]
        company = (j.company or "(no company)")[:25]
        typer.echo(f"{i:>3}  {j.score:>5}  {title:<40}  {company:<25}")
    if len(scored) > top_n:
        typer.echo(f"     … and {len(scored) - top_n} more (use --top-n to see).")
    typer.echo("")


# ---------------------------------------------------------------------------
# List — read-only view of parsed jobs
# ---------------------------------------------------------------------------
@app.command(name="list")
def list_cmd(
    status: str = typer.Option(
        None,
        "--status",
        help="Filter to a specific status (parsed, tailored, applied, etc.).",
    ),
    limit: int = typer.Option(
        25,
        "--limit",
        "-n",
        help="Maximum rows to show.",
    ),
    output_json: bool = typer.Option(
        False,
        "--json",
        help="Emit machine-readable JSON.",
    ),
) -> None:
    """List jobs in memory.db ordered by parsed_at (newest first)."""
    memory.init_db()
    jobs = memory.list_jobs(status=status, limit=limit)

    if output_json:
        json.dump(
            [json.loads(j.model_dump_json()) for j in jobs],
            sys.stdout, indent=2, default=str,
        )
        sys.stdout.write("\n")
        return

    if not jobs:
        typer.echo("No jobs in memory.db. Run `danapply parse ...` first.")
        return

    typer.echo("")
    typer.echo(f"{len(jobs)} job(s):")
    typer.echo("")
    typer.echo(f"{'Score':>5}  {'Status':<15}  {'Title':<35}  {'Company':<22}")
    typer.echo("  " + "-" * 84)
    for j in jobs:
        score_display = str(j.score) if j.score else "—"
        title = (j.title or "(no title)")[:35]
        company = (j.company or "(no company)")[:22]
        typer.echo(f"{score_display:>5}  {j.status:<15}  {title:<35}  {company:<22}")
    typer.echo("")


# ---------------------------------------------------------------------------
# Tailor — generate CV + cover letter + notes for scored jobs
# ---------------------------------------------------------------------------
@app.command(name="tailor")
def tailor_cmd(
    job_id: str = typer.Option(
        None,
        "--job-id",
        help="Tailor a single job by id.",
    ),
    top_n: int = typer.Option(
        None,
        "--top-n",
        "-n",
        help="Tailor the top N scored jobs (sorted by score desc).",
    ),
    all_jobs: bool = typer.Option(
        False,
        "--all",
        help="Tailor every job in memory.db (use with care on large DBs).",
    ),
    language: str = typer.Option(
        None,
        "--language",
        "-l",
        help="Override the output language (EN or DA). Defaults to job's posting language.",
    ),
    content: Path = typer.Option(
        None,
        "--content",
        help="JSON file with Claude-written prose (summary, opening_paragraph, "
             "key_strengths, themes — see workflows/tailor.md). Only valid "
             "with --job-id. Without it, templated defaults are used.",
    ),
    output_json: bool = typer.Option(
        False,
        "--json",
        help="Emit machine-readable JSON.",
    ),
) -> None:
    """Render CV + cover letter + notes for one or more scored jobs.

    Exactly one of ``--job-id``, ``--top-n``, ``--all`` must be provided.
    Output files land in ``~/danapply-data/resume_drafts/`` (CV PDFs)
    and ``~/danapply-data/cover_letters/`` (cover letter PDFs + notes md).

    The real flow is per-job: Claude Code reads the job (``danapply show``),
    the voice profile, and cv_content.md, writes the prose in-conversation,
    and passes it via ``--content``. Batch runs without ``--content`` give
    templated drafts.
    """
    from danapply.render.tailoring import tailor_job

    modes = [bool(job_id), top_n is not None, all_jobs]
    if sum(modes) != 1:
        typer.echo(
            "ERROR: Provide exactly one of --job-id, --top-n, or --all.",
            err=True,
        )
        raise typer.Exit(code=2)

    if language and language not in ("EN", "DA"):
        typer.echo(
            f"ERROR: --language must be EN or DA, got {language!r}.",
            err=True,
        )
        raise typer.Exit(code=2)

    try:
        profile = load_profile(paths.profile_yaml_path())
    except ConfigLoadError as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    content_data: dict | None = None
    if content is not None:
        if not job_id:
            typer.echo("ERROR: --content requires --job-id (one prose payload per job).", err=True)
            raise typer.Exit(code=2)
        data = _read_json_payload(content)
        if not isinstance(data, dict):
            typer.echo("ERROR: --content must hold a JSON object.", err=True)
            raise typer.Exit(code=1)
        content_data = data

    memory.init_db()

    if job_id:
        job = memory.get_job(job_id)
        if not job:
            typer.echo(f"ERROR: No job with id={job_id}", err=True)
            raise typer.Exit(code=1)
        jobs = [job]
    elif top_n is not None:
        if top_n < 1:
            typer.echo("ERROR: --top-n must be >= 1", err=True)
            raise typer.Exit(code=2)
        all_in_db = memory.list_jobs(limit=10_000)
        # Sort by score descending; ties broken by parsed_at (already DESC from list_jobs)
        all_in_db.sort(key=lambda j: -j.score)
        jobs = all_in_db[:top_n]
    else:  # all_jobs
        jobs = memory.list_jobs(limit=10_000)

    if not jobs:
        typer.echo(
            "No jobs to tailor. Run `danapply parse ...` and `danapply score` first."
        )
        return

    cv_dir = paths.resume_drafts_dir()
    cl_dir = paths.cover_letters_dir()

    results: list = []
    for i, j in enumerate(jobs, start=1):
        # Rank prefix only when tailoring a batch (top_n or all)
        rank = i if (top_n is not None or all_jobs) else None
        try:
            result = tailor_job(
                j, profile, output_dir_cv=cv_dir, output_dir_cl=cl_dir,
                rank=rank, language=language,
                voice_profile_dir=paths.profile_dir(),
                apply_dk_register=True,
                content=content_data,
            )
        except ValueError as exc:
            typer.echo(f"ERROR: {exc}", err=True)
            raise typer.Exit(code=1) from exc
        # Advance the lifecycle: a freshly-parsed job becomes "tailored".
        # Later stages (applied / interview / outcome) are never downgraded.
        if j.status == "parsed":
            j.status = "tailored"
            memory.upsert_job(j)
        results.append((j, result))

    if output_json:
        import json as _json
        out = [
            {
                "job_id": r.job_id,
                "title": j.title,
                "company": j.company,
                "score": j.score,
                "tagline_key": r.tagline_key,
                "skills_order": r.skills_order,
                "language": r.language,
                "cv_path": str(r.cv_path),
                "cover_letter_path": str(r.cover_letter_path),
                "notes_path": str(r.notes_path),
                "generation_method": r.generation_method,
            }
            for j, r in results
        ]
        _json.dump(out, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
        return

    typer.echo("")
    typer.echo(f"Tailored {len(results)} job(s):")
    typer.echo("")
    for j, r in results:
        title = (j.title or "(no title)")[:40]
        company = (j.company or "(no company)")[:22]
        voice_marker = "voice✓" if r.voice_applied else "voice—"
        reg_marker = f"reg {r.register_score:.0f}/10" if r.register_applied else "reg—"
        gen_marker = "gen:claude" if r.generation_method == "claude" else "gen:tmpl"
        typer.echo(
            f"  • {title}  —  {company}"
            f"  [{r.tagline_key} · {r.language} · {gen_marker} · {voice_marker} · {reg_marker}]"
        )
        typer.echo(f"     CV:   {r.cv_path}")
        _, page_hint = _cv_page_report(r.cv_path)
        if page_hint:
            typer.echo(f"     ⚠ {page_hint}")
        typer.echo(f"     CL:   {r.cover_letter_path}")
        typer.echo(f"     Notes: {r.notes_path}")
    if not (profile.photo_path and Path(profile.photo_path).exists()):
        typer.echo("")
        typer.echo("  ⚠ No profile photo — most DK CVs include one. "
                   "Add it with `danapply photo set <path>`.")
    typer.echo("")


# ---------------------------------------------------------------------------
# Onboarding — interactive interview to build profile.yaml + targets.yaml
# ---------------------------------------------------------------------------
@app.command(name="onboard")
def onboard_cmd(
    resume: bool = typer.Option(
        False,
        "--resume",
        help="Resume from the last saved chapter (instead of starting over).",
    ),
    reset: bool = typer.Option(
        False,
        "--reset",
        help="Delete any existing onboarding state before starting.",
    ),
) -> None:
    """Run the interactive onboarding interview (standalone terminal use).

    This is the fallback for users running DanApply WITHOUT Claude Code —
    it needs a real TTY for its prompts. Inside Claude Code, onboarding
    happens in-conversation instead (see the skill's
    ``workflows/onboarding.md``); do not invoke this command from there.

    Walks 10 chapters (~30–45 min). State is saved after each chapter so
    Ctrl+C is safe — come back with ``--resume``.

    Writes ``profile.yaml`` + ``targets.yaml`` (+ ``dagpenge.yaml`` if you
    say you're on dagpenge) to ``~/danapply-data/profile/`` at the end.
    """
    from danapply.onboarding import run_onboarding, state_exists

    if reset and state_exists():
        typer.echo("Reset: deleting saved onboarding state.")

    if resume and not state_exists():
        typer.echo("No saved state to resume from — starting fresh.")
        resume = False

    if not resume and state_exists() and not reset:
        typer.echo(
            "Saved onboarding state exists. Use --resume to continue, "
            "or --reset to start over."
        )
        raise typer.Exit(code=1)

    try:
        run_onboarding(resume=resume, reset=reset)
    except KeyboardInterrupt:
        typer.echo("\n(interrupted — resume with `danapply onboard --resume`)")
        raise typer.Exit(code=130) from None


# ---------------------------------------------------------------------------
# Voice — capture / show / clear the user's writing voice
# ---------------------------------------------------------------------------
voice_app = typer.Typer(name="voice", help="Manage the user's voice profile.")
app.add_typer(voice_app, name="voice")


@voice_app.command(name="set")
def voice_set_cmd(
    payload: Path = typer.Argument(
        ...,
        help="Path to a JSON file holding the voice analysis (see "
             "workflows/voice_capture.md for the schema). Pass '-' for stdin.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite an existing voice_profile.yaml.",
    ),
) -> None:
    """Save a Claude-analysed voice profile.

    Claude Code reads the user's writing sample in-conversation, analyses
    it per ``workflows/voice_capture.md``, and hands the structured result
    here. Saves ``voice_profile.yaml`` (source of truth) and
    ``voice_profile.md`` (human-readable companion) into the profile
    directory.
    """
    from danapply.extract.voice import save_voice_profile, voice_profile_from_payload

    yaml_path = paths.voice_profile_yaml_path()
    if yaml_path.exists() and not force:
        typer.echo(
            f"Voice profile already exists at {yaml_path}.\n"
            f"Re-run with --force to overwrite (consider backing it up first)."
        )
        raise typer.Exit(code=1)

    data = _read_json_payload(payload)
    try:
        profile = voice_profile_from_payload(data)
    except ValueError as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    yaml_path, md_path = save_voice_profile(profile, paths.profile_dir())

    typer.echo("")
    typer.echo(f"  ✓ {yaml_path}")
    typer.echo(f"  ✓ {md_path}")
    typer.echo("")
    typer.echo(f"Rhythm: {profile.sentence_rhythm}")
    typer.echo(f"Formality: {profile.formality_register}")
    typer.echo(f"Opening style: {profile.opening_style}")
    if profile.vocabulary_preferences:
        prefs = ", ".join(profile.vocabulary_preferences[:5])
        typer.echo(f"You reach for: {prefs}")
    if profile.vocabulary_avoidances:
        avoid = ", ".join(profile.vocabulary_avoidances[:5])
        typer.echo(f"You avoid: {avoid}")
    typer.echo("")
    typer.echo("Voice captured — tailored cover letters will now match it.")


@voice_app.command(name="show")
def voice_show_cmd() -> None:
    """Display the captured voice profile (or note its absence)."""
    from danapply.extract.voice import load_voice_profile

    voice = load_voice_profile(paths.profile_dir())
    if voice is None:
        typer.echo(
            f"No voice profile at {paths.voice_profile_yaml_path()}.\n"
            f"Capture one with: danapply voice capture <sample-file>"
        )
        raise typer.Exit(code=1)

    typer.echo("")
    typer.echo(f"Voice profile: {paths.voice_profile_yaml_path()}")
    typer.echo(f"Captured: {voice.extracted_at} (method: {voice.extraction_method})")
    typer.echo(f"Sample size: {voice.sample_word_count} words")
    typer.echo("")
    typer.echo(f"Sentence rhythm:   {voice.sentence_rhythm}")
    typer.echo(f"Formality:         {voice.formality_register}")
    typer.echo(f"Opening style:     {voice.opening_style}")
    typer.echo(f"Closing style:     {voice.closing_style}")
    typer.echo(f"Avg sentence len:  {voice.avg_sentence_length_words} words")
    typer.echo(
        f"Register baseline: {voice.superlatives_per_100_words:.2f} superlatives, "
        f"{voice.intensifiers_per_100_words:.2f} intensifiers per 100 words"
    )
    if voice.vocabulary_preferences:
        typer.echo("")
        typer.echo("Vocabulary you reach for:")
        for v in voice.vocabulary_preferences:
            typer.echo(f"  • {v}")
    if voice.vocabulary_avoidances:
        typer.echo("")
        typer.echo("Vocabulary you avoid:")
        for v in voice.vocabulary_avoidances:
            typer.echo(f"  • {v}")
    if voice.characteristic_phrases:
        typer.echo("")
        typer.echo("Characteristic phrases:")
        for p in voice.characteristic_phrases:
            typer.echo(f"  > {p}")
    if voice.notes:
        typer.echo("")
        typer.echo(f"Notes: {voice.notes}")
    typer.echo("")


@voice_app.command(name="clear")
def voice_clear_cmd(
    force: bool = typer.Option(False, "--force", help="Skip confirmation."),
) -> None:
    """Delete the voice profile (returns tailoring to templated defaults)."""
    yaml_path = paths.voice_profile_yaml_path()
    md_path = paths.voice_profile_md_path()

    if not yaml_path.exists() and not md_path.exists():
        typer.echo("No voice profile to clear.")
        return

    if not force:
        typer.echo("This will delete:")
        if yaml_path.exists():
            typer.echo(f"  {yaml_path}")
        if md_path.exists():
            typer.echo(f"  {md_path}")
        typer.echo("")
        typer.echo("Re-run with --force to confirm.")
        raise typer.Exit(code=1)

    for p in (yaml_path, md_path):
        if p.exists():
            p.unlink()
            typer.echo(f"  ✗ removed {p}")


# ---------------------------------------------------------------------------
# Joblog — generate Jobnet Opret-Joblog automation prompt
# ---------------------------------------------------------------------------
@app.command(name="joblog")
def joblog_cmd(
    threshold: int = typer.Option(
        60,
        "--threshold",
        "-t",
        help="Minimum score for auto-inclusion in the prompt.",
    ),
    job_ids: str = typer.Option(
        None,
        "--job-ids",
        help="Comma-separated explicit job IDs (overrides --threshold selection).",
    ),
    mark_logged: bool = typer.Option(
        False,
        "--mark-logged",
        help="Stamp jobnet_logged_at on the given --job-ids and stop — no "
             "prompt file is generated. Use ONLY after you've actually "
             "pasted + saved in Jobnet.",
    ),
) -> None:
    """Generate the Jobnet 'Opret Joblog' prompt for Claude in Chrome.

    Default behaviour: pick all jobs scoring ≥ threshold that haven't been
    logged yet; write to ``joblog_prompts/jobnet_joblog_YYYY-MM-DD.md``.
    The file is never overwritten — supplements are added with
    ``_supplement_N`` suffixes.

    ``--mark-logged --job-ids X,Y`` is the confirmation step after the user
    has saved the entries in Jobnet: it stamps ``jobnet_logged_at``, advances
    early-stage statuses to ``applied``, and generates nothing.
    """
    from danapply.joblog import (
        generate_joblog_prompt,
        pick_jobs_for_joblog,
        resolve_output_path,
    )

    memory.init_db()

    if mark_logged:
        if not job_ids:
            typer.echo(
                "ERROR: --mark-logged requires --job-ids (the jobs you "
                "actually saved in Jobnet).",
                err=True,
            )
            raise typer.Exit(code=2)
        ids = [j.strip() for j in job_ids.split(",") if j.strip()]
        count = memory.mark_jobnet_logged(ids)
        typer.echo(f"Marked {count} job(s) as logged to Jobnet "
                   f"(status → applied).")
        missing = count != len(ids)
        if missing:
            typer.echo(
                f"⚠ {len(ids) - count} id(s) not found in memory.db.",
                err=True,
            )
        return

    if job_ids:
        ids = [j.strip() for j in job_ids.split(",") if j.strip()]
        candidates = [j for j in (memory.get_job(i) for i in ids) if j is not None]
        included, excluded = candidates, []
    else:
        all_jobs = memory.list_jobs(limit=10_000)
        included, excluded = pick_jobs_for_joblog(all_jobs, threshold=threshold)

    if not included:
        typer.echo(f"No jobs to log (threshold {threshold}, "
                   f"{len(excluded)} excluded).")
        if excluded:
            typer.echo("Excluded:")
            for j, reason in excluded[:5]:
                typer.echo(f"  · {j.company or '?'} — {reason}")
        return

    prompt = generate_joblog_prompt(included, excluded=excluded)
    out_path = resolve_output_path()
    out_path.write_text(prompt, encoding="utf-8")

    typer.echo("")
    typer.echo(f"Wrote {len(included)} entries to:")
    typer.echo(f"  {out_path}")
    typer.echo("")
    typer.echo("Open the file, paste into Claude in Chrome on the Jobnet form, "
               "and let Claude fill it out. Then come back and run:")
    typer.echo(f"  danapply joblog --mark-logged --job-ids "
               f"{','.join(j.job_id for j in included)}")


# ---------------------------------------------------------------------------
# Outcome — record an outcome event on an application
# ---------------------------------------------------------------------------
_OUTCOME_STATUSES = (
    "interview_scheduled",
    "interview_completed_advancing",
    "interview_completed_rejected",
    "rejected_pre_interview",
    "ghosted",
    "offer_received",
    "offer_accepted",
    "withdrew",
)


@app.command(name="outcome")
def outcome_cmd(
    job_id: str = typer.Option(
        None,
        "--job-id",
        help="Job to record an outcome on.",
    ),
    status: str = typer.Option(
        None,
        "--status",
        "-s",
        help=f"One of: {', '.join(_OUTCOME_STATUSES)}.",
    ),
    notes: str = typer.Option(
        None,
        "--notes",
        "-n",
        help="Optional free-text notes about the outcome.",
    ),
    list_only: bool = typer.Option(
        False,
        "--list",
        help="List recent outcomes instead of recording a new one.",
    ),
    output_json: bool = typer.Option(
        False,
        "--json",
        help="Emit machine-readable JSON.",
    ),
) -> None:
    """Record or list application outcomes."""
    memory.init_db()

    if list_only:
        outcomes = memory.list_outcomes(limit=50)
        if output_json:
            json.dump(outcomes, sys.stdout, indent=2, default=str)
            sys.stdout.write("\n")
            return
        if not outcomes:
            typer.echo("No outcomes recorded yet.")
            return
        typer.echo("")
        typer.echo(f"{'Job ID':<48}  {'Status':<32}  Recorded")
        typer.echo("  " + "-" * 100)
        for o in outcomes:
            typer.echo(
                f"{o['job_id']:<48}  {o['status']:<32}  {o['recorded_at']}"
            )
        return

    if not job_id or not status:
        typer.echo(
            "ERROR: --job-id and --status are required (unless --list).",
            err=True,
        )
        raise typer.Exit(code=2)

    if status not in _OUTCOME_STATUSES:
        typer.echo(
            f"ERROR: --status must be one of: {', '.join(_OUTCOME_STATUSES)}.",
            err=True,
        )
        raise typer.Exit(code=2)

    job = memory.get_job(job_id)
    if not job:
        typer.echo(f"ERROR: No job with id={job_id}", err=True)
        raise typer.Exit(code=1)

    outcome_id = memory.log_outcome(job_id, status, notes=notes)
    typer.echo(f"Recorded outcome #{outcome_id}: {job.company or '?'} — "
               f"{job.title or '?'} → {status}")


# ---------------------------------------------------------------------------
# Dagpenge — weekly compliance check
# ---------------------------------------------------------------------------
@app.command(name="dagpenge")
def dagpenge_cmd(
    history: bool = typer.Option(
        False,
        "--history",
        help="Show the last 8 weeks of compliance status.",
    ),
    weeks_back: int = typer.Option(
        8,
        "--weeks-back",
        help="When --history is used, how many weeks to show.",
    ),
) -> None:
    """Show dagpenge compliance for this week (or recent history)."""
    from danapply.dagpenge import load_dagpenge_config, weekly_status
    from danapply.dagpenge.tracker import weeks_history

    config = load_dagpenge_config()
    if not config.on_dagpenge:
        typer.echo(
            "dagpenge.yaml says you're not on dagpenge. Nothing to track.\n"
            "Edit ~/danapply-data/profile/dagpenge.yaml if that's wrong."
        )
        return

    if history:
        results = weeks_history(weeks_back=weeks_back, config=config)
        typer.echo("")
        typer.echo(f"Dagpenge compliance, last {weeks_back} weeks "
                   f"(threshold {config.weekly_threshold}/week):")
        typer.echo("")
        for r in results:
            typer.echo(f"  {r.summary_line()}")
        typer.echo("")
        return

    status = weekly_status(config=config)
    typer.echo("")
    typer.echo("─── Dagpenge weekly status ───")
    typer.echo("")
    typer.echo(f"  Week: {status.week_start.isoformat()} → {status.week_end.isoformat()}")
    typer.echo(f"  Threshold: {status.threshold} applications")
    typer.echo(f"  Logged so far: {status.logged_count}")
    typer.echo(f"  Days remaining: {status.days_remaining_in_week}")
    typer.echo("")
    if status.is_compliant:
        margin = status.logged_count - status.threshold
        typer.echo(f"  ✓ Compliant ({margin:+d} margin).")
    elif status.days_remaining_in_week > 0:
        typer.echo(
            f"  ⚠ Behind by {status.shortfall}. "
            f"Need {status.shortfall} more by end of Sunday."
        )
    else:
        typer.echo(f"  ✗ Week closed with {status.shortfall} shortfall.")
    typer.echo("")
    if status.logged_jobs:
        typer.echo("  Logged this week:")
        for j in status.logged_jobs:
            typer.echo(f"   · {j.company or '?'} — {j.title or '?'}")
    typer.echo("")


# ---------------------------------------------------------------------------
# Interview-prep — generate a brief for one job
# ---------------------------------------------------------------------------
@app.command(name="interview-prep")
def interview_prep_cmd(
    job_id: str = typer.Option(
        ...,
        "--job-id",
        help="Job to prep for.",
    ),
    round_number: int = typer.Option(
        1,
        "--round",
        help="Round number — used to tag the output file.",
    ),
    short: bool = typer.Option(
        False,
        "--short",
        help="Tight 1-page brief (top 3 per section).",
    ),
    content: Path = typer.Option(
        None,
        "--content",
        help="JSON file with a Claude-written brief (behavioural_questions, "
             "technical_questions, watch_outs, questions_to_ask, notes — see "
             "workflows/interview_prep.md). Without it, a templated brief "
             "is produced.",
    ),
) -> None:
    """Render an interview-prep brief for one job.

    The real flow: Claude Code reads the job (``danapply show``) + the
    user's profile, writes a company-specific brief in-conversation, and
    passes it via ``--content``. Without ``--content`` you get an honest
    templated fallback.
    """
    from danapply.interview import (
        brief_from_content,
        build_interview_brief,
        render_brief_markdown,
    )

    try:
        profile = load_profile(paths.profile_yaml_path())
    except ConfigLoadError as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    memory.init_db()
    job = memory.get_job(job_id)
    if not job:
        typer.echo(f"ERROR: No job with id={job_id}", err=True)
        raise typer.Exit(code=1)

    if content is not None:
        data = _read_json_payload(content)
        if not isinstance(data, dict):
            typer.echo("ERROR: --content must hold a JSON object.", err=True)
            raise typer.Exit(code=1)
        try:
            brief = brief_from_content(job, data)
        except ValueError as exc:
            typer.echo(f"ERROR: {exc}", err=True)
            raise typer.Exit(code=1) from exc
    else:
        brief = build_interview_brief(job, profile, round_number=round_number, short=short)
    md = render_brief_markdown(brief, round_number=round_number)

    from danapply.models import pascalcase_slug

    out_dir = paths.interview_prep_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    company_slug = (job.company or "unknown").replace(" ", "-").replace("/", "-")
    title_slug = pascalcase_slug(job.title) or "Role"
    out_path = out_dir / f"{company_slug}_{title_slug}_round{round_number}.md"
    out_path.write_text(md, encoding="utf-8")

    typer.echo("")
    typer.echo(f"Wrote interview brief (method: {brief.generation_method}):")
    typer.echo(f"  {out_path}")
    typer.echo("")
    typer.echo(f"  {len(brief.behavioural_questions)} behavioural questions")
    typer.echo(f"  {len(brief.technical_questions)} technical questions")
    typer.echo(f"  {len(brief.watch_outs)} watch-outs")
    typer.echo(f"  {len(brief.questions_to_ask)} questions to ask")
    typer.echo("")


if __name__ == "__main__":
    app()
