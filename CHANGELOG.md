# Changelog

All notable changes to DanApply documented here. Format roughly follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versioned with
[SemVer](https://semver.org/spec/v2.0.0.html).

## [0.5.3] — 2026-06-12

**No em-dashes, adjustable formatting, page-spill detection.**

### Added

- **`cv_font_scale` in profile.yaml** (0.8–1.05, default 1.0): shrinks
  the CV's fonts and spacing uniformly — the one-line fix when the CV
  spills a line or two onto an extra page. The cover letter's shared
  header follows the same scale for visual consistency.
- **Page-spill detection.** `render-base` and `tailor` report the CV's
  page count and print a ⚠ hint when the last page holds only a line or
  two (or the CV exceeds two pages), pointing at `cv_font_scale` or a
  bullet trim.

### Changed

- **No em-dashes in cover letters by default.** New punctuation rule in
  `tailor.md` Step 5: restructure with commas, colons, or full stops;
  the only exception is a user whose own voice sample uses them.
- **"Nothing is written in stone."** `tailor.md` Step 10 and
  `cv_session.md` Step 5 now require telling the user the formatting is
  adjustable after generation (style preset, accent colour, font scale —
  one-line edits + re-render), and proposing layout fixes proactively
  when the engine prints a spill hint.

## [0.5.2] — 2026-06-12

**Cover-letter polish from the live test run.**

### Fixed

- **Closing tagline is a title, not a sentence.** Trailing full stop is
  stripped at render time (engine-level, also for the headline tagline),
  and the accent underline beneath it is gone. `tailor.md` now tells the
  writer: no terminal punctuation on taglines.
- **Signoff name restyled.** The name under "Best regards," was bold and
  oversized; now italic at body size.
- **No more bolted-on application sentences.** `tailor.md` Step 5 gained
  an explicit anti-pattern: "I am applying for the X role at Y" must
  grow out of the preceding line of thought, never appear out of
  nowhere — with a bad/good example pair and a self-check (if the
  sentence could be deleted without leaving a logical hole, it isn't
  connected yet).

## [0.5.1] — 2026-06-12

**Portfolio section fixed: present with a link, absent without one.**

### Fixed

- **No more empty PORTFOLIO box.** The section rendered in every CV and
  cover letter regardless of whether the user had a portfolio (the blank
  scaffold even shipped `portfolio: {display: "", href: ""}`, which
  rendered as an empty highlighted box). Now: a blank or missing
  portfolio block normalises to *no portfolio* at profile-load time, and
  the renderers omit the section entirely — no box, no placeholder. With
  a link set, the block renders on both documents with the clickable URL.

### Changed

- **Portfolio is now an explicit pre-render question.** `cv_session.md`
  Step 1 and `tailor.md` Step 0 ask before every CV generation whether
  the user has a portfolio collection or a single piece; if they paste a
  link it goes into `profile.yaml` (`portfolio.display` + `href`). If
  not, a friendly one-time nudge explains why a portfolio is worth
  building in DK hiring, with low-effort starter ideas per field (case
  study, public dashboard, documented repo, published pieces) — never
  blocking the render, never inventing a URL.
- Blank scaffold ships the portfolio block commented out with fill-in
  instructions instead of empty strings.
- 6 new tests: empty-block normalisation + PDF-text assertions that the
  PORTFOLIO section appears exactly when a link exists.

## [0.5.0] — 2026-06-12

**Findings from the second new-user test, fixed.** The fictional-profile
run surfaced two broken deliverables — the first cover letter never became
a PDF, and the base CV rendered without the user's real summary — plus a
missing design conversation (style, colour, photo). All addressed.

### Fixed

- **Cover letters always ship as PDF.** New `danapply render-letter
  PAYLOAD.json` renders a standalone cover-letter PDF with no job record
  behind it — the first letter written during onboarding (Chapter 9 now
  ends with a rendered PDF, never just markdown), speculative
  applications, any letter drafted outside the pipeline.
- **The base CV renders the user's real summary.** New `danapply
  render-base` reads `## Summary` from `cv_content.md` (and errors
  loudly if it was never written) instead of `render-sample`'s
  placeholder text. `cv_session.md` Step 4 now uses it; `render-sample`
  is documented as smoke-test-only.
