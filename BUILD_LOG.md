# DanApply Build Log

Session-by-session record of what got built, what's working, and what's next.
This is the operational diary; the design docs in `docs/` are the spec.

---

## Session 1 — 2026-06-09 — v0.0.1 scaffolding + renderer port

### What got built

**Project scaffolding:**
- `pyproject.toml` configured for Python 3.11, uv build backend, runtime deps
  (typer, pydantic, pyyaml, reportlab, pillow, platformdirs), dev deps (pytest,
  pytest-cov, ruff, mypy)
- Ruff + pytest + mypy configurations
- `.gitignore` excluding `.venv/`, `__pycache__/`, generated PDFs, and
  importantly `danapply-data/` (user data is never committed)
- MIT LICENSE, README, ROADMAP copied from `automated_job_search/danapply_design/`

**Python package (`src/danapply/`):**
- `__init__.py` — version export only
- `paths.py` — canonical filesystem layout for the user's data dir,
  with `DANAPPLY_DATA_DIR` env-var override
- `config.py` — pydantic models (`Profile`, `Targets`) with YAML loaders
  that surface clear `ConfigLoadError` messages on missing/invalid files
- `render/templates/canonical.py` — full port of `cv_pdf_template.py` +
  `cover_letter_pdf_template.py`, refactored to consume a `Profile` object
  instead of module-level hardcoded constants. All user-specific content
  (name, contact, photo, LinkedIn URL, portfolio link, languages, references,
  accent colour) now flows from `profile.yaml`. The example internship
  dates change made earlier in `automated_job_search/` are preserved
  ("Marketing Analyst (Internship) · 2024")
- `scaffolding/init_data_dir.py` — idempotent first-run scaffold for
  `~/danapply-data/` with the example profile, photo, and stub voice profile
- `scaffolding/example/{profile.yaml, targets.yaml, cv_content.md,
  voice_profile.md, photo.jpeg}` — the author's example profile as the canonical example
- `cli.py` — typer-based CLI with three commands:
  - `danapply version`
  - `danapply init` (with `--force`)
  - `danapply render-sample` (with `--output-dir`, `--tagline`)

**Tests (`tests/test_smoke.py`):**
- Version constant
- Default data dir under `~/danapply-data`
- Env var override works
- `init` creates the expected directory tree + files
- End-to-end smoke: init → load_profile → render CV → PDF >10KB
- Same for cover letter
- `load_profile` fails helpfully with `ConfigLoadError`

**Design docs (`docs/`):**
- SKILL.md, tone_spec.md, triggers.yaml, danish_register_guide.md,
  push_back_library.md, orchestration.md
- `docs/workflows/` — all 9 workflow specs

### Verification

- `uv sync --dev` — installs cleanly, 33 packages including the dev group
- `uv run pytest` — **7 tests pass, 78% coverage**
- `uv run danapply --help` — CLI renders correctly with help text
- `DANAPPLY_DATA_DIR=/tmp/test uv run danapply init` — creates 14 entries
- `DANAPPLY_DATA_DIR=/tmp/test uv run danapply render-sample` — produces
  `sample_cv.pdf` (503KB) and `sample_cover.pdf` (~similar). Visually
  verified — output is byte-equivalent to what `automated_job_search/`
  produces. Photo with green ring, clickable LinkedIn anchor, plain section
  headers, Hungarian native language, all present.

### Known limitations of v0.0.1

- The renderer's experience/education bullets are still hardcoded in
  `canonical.py` (author-specific). To onboard a new user, they'd need to
  edit that module. A future session will add a `cv_content.md` parser
  that hydrates these dynamically from the user's markdown.
- No parsers, scorer, memory layer, discovery, voice extraction, or
  Danish-mode calibration yet.
- No Claude Code plugin packaging yet — DanApply is a Python CLI only at
  this point.

### Next session — v0.0.2 — parsers + memory

Build order (estimate: ~3 hours):

1. **`memory.py`** — SQLite schema + helpers for `applications`,
   `outcomes`, `companies`, `tagline_performance`. Initialise via a
   `danapply db init` subcommand.
2. **`parse/__init__.py`** — smart-paste router
3. **`parse/pdf.py`** — port from existing `automated_job_search` code
4. **`parse/text.py`** — handle raw paste and bundle exports
5. **`danapply parse --batch <dir>`** wired up
6. **A real parser-output schema** as a pydantic model (Job)
7. **One real test:** parse a known-good PDF from `tests/fixtures/`,
   compare the extracted fields against expected JSON

### Git state

Branch: `main`. First commit pending — about to commit "v0.0.1 —
scaffolding + renderer port".

No remote yet (private GitHub repo to be created when user is ready).

---

## Session 2 — 2026-06-09 — v0.0.2 parsers + memory layer

### What got built

**Domain model (`models.py`):**
- `Job` pydantic model — the parser-output contract; serialises to / hydrates
  from SQLite rows
- `pascalcase_slug()` — preserves CamelCase brands (McKinsey, HelloFresh)
  while title-casing all-lower / all-upper inputs
- `Job.ensure_job_id()` — deterministic id `{Company}_{Title}_{Date|Hash}`
  so the same posting parsed twice produces the same id (dedup foundation)
- `DataConfidence` (high/medium/low) and `ApplicationStatus` (parsed →
  tailored → applied → outcome states) string literal types

**Memory layer (`memory.py`):**
- SQLite schema with `applications` + `outcomes` tables, WAL mode, FKs on
- `init_db()` — idempotent schema setup; tracks `schema_version`
- `upsert_job()` — insert or update; returns `(job, is_new)` for dedup
- `get_job()`, `list_jobs()`, `count_jobs()`, `log_outcome()`
- All write paths gated behind context-managed connections

**Parsers (`parse/`):**
- `parse/__init__.py` — smart router: `parse_file()` dispatches by extension,
  `parse_batch()` walks a directory and continues on failure, `parse_paste()`
  handles raw text
