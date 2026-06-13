# DanApply Roadmap

This document tracks what's deferred from v1, what's planned for upcoming
versions, and what's deliberately out of scope.

The goal is honesty about what DanApply does and doesn't do, so users and
contributors can plan accordingly.

---

## Current scope (shipped, v0.3.0)

For reference, the current version includes:

- In-conversation onboarding interview with voice-profile capture
- Paste-first parsing (PDF, text, image via Claude, .eml email files)
- Scoring rubric tuned to user targets
- CV + cover letter tailoring (voice-preserving, Danish-mode calibrated,
  CV body rendered from profile.yaml experience/education)
- Canonical CV template (classic / modern / minimal / danish-formal:
  designed, not yet implemented)
- Jobnet joblog automation prompt generator
- Interview prep brief (triggered on user request)
- Outcome logging (applications + outcomes)
- Dagpenge compliance tracker (weekly count + history)
- Profile update flow
- SQLite memory + markdown audit trail
- Bilingual EN/DA outputs
- MIT licensed, fully local, no telemetry, **zero network access**

---

## Removed by design (not coming back)

**Job-board discovery / crawling** (Jobindex scraper, ATS watchlist,
URL fetching, and the once-planned STAR JobAdService / EURES / The Hub
feeds) was removed in v0.3.0. DanApply is paste-first: the user brings
the postings (paste, file, screenshot, job-alert email), the tool does
everything from there. The engine makes no network requests at all —
that's now a privacy feature, not a missing feature.

---

## v1.x — Confirmed upcoming (next versions)

### Networking module (DK-specific)

Networking is decisive in Denmark — many roles are filled before they're
publicly posted ("lukkede stillinger" / closed positions). DanApply should
support the networking side of the job search, not just the application
side.

Planned features:
- **Outreach tracking:** log every coffee invite, LinkedIn cold message,
  fagforening event, referral request — in the same memory model as
  applications
- **Templates** for DK-appropriate outreach (formal vs casual, EN vs DA,
  alumni vs cold)
- **Event tracking:** fagforening meetings, professional association
  events, sector conferences — flag relevant ones from the user's profile
- **Referral graph:** track who introduced you to whom, who has
  reciprocated, who hasn't (gently)
- **"Lukkede stillinger" angle:** when target companies the user follows
  are growing but not posting publicly, treat them as networking
  opportunities (user-reported signals — no crawling)

This is a big enough module to warrant its own `docs/networking-guide.md`.

### Jobindsats.dk labour-market enrichment

Pull DK labour-market statistics (unemployment by sector, time-to-hire,
salary bands, regional differences) and weave into research notes and
scoring colour.

