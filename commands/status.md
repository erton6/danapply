---
description: What have we been working on? Pipeline, recent activity, compliance
---

Give the user a clear picture of where their job search stands. Load the
danapply skill if it isn't in context, then:

1. Run `danapply status` (engine snapshot: profile, pipeline counts by
   status, most recent jobs, dagpenge week).
2. Run `danapply outcome --list --json` for recent outcome events.
3. Read the most recent file(s) in `~/danapply-data/sessions/` for what
   the last session worked on.

Then summarise conversationally — not a data dump:

- What happened recently (last tailored jobs, outcomes received)
- What's in flight (applied, awaiting response; interviews coming up)
- What needs attention (deadlines inside 7 days, dagpenge shortfall,
  applied >14 days ago with no outcome — possible ghost worth logging)
- One suggested next action, framed as an offer

Tone per `tone_spec.md`: calm, specific, no cheerleading. If there is no
profile yet, say so and offer onboarding instead.

$ARGUMENTS
