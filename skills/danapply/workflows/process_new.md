# Workflow: process_new

The everyday workflow. The user has found jobs (saved as PDFs, pasted
text, screenshots, emails) and wants DanApply to parse, score, dedupe,
and return a ranked list. This is the entry point for most sessions
after onboarding.

**Paste-first, always.** DanApply never fetches websites. The user
brings the posting; you process it.

---

## Metadata

| Field | Value |
|---|---|
| Trigger | User adds files to `raw_searches/`, pastes content, drops image, or says intent matching `process_new` aliases |
| Estimated duration | 30 sec – 3 min depending on batch size |
| Pause/resume | Yes — partial batches can be processed |
| Outputs | Updates to `memory.db` (applications table — status `parsed`), your in-chat ranked report, optional `research_notes/<slug>.md` |
| Prereqs | Onboarding complete; `profile.yaml`, `targets.yaml`, `voice_profile.yaml` exist |

---

## The smart-paste router

DanApply's first job is to figure out **what the user just gave it** without
asking. The detection logic:

| Input shape | Routes to |
|---|---|
| `~/danapply-data/raw_searches/` contains new files | Batch mode: scan all new files |
| Pasted text starts with `http://` or `https://` | Not fetched — ask the user to paste the posting text instead (see below) |
| Pasted text > 200 chars and looks like prose | Paste mode: parse as job description |
| Image attached / dropped | Image mode: **you** read the image directly (Read tool), extract the fields, `danapply ingest` |
| `.eml` files in `raw_searches/` | Email mode: `danapply parse --batch` handles them |
| User asks to check job-alert emails | Email-connector mode (see below) |
| Pasted text matches "bundle pattern" (multiple jobs separated by blank lines, company names, etc.) | Bundle mode: parse as multi-job export |

The router is **silent**. Claude does not announce *"I detected this is a paste"* — it just acts. The user sees the result.

### URL handling

DanApply does not fetch URLs — any URL, any domain. When the user
pastes one, respond:

> *"I don't fetch pages — paste the text of the job ad instead (copy
> from the page, paste here), or save the page as PDF into
> `raw_searches/` and I'll parse that."*

Keep the URL itself: when you later `ingest` or the posting gets
parsed from a paste, store it in the `url` field so the joblog entry
links to the ad. No retries, no spoofed User-Agents, no exceptions.

### Email-connector mode (optional)

If — and only if — the session has an email MCP connector available
(e.g. a Gmail/Outlook connector the user has set up in Claude Code),
you may offer to read their **job-alert emails**: search for recent
alerts, extract each posting per the `ingest` field rules, and store
with `source: "claude:email"`. Read-only; never send, label, or delete
mail.

If no connector is available, the fallback is mechanical: ask the user
to save the alert emails as `.eml` files into `raw_searches/` and run
`danapply parse --batch` — the engine parses .eml natively.

---

## The pipeline

```
detect_input_type → parse → score → rank → present
```

### Step 1 — Parse

For file / paste inputs, run the heuristic parser:

```bash
danapply parse --batch ~/danapply-data/raw_searches/
# or
danapply parse --paste "$TEXT"
```

For **images** (and for any parse that comes back medium/low confidence,
marked ``·`` or ``?``): extract the fields yourself. Read the image or
posting text directly, build a Job JSON per the field rules in
`orchestration.md` (§ `danapply ingest`), write it to a temp file, and:

```bash
danapply ingest ~/danapply-data/sessions/payloads/ingest_<date>.json
```

Never guess dates; never put the job board in the `company` field; pull
up to 10 verbatim requirements — they drive the skills-match score.

**Re-ingesting a correction? Reuse the existing `job_id`.** The id is
derived from company + title + date, so if you fix a garbled field the
derived id changes and you'd create a duplicate. Find the original id
via `danapply list --json`, put it in the payload's `job_id` field, and
the upsert merges instead of duplicating.

A stored Job record looks like:

