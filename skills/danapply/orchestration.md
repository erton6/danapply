# Python engine orchestration — DanApply v0.5.0

The full engine surface as actually shipped. Claude Code uses this
reference to decide which subprocess to call when a user expresses an
intent. The engine is mechanical (parse, score, store, render); **you**
do the judgment work in-conversation and hand results over as JSON.

Invocation: when DanApply is installed as a plugin, run commands as

```bash
uv run --project "${CLAUDE_PLUGIN_ROOT}" danapply <command>
```

(``danapply <command>`` directly works too if the user pip-installed the
engine.) Output is human-readable by default; pass ``--json`` (where
supported) for machine-parseable output suitable for chaining.

The user's data lives at ``~/danapply-data/`` by default. Override with
``DANAPPLY_DATA_DIR=/custom/path``.

---

## Quick reference

| Command | Purpose |
|---|---|
| `danapply init` | Scaffold ``~/danapply-data/`` with a blank profile template |
| `danapply onboard [--resume] [--reset]` | Standalone-terminal interview (NOT for Claude Code sessions — onboard in-conversation instead) |
| `danapply voice set PAYLOAD.json` | Save a Claude-analysed voice profile (you analyse the sample, engine validates + saves) |
| `danapply voice show` / `voice clear` | Inspect / delete the voice profile |
| `danapply parse --batch DIR \| --file PATH \| --paste TEXT` | Heuristic-parse postings into Job records |
| `danapply ingest JOB.json` | Store Job records **you** extracted (screenshots, messy pastes, weak parses) |
| `danapply show --job-id ID` | Dump one job's full record (read before writing prose) |
| `danapply score [--job-id ID]` | Apply 0-100 rubric to parsed jobs |
| `danapply list [--status STATUS]` | Browse memory.db |
| `danapply tailor --job-id ID --content PROSE.json` | Render CV + cover letter + notes from prose **you** wrote |
| `danapply joblog [--threshold N]` | Generate Jobnet 'Opret Joblog' prompt |
| `danapply outcome --job-id ID --status STATUS` | Record an outcome event |
| `danapply outcome --list` | Show recent outcomes |
| `danapply dagpenge [--history]` | Weekly compliance status |
| `danapply interview-prep --job-id ID --content BRIEF.json` | Render an interview brief from content **you** wrote |
| `danapply photo set PATH` | Validate + centre-crop + resize a headshot into profile/photo.jpeg |
| `danapply status` | One-screen overview: profile, pipeline counts, recent jobs, dagpenge week |
| `danapply delete [--force]` | Wipe the entire data directory (profile + memory + PDFs) — irreversible |
| `danapply db init` / `db status` | Initialise or inspect memory.db |
| `danapply render-sample` | Smoke test the renderer end-to-end (placeholder text only) |
| `danapply render-base` | Render the user's REAL base CV (summary from cv_content.md) |
| `danapply render-letter PAYLOAD.json` | Render a standalone cover-letter PDF (no job record needed) |
| `danapply version` | Print installed version |

---

## Setup commands

### `danapply init`

Scaffold the user's data directory. Idempotent — running it twice is safe.

```
danapply init [--force] [--example]
```

- Creates ``~/danapply-data/`` and all subdirectories
- Seeds a **blank** ``profile.yaml``, ``targets.yaml``, ``cv_content.md``,
  ``voice_profile.md`` (placeholder), and ``photo.jpeg``
- ``--example`` seeds the fictional "Sofia Almeida" demo persona instead
  (for trying the renderer)
- ``--force`` **overwrites existing profile files with the seed
  templates — this destroys user edits.** Never run it on an onboarded
  profile without the user's explicit, informed confirmation (archive
  to ``sessions/profile_history/`` first).

Run this once on first use, then onboard.

### `danapply onboard`

**Standalone-terminal fallback only.** This is an interactive
``input()``-driven interview for users running DanApply without Claude
Code; it needs a real TTY and will abort immediately under the Bash
tool. In a Claude Code session, onboarding happens in-conversation
per ``workflows/onboarding.md`` — you ask the questions and write the
profile files.

```
danapply onboard [--resume] [--reset]
```

- State saves after every chapter to
  ``~/danapply-data/sessions/onboarding_state.yaml``
- ``--resume`` picks up from the last completed chapter
- ``--reset`` deletes saved state before starting
- Ctrl+C is safe — resume with ``--resume``