- **Photo ask enforced in the render path.** `render-base` and `tailor`
  warn when no photo is configured; `tailor.md` Step 0 and `quickapply`
  now require asking the user before rendering a text-only header.

### Added

- **CV style presets** — `cv_style: classic | minimal | modern |
  creative` in profile.yaml, all ATS-friendly by construction (single
  column, real text, standard headers; presets vary only restrained
  design touches). One-off override via `--style` on the render
  commands.
- **Explicit base-colour choice.** Accent tints (portfolio box, soft
  section rules) now derive from `accent_color` instead of hardcoded
  greens, so a colour change propagates everywhere. The CV session asks
  for the colour explicitly instead of silently keeping the green
  default.
- **Cover-letter style matching.** `cover_letter_style` in profile.yaml
  — unset means match the CV (the default the workflows now ask about);
  set it only when the letter should look different.
- **Design questions in the workflows.** `cv_session.md` Step 1b asks
  style (matched to the work environment the user applies to), base
  colour, and letter-match; `tailor.md` Step 0 runs the same checks
  before any render.
- 18 new tests (`tests/test_render_base_and_letter.py`) covering summary
  extraction, both new commands, letter-payload validation, and the
  style fields.

## [0.4.0] — 2026-06-11

**Findings from the first real new-user test, fixed.** A from-scratch
onboarding run (fictional persona) surfaced identity, font, tagline, and
flow gaps — all addressed, plus a set of new commands.

### Fixed

- **Identity leakage from stale sessions.** Onboarding now asks the
  user's name FIRST (new Chapter 1 question, the only identity source),
  payload JSONs moved from fixed `/tmp` paths to session-scoped
  `sessions/payloads/<purpose>_<date>.json`, and a pre-flight
  stale-state guard treats leftover voice profiles / payloads / DB rows
  as clutter to clear, never as facts about the current user.
- **Polish (and any non-Latin-1) characters dropped in PDFs.** The
  renderer detects content outside Helvetica's charset and switches the
  whole document to a Unicode TTF family (Arial on macOS, DejaVu on
  Linux, Arial Unicode as last resort) — "Wrocław" and "Łódź" now render
  correctly. Regression test included.
- **Taglines were the author's, not the user's.** The baked-in
  tagline/closing-tagline libraries are gone. Claude writes a per-job
  `tagline` + `closing_tagline` (new optional `--content` fields) and
  confirms them with the user; fallback is `profile.tagline_default`
  and no closing line. tailor.md de-personalised (no more real-person
  career references).
- **Photo never asked for.** Blank init no longer seeds a placeholder
  photo; the CV session explicitly asks for a headshot with sizing
  guidance; `tailor` warns when no photo is installed.

### Added

- **`danapply photo set <path>`** — validates, centre-crops, resizes
  (800px edge, never upscales), installs `profile/photo.jpeg`, points
  `profile.yaml` at it, warns when the source is print-soft (<300px).
- **`danapply status`** — one-screen overview: profile, voice, pipeline
  counts by status, recent jobs, dagpenge week.
- **`danapply delete [--force]`** — wipe the data directory; dry-run by
  default, explicit confirmation required.
- **New plugin commands:** `/danapply:run` (alias), `/danapply:status`
  ("what have we been working on"), `/danapply:jobtracker` (pipeline
  board grouped by stage, ghost detection), `/danapply:quickapply`
  (paste a posting → tailored CV + cover letter, no ceremony),
  `/danapply:delete` (guarded full wipe).
- **Explicit feedback loop:** tailor and cv_session workflows now end
  with "open it — does it sound like you?" and iterate until the user
  is satisfied. Rendering is never the last step.

## [0.3.0] — 2026-06-10