```json
{
  "job_id": "FertinPharma_SustainabilityDataAnalyst_2026-05-27",
  "title": "Sustainability Data Analyst",
  "company": "Fertin Pharma",
  "location": "Vejle, Denmark",
  "posting_date": "2026-05-27",
  "deadline": "2026-06-10",
  "source": "claude:paste",
  "url": "https://...",
  "language": "EN",
  "description_raw": "...",
  "requirements": [...],
  "data_confidence": "high"
}
```

If parsing fails for any single file/paste, log it and continue with the rest. **Never halt the batch.**

### Step 2 — Score

Apply the scoring rubric against `profile/targets.yaml` — 0–100:

- Role Fit (45 pts)
- Skills Match (25 pts)
- Company Fit (20 pts)
- Freshness (10 pts)

```bash
danapply score --json
```

### Step 3 — Dedupe (automatic)

Dedup happens inside the engine on every write: records upsert on
`job_id`, and the engine's lifecycle guards mean a re-parse of an
already-tracked posting refreshes `last_seen_at` and any newly-filled
fields but **never** resets `status`, `score`, or `data_confidence`.
Jobs the user already applied to / interviewed at keep their state —
just don't re-present them as new (check `status` in the
`danapply list --json` output).

### Step 4 — Rank

Sort by total score descending. Cap presented results at top 15.

### Step 5 — Present

Claude reports to the user. Tone-aware presentation.

---

## Presentation patterns

### Single job (smart-paste)

```
"Parsed. Fertin Pharma — Sustainability Data Analyst, Vejle.
 Scored 72/100. Strong tooling match (Excel/Power BI/Python),
 ESG domain is new to you. Closes 10 June — 14 days.

 Want me to tailor materials, or save and move on?"
```

### Small batch (2–5 jobs)

```
"Processed 4 jobs. Ranked:

 #1 (88) UNOPS — AI Business Analyst
 #2 (71) Flying Tiger Copenhagen — Business & Pricing Analyst
 #3 (65) PwC — Associate Strategy& Deals (deadline 15 June — 8 days)
 #4 (45) BNP Paribas — Graduate Analyst FX & EM (below your usual fit zone)

 Tailor any of these, or want details on a specific one first?"
```

### Large batch (6+ jobs)

```
"Processed 15 jobs (3 dropped at relevance filter — they were
 marketing/sales roles, not analyst). Top 10 ranked, full list
 in prioritized_lists/prioritized_jobs_2026-06-07.xlsx.

 Top 5:
 #1 (87) TDC NET — Business Analyst, AI & Automation
 #2 (85) Egon Zehnder — Business Analyst
 #3 (84) Telenor — Market Insights Analyst (deadline 3 June — 3 days)
 #4 (81) Danske Bank — Junior BA, Asset Finance Tribe
 #5 (79) Imbox Protection — Strategy & PMO Associate (Aarhus)

 Want me to tailor the top 3, or look at any specifically?"
```

### When parsing fails for some files

Always surface failures transparently, not buried in success summary:

```
"Processed 8 out of 10 files. 2 failed to parse:
 - 'broken_export.html' — unrecognised structure
 - 'screenshot_unclear.png' — Claude couldn't extract a job from this image

 Want me to look at the failures, or skip and rank what worked?"
```

---

## Tone calibration during presentation

Adjust report length and warmth based on dagpenge / stress signals from `profile.yaml`:

| Signal | Report style |
|---|---|
| Dagpenge with weekly deficit | Lead with how the new jobs help close the gap |
| Stress level 4–5 | Shorter report; top 3 only; offer to skip details |
| Search > 6 months | No mention of "great matches"; just facts |
| Default | Top 5 with one-line context; offer to tailor |

---

## Push-back triggers

### When top results look off-target

If the top 3 jobs are all from an industry the user excluded in `profile.yaml`:

> *"Worth flagging: the top 3 are all in [industry], which is on your excluded list. Either the listings drifted into your search, or you want to revisit that exclusion. Which?"*