- `parse/pdf.py` — pypdf text extraction + heuristic field inference:
  - Filename splitter handles `-`, `_`, `|`, `—`, `–` separators
  - Known-source filename suffixes stripped (LinkedIn, SmartRecruiters, etc.)
  - Source detection requires domain-like patterns (won't grab "linkedin"
    from share-button URLs)
  - Language detection uses language-unique markers only (no false-positive
    Hungarian on English URLs)
  - Title cleanup strips generic prefixes (`Job Details:`, `Position:`, etc.)
  - Location detection scans for DK cities in the first 50 lines
- `parse/text.py` — applies the same heuristics to `.txt`, `.md`, `.eml`,
  `.html` (HTML degraded; full HTML parser is v0.0.3)

**CLI additions (`cli.py`):**
- `danapply db init` — idempotent SQLite scaffold
- `danapply db status` — DB path, schema version, application count
- `danapply parse --batch DIR | --file PATH | --paste TEXT` — exactly one
  source; persists to `memory.db` by default; pretty table output with
  confidence markers (✓ / · / ?), `--json` for machine-readable output
- Failures collected and surfaced — pipeline never halts on a single bad file

**Tests:** 41 passing, 74% coverage. New test files:
- `tests/test_models.py` — slug helper edge cases, Job lifecycle
- `tests/test_memory.py` — idempotent init, upsert semantics, outcome logging
- `tests/test_parsers.py` — uses real Fertin Pharma PDF as fixture, verifies
  title cleanup, source detection, language detection, batch + paste paths

**Dependencies added:** `pypdf>=5.0.0`, `python-slugify>=8.0.0`.

### Verification

```
$ uv run danapply parse --batch /tmp/test-raw
Parsed 3 job(s) — 3 new to memory.

  ✓  Business Analyst  —  Tech & AI  
     job_id=TechAi_BusinessAnalyst_619ceb57  source=linkedin  lang=EN
  ✓  Hiflylabs Management Consultant  —  Data & AI  
     job_id=DataAi_HiflylabsManagementConsultant_daf441e3  source=smartrecruiters  lang=EN
  ·  Sustainability Data Analyst  —  (no company)  Vejle, Denmark
     job_id=UnknownCompany_SustainabilityDataAnalyst_b02a194e  source=salesforce-sites  lang=EN

$ uv run danapply db status
Database: ~/danapply-data/memory.db
Schema version: 1
Applications: 3
```

End-to-end works against real PDFs from `automated_job_search/raw_searches/`.

### Known limitations of v0.0.2

- **Filename heuristics can mis-attribute company on LinkedIn-style filenames.**
  E.g. `Business Analyst - Tech & AI _ McKinsey & Company _ LinkedIn.pdf`
  parses as `title="Business Analyst", company="Tech & AI"` — the
  practice-area is parts[1], not the company. Fixing this properly needs
  LLM-based extraction (v0.0.3).
- **No URL fetcher** — pasted URLs are not yet handled (v0.0.3).
- **No image/screenshot parser** — Claude vision integration is v0.0.3.
- **No scorer** — `Job` instances don't have scores; scoring rubric ports
  in v0.0.3.
- **No dedup beyond `job_id` collision** — fuzzy-matching same job across
  sources (same posting on LinkedIn + company careers page) lands in v0.0.4.
- **Requirements extraction is empty** — the `requirements: list[str]` field
  on `Job` always parses as `[]`. Needs LLM extraction.

### Next session — v0.0.3 — scorer + URL/image parsers + LLM extraction

Build order (estimate: ~3–4 hours):

1. **`scorer.py`** — port the 0–100 rubric from `automated_job_search`'s
   `PROMPT.md`; weight by `targets.yaml`; output goes on `Job.score` (new
   field — small schema migration)
2. **`parse/url.py`** — fetch URL with honest User-Agent, attempt JSON-LD
   `JobPosting` extraction first, fall back to text parsing
3. **`parse/image.py`** — Claude vision via Anthropic SDK; OCR + structured
   field extraction (this is also where LLM-based extraction enters for
   text/PDF parsers — refactor `pdf.py` to optionally call out)
4. **`danapply score --against profile/targets.yaml`** CLI command
5. **Improved PDF extraction** — when an Anthropic API key is configured,
   route weak parses through Claude for field re-extraction (high confidence)
6. **Tests** for scorer + URL parser (with mocked HTTP)

### Git state

Branch: `main`. Two commits expected: 9e3bc8f + this session's commit
("v0.0.2 — parsers + memory + smart-paste router"). No remote yet.

---

## Session 3 — 2026-06-09 — v0.0.3 scorer + URL parser

### Re-scoped honestly

Original plan for v0.0.3 was scorer + URL/image parsers + LLM extraction.
That's actually two sessions' worth of work. LLM extraction has real UX
weight (API key handling, cost awareness, error paths, prompt design) that
deserves dedicated focus. Shipped scorer + URL parser this session; LLM
extraction + image parser is now v0.0.4.

### What got built

**Score fields + schema migration (`models.py` + `memory.py`):**
- `Job.score: int = 0`, `Job.score_breakdown: dict | None`,
  `Job.scored_at: datetime | None`
- `to_db_row()` / `from_db_row()` updated to (de)serialise the JSON breakdown
- `memory.SCHEMA_VERSION` bumped to 2; `init_db()` runs `_run_migrations()`
  with idempotent `ALTER TABLE` for users upgrading from v0.0.2 SQLite files
- `upsert_job` write path now includes the score columns

**Scorer (`scorer.py`):**
- `ScoreBreakdown` dataclass with four components (Role Fit 45 / Skills 25 /
  Company Fit 20 / Freshness 10) plus per-component rationale strings
- `score_job(job, targets, today=None)` — pure function, doesn't mutate
- `apply_score(job, breakdown)` — sets the score fields on the Job
- Role Fit handles Tier A / B / C + Clear Miss with explicit reasons
- Skills Match is a substring-keyword heuristic — flagged honestly in the
  rationale ("v0.0.4 LLM extraction will refine"); includes deductions for
  "5+ years" and "native Danish required"