**Paste-first intake, honest rendering, and a reconciled skill layer.**
Driven by a full code review: discovery/crawling removed by design, the
renderer no longer ships anyone's career, and the skill docs now describe
only commands the engine actually has.

### Removed

- **All web fetching.** The `discover` command, the Jobindex + watchlist
  sources, `parse --url`, and the `httpx`/`beautifulsoup4`/`lxml`
  dependencies are gone. Intake is paste / files (PDF, TXT, MD, EML) /
  screenshots / job-alert emails — the engine makes zero network requests.
  `Profile.watchlist` removed with it.
- **Phantom CLI surface in the skill docs** — ~20 commands/flags that were
  never implemented (`joblog --confirm-logged`, `dagpenge-check`/`-set`,
  `watchlist add`, `enrich`, `parse --dedupe`, assorted `onboard`/
  `outcome`/`discover` flags, `python -m danapply`). Workflows now
  reference only the real engine; a regression test
  (`test_no_phantom_cli_commands_in_skill_docs`) keeps it that way.

### Fixed

- **Re-parsing no longer wipes pipeline state.** `upsert_job`'s update
  path clobbered `score` (→ 0), `status` (→ `parsed`), and downgraded
  `data_confidence` whenever an already-tracked posting was parsed again.
  Lifecycle fields are now guarded; regression tests added.
- **`joblog --mark-logged` stamps without generating.** It previously
  wrote a spurious supplement prompt file on every confirmation. It now
  requires `--job-ids`, stamps `jobnet_logged_at`, advances early-stage
  statuses to `applied`, and writes nothing.
- **The renderer no longer fabricates.** Experience and education render
  from `profile.yaml` (`experience:` / `education:` lists — new schema);
  the demo persona's career moved into the `--example` scaffold where it
  belongs. Templated fallback prose (summary, strengths, themes) is built
  strictly from profile facts; `render-sample` uses explicit placeholder
  text. Skills paragraphs hydrate from `user_skills`.
- **Status lifecycle is reachable.** `tailor` advances `parsed` →
  `tailored`; `--mark-logged` advances to `applied`; outcome statuses
  still win. `list --status tailored` now means something.
- **`init --force` docs told the truth backwards** — it overwrites
  user-edited profile files with blank seeds. Docs corrected with a loud
  warning; the report no longer mislabels created files as overwritten.
- Scorer keyword matching is word-boundary anchored (`"r "` no longer
  matches every word ending in *r*); `interview-prep` filenames include
  the role so two roles at one company don't overwrite each other;
  `PRAGMA foreign_keys` applies to every connection; timestamps are
  consistently local ISO.

### Changed

- **Onboarding is in-conversation, full stop.** SKILL.md, the `/danapply`
  command, and `workflows/onboarding.md` all direct Claude to conduct the
  interview in chat and write the profile files itself. `danapply
  onboard` remains as the standalone-terminal fallback and is documented
  as such (it cannot run under Claude Code's Bash tool).
- `workflows/cv_session.md` wired into SKILL.md and the onboarding
  Phase B hand-off.
- Optional email intake: `.eml` files parse natively; if the session has
  an email MCP connector, Claude may read job-alert emails directly and
  `ingest` the postings (read-only).

## [0.2.0] — 2026-06-10

**Architecture inversion: Claude Code plugin first, no API key anywhere.**
DanApply is now a Claude Code plugin whose conversational layer does all
language work in-conversation; the Python engine is the deterministic
machinery underneath (parse, score, SQLite, PDF render). The Anthropic
SDK dependency is gone — there is no API key to configure.

### Added

- **Plugin packaging** — `.claude-plugin/plugin.json` + `marketplace.json`
  (the repo is installable as a plugin and self-hostable as a marketplace),
  `commands/danapply.md` (`/danapply` session launcher)
- **`danapply ingest`** — store Job records Claude extracted
  in-conversation (screenshots, messy pastes, weak heuristic parses)
- **`danapply show --job-id`** — dump one job's full record (Claude reads
  it before writing prose)
