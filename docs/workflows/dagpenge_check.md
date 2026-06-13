# Workflow: dagpenge_check

DK-specific compliance tracker for users on unemployment benefits.
Reports week-to-date application count against the weekly threshold,
flags shortfalls with days remaining, and suggests jobs from recent
discovery to close any gap.

---

## Metadata

| Field | Value |
|---|---|
| Trigger | User asks; or session-start ritual surfaces a deficit; or end-of-week summary |
| Estimated duration | < 30 sec |
| Pause/resume | Not needed |
| Outputs | A short report; no file writes unless user requests a summary |
| Prereqs | `profile/dagpenge.yaml` exists |

---

## The dagpenge weekly requirement

For DK unemployment benefits (dagpenge), the user must log a minimum
number of *meaningful* job applications per week to their Jobnet account.
The default minimum is **2 per week**, but it can be higher depending on
the a-kasse and the user's My Plan.

What counts:
- A job logged to Jobnet through "Opret Joblog"
- Within the user's My Plan target field
- During the calendar week (typically Monday–Sunday in DK conventions)

What doesn't count (or is at risk of being challenged):
- Jobs significantly outside the My Plan field
- Roles where the user is clearly unqualified
- Duplicate logs of the same posting
- Late entries (logged after the week ended)

DanApply does not interpret a-kasse rules definitively — that's the
caseworker's job. It tracks what is most likely to count and flags
ambiguity.

---

## What this workflow does

Three actions, depending on context:

### Action 1 — Status report

Read `dagpenge.yaml`, count this week's joblog entries, compare to threshold:

```
"Dagpenge check, week of 9–15 June 2026 (today: Wed 11):

 Required this week:    2
 Logged so far:         1 (UNOPS, logged Tuesday)
 Pending submission:    2 (Flying Tiger, PwC — tailored not yet logged)
 Days remaining:        4 (until Sunday EOD)

 You're on track. Once you submit the 2 pending applications and log them,
 you'll be at 3/2 — comfortable margin."
```

### Action 2 — Shortfall warning

When the count is below threshold and time is short:

```
"Dagpenge check, week of 9–15 June 2026 (today: Sat 14):

 Required this week:    2
 Logged so far:         0
 Pending submission:    0
 Days remaining:        1 (Sunday)

 ⚠️ You need 2 logged applications by Sunday EOD to stay compliant.
 No applications in flight. Two options:

 1. Pull from your pipeline — you have 3 jobs scored ≥60 already
    parsed (TDC NET, Egon Zehnder, Danske Bank). I can tailor any
    two right now.
 2. Got new postings? Paste them or drop the files in raw_searches
    and I'll process, score, and tailor the best fits today.

 Which works?"
```

### Action 3 — My Plan alignment check

Before generating any joblog prompt, verify each job's title/field
against `dagpenge.yaml.my_plan_field`:

```
"Quick alignment check before I generate the joblog:

 Your My Plan field: Analyst, Economist, Business Researcher

 - TDC NET: Business Analyst — Tech & AI         ✓ fits
 - Telenor: Market Insights Analyst              ✓ fits
 - Imbox Protection: Strategy & PMO Associate    ⚠ 'PMO' could be questioned;
                                                   'Strategy' anchors it as
                                                   acceptable. Worth including
                                                   but mention 'strategy
                                                   analyst' framing if asked.

 Want me to proceed with all three, or skip Imbox?"
```

---

## How the count works

Week boundaries: **Monday 00:00 to Sunday 23:59** local DK time
(`Europe/Copenhagen`). The week starting tomorrow is "next week"
even if the user is logging tonight.

Count rules:

- Each row in `memory.db.applications` with a `jobnet_logged_at`
  timestamp in the current week → counts as 1 (this is exactly what
  `danapply dagpenge` computes)
- Each row with no `jobnet_logged_at` AND `status: tailored` → treat as
  **pending** in your report (will count once submitted and logged)
- My Plan alignment is your judgment call (Action 3) — the engine does
  not track it; flag questionable titles in conversation

---

## The "close the gap" suggestion logic

When the user is below threshold and asks for help:

1. Read `targets.yaml` and `memory.db.applications`
2. Pull the top-scoring unprocessed jobs (status `parsed`, never `tailored`)
3. Filter for ones that align with `my_plan_field`
4. Surface 2–3 candidates that are easy to tailor and submit fast

```
"To close the gap, here are 3 jobs from your pipeline that fit
 your My Plan and are quick to tailor:

 #1 (84) Telenor — Market Insights Analyst (deadline 3 June — TODAY)
    Strong fit, deadline today; would need to apply by EOD.

 #2 (79) Imbox Protection — Strategy & PMO Associate
    Aarhus-based, easy submission via LinkedIn.

 #3 (71) Trustpilot — Business Detection Analyst
    Hybrid CPH, fraud-detection angle is new but you have the SQL/data
    background.

 Tailor any of these?"
```

