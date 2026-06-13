---
description: Skip the ceremony — paste a posting, get a tailored CV + cover letter
---

Fast path: the user has one job posting and wants materials NOW. Load the
danapply skill if it isn't in context, then compress the normal flow:

1. **Intake.** Take whatever came with the command (pasted text,
   screenshot, file path). Extract the fields yourself and store via
   `danapply ingest` (or `danapply parse --paste/--file` for clean
   input). If nothing was provided, ask for the posting — one line, no
   ritual. URLs: ask for the pasted text instead; DanApply never fetches.
2. **Skip:** scoring commentary, fit push-back, research notes,
   session greeting. (The engine still scores silently on ingest — fine.)
   **Don't skip the pre-render checks** (`workflows/tailor.md` Step 0):
   if the profile has no photo, ask once before rendering; if style and
   accent colour were never confirmed, ask the compact design questions
   (CV style, base colour, letter-matches-CV) — one message, then render.
3. **Write the content** per `workflows/tailor.md` Steps 2–7, but
   without intermediate confirmations: draft the per-job tagline,
   summary, opener, four strengths, three themes, and closing tagline in
   one pass — voice-matched, Danish-mode, every claim traceable to
   `cv_content.md` / `profile.yaml`.
4. **Render:** `danapply tailor --job-id <id> --content <payload>`.
5. **Deliver + verdict.** Hand over both PDF paths and ask the one
   question that still matters: *"Open them — anything to change?"*
   Iterate if yes.

Quickapply skips ceremony, not honesty: never fabricate, never skip the
final does-it-sound-like-you check.

Requires an onboarded profile. If `~/danapply-data/profile/profile.yaml`
is missing, say quickapply needs a profile first and offer onboarding
(~30 min, one-time).

$ARGUMENTS
