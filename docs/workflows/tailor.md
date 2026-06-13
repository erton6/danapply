# Workflow: tailor

Generate a tailored CV and cover letter for one or more parsed jobs. This
is where the voice profile, the Danish-mode register filter, and the user's
`cv_content.md` come together into actual application materials.

---

## Metadata

| Field | Value |
|---|---|
| Trigger | User selects jobs to tailor from a ranked list, or directly invokes ("CV for [company]") |
| Estimated duration | 30 sec per job (parallelisable across jobs) |
| Pause/resume | Yes — partial batches OK |
| Outputs | One CV PDF, one cover letter PDF, one notes markdown per job |
| Prereqs | Onboarding complete; target job(s) already parsed and in `memory.db` |

---

## Inputs

- One or more `job_id`s from the user's pipeline
- The user's `profile/cv_content.md`
- The user's `profile/voice_profile.md`
- The user's `profile/targets.yaml` (informs tagline/skill-order selection)
- The job's parsed metadata + description (from `memory.db` and `research_notes/<slug>.md`)

---

## The three tailoring levers

Per `PROMPT.md` Step 7, tailoring adjusts only specific facets per job. The
underlying truth (experience, dates, education, references) **never changes**.

1. **Tagline** under the name (one of ~6 standard options, or custom).
2. **Summary paragraph** — rewrite to mirror the job's language and emphasise the most relevant facet of the user's profile.
3. **Skills order** — reorder Research / Commercial / Stakeholder buckets based on the role.
4. **Optional bullet overrides** — rephrase existing bullets, never invent new ones.

The cover letter has more tailorable slots: opener, four strengths, three theme heading/paragraph pairs, closing tagline. All drawn from `cv_content.md` and research notes — never fabricated.

---

## The pipeline

```
load_inputs → choose_tagline → draft_summary → order_skills →
draft_cover_letter → apply_voice_profile → apply_danish_register →
render_pdfs → write_notes
```

### Step 0 — Pre-render checks (once per session, never skip)

Before rendering anything, check the profile is presentation-ready:

1. **Photo.** If `profile.yaml` has no `photo_path` (or the file is
   missing), ask: *"Most Danish CVs include a photo, top-right. Want to
   add one before I render? A recent headshot works — `danapply photo
   set <path>` installs it."* Render text-only only after the user
   explicitly says skip — never silently.
2. **Design confirmed.** If the user has never been asked about style and
   colour (fresh profile still on the defaults), run the design questions
   from `cv_session.md` Step 1b: CV style (classic / minimal / modern /
   creative — match the work environment they're applying to), accent
   colour (dark green `#1F4737` default — ask explicitly), and whether
   the cover letter matches the CV style. All presets are ATS-friendly;
   say so. Write the answers to `profile.yaml`.
3. **Portfolio.** If `profile.yaml` has no `portfolio` block, ask before
   generating: *"Do you have a portfolio or a single piece online — a
   case study, dashboard, repo, published article? Paste the link and it
   goes in a highlighted clickable block on both documents."* If yes →
   write `portfolio.display` + `portfolio.href` to `profile.yaml`. If
   no → the section is omitted from the PDFs entirely (no empty box),
   and give the friendly nudge from `cv_session.md` Step 1 once per
   session: a portfolio is genuinely useful in DK hiring, and one good
   anonymised case study is enough to start. Never block the render on
   it, never invent a URL.

Ask once, remember for the session. The engine reads `cv_style` /
`cover_letter_style` / `accent_color` / `portfolio` from `profile.yaml`
on every render.

### Step 1 — Load inputs

For each job to tailor:

- Read `profile/cv_content.md`, `voice_profile.yaml`, `targets.yaml`
- Read `research_notes/<slug>.md` (for company context, if present)
- Read the job's full record: `danapply show --job-id <id>`

### Step 2 — Write the tagline

The tagline is the headline under the user's name on both the CV and the
cover letter. **There is no tagline library — you write one per job**,
grounded in the user's profile and the role's character:

- Research-heavy role → lead with the user's analytical / research identity
- Strategy / consulting → lead with their advisory / problem-solving identity
- Content / communication → lead with their narrative / communication identity

Shape: 5–10 words; the "Role identity | what you deliver" pattern works
well in DK. Same register rules as everything else — no superlatives.
It's a title, not a sentence: **no trailing full stop** (the engine
strips one if it slips through).

**Confirm with the user before rendering:** show your suggestion next to
their `tagline_default` from profile.yaml and let them pick or edit. If
they'd rather keep their default, omit the `tagline` field from the
content JSON — the engine falls back to `profile.tagline_default`. Log
the choice in the notes file so future renders stay consistent.

### Step 3 — Draft summary

