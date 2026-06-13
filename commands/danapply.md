---
description: Start a DanApply session — process, tailor, and track Danish job applications
---

You are starting a DanApply session. The DanApply skill (danapply) defines
the full behaviour — load it now if it isn't already in context, then run
its first-run / session-start ritual:

1. Check for a profile:
   ```bash
   test -f ~/danapply-data/profile/profile.yaml && echo exists || echo missing
   ```
2. **Missing** → the user has never onboarded. Verify the engine is
   available (`uv run --project "${CLAUDE_PLUGIN_ROOT}" danapply version`;
   run `danapply init` if the data dir doesn't exist yet), then conduct
   the onboarding interview **in this conversation** per the skill's
   `workflows/onboarding.md` — you ask the questions and write the
   profile YAML files yourself. Nothing else first. (Do NOT run
   `danapply onboard` — that is the standalone-terminal fallback and
   has no TTY here.)
3. **Exists** → run the session-start ritual from SKILL.md: read
   profile.yaml, targets.yaml, dagpenge.yaml (if present), check
   `danapply list --limit 5 --json` and `~/danapply-data/raw_searches/`
   for new files, then greet the user with one specific observation and
   one open question.

If the user passed arguments after /danapply, treat them as the first
user request (e.g. `/danapply here's a job posting…` → process it
instead of the greeting). DanApply is paste-first: it never crawls job
boards or fetches URLs — postings arrive as pastes, files, screenshots,
or job-alert emails.

$ARGUMENTS
