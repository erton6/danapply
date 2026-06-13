# Workflow: log_outcome

Record an outcome on a previously submitted application. This feeds the
memory layer that lets DanApply learn which kinds of applications convert
and which don't — the foundation for the tagline-performance feature.

---

## Metadata

| Field | Value |
|---|---|
| Trigger | User reports any outcome: "I got rejected", "they ghosted", "I got an offer", "moved to next round", "first interview went well" |
| Estimated duration | 30 sec |
| Pause/resume | Not needed (single-shot) |
| Outputs | `memory.db` updates: `applications`, `outcomes`, `tagline_performance`; optional brief response from Claude |
| Prereqs | The relevant application exists in `memory.db` |

---

## The outcome taxonomy

DanApply tracks five outcome categories. They're a deliberate simplification
of reality (lots of edge cases collapse into one of these):

| Status | What it means | Triggers learning? |
|---|---|---|
| `interview_scheduled` | Got the invite, interview not yet held | Yes — positive signal on the application |
| `interview_completed_advancing` | Did the interview, moved to next round | Yes — strong positive signal |
| `interview_completed_rejected` | Did the interview, didn't advance | Yes — application got attention but didn't land |
| `rejected_pre_interview` | Rejection without interview (form letter or silence becoming explicit) | Yes — likely the application itself didn't resonate |
| `ghosted` | No response after the user's defined threshold (default 6 weeks) | Yes — same as rejection but ambiguous |
| `offer_received` | Got an offer | Strongest positive signal |
| `offer_accepted` | Accepted and starting | Pipeline can be paused/archived |
| `withdrew` | User pulled out before completion | Doesn't feed learning |

The user reports the outcome in natural language; Claude maps it to one of
these statuses.

---

## Trigger detection and mapping

| User phrasing | Maps to status |
|---|---|
| "I got an interview" / "they invited me" | `interview_scheduled` |
| "first interview went well", "moved to next round" | `interview_completed_advancing` |
| "interview didn't go anywhere", "got a no after interview" | `interview_completed_rejected` |
| "rejected", "got the rejection email", "they said no" | `rejected_pre_interview` (if no interview happened) or `interview_completed_rejected` (if it did) |
| "no response from", "still nothing from X" + > 6 weeks since application | `ghosted` |
| "got the offer", "they offered me the role" | `offer_received` |
| "I'm accepting", "starting at X in [month]" | `offer_accepted` |
| "I withdrew", "I'm not pursuing this anymore" | `withdrew` |

If phrasing is ambiguous, ask one clarifying question rather than guess.

---

## The interaction pattern

The workflow is intentionally low-friction. Three turns max:

```
User: "I got rejected by Lunar"

Claude (looks up Lunar in memory.db, finds 1 active application):
  "Logged. Lunar — Insights Analyst, applied 2026-05-14, rejection
   without interview. That's the third 'rejected pre-interview' this
   month in the data-analyst track — worth talking about your CV
   positioning if you want, or just move on?"

User: "Move on"

Claude: "OK. Let me know what's next."
```

Or, when the user wants to reflect:

```
User: "I got the offer from UNOPS!"

Claude (looks up UNOPS, status was 'interview_completed_advancing'):
  "That's a real win. Logging it. Want to talk through the offer
   terms, or is that for later? Also — if you're going to accept,
   I'll archive the rest of your active pipeline. Your call."

User: "Need to think about the offer. Don't archive yet."

Claude: "Got it. Stays active. Anything you want to capture about
         the offer terms while it's fresh?"
```

---

## The optional "what happened" capture

After logging an outcome, Claude can offer (not require) a short reflection:

- For positives: "Anything that surprised you about how this went?"
- For interview-related rejections: "Did they say what tipped the decision? Useful for the rest of the pipeline."
- For ghost/silent rejection: nothing — there's nothing useful to capture, and pushing for reflection here feels invasive

Captured reflections go into a `notes` field on the outcome row. Free-text;
not parsed structurally.

---

## Pattern analysis (your job, not the engine's)

There is no aggregate-stats table — the raw material is
`danapply outcome --list --json` (every outcome event) plus each job's
notes file in `cover_letters/` (which records the tagline and skills
order used). When the user asks pattern questions, or every ~10
outcomes, do the analysis yourself:

- *"For consulting-track roles, which tagline gets the most interviews?"*
- *"Has my ghost rate gone up in the last 30 days?"*

Surface findings when they're relevant (e.g. before tailoring the next
batch), not on every turn.

```bash
danapply outcome --job-id <id> --status <status>
danapply outcome --job-id <id> --status <status> --notes "<text>"
danapply outcome --list --json                  # raw material for analysis
```

---

## Push-back triggers

### When the user reports an outcome very quickly after applying

If the user says "rejected" on an application submitted < 24h ago:

> *"That's fast — were they actively rejecting, or did you maybe pull
> the application yourself? Just want to make sure I log the right thing."*

### When the user has multiple "ghosted" in a row

If 3+ consecutive `ghosted` outcomes show up:

> *"Three ghost responses in a row. That's normal volume for a job
> search but worth checking the pattern — are they all the same company
> type or language? Sometimes a string of silences means the CV is
> being filtered out at the screening stage. Want to look at it?"*

### When the user gets a clear win after a long dry spell

If the search duration is > 4 months and the user reports their first
interview or offer:

> *"That's significant. After [N] months of mostly silence, this one
> landing. Want to talk about what was different — or just enjoy it?"*

Soft, brief, not performative.

---

## Operational rules

1. **Map carefully.** Don't auto-map ambiguous phrasings. If "I got a no" could mean pre-interview rejection or post-interview rejection, ask.

2. **Update `memory.db` atomically.** Both the `applications` row and the `outcomes` row update in one transaction; tagline-performance updates after.

3. **Don't editorialise on negative outcomes.** Log it, move on. The user doesn't need DanApply telling them rejection is a learning opportunity.

4. **Surface patterns sparingly.** If the data shows something notable (multiple ghostings, sudden success), say it once, factually. Don't dwell.

5. **Never auto-archive on offer-accepted.** Always ask: "Want me to archive the rest of your pipeline?" Some users prefer to keep them alive as backup.

6. **Capture timing.** Time-from-application-to-outcome is a useful metric for ghosting thresholds. Track it.

---

## Edge cases

### User reports an outcome for a job not in the pipeline

```
"I don't have [Company] in your applications. Did you apply through a
 different channel? Want me to create a backfill record so we can
 log this outcome — title, date applied, anything else you remember?"
```

Branch to a quick backfill flow, then log the outcome.

### User changes a previously logged outcome

Common: ghost → rejection ("the rejection email finally came"), or
interview-rejected → offer ("they reconsidered and came back").

```
"Updating from 'ghosted' to 'rejected_pre_interview' on [Company].
 Want to capture anything about the timing? Could be useful pattern."
```

Or:

```
"Wait — they came back with an offer after a previous rejection?
 That's rare. Updating to offer_received. Want to add notes on what
 changed?"
```

### User reports multiple outcomes in one message

```
"OK, three updates:
 1. Lunar — interview rejected
 2. Templafy — moved to second round
 3. Pleo — ghosted (logging at 7 weeks, past your threshold)

 Confirm I got them right?"
```

Process them as a batch after confirmation.

### User reports an outcome from someone *else's* application

(Friend asks for advice on their job search.) Log it under a temporary
`user_id: friend_alice` namespace if the feature exists, or just decline:

> *"I'm built around your pipeline — I can't track other people's
> applications cleanly. If you want to talk through the strategy in
> general terms, happy to, but I won't log it."*

---

## The learning surface

Once enough outcomes are logged (~20+), DanApply can start surfacing
insights when relevant:

- Before tailoring: *"For consulting-track roles, your 'Analyst & Consultant'
  tagline has a 40% interview rate; your 'Analyst & Researcher' tagline
  has 22%. Want me to lean to the first one for this McKinsey-adjacent
  role?"*
- Before applying: *"You've ghosted on 6 of the last 8 EN-only DK roles
  in the marketing-adjacent space. Either the CV isn't landing for that
  vertical, or those roles weren't great fits to begin with. Worth a
  check?"*
- Periodic check-in: *"Quick stat — your interview rate is 18% overall
  this quarter, which is roughly normal for your seniority and search
  conditions. Don't read too much into recent silences."*

These insights surface **at most once per session** and only when they're
genuinely useful. Not on every turn — that would be exhausting.

---

## CLI calls used in this workflow

```bash
danapply outcome --job-id <id> --status <status>                  # log basic outcome
danapply outcome --job-id <id> --status <status> --notes "<text>" # with reflection
danapply outcome --list                                           # recent outcomes
danapply outcome --list --json                                    # machine-readable, for analysis
```

Correcting a previous outcome: log a new event with the right status —
the latest event wins on `applications.status`, and the full history
stays in the `outcomes` table. Off-pipeline job (applied outside
DanApply): `danapply ingest` it first, then log the outcome. Ghost
detection and pipeline archiving after an accepted offer are your
judgment calls in conversation, logged as ordinary `ghosted` /
`withdrew` outcomes per job.

---

## What this workflow does NOT do

- Does not auto-detect outcomes. Only logs what the user reports.
- Does not chase up silent applications. (Future v1.x feature: gentle reminder when X weeks pass.)
- Does not change CV / cover letter content based on outcomes. Voice profile is sacred.
- Does not run scheduled. Only on user trigger.