Length: 4–6 sentences. Content rules:

- Lead with the facet of the user's profile most relevant to the role
- Mention the user's most recent role (from `profile.yaml` experience /
  `cv_content.md`) with the framing that fits this posting
- Include their education where it strengthens the case
- Close with a forward-looking line if natural

**Strict rule:** every sentence in the summary must trace to
`cv_content.md` or `profile.yaml`. If a fact isn't there, don't say it.
Period.

### Step 4 — Order skills

Three skill buckets exist in `cv_content.md`:
- Research & Analysis
- Business & Commercial Insight
- Stakeholder Engagement & Communication

Reorder based on the role:

| Role character | Order |
|---|---|
| Pure data / research analyst | research → commercial → stakeholder |
| Strategy / consulting analyst | research → stakeholder → commercial |
| Content / communication-heavy | stakeholder → commercial → research |
| Product / commercial analyst | commercial → research → stakeholder |
| Generalist BA | research → commercial → stakeholder (default) |

Skill paragraph **content** within each bucket can be lightly rephrased per role (e.g. emphasising specific tools), but the underlying facts never change — they come from `cv_content.md` and `profile.user_skills`, nowhere else.

### Step 5 — Draft cover letter

Use the canonical 5-block structure from `voice_profile.md`:

1. **Opener** (3–5 sentences) — custom for the job. The "digitalisation default" opener from `cv_content.md` is the fallback when the role is about digitalisation/strategy/transformation. For other contexts (sustainability, pricing, fraud detection, etc.), write a fresh opener that:
   - Names a genuine insight about the field
   - Connects to the user's actual skills
   - Ends with the explicit purpose — but the application statement must
     **grow out of the preceding thought**, never appear bolted on.

   **Anti-pattern (never do this):** an insight or anecdote, then an
   abrupt "I am applying for the {RoleTitle} role at {CompanyName}"
   that doesn't follow from anything before it:

   > *"…the interesting work was not writing the queries — it was
   > calibrating the output to how teams actually made decisions. I am
   > applying for the Digital Transformation Analyst role at FairWind."*

   The second sentence appears out of nowhere. Instead, make the purpose
   the *conclusion* of the line of thought — name what the insight has
   to do with this role at this company:

   > *"…the interesting work was not writing the queries — it was
   > calibrating the output to how teams actually made decisions. That
   > calibration work is what the Digital Transformation Analyst role
   > at FairWind seems to centre on, and it is why I am applying."*

   Read the opener back as one paragraph before packaging it: if the
   application sentence could be deleted without leaving a logical
   hole, it isn't connected yet — rewrite it.

2. **Four strength bullets** — drawn from the user's actual experiences (cv_content.md), tailored to the posting's listed requirements. Never invent.

3. **Three theme blocks** — heading + paragraph pairs:
   - First theme: the user's strongest selling point for *this specific role*
   - Second theme: stakeholder / cross-functional angle
   - Third theme: personal qualities + forward-looking close

4. **Closing tagline** (the short line that anchors the letter) — write
   one per job in the user's voice: 4–8 words, role-toned, no
   overclaiming. It renders as a centred **title** above the letter —
   no trailing full stop (the engine strips one if it slips through).
   Offer it to the user alongside one alternative; they pick, edit, or
   skip. If skipped, omit the `closing_tagline` field — the letter
   renders cleanly without one.

**Punctuation rule — no em-dashes by default.** Do not use em-dashes
(—) anywhere in the cover letter. They are the single most recognisable
AI-writing tell, and recruiters have seen thousands of them this month.
Restructure with a comma, a colon, a full stop, or two sentences. The
only exception: the user's own voice sample uses them — then match the
user's actual frequency, not yours.

### Step 6 — Apply voice profile

Run the draft cover letter (and summary) through `voice_profile.md` for **style normalisation**:

- Sentence rhythm matches the user's baseline
- Vocabulary preferences enforced (use words the user uses; avoid words they don't)
- Opening style matches user's pattern (anecdote / claim / question)
- Direct quotes from `voice_profile.md` pattern-matched against the draft — if the draft has phrasings that diverge from the user's known voice, flag for revision

Style-preservation is the moat. Without it, generated letters sound like ChatGPT — which recruiters spot in two seconds.

Grammar is silently corrected. Characteristic patterns (slightly non-native English rhythms for internationals, hedging that's typical for the user, etc.) are preserved.

### Step 7 — Apply Danish-mode register

If the target is a Danish employer (any of: company has DK address, posting in DA, employer is on the "Danish-founded" list like Novo Nordisk / Maersk / LEGO), apply the calibration from `danish_register_guide.md`:

- Strip superlatives, intensifiers
- Replace US-power verbs with calibrated alternatives
- Convert "I am skilled at X" → "experience with X / Y / Z"
- Convert self-praise → third-party voice where possible
- Strip filler phrases ("self-starter", "results-driven", etc.) entirely

The register applies to:
- CV summary paragraph
- CV skills paragraphs
- Cover letter throughout
- Tagline

The register does **not** apply to:
- The user's actual experience bullets (those are facts)
- Job titles, company names, dates
- Education content

See `danish_register_guide.md` for the full swap tables.

### Step 8 — Hand the prose to the engine

You wrote the prose in Steps 3–7. Package it as the content JSON and let
the engine render the PDFs:

```json
{
  "tagline":           "the per-job headline from Step 2 (optional — omit to use profile.tagline_default)",
  "summary":           "the CV summary paragraph from Step 3",
  "opening_paragraph": "the cover letter opener from Step 5",
  "key_strengths":     ["the", "four", "strength", "bullets"],
  "themes": [
    {"heading": "first theme heading", "paragraph": "first theme body"},
    {"heading": "second theme heading", "paragraph": "second theme body"},
    {"heading": "third theme heading", "paragraph": "third theme body"}
  ],
  "closing_tagline":   "the per-job closing line from Step 5 (optional — omit to skip)"
}
```

```bash
# write the JSON to a temp file, then:
danapply tailor --job-id <job_id> --content ~/danapply-data/sessions/payloads/<job_id>_content.json [--language EN|DA]
```

The engine validates the shape (exactly 4 strengths, exactly 3 themes —
errors are printed verbatim so you can fix and retry), applies your
taglines (falling back to `profile.tagline_default` when omitted), picks
the skills order, renders both PDFs with the user's photo / accent
colour / references, and writes the notes file. The structural layout
never changes.

Because you already applied the voice profile (Step 6) and the Danish
register (Step 7) **at writing time**, the engine skips its rule-based
register filter on your prose — `gen:claude` in the output confirms the
path taken.

### Step 9 — Review the notes file

The engine writes the audit trail automatically:

```
~/danapply-data/cover_letters/<rank>_<slug>_notes.md
```

It contains the score breakdown, tailoring choices (tagline, skills
order), voice + generation markers, and file paths. Add anything the
engine can't know — company-values concerns, weak-fit areas worth
flagging, research-note context — by appending to the file after the run.

### Step 10 — Get the user's verdict (never skip)

Rendering is not the end of the workflow. Ask the user to actually open
the PDFs and react, every time:

> *"Open the CV and the cover letter and tell me honestly — does this
> sound like you? Anything you'd change: the tagline, the opener, a
> bullet, the whole angle?"*

**And tell them the formatting is adjustable — nothing is written in
stone.** Mention it explicitly when handing over the files: the style
preset, accent colour, and font size can all change after the fact with
a quick re-render. Watch the engine's layout hints and proactively
propose fixes:

- The tailor/render output prints a ⚠ when the CV spills only a line or
  two onto an extra page. Don't wait to be asked: *"The CV runs a couple
  of lines onto page 2 — I can shrink the font a touch
  (`cv_font_scale: 0.95`) or trim one bullet so it sits on two clean
  pages. Want me to?"*
- Same for second thoughts about the look: *"If the navy feels off or
  you want it more minimal, say so — changing it is one line and a
  re-render."*

- Requested changes → edit the content JSON, re-run `danapply tailor
  --content` (same job_id overwrites the files), and ask again.
- Iterate until the user says it's good. Only then offer the next step
  (joblog prompt / submission).
- If the user spots a profile-level problem (wrong fact, stale
  experience), fix `profile.yaml` / `cv_content.md` first, then re-render.

---

## Presentation patterns

### Single job tailored

```
"Done. Files saved:
 - resume_drafts/01_FertinPharma_SustainabilityDataAnalyst_cv.pdf
 - cover_letters/01_FertinPharma_SustainabilityDataAnalyst_cover.pdf
 - cover_letters/01_FertinPharma_SustainabilityDataAnalyst_notes.md

 Tagline: [the per-job tagline you agreed in Step 2]
 Skills order: Research → Commercial → Stakeholder
 Custom opener tied to CSRD + GHG Protocol (named in the posting).

 Open both PDFs and tell me — does it sound like you? Anything to
 change before we call it done?"
```

### Multiple jobs tailored

```
"Tailored 3 jobs:

 #1 UNOPS — AI Business Analyst
    tagline: [per-job tagline #1]
    custom opener: AI scale-up + evidence-based decision-making

 #2 Flying Tiger — Business & Pricing Analyst
    tagline: [per-job tagline #2]
    custom opener: pricing as a quantitative+commercial+stakeholder loop

 #3 PwC — Associate Strategy& Deals
    tagline: [per-job tagline #3]
    custom opener: commercial DD at the intersection of three skills

 All files in resume_drafts/ and cover_letters/. Have a look at each —
 which ones are right, and which need another pass?"
```

---

## Push-back triggers

### When the job is below threshold

If the user asks to tailor a job that scored < 60:

> *"This one scored [X]/100 — below your usual fit zone. The main gaps are
> [specific from research notes]. I can still tailor it, but worth knowing
> you're spending effort on a long shot. Still want me to proceed?"*

If yes → proceed. If no → cancel.

### When two jobs in the batch are near-duplicates

If the user wants to tailor two roles that are almost identical (same company, similar title, e.g. "Business Analyst" and "Senior Business Analyst" at the same place):

> *"These two are very similar — same company, overlapping role. Want one
> custom-tailored version for each (more work, possibly clearer fit), or
> one shared package you submit to both (less work, slight risk of mismatch)?"*

### When the user requests something that breaks voice

If user says "make it more formal" but the voice profile is casual-warm:

> *"That'd take it further from your natural voice. I can lean slightly
> more formal while staying in your register, or I can override the voice
> profile for this one job — but the override would only apply here, not
> become your new default. Which?"*

---

## Operational rules

1. **Never fabricate.** Every sentence in the CV and cover letter must trace to `cv_content.md` (for user content) or research notes (for company specifics). If a fact isn't there, don't say it.

2. **Never auto-tailor.** Even on a perfect 95-score job. Tailoring is the user's explicit request.

3. **Never override voice profile globally.** Per-job adjustments OK; global voice changes only via `update_profile`.

4. **Always write all three files.** CV + cover letter + notes. Even if user only asked for one — the others are cheap to produce and useful later.

5. **Always log the tailoring choices in the notes file.** This is the audit trail for "why does this CV look this way?" months later.

6. **Always update `memory.db`.** Status: `parsed` → `tailored`. Records which tagline / skills order / opener type was used (for tagline-performance tracking later).

7. **Hard layout rules from `PROMPT.md`.** Two-page CV, photo top-right with accent-coloured ring, plain section headers, "▸" bullets, PORTFOLIO block. The user's `cv_style` preset and `accent_color` vary the design touches; the structural layout never changes.

---

## Edge cases

### Job is in Danish, user's voice profile is from an English-language exercise

> *"This posting is in Danish. Your voice profile was captured from English
> writing. I'll generate the cover letter in Danish using calibrated Danish-
> mode register, but the tone won't be as personalised as your English
> outputs. Want me to proceed, or would you rather draft a Danish-language
> sample first to extend your voice profile?"*

### User wants to tailor a job not yet parsed

> *"That one's not in your pipeline yet. Want me to parse it first, then
> tailor? Paste the URL or text."*

(Chain to `process_new` first.)

### User wants only the cover letter, not the CV

The engine always renders the full bundle (CV + cover letter + notes) —
the extras are cheap and useful later. Point the user at the file they
asked for; mention the others exist.

### User asks for a different look

Four style presets exist: `classic`, `minimal`, `modern`, `creative` —
set via `cv_style` / `cover_letter_style` in `profile.yaml` (the engine
picks them up on every render; one-off overrides via
`danapply render-base --style <name>`). All are ATS-friendly. If the
user asks for something beyond these (multi-column, graphics, photos in
the body), be honest: that would hurt ATS parsing, and DanApply won't do
it.

---

## CLI calls used in this workflow

```bash
danapply show --job-id <id>                                  # read the posting before writing
danapply tailor --job-id <id> --content <prose.json>         # render your prose (the real flow)
danapply tailor --job-id <id> --content <prose.json> --language DA   # force language
danapply tailor --top-n 5                                    # batch, templated prose (fallback)
danapply tailor --all                                        # everything in memory.db, templated
```

Full argument details + content JSON schema in `orchestration.md`.

---

## Outputs (after a tailor run for one job)

```
~/danapply-data/
├── resume_drafts/
│   └── 01_FertinPharma_SustainabilityDataAnalyst_cv.pdf
├── cover_letters/
│   ├── 01_FertinPharma_SustainabilityDataAnalyst_cover.pdf
│   └── 01_FertinPharma_SustainabilityDataAnalyst_notes.md
└── memory.db                            # applications: status → 'tailored'
```

---

## What this workflow does NOT do

- Does not submit applications.
- Does not log to Jobnet (that's `joblog_prompt`).
- Does not fetch new jobs.
- Does not change the user's profile or voice.
- Does not modify `cv_content.md` (that's `update_profile`).

The default state after `tailor`: materials are ready, sitting in the user's `resume_drafts/` and `cover_letters/` folders, waiting for the user to review and submit.