### When a high-score job is paste-only-low-confidence

If a top-ranked job has `data_confidence: low` (e.g. parsed from a screenshot
with OCR errors):

> *"Top job here is McKinsey BA, scored 87 — but I parsed it from a screenshot
> and some text didn't come through clean. Worth double-checking the actual
> posting before I tailor anything."*

### When the batch contains likely duplicates of in-flight applications

> *"Two of these (Pleo Insights Analyst, Lunar Data Analyst) match jobs you've
> already applied to. Skipping them in the ranking. Want them shown anyway?"*

---

## Operational rules

1. **Never halt on a single parse failure.** Process what works, log what doesn't, surface failures explicitly at the end.

2. **Confidence levels matter.** Jobs parsed from PDFs or known ATS systems → `data_confidence: high`. Jobs parsed from OCR'd screenshots or pasted text without obvious structure → `data_confidence: medium`. Jobs where critical fields (title, company) are uncertain → `data_confidence: low`.

3. **Never tailor automatically.** Even on a perfect 95-score job. The user picks what to tailor. (Tailor is its own workflow.)

4. **Always write to `memory.db`.** Every parsed job gets recorded with `status: parsed`, even if the user doesn't tailor it. This prevents re-ranking in future sessions.

5. **Research notes are optional but cheap.** For jobs the user shows interest in, write a short `research_notes/<slug>.md` audit trail with the Write tool — useful for future tailor / interview-prep runs.

---

## Edge cases

### User runs process_new with empty `raw_searches/` and no paste

> *"raw_searches is empty and you didn't paste anything. Did you mean to drop a file in, or do you have a posting to paste?"*

### User pastes a job they've already applied to

Detect via `memory.db` match. Surface:

> *"You applied to this one on 2026-05-31 — it's already in your pipeline as 'submitted'. Want to mark a new outcome on it (interview / rejection / etc.), or re-process anyway?"*

If user says re-process: continue, but with a flag `re_parsed: true` for future-proofing.

### User pastes a job in a language other than EN/DA

> *"This posting is in [language]. I can still parse it, but the tailored materials would need to be in your applied language. Should I generate the CV/cover letter in English (your default), or do you actually need [other language]?"*

(DanApply v1 only supports EN/DA outputs. Other languages → tell the user.)

### User pastes the same content twice in a row

Detect via hash of normalised content. Don't reprocess:

> *"That's the same one you just pasted — already in this session's results."*

---

## CLI calls used in this workflow

```bash
danapply parse --batch <dir> --json           # batch mode (.pdf/.txt/.md/.eml)
danapply parse --paste "<text>" --json        # paste mode
danapply parse --file <path> --json           # single file

danapply ingest <job.json>                    # images / messy pastes / weak parses /
                                              # email finds — you extracted the fields

danapply score                                # apply scoring rubric to everything new
danapply list --limit 10                      # ranked view for the report
```

Dedup happens automatically on every persist (job_id is content-derived).
The user-facing report is yours to write — summarise from `danapply score
--json` output per the presentation patterns above.

Full argument details in `orchestration.md`.

---

## Outputs (after a process_new run)

```
~/danapply-data/
├── raw_searches/                        # files processed; consider archiving older ones
├── research_notes/
│   └── FertinPharma_SustainabilityDataAnalyst.md   # optional, for jobs of interest
├── memory.db                            # applications table updated
└── sessions/
    └── _run_summary_2026-06-07.md       # appended to (or created)
```

---

## What this workflow does NOT do

- Does not generate CVs or cover letters (`tailor` workflow does that).
- Does not fetch the web — no job-board crawling, no URL fetching, ever.
- Does not log applications as "submitted" (`joblog_prompt` + `log_outcome` do).
- Does not run on every session start — only when the user adds content or asks.

The default state after process_new: jobs are parsed, scored, ranked, and waiting in the pipeline. The user picks what to do next.