- **`danapply voice set`** — save a Claude-analysed voice profile
  (replaces the API-backed `voice capture`)
- **`danapply tailor --content`** — render CV/cover-letter PDFs from
  Claude-written prose (summary, opening, 4 strengths, 3 themes)
- **`danapply interview-prep --content`** — render a Claude-written brief
- **`workflows/voice_capture.md`** — in-conversation voice-analysis
  instructions + payload schema (migrated from the deleted LLM prompt)
- **Schema v4** — `requirements` persisted as a JSON column in memory.db
  (Claude-extracted requirements drive the sharp skills-match path);
  migration runs automatically

### Removed

- `anthropic` dependency, `llm.py` wrapper, `~/.danapply/credentials.toml`,
  `DANAPPLY_MODEL`
- `parse --image`, `parse --boost`, `score --boost` (Claude does this work
  in-conversation now)
- API-backed LLM paths in voice extraction, register calibration, skills
  matching, field boosting, interview prep, and cover-letter generation

### Changed

- `SKILL.md` + `orchestration.md` + workflow docs rewritten for the
  "Claude writes, engine renders" division of labour; fictional
  `danapply render` CLI surface in the workflow docs replaced with the
  real one
- Rule-based Danish-register filter now runs **only** over templated
  fallback prose — Claude-written content follows the register guide at
  writing time
- `docs/` re-synced with `skills/danapply/` (was stale since v0.0.1)

### Stats

- **287 passing tests** (71% coverage)

---

## [0.1.0] — 2026-06-09

**First feature-complete v1 baseline.** Every workflow from the design
docs has a working CLI command. Full pipeline (onboarding → discover →
parse → score → tailor → joblog → outcome → dagpenge → interview prep)
works end-to-end.

### Added

- **`skills/danapply/`** — Claude Code plugin package
  - `SKILL.md` with frontmatter declaring triggers + allowed tools
  - `orchestration.md` — full CLI reference matching what actually ships
  - `tone_spec.md`, `danish_register_guide.md`, `push_back_library.md`,
    `triggers.yaml` (machine-readable)
  - `workflows/` — 9 per-workflow specs
- **`INSTALL.md`** — Path 1 (Python CLI standalone) + Path 2 (CLI + plugin)
- **`CHANGELOG.md`** — this file
- **Skill-files sanity tests** — 24 tests asserting plugin files exist,
  SKILL.md has valid YAML frontmatter, triggers.yaml parses cleanly,
  orchestration.md and SKILL.md reference all 14 shipped commands

### Changed

- README rewritten to reflect actual shipped product (was design-era)
- Version bumped to `0.1.0`

### Stats

- **322 passing tests** (74% coverage)
- **94 files** across `src/danapply/`, `tests/`, `skills/danapply/`, docs
- **~7,500 lines of Python**

---

## [0.0.9] — 2026-06-09

Lifecycle-closer workflows: joblog, outcome, dagpenge, interview-prep.

### Added

- **Schema migration v3** — `applications.jobnet_logged_at` column
- **`danapply joblog`** — generates Jobnet 'Opret Joblog' prompt with
  supplement-file pattern (never overwrites)
- **`danapply outcome`** — record + list outcome events; 8-status taxonomy
- **`danapply dagpenge`** — weekly compliance status with history
- **`danapply interview-prep`** — LLM-powered or templated interview brief
- New modules: `joblog/`, `dagpenge/`, `interview/`
- 41 new tests (274 total, 71% coverage)

---

## [0.0.8] — 2026-06-09

**Onboarding interview orchestration.** Walks 11 chapters and builds
profile.yaml + targets.yaml + (optional) dagpenge.yaml.

### Added

- **`onboarding/`** package: `models.py`, `chapters.py`, `state.py`,
  `profile_builder.py`, `runner.py`
- **`danapply onboard [--resume] [--reset]`** CLI command
- 23 new tests (233 total, 72% coverage)
- State saved after every chapter — `Ctrl+C` then `--resume` works