- **Format:** REST/JSON, free, no agreement needed
- **Value:** richer research notes ("Insights Analyst openings in DK are
  up 15% YoY; median time-to-hire 47 days"); informed salary expectations
- **Priority:** lower than networking (interesting but not decisive)

### Voice-profile drift detection

DanApply already has the infrastructure in `update_profile.md` for
detecting voice drift in user cover letters. v1 ships this as a manual
check during update_profile; v1.x makes it automatic and surfaces
proactively when drift is meaningful.

### Interview roleplay

Currently `interview_prep` generates a written brief. v1.x adds an
optional roleplay mode: Claude plays the interviewer, the user practices
out loud (via Claude Code's voice mode if/when available, or via text).

Honest about its limits: it can't replace real interview practice with
humans, but it helps with structuring answers and getting comfortable
with the question types.

### Automated outcome reminders

When 4+ weeks pass since an application with no logged outcome:

> *"You applied to [Company] on [date]. No outcome logged. Want me to
> mark it as ghosted, or are you still expecting to hear back?"*

Helps keep the outcomes DB honest, which keeps the tagline-performance
metrics meaningful.

### Salary negotiation support

When the user gets an offer:

- Compare offered salary against `targets.yaml` band and against
  Jobindsats statistics for the role/region
- Generate negotiation talking points based on the user's actual leverage
  (other offers in pipeline, market data, scarcity of skills)
- Stop short of writing the negotiation email (the user owns this part)

---

## v2 — Possible future

### Other Nordic markets

DanApply's architecture is DK-first but the patterns generalise. v2 could
add:

- **Sweden (SE):** Arbetsförmedlingen, Academic Work, smaller Swedish boards
- **Norway (NO):** NAV, Finn.no jobs, smaller boards
- **Finland (FI):** TE-palvelut, Duunitori, Oikotie

Each market needs its own dedicated module — language conventions,
labour-market regulations, dominant job sites, and cultural register
all differ enough that a generic "Nordic" abstraction would oversimplify.

### Other EU markets

If there's interest from contributors:
- Germany (DE) — would need its own module given language complexity
- Netherlands (NL) — bilingual EN/NL market, similar to DK in structure
- Austria, Switzerland — German-speaking, often grouped with DE

DanApply will never try to be a "global" job tool. Each market gets a
focused module or doesn't get one.

### Multi-user / family / coaching modes

DanApply v1 is single-user. v2 could explore:

- **Family mode:** two partners job-searching together, shared dagpenge
  tracking, conflict-aware ranking (don't surface roles that would
  require relocation incompatible with the partner's plans)
- **Coaching mode:** a career coach or a-kasse advisor uses DanApply
  with their client; both can see the data; coach can add notes

Both would require careful thinking about consent, data separation, and
the line between tool-for-individual and tool-for-relationship.

### Mobile interface

v1 is keyboard-and-Claude-Code. A lightweight mobile companion (read-only
pipeline view, quick outcome logging, deadline reminders) could be
valuable. Would require server-side infrastructure, which conflicts with
the all-local principle — so this is a hard sell. Probably never happens.

### Calendar integration

For interview scheduling: auto-create calendar events from interview prep
briefs. Two-way sync with Google Calendar / iCal / Outlook. Useful but
introduces auth complexity. Possible if there's demand.

---

## Out of scope (forever)

These are intentionally not on the roadmap. Listed here so contributors
know not to PR them:

### Job-site scraping, at any scale

DanApply does **zero web fetching** as of v0.3.0 — and that's permanent.
Crawlers, watchlists, background polling, distributed scraping, or a
redistributable DK jobs database are all out of scope.

Reasons:
- Legal exposure (most sources prohibit it in ToS even when robots.txt
  is permissive)
- Reliability tax (parsers break on layout changes; maintaining
  industrial-scale scrapers is a full-time job)
- Ethical posture (we want to be a guest on these sites, not a leech)

### Auto-submission of applications

The user always reviews and submits. DanApply prepares; the human submits.

Reasons:
- Quality control (auto-submitted applications get caught and burn the
  user's reputation with that employer)
- Job sites' ToS prohibit it
- Dagpenge regulations require the applications to be the user's own
  choice and effort
- It's a bad incentive — quantity-over-quality applications hurt the
  user's search, not help it

### LinkedIn / Glassdoor / Indeed automation

These platforms aggressively block automated access. Workarounds are
fragile, legally exposed, and arms-race-prone. DanApply's posture is
to politely redirect ("paste the text instead") rather than play
cat-and-mouse.

If LinkedIn ever publishes an official partner API for individual
job-seekers, that changes the calculus.

### Cloud sync / SaaS

DanApply data stays local. Never on Anthropic's servers, never on a
DanApply server, never on AWS S3.

Optional git-backup is fine — that's the user's choice and stays on
their account. Anything more (login, multi-device sync, cloud profile)
is out of scope.

### Paid features

DanApply is FOSS. There will never be a Pro tier, a usage limit, a
"premium" template, or a paywall.

If someone wants to fork and build a paid product on top — that's the
MIT license at work. The original tool stays free.

### Job recommendations based on what other DanApply users applied to

Would require centralised data collection. Conflicts with all-local
principle. Not happening.

### Auto-writing personalised LinkedIn outreach at scale

LinkedIn's ToS prohibits it. Also: it's not networking, it's spam.
DanApply will help with one-at-a-time thoughtful outreach (in v1.x's
networking module), not bulk messaging.

### Resume keyword stuffing for ATS gaming

DanApply produces ATS-readable CVs (clean layout, no graphics-as-text,
selectable text in PDF). But it won't stuff keywords for ATS gaming.
That game produces worse outcomes than honest applications.

---

## Contribution-friendly roadmap items

If you want to contribute to DanApply, these are good entry points:

| Difficulty | What |
|---|---|
| Easy | Add a parser for a smaller DK board (jobsinaarhus.eu improvements, new EN-only boards) |
| Easy | Add a CV template (modern, minimal, danish-formal — designed but not built) |
| Easy | Improve Danish-register swap tables — add patterns the current guide misses |
| Easy | Documentation guides for specific user paths |
| Medium | Improve the smart-paste router — handle a new input shape robustly |
| Medium | Add a parser for an ATS system we don't yet handle (Personio, Recruitee, etc.) |
| Medium | Voice-profile drift detection |
| Hard | STAR JobAdService SOAP client + setup guide |
| Hard | Interview roleplay mode |
| Hard | Networking module (full design + implementation) |

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to propose and submit work.

---

## How priorities are decided

This is a personal project that became OSS. Priorities reflect:

1. **What real DK job-seekers need next** — based on issues, feedback,
   and the maintainer's own search experience
2. **What's defensible to ship** — features that don't compromise the
   privacy / honesty / no-scraping principles
3. **What's maintainable** — features that don't add a maintenance
   burden disproportionate to their value
4. **What the contributors actually build** — a working PR beats a
   planned roadmap item

If you want a feature that's not listed here, open an issue describing
the need. If it fits the principles, it can go on the roadmap. If it
doesn't, expect an honest "no" with the reasoning.
