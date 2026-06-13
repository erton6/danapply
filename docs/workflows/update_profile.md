# Workflow: update_profile

A re-entry to onboarding for users who have already completed it.
Pre-fills previous answers and lets the user update only what's changed.
Designed for quarterly check-ins or whenever life circumstances shift.

This is a **variant** of `onboarding.md`, not a separate flow.
Read `onboarding.md` for the full chapter detail; this file documents
how update mode differs.

---

## Metadata

| Field | Value |
|---|---|
| Trigger | User says "update my profile", "my situation changed", "re-do onboarding", "I got a new job", "I'm no longer on dagpenge", etc. |
| Confirms before running | **Yes** — destructive to current profile if user proceeds without backup |
| Estimated duration | 10–20 min (skips chapters that don't change often) |
| Pause/resume | Yes, after every chapter |
| Outputs | Updated `profile.yaml`, `targets.yaml`, conditionally `voice_profile.md`, `cv_content.md`, `dagpenge.yaml`; previous versions archived in `sessions/profile_history/` |
| Prereqs | A complete profile already exists |

---

## Pre-flight: archive current state

Like onboarding, update mode runs **in this conversation** — you ask
about what changed and edit the YAML files in place with the Edit tool.

Before any changes, archive the current profile with plain shell:

```bash
mkdir -p ~/danapply-data/sessions/profile_history/$(date +%F)
cp ~/danapply-data/profile/*.yaml ~/danapply-data/profile/*.md \
   ~/danapply-data/sessions/profile_history/$(date +%F)/
```

This copies the current state of:

- `profile.yaml`
- `targets.yaml`
- `voice_profile.yaml` + `voice_profile.md`
- `cv_content.md`
- `dagpenge.yaml` (if exists)

To:

```
~/danapply-data/sessions/profile_history/<YYYY-MM-DD>/
├── profile.yaml
├── targets.yaml
├── ...
└── archived_at.txt
```

This is non-negotiable. The user gets a 1-line confirmation before any
chapter starts:

> *"Archiving your current profile to `sessions/profile_history/2026-06-10/`
> before we update. If anything in the new pass goes wrong, you can roll
> back. OK to continue?"*

---

## Which chapters get re-run

Update mode skips the chapters that don't typically change between
quarterly check-ins, and focuses on the ones most likely to:

| Chapter | Re-run in update mode? |
|---|---|
| 0 — Welcome | Skip (the user already knows what this is) |
| 1 — Where you stand | **Yes** (employment status changes often) |
| 2 — Your story so far | Skip (career history adds incrementally; user offers a delta) |
| 3 — What you're aiming for | **Yes** (targets evolve) |
| 4 — Constraints & red lines | **Yes** (visa, language, exclusions can change) |
| 5 — Honest self-assessment | Optional — user is asked if anything has shifted |
| 6 — Reality-check synthesis | **Yes** (always — show updated picture) |
| 7 — DK admin | **Yes** (dagpenge status, a-kasse, My Plan can change) |
| 8 — CV calibration | Optional — only if user adds a new CV file |
| 9 — Voice exercise | Skip — voice doesn't drift quickly. **Unless** the user requests it explicitly, or DanApply detects voice drift (see below). |
| 10 — Wrap-up | **Yes** (always) |

Default duration: ~15 min for Chapters 1, 3, 4, 6, 7, 10 plus optional 5–10 min for 5/8/9 if triggered.

---

## The delta-capture pattern

For each re-run chapter, Claude presents the existing answer first, then
asks what's changed:

```
"Quick refresh — last time we talked, you were:

 - Employment status: unemployed
 - Search duration: 3 months
 - Stress level: 3/5
 - Triggered by: contract ended

 What's different now?"
```

User can:

- Say "nothing changed" → keep as is, move on
- Say "I'm now employed" → update employment status, recalculate search duration (probably 0)
- Say "still searching but the contract started so I'm employed-while-searching" → update with a more specific status
- Add detail → "still on dagpenge but I'm starting an unpaid internship next week"

The capture is conversational; the YAML update happens silently after.

---

## Career-history additions (Chapter 2 variant)

Chapter 2 is skipped by default, but the user can offer additions:

```
Claude: "Career history same as last time — NordRetail, Lisbon Media Group, Iberia Insights?"

User: "I finished the NordRetail internship in May and started at Copenhagen Insights
       as a contractor in June."

Claude: "Got it. Adding:
        - Contractor at Copenhagen Insights, June 2026 – present, [location?].
        Update NordRetail to: Marketing Analyst (Internship), 2024, ended.
        Want to tell me about Copenhagen Insights — what the role involves, what's energising/
        draining about it so far?"
```

The user fills in just the delta; everything else stays.

---

## Voice profile drift detection

This is the one place where update mode does something onboarding doesn't:
**detect when the user's voice has drifted**.

How: Claude compares recent cover-letter drafts (the user's own writing
captured in cover_letters/*.md) against `voice_profile.md`. If the markers
have shifted significantly — different vocabulary, different sentence
rhythm, different formality level — Claude surfaces it:

```
"Quick observation: your last 4 cover-letter drafts have moved toward
 shorter sentences (avg dropped from 19 words to 13) and you've started
 using 'I have' more than 'I am' as the opening pattern. Your voice
 profile from onboarding doesn't capture this shift.

 Want to do a quick refresh of the voice exercise? It'd take 15 minutes
 and the next cover letters would feel more like your current voice. Or
 leave it and we can do it later."
```

The detection runs on the **last 5 drafts**. If the drift is mild or
inconsistent, Claude doesn't flag it. Only meaningful, directional shifts
trigger the surface.

---

## Dagpenge transition handling

Special case: user is **transitioning into or out of dagpenge**:

### Just started dagpenge

```
Claude: "You're newly on dagpenge — congratulations on getting set up
        with the a-kasse, that paperwork is annoying. Two things I need
        to capture:

        1. Which a-kasse?
        2. What's the job title or field on your My Plan (Min Plan)?
        3. When did dagpenge start, and what's your weekly application
           requirement (usually 2)?

        After this I'll set up the compliance tracker."
```

Creates `dagpenge.yaml` for the first time.

### Just got off dagpenge (got a job)

```
Claude: "You're off dagpenge — that's a real win. Confirm before I close
        the compliance tracker:

        - Last day on dagpenge: [date]?
        - New employer: [Copenhagen Insights, per chapter 2]?
        - Want me to archive the dagpenge.yaml history, or keep it
          accessible in case the new role doesn't work out?"
```

Archives `dagpenge.yaml` to `sessions/profile_history/`. The compliance
tracker goes dormant but data is retained.

### Mid-search but no longer on dagpenge for other reasons

(Sanctions, switching a-kasser, taking unpaid leave, etc.)

```
Claude: "You're still searching but off dagpenge — let me make sure I
        understand the situation. Are you between a-kasser, on a break,
        or has something else changed? The compliance tracker pauses
        either way; I just want to capture the situation correctly."
```

---

## Push-back triggers

### When the user wants to update targets but their stories haven't changed

If the user shifts targets dramatically without changing career history:

> *"You're shifting from 'analyst' to 'product manager' as the primary
> target — that's a big move. Walk me through what changed. Did you do
> a project recently that pulled you that direction, or is it more a
> realisation about what you want?"*

This is push-back as honest curiosity, not blocking. The user can answer
and DanApply updates targets.

### When the user wants to make the profile less accurate to seem more competitive

If the user asks to remove or downplay an honest constraint (e.g. "drop
'intermediate Danish' and just say 'fluent' — I'm close enough"):

> *"I'd rather not. Overclaiming on languages is one of the easiest
> things for a DK recruiter to test in the first interview. If you're
> close to B2 we can call it 'intermediate, actively improving' (true)
> rather than 'fluent' (overclaim). The honest version is also doing
> better in DK recruiter conversations than the inflated one."*

Drop the push-back if the user insists. It's their profile.

### When the user has gone through a major life event

If the user mentions parental leave, illness, bereavement, etc.:

> *"Sorry to hear that. Want to keep going with the update now, or come
> back later? There's no rush on this — your previous profile is still
> valid until we change it."*

---

## Operational rules

1. **Always archive before updating.** Non-negotiable. The user must be able to roll back.

2. **Always show the previous answer before asking for the new one.** Delta-capture is faster and more accurate than starting fresh.

3. **Don't re-run chapters that don't need it.** Respect the user's time.

4. **Voice exercise is opt-in.** Only re-run if user requests it or drift is detected.

5. **Profile history is forever.** Never delete archived versions.

6. **Treat life events with care.** This isn't a CRM update — these are personal facts about someone's working life. Sensitivity matters.

---

## Quarterly check-in suggestion

After onboarding, `profile.yaml` includes a `last_updated` timestamp. On
session start, if more than 90 days have passed:

```
"It's been 4 months since we last updated your profile. Want to do a
 quick refresh? Takes about 10–15 minutes and keeps everything aligned.
 Or skip and we can do it whenever."
```

Default to skip — never block.

---

## Edge cases

### User says "update" but means "fix one specific thing"

```
User: "Update my profile — my German is now B2 not B1."

Claude (does a minimal update, not a full re-run):
  "Done. German updated to B2 in profile.yaml. Anything else, or move on?"
```

Don't force a full update flow for a single-field change.

### User wants to delete their profile entirely

```
User: "Erase everything and start over."

Claude: "Sure. Before I do, want me to archive the current state to
        profile_history first? That way you can pull facts back in if
        the new pass is incomplete. Yes/no?"
```

After confirmation: archive, then re-run full onboarding.

### Profile has been corrupted or partially written

If `danapply` detects malformed YAML in profile files:

```
"Something's off with your profile.yaml — looks like a YAML syntax
 error around line 23. Want me to restore from the most recent archive
 (last updated 2026-05-14) and apply your recent changes again?"
```

---

## CLI calls used in this workflow

```bash
danapply render-sample        # validate the edited profile renders cleanly
danapply voice set <payload>  # only if the voice exercise is re-run
```

Everything else is conversation + the Edit tool on the profile YAMLs.
Archive/rollback is plain `cp` from `sessions/profile_history/<date>/`.
A full erase + re-onboard means: archive, delete the profile files,
re-run `danapply init`, then the in-conversation onboarding interview.

---

## Outputs (after update)

Same structure as onboarding, with archived previous versions:

```
~/danapply-data/
├── profile/                          # updated to current
│   ├── profile.yaml
│   ├── targets.yaml
│   ├── voice_profile.yaml            # only changed if voice exercise re-run
│   ├── cv_content.md                 # only changed if CV recalibrated
│   └── dagpenge.yaml                 # updated or removed
└── sessions/profile_history/
    └── 2026-06-10/                   # archived previous state
        ├── profile.yaml
        ├── targets.yaml
        ├── voice_profile.md
        ├── cv_content.md
        ├── dagpenge.yaml
        └── archived_at.txt
```

---

## What this workflow does NOT do

- Does not run automatically. Always user-triggered.
- Does not modify generated artifacts (CVs, cover letters) from previous applications. Past outputs are historical.
- Does not interact with external services (a-kasse, Jobnet, etc.) — only updates local state.
- Does not nag for updates. Suggests at 90+ days, accepts a skip without further prompting.
