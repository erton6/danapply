---
description: Show the application pipeline as a tracker board
---

Show the user's full application pipeline. Load the danapply skill if it
isn't in context, then:

1. `danapply list --limit 100 --json` for every tracked job
2. `danapply outcome --list --json` for outcome history

Present a tracker view grouped by stage, newest first within each group:

```
PARSED (scored, not yet tailored)
  78  Senior Analyst — Acme A/S          deadline 2026-06-20
TAILORED (materials ready, not submitted)
  ...
APPLIED (submitted / logged to Jobnet)
  ...
INTERVIEWS
  ...
CLOSED (offers, rejections, withdrawn, ghosted)
  ...
```

Per row: score, title, company, and the single most useful date
(deadline before applying; applied/logged date after; outcome date when
closed).

After the board, flag — only if present:
- deadlines within 7 days on PARSED/TAILORED jobs
- APPLIED jobs >14 days without an outcome (*"want me to log these as
  ghosted, or still hoping?"*)
- anything in INTERVIEWS without an interview-prep brief

Offer one next action; let the user pick. Outcomes are recorded via
`danapply outcome --job-id <id> --status <STATUS>`.

$ARGUMENTS