---

## [0.0.7] — 2026-06-09

**Voice extraction + Danish-mode register filter.** The moat.

### Added

- **`extract/voice.py`** — `VoiceProfile` model + `extract_voice()` via
  Claude tool-use; templated fallback on all error paths
- **`extract/register.py`** — rule-based + LLM-based Danish-mode
  calibration with diff log and 1–10 score
- **`render/tailoring.py`** — voice-aware + register-aware generation
- **`danapply voice capture/show/clear`** CLI subcommands
- 42 new tests (210 total, 71% coverage)

---

## [0.0.6] — 2026-06-09

**Discovery fetchers.**

### Added

- **`discover/`** package with `DiscoverySource` Protocol
- **`discover/jobindex.py`** — listing-page fetch + parse
- **`discover/watchlist.py`** — per-company ATS fetcher (Greenhouse /
  Lever / Teamtailor / SmartRecruiters / etc.)
- **`Profile.watchlist`** with `WatchlistEntry` (max 20)
- **`danapply discover [--source N] [--persist] [--score]`** CLI
- 22 new tests (171 total)

---

## [0.0.5] — 2026-06-09

**Tailoring workflow + user_skills-aware scoring.**

### Added

- **`Profile.user_skills`** — tools / methods / domains / soft_skills
  lists
- **`extract/skills.py`** — heuristic + LLM-powered requirements match
- **`render/tailoring.py`** — full orchestration: tagline + skills order
  + CV + cover letter + notes
- **`danapply tailor`** + **`danapply score --boost`** CLI
- 36 new tests (149 total)

---

## [0.0.4] — 2026-06-09

**LLM extraction backbone + image parser.**

### Added

- **`llm.py`** — Anthropic SDK wrapper with API key resolution + prompt
  caching
- **`extract/fields.py`** — LLM re-extraction of weak heuristic parses
- **`parse/image.py`** — Claude vision for screenshots
- **`danapply parse --boost --image`** CLI flags
- 36 new tests (113 total)

---

## [0.0.3] — 2026-06-09

**Scorer + URL parser.**

### Added

- **Schema migration v2** — score, score_breakdown, scored_at columns
- **`scorer.py`** — 0–100 rubric (Role 45 + Skills 25 + Company 20 +
  Freshness 10) with per-component rationale
- **`parse/url.py`** — JSON-LD JobPosting first, OG meta fallback, plain
  text last; blocked-domain detection
- **`danapply score`**, **`danapply list`**, **`danapply parse --url`** CLI
- 36 new tests (77 total)

---

## [0.0.2] — 2026-06-09

**Parsers + memory layer.**

### Added

- **`models.py`** — `Job` pydantic with deterministic `job_id`
- **`memory.py`** — SQLite layer with WAL mode + idempotent migrations
- **`parse/`** smart router: PDF (pypdf), text, paste; filename
  heuristics + language detection + source attribution
- **`danapply parse --batch --file --paste`** + **`danapply db init`**
  CLI commands
- 34 new tests (41 total)

---

## [0.0.1] — 2026-06-09

**Initial scaffolding + canonical renderer port.**

### Added

- Python package with `pyproject.toml` (uv build, py311, ruff +
  pytest + mypy)
- `src/danapply/` skeleton with `paths.py`, `config.py` (pydantic
  Profile + Targets)
- `render/templates/canonical.py` — full CV + cover-letter renderer
  ported from the original `automated_job_search/cv_pdf_template.py`,
  now profile-driven
- `scaffolding/init_data_dir.py` — idempotent `~/danapply-data/` setup
- `danapply init`, `danapply render-sample`, `danapply version` CLI
- 7 smoke tests, 78% coverage

---

[0.5.3]: https://github.com/erton6/danapply/releases/tag/v0.5.3

<!-- Versions 0.0.1–0.5.2 are documented above as development history; this
repository was published to GitHub at v0.5.3 (single initial commit), so only
that tag exists as a release. -->