---

## Voice management

### `danapply voice set PAYLOAD.json`

Save a voice profile that **you analysed in-conversation**. You read the
user's writing sample (Read tool), analyse it per
``workflows/voice_capture.md``, write the structured JSON to a temp file,
and pass it here. The engine validates against the ``VoiceProfile`` schema
and saves ``voice_profile.yaml`` (source of truth) + ``voice_profile.md``
(human-readable).

```
danapply voice set <payload.json> [--force]
danapply voice set - [--force]        # read JSON from stdin
```

- Validation errors are printed verbatim — fix the JSON and retry
- ``--force`` overwrites an existing voice profile
- 500+ word samples produce better profiles; tell the user if theirs is thin

### `danapply voice show` / `danapply voice clear`

Inspect or delete the captured voice profile.

---

## Parsing

DanApply never fetches websites — postings arrive as pasted text or
files. If the user gives a URL, ask for the posting text (or a saved
PDF) instead; keep the URL for the Job record's ``url`` field.

### `danapply parse`

Turn job postings (PDF, text file, .eml) into `Job` records via
deterministic heuristics.

```
danapply parse --batch DIR        # process every file in a directory (.pdf/.txt/.md/.eml)
danapply parse --file PATH        # one file
danapply parse --paste "TEXT"     # raw text paste
danapply parse --no-persist      # don't write to memory.db
danapply parse --json             # machine-readable output
```

Behaviour:
- Confidence markers in output: ``✓`` high, ``·`` medium, ``?`` low
- Failures collected and surfaced at the end — pipeline never halts on
  a single bad file
- **Medium/low-confidence parse?** Read the posting yourself, extract
  the fields properly, and re-store via ``danapply ingest`` — and put
  the ORIGINAL ``job_id`` (from the parse output) in your payload, so
  the corrected record merges instead of duplicating. Lifecycle fields
  (status, score, confidence) are guarded: a re-parse never downgrades
  them.

### `danapply ingest`

Store `Job` records that **you extracted in-conversation** — from
screenshots (Read the image directly), messy pastes, or postings whose
heuristic parse came back weak.

```
danapply ingest <job.json>          # one Job object or a list
danapply ingest - < job.json        # stdin
danapply ingest <job.json> --json   # machine-readable result
```

Field semantics (extraction rules — follow these exactly):
- ``title`` — as posted; strip prefixes like "Job Details:" / "Position:"
- ``company`` — the hiring entity, **never** the job board or recruiter
  platform (LinkedIn, SmartRecruiters, etc.)
- ``location`` — primary work location; for multi-location postings pick
  the most prominent Danish one
- ``posting_date`` / ``deadline`` — YYYY-MM-DD; **omit rather than guess**
  ambiguous dates ("two days ago" → omit)
- ``requirements`` — up to 10 verbatim, concrete requirements (skills,
  tools, years, language demands); skip soft platitudes ("team player")
- ``language`` — EN / DA / DE / HU / SV / NO / FI / OTHER
- ``description_raw`` — the full posting text
- ``source`` — where it came from, e.g. ``claude:screenshot``,
  ``claude:paste``, ``claude:email``
- ``job_id`` — leave empty for new jobs (the engine derives it); set it
  to the EXISTING id when re-ingesting a correction of a weak parse, so
  the records merge instead of duplicating
- Never invent a field that isn't in the posting; honest gaps beat guesses

### `danapply show`

Dump one job's full record as JSON — including ``description_raw``,
``requirements``, and the score breakdown. **Read this before writing
tailored prose or an interview brief.**

```
danapply show --job-id ID
```

---

## Scoring

### `danapply score`

Apply the 0-100 rubric (Role Fit 45 + Skills 25 + Company 20 +
Freshness 10) to parsed jobs.

```
danapply score                          # score all unscored jobs
danapply score --job-id ID              # score one specific job
danapply score --against PATH           # custom targets.yaml
danapply score --top-n N                # limit output to top N
danapply score --json
```

- Per-component rationale always shown; honest about heuristic limitations
- The skills component matches ``job.requirements`` against the user's
  curated keywords. If a score looks off, read the rationale — when the
  problem is missing/weak requirements, extract them yourself and
  ``danapply ingest``, then re-score

---

## Tailoring

### `danapply tailor`

Render CV PDF + cover letter PDF + notes markdown. **You write the prose;
the engine renders it.**

