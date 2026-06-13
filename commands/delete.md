---
description: Delete the DanApply profile and all data (irreversible)
---

The user wants to wipe their DanApply data. This is irreversible, so:

1. Tell them exactly what goes: the entire `~/danapply-data/` directory —
   profile, captured voice, memory.db (every tracked application and
   outcome), all generated CVs, cover letters, and Jobnet prompts.
2. Ask for explicit confirmation in their own words. A bare "ok" on an
   ambiguous question is not enough; "yes, delete everything" is.
3. On confirmation, run:

   ```bash
   danapply delete --force
   ```

4. Confirm what was deleted and offer the two restart paths:
   - `danapply init` + onboarding for a fresh profile
   - `claude plugin uninstall danapply@danapply` (run by the user in
     their terminal) if they also want the plugin itself gone — that
     part is theirs to run, not yours.

If they only want to reset part of it (e.g. just the voice profile →
`danapply voice clear`, or just re-onboard → keep memory.db and rebuild
the profile in conversation), offer that instead of the full wipe.

$ARGUMENTS
