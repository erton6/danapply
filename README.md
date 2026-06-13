# DanApply

**A job-application co-pilot for the Danish job market, built as a
Claude Code plugin.**
Python 3.11+ engine • MIT license • No API key required

> *"DanApply's job is to be a clear surface. Reflect what's there.
> Suggest next steps. Push back honestly. Stay out of the way otherwise."*

[![tests](https://img.shields.io/badge/tests-305_passing-green)]()
[![coverage](https://img.shields.io/badge/coverage-77%25-green)]()
[![python](https://img.shields.io/badge/python-3.11+-blue)]()

> **New here and not very technical?** Start with
> **[GETTING_STARTED.md](GETTING_STARTED.md)** — a plain-language,
> step-by-step manual from "nothing installed" to your first application.

---

## What it does

A personal pipeline that takes you from "I saw a job posting" to
"application submitted, Jobnet logged, interview prepared", without the
busywork in between. You talk to it in Claude Code:

```
/danapply
› Morning, Sofia. Two new PDFs in raw_searches/ and the Pleo deadline
  is Friday. Got new postings for me, or something specific?

You: process the new files and tailor the top 3
› (parses the PDFs, scores everything against your targets, writes
   three voice-matched cover letters, renders the PDFs, and tells you
   exactly what it did and why)
```

**Intake is paste-first.** DanApply never crawls job boards or fetches
URLs — you bring the postings (paste, file, screenshot, or job-alert
email) and it does everything from there.

Claude does the judgment work **in your session** — reading postings,
writing cover letters in your voice, prepping interviews. The bundled
Python engine does the mechanical work — parsing PDFs, the 0-100 scoring
rubric, SQLite memory, PDF rendering, Jobnet prompts, dagpenge math.

**Every workflow is real and works today.** New here? See
[GETTING_STARTED.md](GETTING_STARTED.md) for a plain-language setup walkthrough.

---

## What's distinctive

**No API key. No second AI.** Other "AI job tools" proxy your data
through their backend and bill you for tokens. DanApply's language work
happens inside the Claude Code session you already have. The engine
never calls a model.

**Voice preservation.** DanApply captures how you actually write
(sentence rhythm, vocabulary, opening style, characteristic phrases —
analysed by Claude from a sample you provide) and every generated cover
letter is written against that profile. Your applications sound like
you, not like an AI template.

**Danish-mode register.** Cover letters are written to what DK
recruiters actually respond to: no overclaiming (`exceptional`,
`proven`, `world-class`), no US-power verbs (`spearheaded` → `co-led`),
factual structure over self-promotion. The register rules are part of
the writing instructions, not a find-and-replace afterthought.

**Jobnet integration.** Auto-generates the "Opret Joblog" prompt for
Claude in Chrome — your dagpenge weekly count happens at the speed of
paste, not the speed of typing.

**Honest scoring.** A transparent 0-100 rubric (Role Fit 45 + Skills 25 +
Company 20 + Freshness 10) with per-component rationale, computed
deterministically. When the heuristic is the weak link, Claude says so
and fixes the inputs instead of hiding it.

**Local-first.** All data lives in `~/danapply-data/`. No telemetry. No
cloud sync. No paywalls. No network access at all — the engine never
fetches anything.

---

## What it isn't

- **Not a scraper.** Zero web fetching. You bring the postings; DanApply
  processes them.
- **Not an auto-submitter.** Prepares applications; you review + submit.
- **Not a generic résumé builder.** Opinionated about Danish-mode register.
  Won't produce overclaiming CVs.
- **Not a SaaS.** Runs entirely on your machine, inside your Claude Code
  session.

---

## Who it's for

- **Internationals moving to / already in Denmark** searching for analyst,
  consultant, researcher, or insights roles.
- **Danes** who want a structured pipeline that respects their voice.
- **People on dagpenge** who need weekly compliance tracking + Jobnet
  automation that works for them, not against them.

---

## Install

**Non-technical? → [GETTING_STARTED.md](GETTING_STARTED.md)** walks you
through everything (installing Claude Code, `uv`, and the plugin) in
plain language.

**Quick version** (assumes [Claude Code](https://code.claude.com/docs/en/setup)
and [`uv`](https://docs.astral.sh/uv/) are installed):

```bash
claude plugin marketplace add erton6/danapply
claude plugin install danapply@danapply
```

Then type `/danapply` in Claude Code. The Python engine builds itself on
first run via `uv` — no manual setup step. See **[`INSTALL.md`](INSTALL.md)**
for the technical reference.

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  CLAUDE CODE (the interface AND the writer)          │
│  • reads skills/danapply/ (SKILL.md + workflows)     │
│  • analyses voice samples, extracts jobs from        │
│    screenshots, writes cover letters + briefs        │
│  • hands structured JSON to the engine               │
└──────────────────────────────────────────────────────┘
                 ↓ Bash: danapply <command>
┌──────────────────────────────────────────────────────┐
│  PYTHON ENGINE (deterministic machinery)             │
│  • parse / ingest / score / show / list              │
│  • tailor --content / interview-prep --content       │
│  • joblog / outcome / dagpenge                       │
│  • voice set / init for one-time setup               │
└──────────────────────────────────────────────────────┘
                 ↓ reads/writes
┌──────────────────────────────────────────────────────┐
│  USER DATA (~/danapply-data/)                        │
│  profile/ + raw_searches/ + memory.db (SQLite)       │
│  + resume_drafts/ + cover_letters/ + joblog_prompts/ │
└──────────────────────────────────────────────────────┘
```

The split is strict: Claude owns everything that needs judgment, the
engine owns everything that must be deterministic and auditable. Prose
crosses the boundary as validated JSON (`--content` flags), so files,
dedup, and the audit trail stay consistent.

---

## Getting jobs in

DanApply is deliberately paste-first — no crawling, no URL fetching:

| You bring | DanApply does |
|---|---|
| Pasted posting text | Heuristic parse → score → pipeline |
| Files in `raw_searches/` (PDF / TXT / MD / EML) | Batch parse → score |
| Screenshot of a posting | Claude reads the image, extracts fields, stores via `ingest` |
| Job-alert emails | Save as `.eml` and batch-parse — or, if your Claude Code session has an email connector, Claude reads the alerts directly |
| A URL | Not fetched — paste the text instead (the link is kept for the Jobnet log) |

---

## Privacy & ethics

- All data is local. Profile, applications, outcomes — everything stays
  in `~/danapply-data/` on your machine.
- No telemetry, no tracking, no analytics. DanApply doesn't phone home.
- No third-party AI backend. Your writing sample and applications are
  seen only by the Claude session you're already in.
- No web access. The engine makes zero network requests — nothing to
  fetch, nothing to leak.
- Never invent personal data. Every CV claim traces to your
  `cv_content.md`; contact people, phones, emails are never fabricated.
- Never auto-submit. You review every application before it goes out.
- Voice profile is sacred. Generated text preserves your authentic voice.
  Calibration only adjusts overclaiming, not personality.

---

## Roadmap

See [`ROADMAP.md`](ROADMAP.md) for what's coming. Highlights:

- **Networking module** — DK-specific networking: coffee invites,
  fagforening events, kollega referrals, "lukkede stillinger".
- **Voice-profile drift detection** — flag when your writing has shifted
  significantly.
- **Other Nordic markets** — SE / NO / FI equivalents.

(Job-board discovery/crawling was removed by design in v0.3.0 — intake
is paste-first and stays that way.)

---

## Contributing

DanApply is built for the Danish job market. Contributions welcome in:

- Parsers for additional DK-specific sources
- CV layout templates (classic, modern, minimal, danish_formal — designed,
  not yet implemented)
- Improvements to the Danish-mode register guide
- Documentation guides for specific user paths
- Bug reports on parser edge cases against real job postings

Out of scope (don't PR): job-site scraping at scale, auto-submission, cloud
sync, paid features, non-DK markets in v1.

---

## Status

| Version | Tests | Status |
|---|---|---|
| v0.5.3 | 305 passing | **Current** — standalone letters, base CV from real content, style presets + accent colour, portfolio handling, formatting controls |
| v0.4.0 | 275 passing | Identity-first onboarding, Unicode PDFs, per-job taglines, photo flow |
| v0.3.0 | 261 passing | Paste-first intake, profile-driven CV body, in-conversation onboarding |

DanApply is in pre-alpha, validated against fictional-profile end-to-end runs.

---

## License

[MIT](LICENSE) — do what you want, with attribution. No warranty.

---

## Acknowledgments

Built by [erton6](https://github.com/erton6) for the Danish job
market, with help from Claude Code. If DanApply helps you land a role
in DK, that's the win.