The real flow, per job:

1. ``danapply show --job-id ID`` — read the full posting
2. Read ``profile/voice_profile.yaml`` + ``profile/cv_content.md``
3. Write the prose per ``workflows/tailor.md`` (voice-matched,
   Danish-mode, every claim grounded in cv_content.md)
4. Save the content JSON to a temp file, then:

```
danapply tailor --job-id ID --content ~/danapply-data/sessions/payloads/<id>_content.json [--language EN|DA]
```

Content JSON shape (validated by the engine; errors printed verbatim):

```json
{
  "tagline":           "optional — per-job headline under the name; omit to fall back to profile.tagline_default",
  "summary":           "CV summary paragraph, 60-100 words",
  "opening_paragraph": "cover letter opening, 80-130 words",
  "key_strengths":     ["exactly", "four", "strength", "statements"],
  "themes": [
    {"heading": "4-8 words", "paragraph": "60-100 words"},
    {"heading": "...", "paragraph": "..."},
    {"heading": "...", "paragraph": "..."}
  ],
  "closing_tagline":   "optional — short cover-letter closing line; omit to skip the block"
}
```

There is **no tagline library in the engine** — write the per-job
``tagline`` / ``closing_tagline`` yourself per ``workflows/tailor.md``
(Step 2 / Step 5) and confirm them with the user.

Batch / fallback (templated prose, no ``--content``):

```
danapply tailor --top-n N
danapply tailor --all
```

- Output files: ``~/danapply-data/resume_drafts/<rank>_<slug>_cv.pdf``
  + ``~/danapply-data/cover_letters/<rank>_<slug>_cover.pdf``
  + ``~/danapply-data/cover_letters/<rank>_<slug>_notes.md``
- Status markers in CLI output: ``gen:claude/tmpl``, ``voice✓/—``,
  ``reg N/10`` (the rule-based register filter only runs on templated
  prose — your writing is expected to follow the register guide itself)
- A successful tailor advances the job's status ``parsed`` →
  ``tailored`` (later stages are never downgraded), so
  ``danapply list --status tailored`` shows what's drafted but not
  yet applied

---

## Lifecycle closers

### `danapply joblog`

Generate the Jobnet 'Opret Joblog' prompt for Claude in Chrome.

```
danapply joblog                                 # auto-pick scored ≥60
danapply joblog --threshold 70                  # custom threshold
danapply joblog --job-ids ID1,ID2,ID3           # explicit selection
danapply joblog --mark-logged --job-ids X,Y     # stamp jobnet_logged_at (no file generated)
```

- Output: ``~/danapply-data/joblog_prompts/jobnet_joblog_YYYY-MM-DD.md``
- Never overwrites; subsequent same-day calls write
  ``_supplement_1.md``, ``_supplement_2.md``, etc.
- ``--mark-logged`` requires ``--job-ids``, stamps the timestamp,
  advances early-stage statuses to ``applied``, and generates nothing.
  Use it ONLY after the user has pasted into Claude in Chrome and
  clicked Gem in Jobnet

### `danapply outcome`

Record outcomes on submitted applications.

```
danapply outcome --job-id ID --status STATUS [--notes "..."]
danapply outcome --list                                # show recent
danapply outcome --list --json
```

Valid statuses:
``interview_scheduled``, ``interview_completed_advancing``,
``interview_completed_rejected``, ``rejected_pre_interview``,
``ghosted``, ``offer_received``, ``offer_accepted``, ``withdrew``

### `danapply dagpenge`

Weekly dagpenge compliance status.

```
danapply dagpenge                  # this week
danapply dagpenge --history        # last 8 weeks
danapply dagpenge --history --weeks-back N
```

- Reads ``profile/dagpenge.yaml`` for threshold + state
- Counts ``jobnet_logged_at`` entries within Monday→Sunday bounds
- Reports days remaining + shortfall

### `danapply interview-prep`

Render a focused interview brief for one job. **You write the brief; the
engine renders it.** Read the job (``danapply show``) + the user's profile
first, then write company-specific content per
``workflows/interview_prep.md``:

```
danapply interview-prep --job-id ID --content ~/danapply-data/sessions/payloads/<id>_brief.json [--round 2]
```

Brief JSON shape:

```json
{
  "behavioural_questions": ["5-7, tied to the user's actual experiences"],
  "technical_questions":   ["3-5, matched to tools named in the posting"],
  "watch_outs":            ["3-6 honest concerns, not anxiety"],
  "questions_to_ask":      ["4-6 substantive questions"],
  "notes":                 "optional paragraph on tone/format"
}
```

Without ``--content`` a generic templated brief is produced (honest about
its limitations).

- Output: ``~/danapply-data/interview_prep/<company>_round<N>.md``

---

## Inspection / utilities

### `danapply list`

Read-only view of memory.db.

```
danapply list                           # 25 most recent
danapply list --limit 100
danapply list --status tailored         # filter by status
danapply list --json
```

### `danapply photo set`

Install a headshot as the CV profile photo. The engine centre-crops to a
square, resizes to render-optimal resolution (800px edge; never
upscales), saves ``profile/photo.jpeg``, and points ``profile.yaml``'s
``photo_path`` at it.

```
danapply photo set <path-to-headshot>
```

- Warns when the source is under 300px (soft in print) — relay that to
  the user and ask for a bigger one (≥400px square recommended)
- Errors readably on non-image files

### `danapply status`

One-screen overview: profile name + photo state, voice captured or not,
pipeline counts by status, five most recent jobs, dagpenge week (when
on dagpenge). The `/danapply:status` command builds its summary on top
of this.

```
danapply status
```

### `danapply delete`

Wipe the entire data directory — profile, voice, memory.db, every
generated file. **Irreversible.** Without ``--force`` it only prints
what would be removed.

```
danapply delete            # dry-run: shows what would be deleted
danapply delete --force    # actually deletes ~/danapply-data
```

Get the user's explicit confirmation in conversation before ever
running the ``--force`` form.

### `danapply db init` / `db status`

```
danapply db init        # idempotent schema scaffold + migrations
danapply db status      # show DB path, schema version, job count
```

### `danapply render-sample`

Smoke test for the renderer — confirms profile.yaml loads + PDF generation
works end-to-end. **Placeholder text only** — never hand its output to the
user as their CV; use `render-base` for that.

```
danapply render-sample [--output-dir DIR] [--tagline "OVERRIDE"]
```

### `danapply render-base`

Render the user's **real** base CV: the summary comes from
`cv_content.md` (`## Summary` — the CV session writes it), everything
else from `profile.yaml` (photo, links, experience, education, skills,
`cv_style`, `accent_color`). Errors if the summary was never written.
Output: `resume_drafts/base_cv.pdf`.

```
danapply render-base [--output-dir DIR] [--tagline "OVERRIDE"] [--style classic|minimal|modern|creative]
```

`--style` is a one-off override; without it the profile's `cv_style`
decides. Warns when no photo is configured — ask the user before
rendering text-only.

Output reports the page count and prints a ⚠ hint when the last page
holds only a line or two (`danapply tailor` prints the same hint per
CV). The fix is a one-line profile.yaml edit: `cv_font_scale: 0.95`
(allowed 0.8–1.05) shrinks fonts/spacing uniformly — propose it to the
user instead of waiting for them to notice.

### `danapply render-letter`

Render a standalone cover-letter PDF from prose **you** wrote — no job in
`memory.db` required. Use it for the first letter written during
onboarding, speculative applications, or any letter drafted outside the
pipeline. A letter must always ship as a PDF, never just markdown.

```
danapply render-letter PAYLOAD.json [--language EN|DA] [--output PATH] [--style ...]
```

Payload shape: `role_title`, `company_name`, `opening_paragraph`,
`key_strengths` (exactly 4), `themes` (exactly 3 heading/paragraph
objects), optional `tagline` / `closing_tagline` / `signoff`. Validation
errors print verbatim — fix the JSON and retry. Default output:
`cover_letters/<company>_<role>_cover.pdf`. The style follows
`profile.cover_letter_style` (falling back to `cv_style`) unless
`--style` overrides it.

### `danapply version`

```
danapply version    # prints: DanApply 0.3.0
```

---

## Exit codes

- ``0`` — success
- ``1`` — recoverable error (config missing, job not found, payload failed
  validation — the message tells you what to fix)
- ``2`` — invalid arguments (missing required flag, mutually-exclusive
  flags both set)
- ``130`` — Ctrl+C / interrupt

---

## Environment

- ``DANAPPLY_DATA_DIR`` — override the data dir (default ``~/danapply-data``)

No API key. The engine never calls a model — all judgment work happens
in this conversation.