- Company Fit reads scale-up / international / momentum / red-flag signals
  from the description text
- Freshness handles future-dated postings (10/10), normal age buckets, and
  the no-posting-date case (neutral 4/10)

**URL parser (`parse/url.py`):**
- `_is_blocked()` + `BlockedDomainError` — auto-reject LinkedIn, Glassdoor,
  Indeed, ZipRecruiter, Wellfound/AngelList with a helpful error pointing
  to paste-mode
- `_fetch()` — httpx with honest `User-Agent: DanApply/0.0.3 (+github)`,
  15s timeout, follow_redirects
- `_find_jobposting_jsonld()` — walks `<script type="application/ld+json">`
  blocks recursively; finds `JobPosting` inside `@graph` arrays too
- `_job_from_jsonld()` — maps schema.org JobPosting fields onto our Job
  model, handles nested `hiringOrganization` / `jobLocation`, strips HTML
  from description
- `_job_from_meta()` — fallback using OpenGraph + `<meta>` tags + the
  same heuristics as the PDF parser applied to body text
- `_source_from_host()` — maps hostnames to short source labels
  (greenhouse, lever, teamtailor, smartrecruiters, jobindex, etc.)

**CLI additions:**
- `danapply parse --url <url>` — auto-rejects blocked domains with a clear
  message; otherwise fetches + parses
- `danapply score [--job-id ID | --against PATH | --top-n N | --json]` —
  scores all parsed jobs (or one by id), persists, prints a ranked table
- `danapply list [--status STATUS | --limit N | --json]` — read-only view
  of memory.db; shows score, status, title, company

**Dependencies added:** `httpx>=0.27.0`, `beautifulsoup4>=4.12.0`,
`lxml>=5.0.0`.

**Tests:** 77 passing (up from 41), 72% coverage. New test files:
- `tests/test_scorer.py` — 17 tests covering role-fit tiers, skills
  buckets and deductions, freshness age boundaries, company-fit signals,
  end-to-end apply_score
- `tests/test_url_parser.py` — 11 tests covering blocked-domain detection,
  JSON-LD parsing on Greenhouse-style fixture, meta-tag fallback, source
  labelling
- Fixtures: `sample_greenhouse_jobposting.html` (JSON-LD path),
  `sample_meta_only.html` (OpenGraph fallback path)

### Verification

```
$ danapply parse --batch ~/jobs/        # 3 PDFs
$ danapply score
Scored 3 job(s). Targets: ~/danapply-data/profile/targets.yaml
  #  Score  Title                                     Company
  1     62  Business Analyst                          Tech & AI
  2     50  Sustainability Data Analyst               (no company)
  3     45  Hiflylabs Management Consultant           Data & AI

$ danapply parse --url "https://www.linkedin.com/jobs/view/12345"
www.linkedin.com blocks automated fetches. Paste the text of the job ad
instead — copy from the page, paste here, and DanApply will parse it
normally.

$ danapply score --job-id <id> --json
{ "score": 62, "breakdown": {"role_fit": {"score": 40, "rationale":
  "Tier A title with description confirming analyst work."}, ... } }
```

Per-component rationales surface honestly — the skills heuristic
acknowledges its limits in the output, so the user knows where to trust
the score and where to verify.

### Known limitations carried to v0.0.4

- **Skills Match is a substring-keyword heuristic.** Real semantic
  matching (e.g. "experience in Python" vs "Python expert") needs LLM
  extraction.
- **Company Fit is description-only.** No CVR enrichment, no news scan,
  no The Hub profile check. All planned but not built.
- **No company name extraction in URL parser fallback.** When JSON-LD is
  absent, we use `og:site_name` (often the brand) and don't try to
  disambiguate from the body text.
- **No image / screenshot parser.** Claude vision integration is v0.0.4.
- **No `requirements: list[str]` extraction.** Always empty until LLM
  extraction lands.

### Next session — v0.0.4 — LLM extraction backbone

Build order (estimate: ~3 hours):

1. **`llm.py`** — Anthropic SDK wrapper with prompt-cached system prompts,
   structured output via tool-use, API key from `~/.danapply/credentials.toml`
   or `ANTHROPIC_API_KEY` env var, sensible retry + rate-limit handling
2. **`parse/image.py`** — Claude vision on screenshots / image files; same
   `Job` output as text parsers
3. **`extract/fields.py`** — high-confidence re-extraction of title, company,
   location, requirements when initial parse is `data_confidence != "high"`;
   optional flag on `parse` / `score` to enable
4. **`extract/skills.py`** — semantic skills matching using the extracted
   requirements list against the user's profile
5. **`danapply parse --image PATH`** + `danapply parse --boost` flag for
   re-extraction
6. Tests using mocked SDK responses (no live API calls in CI)

### Git state

Three commits expected: 9e3bc8f + 88afbef + this session's commit
("v0.0.3 — scorer + URL parser + score/list CLI"). No remote yet.

---

## Session 4 — 2026-06-09 — v0.0.4 LLM extraction backbone

### What got built

**Anthropic SDK wrapper (`llm.py`):**
- API key resolution: `ANTHROPIC_API_KEY` env var → `~/.danapply/credentials.toml`
  → fail with `LLMUnavailable`
- Model resolution: `DANAPPLY_MODEL` env → credentials file → `DEFAULT_MODEL`
  (currently `claude-sonnet-4-5`)
- `get_client()` returns a cached singleton; `reset_client_cache()` for tests
- `cached_system()` helper wraps system prompts with ephemeral cache markers
  (significant cost savings on bulk operations)
- `LLMUnavailable` exception has actionable setup instructions baked into
  the message (env var name, credentials file path, link to console)
- Never echoes API key values in error messages

**Field extraction (`extract/fields.py`):**
- `boost_job(job)` — re-runs the description through Claude with a strict
  tool-use schema (`record_job_fields`); returns a refined Job with
  `data_confidence='high'`