The suggestion is **bounded to ≤ 3 options** — too many feels overwhelming
when the user is stressed about a deadline.

---

## Tone calibration

Dagpenge compliance is **stress-adjacent**. The user is at financial risk
if the rule is broken. Tone needs to be calm and competent — not panicky,
not breezy.

✅ Do:
- Be specific about numbers, days, and what counts
- Give concrete next steps when behind
- Acknowledge the stress only if it's clearly there ("tight week — let's keep moving")

❌ Don't:
- "Don't worry, we'll figure it out!" (false reassurance)
- "You need to apply NOW or you'll lose benefits!" (panic-induction)
- Long explanations of the rules (the user already knows them)
- Cheerful framing ("Great progress!") on a stressful topic

---

## Push-back triggers

### When the user wants to log a job that doesn't align

> *"This job is outside your My Plan field. Logging it counts for now
> but your caseworker could question it. Two options: (1) keep it, accept
> the risk, log normally; (2) skip it and find a clearer match. Which?"*

### When the user has been hovering at minimum for weeks

If for 4+ weeks in a row the user has logged exactly 2 (no margin):

> *"You've been at exactly 2 logged applications for the last 4 weeks.
> That's compliant, but a single missed week would put you in trouble.
> Worth talking about either raising the cadence a bit, or looking at why
> the search isn't generating more applications you'd want to make."*

### When the threshold itself seems wrong

If the user's a-kasse has a custom threshold (some require 3+) and the
weekly_threshold value in `dagpenge.yaml` was guessed:

> *"Quick check — your weekly_threshold is set to 2. Is that confirmed
> with your a-kasse, or should I bump it? Some a-kasser require more."*

---

## Operational rules

1. **Never auto-generate applications to hit the number.** DanApply suggests; the user always decides. Quantity-padding undermines the search.

2. **Always honour the user's My Plan field.** Don't push jobs that fall outside it, even if they'd be high-fit otherwise.

3. **Always flag at-risk jobs in the count.** The user must see what could be challenged.

4. **Respect calendar weeks.** Don't shift weeks to make the numbers look better.

5. **Don't moralise.** If the user is behind because they're stressed or unmotivated, log the facts and suggest. Don't lecture.

6. **Surface proactively only when relevant.** On the session-start ritual, mention dagpenge only if:
   - The user is behind for the current week, OR
   - There are <48 hours until end of week and the user hasn't hit threshold yet, OR
   - The user just hit a milestone (first week, 10th week, etc.)

   Otherwise stay quiet.

---

## Edge cases

### Mid-week joblog status check

```
"Wednesday status: 1/2 logged. You've got 2 jobs tailored and ready to
 submit (Flying Tiger, PwC). Submit them and log this week — done."
```

### User completes the weekly count midweek

```
"Both logged. You're at 2/2 for the week with 4 days to spare. No
 compliance pressure for the rest of the week — use it for higher-fit
 applications, not more applications."
```

### User on dagpenge but with custom rules (e.g. activation programme)

If `dagpenge.yaml` has `activation_program: true` or similar fields:

```
"Note: you're on an activation programme — your case may have additional
 requirements beyond the weekly application count. I'm tracking applications
 only; check with your caseworker about activation-specific obligations
 (course attendance, meetings, etc.)."
```

### User has multiple a-kasser or mid-transition

Out of scope for v1. Log a note:

```
"Mid-transition between a-kasser — I'll keep tracking against the
 thresholds you set, but treat any compliance signal from me as
 informational only until you confirm with the new a-kasse."
```

---

## CLI calls used in this workflow

```bash
danapply dagpenge                            # current week status
danapply dagpenge --history                  # last 8 weeks
danapply dagpenge --history --weeks-back N   # custom window
```

Threshold or My Plan changes are config edits, not commands: update
`~/danapply-data/profile/dagpenge.yaml` (`weekly_threshold`,
`my_plan_field`) with the Edit tool and confirm the new values back to
the user. The "close the gap" and alignment checks are your judgment
calls built on `danapply list --json` output — there is no engine
command for them.

---

## Outputs

Default behaviour: spoken response only, no file writes.

If the user asks for history, summarise `danapply dagpenge --history`
in chat; optionally write `sessions/dagpenge_history_<date>.md` with
count vs threshold per week and any at-risk notes.

---

## What this workflow does NOT do

- Does not interact with the a-kasse or Jobnet directly.
- Does not interpret a-kasse-specific rules definitively. Surfaces facts, the user verifies with their caseworker.
- Does not auto-fill applications. (Hitting the count by spam-applying is a bad strategy and DanApply won't enable it.)
- Does not extend to other DK benefits (kontanthjælp, SU, etc.). Dagpenge only in v1.