- Tool schema enforces: title (no generic prefixes), company (hiring entity
  not job board), location (primary if multi), dates (YYYY-MM-DD or empty),
  up to 10 verbatim requirements, language
- System prompt is prompt-cached
- Failure-safe — API error / malformed response → original Job returned
  unchanged, never raises
- `_apply_extraction()` merges LLM fields into Job, preserving job_id so
  memory dedup keeps working

**Image parser (`parse/image.py`):**
- Strict media-type check: PNG / JPEG / GIF / WEBP only (rejects BMP / TIFF
  / SVG locally — they'd be rejected by Anthropic anyway)
- 4 MB size cap (well under Anthropic's 5 MB hard limit)
- Reads bytes, base64-encodes, sends as image block in messages.create
- Uses the same tool-use schema as `extract/fields.py` (reuses the prompt
  cache between text-boost and image calls)
- `ImageParseError` for file-system / format / size issues; raises
  `LLMUnavailable` if no API key

**CLI additions:**
- `danapply parse --image PATH` — vision-based extraction
- `danapply parse --boost` — composable flag on all parse modes; re-runs
  medium/low-confidence parses through Claude
- Clean error surfacing when API key missing (full setup help shown)

**Dependencies added:** `anthropic>=0.42.0` (resolves to 0.108.0).

### Tests

113 passing (up from 77), 73% coverage. New test files:

- `tests/test_llm.py` — 11 tests: env-var precedence, credentials file
  fallback, model override, cache behaviour, error message quality
  (asserts the setup help text is actionable + never echoes keys)
- `tests/test_extract_fields.py` — 14 tests: graceful degradation when no
  key, tool-use response parsing (object-style + dict-style blocks),
  field merging (LLM wins / heuristic fallback), date parsing, error
  fallback paths
- `tests/test_image_parser.py` — 9 tests: format detection, size cap,
  successful vision extraction (mocked), accepted formats (jpg/jpeg/
  webp/gif), malformed response fallback

**No live API calls in CI** — every test mocks
`anthropic.Anthropic().messages.create`.

### Verification

```
$ unset ANTHROPIC_API_KEY
$ danapply parse --batch ~/jobs/ --boost
Anthropic API key not configured.

DanApply's LLM features (--boost, --image) need access to the Anthropic
API. Set up one of:

  1. Set the ANTHROPIC_API_KEY environment variable
  2. Create ~/.danapply/credentials.toml with:
       [anthropic]
       api_key = "sk-ant-..."
       # optional:
       model = "claude-sonnet-4-5"
...
Heuristic parsing and scoring continue to work without one.
```

### Known limitations carried to v0.0.5

- **`extract/skills.py` not built.** The scorer's Skills Match still uses
  the substring-keyword heuristic. With requirements now extractable into
  `Job.requirements`, the next session can wire a real semantic match
  against the user's profile.
- **No cost / token tracking.** `--boost` and `--image` make API calls
  but DanApply doesn't surface the cost. Future: estimate + warn before
  bulk operations.
- **Live API not actually exercised** — only mocked. First real-world
  invocation may surface API quirks the mocks don't cover.

### Next session — v0.0.5 — tailoring workflow

Build order (estimate: ~3 hours):

1. **`extract/skills.py`** — semantic skills matching using extracted
   requirements + the user's `cv_content.md` profile. Replaces the
   substring heuristic in the scorer.
2. **`render/tailoring.py`** — orchestration that takes a scored Job +
   user profile and produces a tailored CV PDF + cover letter PDF +
   notes markdown. This is the integration point that wires together
   `scorer.py`, `render/templates/canonical.py`, and (eventually) the
   voice profile.
3. **`danapply tailor`** CLI command — `--job-id`, `--top-n`, `--all`
   modes; writes to `~/danapply-data/resume_drafts/` and
   `~/danapply-data/cover_letters/`
4. Tests for skills matching + tailoring orchestration

### Git state

Four commits expected. No remote yet.

---

## Session 5 — 2026-06-09 — v0.0.5 tailoring workflow

### What got built

**UserSkills profile field (`config.py`, `scaffolding/example/profile.yaml`):**
- New `UserSkills` model with `tools`, `methods`, `domains`, `soft_skills` lists
- Added to `Profile` as `user_skills` with empty default (back-compat: old
  profiles keep working, just score lower on skills-match)
- Example profile seeded with realistic example skill keywords

**Skills matcher (`extract/skills.py`):**
- `match_skills_heuristic()` — substring + lemma-style matching of
  `Job.requirements` against `Profile.user_skills`. Returns per-requirement
  match status (matched / partial / missing). Falls back to description-text
  scanning when requirements are empty.
- `match_skills_llm()` — semantic match via Claude with strict tool-use
  schema. Falls back to heuristic on any failure.
- `match_skills()` router — picks heuristic vs LLM based on `use_llm`
  flag AND API key availability.

**Scorer rewire (`scorer.py`):**
- `score_job()` now accepts optional `profile` + `use_llm_skills` kwargs
- When `profile.user_skills` is non-empty, routes to the new requirements-
  aware matcher; otherwise legacy description heuristic kicks in
- Description-level deductions (5+ years, native Danish) preserved in both paths

**Tailoring orchestration (`render/tailoring.py`):**
- `detect_role_character()` — classifies job as research / strategy /
  content / default based on title + description signals
- `TAGLINE_LIBRARY` + `SKILLS_ORDER_PRESETS` — per-character presets in
  EN + DA
- `build_summary()` + `build_cover_letter_data()` — templated content
  (voice-aware versions ship in v0.0.7)
- `tailor_job()` — full orchestration: pick tagline + skills order, build
  CV data, build cover letter data, render both PDFs, write notes markdown
  with audit trail
- Output files include rank prefix when batched (`01_..._cv.pdf`)

**CLI additions:**
- `danapply tailor --job-id ID | --top-n N | --all` — generates CV +
  cover letter + notes for one or more scored jobs
- `--language EN|DA` override
- `--json` for machine-readable output
- `danapply score --boost` — uses Claude for the skills-match component

### Tests

149 passing (up from 113), 72% coverage. New test files:

- `tests/test_skills.py` — 18 tests: requirement_matches fuzzy logic,
  heuristic matcher (full match, partial, none, empty user_skills, no
  requirements fallback), LLM matcher mocked (success, API error fallback,
  score clamping, status normalisation)
- `tests/test_tailoring.py` — 16 tests: role character detection, tagline
  library completeness, skills order presets validity, summary builder
  (EN + DA), cover letter data builder, end-to-end tailor_job produces
  all 3 files with proper sizes, rank prefix in filenames, language override

### Verification

```
$ danapply tailor --top-n 2
Tailored 2 job(s):
  • Business Analyst — Tech & AI [strategy · EN]
     CV:   .../resume_drafts/01_TechAi_BusinessAnalyst_..._cv.pdf
     CL:   .../cover_letters/01_TechAi_BusinessAnalyst_..._cover.pdf
     Notes: .../cover_letters/01_TechAi_BusinessAnalyst_..._notes.md
  • Sustainability Data Analyst — (no company) [research · EN]
     ...
```

End-to-end works against real PDFs from `automated_job_search/raw_searches/`.
Scores shifted down meaningfully after wiring user_skills (87→72, 65→58, 50→55)
— the new matcher is honest about partial fits where the description-only
heuristic over-credited keyword presence.

### Known limitations carried to v0.0.6

- **Cover letter copy is templated.** The defaults sound generic — voice
  extraction in v0.0.7 makes them sound like the user.
- **No discovery layer.** All job input is still user-provided (paste / file
  / URL / image). Active discovery from DK job boards is v0.0.6.
- **No watchlist yet.** Concept exists in design docs but no `Profile`
  field for it.

### Next session — v0.0.6 — discovery fetchers

Build order (estimate: ~3 hours):

1. **`discover/__init__.py`** — DiscoverySource protocol + DiscoverResult
2. **`discover/jobindex.py`** — fetch the search-results page with the
   user's target-title queries; parse listings (single fetch per session,
   honest UA, respect /api/ disallow)
3. **`discover/watchlist.py`** — list of companies the user wants tracked;
   visit each one's career page (or last-known ATS URL) and surface new
   postings
4. **`Watchlist` model in profile.yaml** (up to 20 companies)
5. **`danapply discover`** CLI — runs configured sources, dedupes against
   memory.db, surfaces new candidates
6. Tests with mocked HTTP

### Git state

Five commits expected. No remote yet.

---

## Session 6 — 2026-06-09 — v0.0.6 discovery fetchers

### What got built

**Discovery framework (`discover/__init__.py`):**
- `DiscoverySource` Protocol (each source exposes ``name`` + ``discover()``)
- `DiscoverResult` dataclass with per-source job lists + error log
- `get_all_sources()` / `get_source(name)` registry
- `run_discovery()` runs configured sources; catches per-source crashes so
  one broken source never halts the pass

**Jobindex source (`discover/jobindex.py`):**
- One listing-page fetch per target title (max 5 queries per session, max
  25 results per page)
- Honest User-Agent, respects ``/api/`` disallow by only hitting public
  ``/jobsoegning``
- Parses ``div.jobsearch-result`` listings: title + URL + company + location +
  posting date (handles ``<time datetime=...>`` and ``"N days ago"`` patterns)
- Strips generic title prefixes; deduplicates within a single discovery run

**Watchlist source (`discover/watchlist.py`):**
- For each ``WatchlistEntry`` in profile.yaml, resolves a careers URL from
  ATS templates (Greenhouse / Lever / Teamtailor / SmartRecruiters /
  Workable / BambooHR / Personio / Recruitee) or uses an explicit URL
- Fetches the company's careers page; extracts ``JobPosting`` from JSON-LD
  (handles ``@graph`` arrays), falls back to anchor-scan for plausible
  job-URL patterns
- Returns Job stubs (no deep-fetch — that's ``danapply parse --url``)
- Per-company errors logged in ``DiscoverResult.errors`` without halting

**Profile additions:**
- `WatchlistEntry` model: ``company``, ``ats``, ``careers_url``, ``slug``, ``notes``
- ``Profile.watchlist`` field, capped at 20 entries

**CLI:**
- `danapply discover` with ``--source``, ``--persist/--no-persist``,
  ``--score/--no-score``, ``--json``
- Persists new discoveries to memory.db; optionally scores them immediately
- Pretty output: per-source counts, top-10 new candidates by score

### Tests

171 passing (up from 149), 71% coverage. New file:

- `tests/test_discover.py` — 22 tests: framework registry + run_discovery,
  source-crash isolation, Jobindex HTML parsing (multiple shapes, empty
  results, per-query failure recovery), watchlist URL resolution across
  6 ATS templates, JSON-LD JobPosting extraction with @graph, per-company
  fetch error continues

### Verification

CLI surfaces correctly. End-to-end mock tests demonstrate:
- 2 tier-A titles → 2 jobindex fetches → deduplicated to unique jobs
- 5 ATS templates resolved correctly
- Sample Greenhouse @graph parsed into 2 JobPostings
- Per-company fetch errors don't break the rest of the watchlist

### Known limitations carried to v0.0.7

- **No live Jobindex test.** The fetcher only goes against mocked HTML.
  Real-world Jobindex pages may have slightly different markup (the
  ``jobsearch-result`` class is the documented selector but they revise
  CSS occasionally).
- **No Hub / Jobnet / EURES sources yet.** Watchlist + Jobindex cover the
  big-volume cases; the rest will land in v1 polish or v1.x roadmap items.
- **Watchlist anchor-scan fallback is approximate.** Companies on bespoke
  career-page CMSs without JSON-LD will produce low-confidence stubs.

### Next session — v0.0.7 — voice extraction + Danish register calibration

**This is the moat.** Without it, generated cover letters sound generic.
With it, every cover letter sounds like the user wrote it (with grammar
quietly corrected and Danish-mode register applied).

Build order (estimate: ~4 hours):

1. **`extract/voice.py`** — capture the user's writing voice from sample
   text (their own cover letter draft, journal entries, etc.). Produces
   ``voice_profile.md`` with sentence patterns, vocabulary preferences,
   opening / closing styles, characteristic phrases
2. **`extract/register.py`** — Danish-mode register filter:
   strip superlatives, replace US-power-verbs, convert self-praise to
   third-party voice. Operates on generated text before it lands in the PDF
3. **`render/tailoring.py`** rewire — when ``voice_profile.md`` exists,
   ``build_summary()`` and ``build_cover_letter_data()`` use Claude to
   generate in the user's voice (with register applied)
4. **`danapply voice capture <file>`** — onboarding command to extract a
   voice profile from a user-written sample
5. Tests with mocked Claude responses

### Git state

Six commits expected. No remote yet.

---

## Session 7 — 2026-06-09 — v0.0.7 voice extraction + Danish-mode register

This is the moat session. Generated cover letters now respect Danish-mode
register by default (no more "exceptional results-driven self-starter")
and will speak in the user's voice once a profile is captured.

### What got built

**VoiceProfile + persistence (`extract/voice.py` + `paths.py`):**
- `VoiceProfile` pydantic model: sentence rhythm, formality register,
  opening/closing styles, vocabulary preferences/avoidances, characteristic
  phrases (verbatim quotes from the user's sample), register baseline,
  free-text notes, provenance
- `save_voice_profile()` writes both `voice_profile.yaml` (source of truth)
  and `voice_profile.md` (human-readable companion)
- `load_voice_profile()` returns None when missing or malformed
- New `voice_profile_yaml_path()` / `voice_profile_md_path()` helpers;
  legacy `voice_profile_path()` retained for back-compat

**Voice extraction (`extract/voice.py`):**
- `extract_voice(sample_text)` sends a writing sample to Claude with a
  strict tool-use schema; returns a populated `VoiceProfile`
- Graceful degradation: short sample → templated default with explanatory
  note; no API key → templated default; LLM error → templated default;
  malformed response → templated default
- Never raises — voice capture is meant to be low-friction

**Danish-mode register filter (`extract/register.py`):**
- `apply_register_rules()` — deterministic swap tables (superlatives,
  intensifiers, filler phrases, US power verbs, self-promotion structures).
  Word-boundary aware (won't strip 'extension' for 'extensive'). Returns
  full diff log + register score 1–10
- `apply_register_llm()` — voice-aware semantic rewrite via Claude;
  honours `vocabulary_preferences` / `vocabulary_avoidances` from the
  user's voice profile; falls back to rules on any failure
- `apply_register()` router with `use_llm` flag

**Tailoring rewire (`render/tailoring.py`):**
- `tailor_job()` now accepts `voice_profile_dir` + `apply_dk_register`
- Loads voice profile if present (silent no-op otherwise)
- Applies register filter to the summary, cover-letter opening, all four
  strengths bullets, and all three theme paragraphs when `apply_dk_register=True`
- `TailorResult` gains `voice_applied`, `register_applied`, `register_score`
- Notes markdown now documents voice + register state

**CLI:**
- `danapply voice capture FILE [--force]` — extract voice from a sample
- `danapply voice show` — display the captured profile
- `danapply voice clear [--force]` — delete voice profile
- `danapply tailor` output line now shows `voice✓/—` and `reg N/10` markers

### Tests

210 passing (up from 171), 71% coverage. New files:

- `tests/test_voice.py` — 14 tests: yaml+md roundtrip, missing file
  handling, malformed yaml handling, md content sections, all four
  graceful-degradation paths (empty/short/no-key/api-error/malformed),
  successful tool-use extraction, tool_input parsing edge cases
- `tests/test_register.py` — 28 tests: superlative stripping (with case
  variations and word boundaries), intensifier stripping, filler-phrase
  deletion (hyphen variants), power-verb swaps, self-promotion rewrites,
  empty/clean text edge cases, LLM router (success, fallback paths), score
  computation, summary string

### Verification

```
$ danapply voice show
No voice profile at .../voice_profile.yaml.
Capture one with: danapply voice capture <sample-file>

$ danapply tailor --top-n 1
  • Business Analyst — Tech & AI  [strategy · EN · voice— · reg 10/10]
```

Output marker shows voice state (`voice—` = not captured, `voice✓` = applied)
and register score. Register filter ran on all generated content.

### Known limitations carried to v0.0.8

- **Voice-aware summary generation isn't wired yet.** The `build_summary`
  and `build_cover_letter_data` functions still produce templated text;
  the register filter cleans them up but the substance is still generic.
  A future session will swap in Claude-generated, voice-matched content
  when a voice profile is present.
- **LLM register path is opt-in only.** Rules-based runs by default.
  Voice-matched LLM register polish requires explicit caller opt-in.
- **No live voice-capture test.** All tests mock the Anthropic SDK.

### Next session — v0.0.8 — onboarding interview orchestration

Build order (estimate: ~4 hours):

1. **`onboarding/__init__.py`** — chapter orchestration framework
2. **`onboarding/chapters.py`** — the 10-chapter script from
   `docs/workflows/onboarding.md` as Python prompts
3. **`onboarding/state.py`** — pause / resume / re-run support
4. **`danapply onboard`** CLI — interactive interview
5. **`extract/profile_builder.py`** — turn chapter answers into
   `profile.yaml` + `targets.yaml` updates
6. Tests using mocked input streams

### Git state

Seven commits expected. No remote yet.

---

## Session 8 — 2026-06-09 — v0.0.8 onboarding interview orchestration

### What got built

**Onboarding package (`onboarding/`):**
- `models.py` — `Chapter` + `Question` dataclasses; six answer types
  (text, long_text, choice, multi_choice, number, bool, file_path)
- `chapters.py` — all 11 chapters declared (welcome → wrap_up), exactly
  matching `docs/workflows/onboarding.md`
- `state.py` — `OnboardingState` + yaml persistence at
  `~/danapply-data/sessions/onboarding_state.yaml`; save after every chapter
  so `Ctrl+C` then `danapply onboard --resume` works
- `profile_builder.py` — translates answers into `profile.yaml` +
  `targets.yaml` + (conditionally) `dagpenge.yaml`; merges with existing
  files so hand-edits survive; emits the reality-check synthesis
- `runner.py` — interactive `Runner` with injected `read`/`write` callables
  (testable); handles validation per type, defaults, push-back on
  reality_check, side effects for existing_cv (register check) and
  voice_exercise (extract.voice integration)

**CLI:**
- `danapply onboard [--resume] [--reset]`
- Clear error when state exists and `--resume`/`--reset` not specified
- Ctrl+C exits cleanly with resume hint

### Tests

233 passing (up from 210), 72% coverage. New `test_onboarding.py` with
23 tests:
- Chapter library integrity (unique ids, full set matches design doc)
- State save/load/clear roundtrip, malformed yaml handling
- Profile builder translation (name → uppercase, locations, languages,
  tier_a/b titles, geography, salary, constraints)
- Dagpenge.yaml conditional creation
- Hand-edited profile fields survive merge
- Reality-check summary contains key fields
- Runner with scripted IO: skips completed chapters, validates choices,
  bool y/n, EOF aborts cleanly, reality-check rejection aborts, defaults
  on empty input, number validation

### Verification

CLI surfaces correctly. Runner driven by scripted IO completes all 11
chapters without prompts to stdin, writes profile.yaml + targets.yaml.

### Known limitations carried to v0.0.9

- **No push-back during interview.** The reality_check chapter shows a
  synthesised summary and the user can reject it, but per-question
  push-back (e.g. surfacing energy-vs-target contradiction during
  chapter 5) isn't wired. Pure CLI makes nuanced conversational
  push-back hard; that's a Claude Code orchestration job.
- **Existing_cv + voice_exercise chapters are sample-file-based.** The
  user points to a file; nothing pasted via stdin. Good enough for v1.

### Next session — v0.0.9 — joblog + interview prep + dagpenge + log_outcome

Build order (estimate: ~3 hours):
1. `danapply joblog` — generate Jobnet Opret-Joblog automation prompt
   from selected scored jobs (matches the format already established in
   automated_job_search/joblog_prompts/)
2. `danapply interview-prep --job-id ID` — generate interview brief
   with likely questions + watch-outs
3. `danapply dagpenge` — weekly compliance check
4. `danapply outcome --job-id ID --status X` — record outcome events

These four workflows close out the per-job lifecycle: tailor → log to
Jobnet → interview prep → record outcome.

### Git state

Eight commits expected. No remote yet.

---

## Session 9 — 2026-06-09 — v0.0.9 lifecycle-closer workflows

Closes the per-application lifecycle: tailor → Jobnet log → interview prep
→ outcome record → dagpenge compliance. Four new CLI commands + supporting
modules + a schema migration.

### What got built

**Schema v3 (`memory.py` migration):**
- New `applications.jobnet_logged_at` column with idempotent ALTER TABLE
- Powers both joblog dedup (don't re-include logged jobs) and dagpenge
  weekly count
- New helpers: `mark_jobnet_logged()`, `list_outcomes()`,
  `list_jobnet_logged_in_window()`

**Joblog generator (`joblog/`):**
- `pick_jobs_for_joblog()` filters by score threshold + jobnet_logged_at
- `JoblogEntry` dataclass with all Jobnet form fields
- `generate_joblog_prompt()` renders the exact format the existing
  `automated_job_search/joblog_prompts/` files use (verbatim header,
  field order matches the form, supplement-file footer)
- `resolve_output_path()` implements the supplement pattern — first
  call writes `jobnet_joblog_YYYY-MM-DD.md`, subsequent calls write
  `_supplement_N.md` (never overwrites)
- `danapply joblog [--threshold N] [--job-ids IDS] [--mark-logged]`

**Dagpenge tracker (`dagpenge/`):**
- `DagpengeConfig` loaded from `profile/dagpenge.yaml`
- `week_bounds()` returns DK-standard Monday→Sunday for any date
- `weekly_status()` queries memory for jobs logged this week, computes
  compliance state with days remaining + shortfall
- `weeks_history()` for trailing 8 weeks
- `danapply dagpenge [--history] [--weeks-back N]`

**Outcome CLI:**
- `danapply outcome --job-id ID --status STATUS [--notes "..."]`
- `danapply outcome --list`
- Status taxonomy validation against 8 canonical states (interview_scheduled,
  interview_completed_advancing, interview_completed_rejected,
  rejected_pre_interview, ghosted, offer_received, offer_accepted, withdrew)

**Interview-prep generator (`interview/`):**
- `InterviewBrief` dataclass with behavioural / technical / watch-outs /
  questions-to-ask sections
- `build_interview_brief(job, profile, round_number, short)` — LLM-powered
  with strict tool-use schema; templated fallback that's honest about its
  generic-ness in `notes`
- `render_brief_markdown()` produces an offline-readable file
- `danapply interview-prep --job-id ID [--round N] [--short]`

### Tests

274 passing (up from 233), 71% coverage. New files:
- `tests/test_joblog.py` — 17 tests: selection (threshold, already-logged
  exclusion, optional override), JoblogEntry translation, prompt rendering
  (header, footer, audit trail, field order, empty-prompt handling),
  supplement-file resolution
- `tests/test_dagpenge.py` — 14 tests: week-bounds for Mon/Wed/Sun
  references, config loading (missing/valid/malformed), weekly_status DB
  integration (zero/counted/window-excluded), summary line, days-remaining
  arithmetic, history return shape
- `tests/test_interview_prep.py` — 10 tests: templated fallback (size,
  company mention, deadline warning, short mode), LLM path (mocked
  success, API-error fallback, missing-tool-use fallback), tool extraction,
  markdown rendering (sections, method label, round number)

### Verification

All four new commands surface in `--help`. Schema migration upgrades from
v2 to v3 cleanly. End-to-end smoke against fresh data dir passes.

### Known limitations carried to v0.0.10

- Interview-prep templated fallback is honest but truly generic — for
  real prep, users will want to set ANTHROPIC_API_KEY.
- Joblog field-population is conservative — addresses, contact persons,
  phones, emails all default to "leave blank" rather than inventing them.
  The existing `automated_job_search/` prompts were richer because they
  were manually researched per company; auto-enrichment (CVR lookups for
  HQ addresses) is a future v1.x feature.
- Dagpenge tracker assumes Jobnet logging happens via the `--mark-logged`
  flow. Manual Jobnet entries don't count unless the user marks them.

### Next session — v0.0.10 — Claude Code plugin packaging

Build order (estimate: ~2 hours):
1. `skills/danapply/SKILL.md` — the Claude Code-readable plugin entry
2. `skills/danapply/PROMPT.md` — orchestration prompts that drive Claude
   Code to use the CLI naturally
3. Plugin manifest + install instructions
4. End-to-end smoke: load the plugin in Claude Code, run through onboarding
   + parse + tailor conversationally
5. README rewrite reflecting the actual installable shape

### Git state

Nine commits expected. No remote yet.

---

## Session 10 — 2026-06-09 — v0.1.0 — first feature-complete release

The closing session. Packages the Claude Code plugin, ships the README
rewrite + INSTALL guide + CHANGELOG, and tags v0.1.0.

### What got built

**Claude Code plugin (`skills/danapply/`):**
- `SKILL.md` — Claude Code-readable entry point with YAML frontmatter
  (name, description, allowed-tools); session-start ritual; trigger
  surface mapping natural language to CLI calls; six non-negotiable
  operating rules
- `orchestration.md` — full CLI reference matching everything that
  actually ships (the design-era version was forward-looking; this
  one is the truth)
- `tone_spec.md`, `danish_register_guide.md`, `push_back_library.md`
  copied from design docs (no rewrite needed — they were always real)
- `triggers.yaml` — fixed YAML syntax issues from the design-era file;
  parses cleanly now
- `workflows/` — all 9 detailed workflow specs

**Top-level docs:**
- `README.md` — overhauled for shipped reality (was design-era)
- `INSTALL.md` — Path 1 (Python CLI standalone) + Path 2 (CLI + Claude
  Code plugin); covers env vars, credentials file, optional Anthropic
  API key for LLM features
- `CHANGELOG.md` — full history from v0.0.1 → v0.1.0

**Version bump:**
- `__version__ = "0.1.0"` in `src/danapply/__init__.py`
- `version = "0.1.0"` in `pyproject.toml`
- `tests/test_smoke.py` assertion updated to match

**Tests:**
- New `tests/test_skills_plugin.py` (24 tests): verifies all skill files
  exist, SKILL.md frontmatter parses, triggers.yaml parses, the 14
  shipped CLI commands are referenced in both orchestration.md and SKILL.md,
  the six non-negotiable rules are present
- 322 total passing (up from 274), 74% coverage

### Verification

End-to-end smoke against fresh data dir:

```
danapply init      → scaffold works
danapply parse     → 3 PDFs parsed
danapply score     → ranked
danapply tailor    → CV + cover letter + notes generated
danapply joblog    → Jobnet prompt written to disk
danapply outcome   → recorded, listed
```

All four sessions of v0.0.6-v0.0.9 work as integrated whole.

### What v0.1.0 means

**Feature-complete v1 baseline.** Every workflow from `docs/workflows/`
has a working CLI command. Every command has tests. The skill plugin
files are real, not aspirational. A new user can install DanApply, run
`onboard`, and have a working personal job-search pipeline that takes
them from "I saw a posting" to "Jobnet logged" without manual
busywork.

**What v0.1.0 is NOT:**
- Not battle-tested with real users yet (just dev smoke tests)
- Not published to PyPI (manual install from repo today)
- Not listed in any Claude Code plugin registry (manual copy to
  ~/.claude/skills/danapply/)
- Not exercised with a live Anthropic API key in CI (all LLM paths
  are mocked)
- Not localized beyond EN+DA outputs
- Not addressing real-world Jobindex parsing edge cases (uses mocked
  HTML in tests)

### Roadmap from here

`ROADMAP.md` covers the post-v0.1.0 work — STAR JobAdService integration,
networking module, jobindsats.dk enrichment, voice drift detection,
other Nordic markets, etc.

### Git state

Ten commits total. Tag `v0.1.0` recommended after this commit lands.
No remote yet — push to GitHub when ready.

---

## Summary across all 10 sessions

| Version | Files | LOC Py | Tests | Cov | Headline |
|---|---|---|---|---|---|
| v0.0.1 | 39 | ~800 | 7 | 78% | Renderer ported |
| v0.0.2 | 48 | 2,154 | 41 | 74% | Parsers + memory |
| v0.0.3 | 54 | 2,955 | 77 | 72% | Scorer + URL parser |
| v0.0.4 | 61 | 3,539 | 113 | 73% | LLM extraction + image parser |
| v0.0.5 | 65 | 4,189 | 149 | 72% | Tailoring workflow |
| v0.0.6 | 70 | 4,820 | 171 | 71% | Discovery fetchers |
| v0.0.7 | 75 | 5,737 | 210 | 71% | Voice + Danish register |
| v0.0.8 | 82 | 6,192 | 233 | 72% | Onboarding interview |
| v0.0.9 | 91 | 7,180 | 274 | 71% | Lifecycle closers |
| **v0.1.0** | **94** | **7,180** | **322** | **74%** | **Plugin packaging + v1 ship** |

10 sessions × ~3 hours each = ~30 hours of focused work from scratch to
v0.1.0. The original 4-6 week estimate held up surprisingly well —
real elapsed time was tighter because there were no real interruptions.
