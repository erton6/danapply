# Workflow: interview_prep

Triggered when the user reports an interview invitation. Generates a focused
preparation brief: likely questions, things to watch for, what to ask the
interviewer, and the company-specific context to revisit.

This is one of the highest-value workflows because **the user is usually
short on time** (interview in 2–5 days) and DanApply already has all the
company research in memory.

---

## Metadata

| Field | Value |
|---|---|
| Trigger | User says "I got an interview", "they invited me", "[company] wants to talk", "interview prep for X" |
| Estimated duration | 2–5 min generation, 30–60 min for user to review |
| Pause/resume | Yes — user can return to the brief any time |
| Outputs | `interview_prep/<company>_<role>_<date>.md`, status update in `memory.db` |
| Prereqs | The relevant job exists in `memory.db`; the more research notes exist, the better |

---

## Trigger detection

The interview-prep trigger is **time-sensitive**, so Claude should be liberal
about detecting it. From `triggers.yaml`:

- "I got an interview"
- "they invited me to talk"
- "[Company] wants to interview me"
- "interview tomorrow at"
- "I have a case interview"
- "scheduled an interview"
- "first interview went well, second round next week" → also triggers prep for the next round

If the phrasing is ambiguous (could be a new invite or a casual mention),
ask one clarifying question:

> *"To make sure I run the right thing — do you want me to prep for an
> interview (which company?), or are you logging an outcome on an
> existing application?"*

If the user says "interview" but DanApply can't find the company in
`memory.db`:

> *"I don't have [Company] in your pipeline. Did you apply through a
> different channel, or want me to parse the job posting first so I have
> the context for prep?"*

---

## Information gathering

Once the company and role are confirmed, Claude pulls:

### From local state (already in DanApply)

- `memory.db.applications` row for this job (score, date applied, status)
- `research_notes/<slug>.md` — full company context from the parse + score step
- `cover_letters/<rank>_<slug>_notes.md` — what was emphasised in the application
- `profile/profile.yaml` — user's actual experience, energy markers, self-assessment

### From external sources (low-budget, focused)

- One Google news scan: `"{company}" 2026` → recent activity, layoffs, leadership changes
- LinkedIn employee count check (if accessible) → growth signals
- The Hub profile (if applicable) → scale-up signals
- Glassdoor interview reviews (if accessible — usually paste-only) → process insights

**Budget:** 3–5 external fetches max (WebSearch / WebFetch). The point is
to refresh recent context, not to redo all the research.

---

## The brief structure

Every brief has the same 6 sections:

### 1. Snapshot (one paragraph)

Reminds the user what they applied for and the key context:

```
You applied to McKinsey for the Business Analyst – Tech & AI role
(Budapest | Warsaw) on 2026-05-17. The role focuses on AI use case
development, requirements gathering, and process analysis. McKinsey
recognised your CCO endorsement during application review (inferred
from the invite-quickness). Interview: case-based, expect 2–3 rounds.
```

### 2. Likely behavioural questions (5–7)

Drawn from the role + the user's profile:

```
Behavioural questions to expect:

1. "Walk us through a time you turned ambiguous requirements into a
   structured deliverable." [The NordRetail campaign-dashboard project is
   the obvious story.]

2. "How do you make sure AI use cases deliver real business value, not
   just technical novelty?" [Your NordRetail + Lisbon Media Group coverage
   gives you a real take here — combine the practitioner perspective with
   the editorial "show me the receipts" instinct.]

3. "Describe a project where you had to align multiple stakeholders with
   different priorities." [Your editorial-campaign coordination +
   cross-team stakeholder work are the story.]

4. "Tell us about a time you challenged a senior colleague's assumption."
   [If you have one — the Iberia Insights market-sizing work might fit.
   If not, prepare an honest "I'm still building this muscle" answer.]

5. "Why McKinsey, specifically?" [Your three-part answer from the
   application is the foundation; expect them to push on specifics.]

6. "What's an analytical method you've used that most peers haven't?"
   [Quantitative methods from your MSc. Be ready to explain customer
   segmentation in non-technical terms in 60 seconds.]

7. "Describe a failure and what you learned from it." [Default story
   from your self-assessment in profile.yaml.]
```

### 3. Likely technical / case questions (3–5)

Role-specific:

```
Technical / case questions to expect:

1. "How would you scope an AI use case for a client?"
   Frame: business problem → data availability → success criteria →
   risk assessment → MVP. Reference your NordRetail segmentation work
   as a concrete example.

2. "Walk us through how you'd analyse [some business question]."
   Standard case structure: clarify → structure → analyse → synthesise.
   For Tech & AI cases specifically: include data sources, model choice
   rationale, and how you'd validate results.

3. "A client wants to deploy an AI chatbot. What questions do you ask
   first?" Show humility about AI limits + sharpness about use-case fit.

4. "Walk us through your CV." 3-minute version. Practice this — most
   people overcomplicate.

5. (For technical case interviews) Pen-and-paper Excel logic, simple
   estimation problems, market sizing. Standard MBB stuff.
```

### 4. Watch out for (red flags + context)

Pulled from research notes and updated with recent news scan:

```
Watch out for:

- McKinsey's interview process is famously selective — multiple rounds
  with case + fit + values screens. The case rounds matter most.
- The Tech & AI practice has been expanding aggressively in 2025–2026.
  Recent press: "Generative AI Practice expansion" (Bloomberg, 2026-03).
- Travel expectation: typical McKinsey is 3–4 days/week at client site.
  Confirm Budapest vs Warsaw office at offer stage.
- Hungarian fluency was a posting requirement — they may test this in
  the interview. Be ready to switch languages.
- The case interview can include behavioural pressure ("you're losing
  the room") — stay grounded, don't rush.
```

### 5. Questions to ask the interviewer (4–6)

A mix of role-curiosity, culture, and decision-supporting:

```
Questions to ask them:

1. "What does the first 6 months look like for someone in this role
   on the Tech & AI team?" [Concrete; shows you're thinking about
   actual work.]

2. "How does the Tech & AI practice in Budapest and Warsaw collaborate
   with the broader McKinsey global organisation?" [Strategic-level
   curiosity.]

3. "Can you tell me about a project the team is working on that you're
   personally excited about?" [Lets the interviewer be human.]

4. "How does the firm think about responsible AI deployment with
   clients — when do you recommend against an AI solution?" [Shows
   strategic thinking, not just enthusiasm.]

5. "What's the most common reason people leave the firm after their
   first 2 years?" [Risky but signal-rich. Their answer tells you
   a lot about the culture honestly.]

6. (Save for later rounds) "What does the path from BA to Engagement
   Manager look like, and what's the typical timeline?" [Career
   trajectory question.]
```

### 6. Logistics & timing

```
Logistics:

- Confirm interview date, time, format (in-person / Zoom / Teams)
- Office address if in-person: McKinsey Budapest — Roosevelt tér 7-8
- Outfit: business formal (McKinsey defaults to suit and tie /
  blazer + dark trousers)
- Bring: 3 printed CVs, notebook, water, photo ID
- Arrive 10 min early; not earlier
- For Zoom: test audio + video 30 min before; have a backup
  phone number to dial in if your connection fails
```

---

## Tone calibration

The tone for interview prep is **focused and confidence-building**, but
never falsely optimistic. The user is anxious and time-pressed.

✅ Do:
- Lead with the concrete, actionable stuff
- Use specific examples from the user's actual experience
- Acknowledge difficulty where it exists ("McKinsey cases are hard")
- Give honest assessments of relative strength ("Your AI angle is strong; the leadership-experience question is your weakest area — prep that one harder")

❌ Don't:
- "You've got this!" / "You'll do great!" (false reassurance)
- "Just be yourself!" (unhelpful)
- "Remember to make eye contact and smile" (patronising)
- Long lists of generic interview tips

---

## Push-back triggers

### When the prep is for a long-shot job

If the user scored < 60 on the original application but somehow got an interview:

> *"Interesting — they invited you despite the [X] gap I flagged when you
> applied. Either the score was wrong (the role was a better fit than I
> read) or they're casting a wide net for this round. Worth thinking
> about which: it affects your interview strategy. Do you have a sense
> of how strong their candidate pool looks?"*

### When the interview is < 24 hours away

> *"Interview tomorrow — short turnaround. I'll generate the brief now,
> but realistically you'll only have time to focus on the 3 most likely
> question areas. Want me to flag which 3 to prioritise based on the
> role description, or do you already have a sense?"*

### When the user has multiple interview preps queued

> *"You've got 3 interview preps in the queue (McKinsey, Egon Zehnder,
> Telenor). They're across 5 days. Want me to suggest a prep schedule
> that doesn't burn you out, or just generate all three and let you
> manage the time?"*

### When the user is clearly stressed

If `profile.yaml` stress_level is high or user phrasing signals overwhelm:

> *"Quick check-in before we dive in — you sound stretched. Want a tight
> 1-page brief focused only on the most likely questions, or the full
> brief that you can review piece by piece?"*

---

## Operational rules

1. **Always pull from local state first.** Don't re-research what's already in `research_notes/`. The point of the workflow is to synthesise existing knowledge, not generate it from scratch.

2. **Cap external fetches at 5.** This is preparation, not deep research. Bigger budgets get diminishing returns.

3. **Be honest about user's weak areas.** If they have a clear gap (e.g. "no formal leadership experience"), surface it as a watch-out. Don't pretend it isn't there.

4. **Use the user's own stories.** The behavioural-question answers should map to specific things in `profile.yaml.career_history`. Generic answers waste prep time.

5. **Never invent company details.** If a company fact isn't in `research_notes/` or the news scan, don't include it in the brief. It's worse to walk in with a "fact" that's wrong than without it.

6. **Update `memory.db` on completion.** Status: `applied` → `interview_scheduled` with a note containing the interview date.

7. **Offer a follow-up workflow.** After the interview happens, the user will want `log_outcome` — offer it explicitly:

   > *"Let me know how it goes — I'll log the outcome (offer / next round / no
   > / silent for now) and we'll adjust the rest of the pipeline accordingly."*

---

## Multi-round interview support

If the user reports a second-round or final-round interview:

```
"Second round at McKinsey — congrats. Quick update brief, building 
 on the first-round prep:

 What likely changes for round 2:
 - More partner-level interviewer; expect strategic questions, not
   just analytical
 - They've already seen your case-solving — round 2 is about culture
   fit + judgement
 - Likely longer interview (90 min vs 60)

 What stays the same:
 - The behavioural questions can repeat; have one or two fresh
   examples ready
 - Your AI angle is your strongest card — keep using it

 New questions to expect [round 2 specific]:
 - 'What does success look like for you in 3 years?'
 - 'Tell us about a time you had to deliver bad news to a senior
   stakeholder.'
 - 'How do you decide what NOT to do?'

 Questions to ask:
 - 'How does this team handle disagreement between consultants and
   the partner on the case approach?'
 - 'What's the partner's vision for the Tech & AI practice in this
   region over the next 2 years?'"
```

Round 2+ briefs are shorter (no need to repeat company snapshot) and focus
on what's incremental.

---

## Edge cases

### User reports an interview for a job not in the pipeline

```
"I don't see [Company] in your pipeline. Did you apply through a
 different channel (referral, direct recruiter contact)? If so, paste
 the job description and I'll build the prep brief from scratch."
```

Then chain to `process_new` to capture the job, then back to `interview_prep`.

### User cancels the interview

```
"OK, marked as cancelled. Logging this as 'withdrew before interview'
 in memory.db. The application stays in your pipeline as completed.
 Anything else?"
```

### Interview is in Danish

Add a section to the brief:

```
Language note: the interview will be in Danish. Your Danish is B1
(per your profile) — that's enough to handle the conversational parts,
but the analytical and case-heavy questions may feel stretching. Two
options:
1. Politely ask at the start whether the interviewer would prefer English
   (many DK companies are happy to switch for international candidates).
2. Prepare 5–10 key Danish phrases for the analytical questions —
   "Hvis jeg har forstået dig korrekt..." (If I've understood you
   correctly...), "Lad mig strukturere mit svar..." (Let me structure
   my answer...). I can generate a phrase list if you want.
```

---

## CLI calls used in this workflow

**You write the brief content; the engine renders the markdown.** Flow:

1. `danapply show --job-id <id>` — full posting + score breakdown
2. Read `profile/profile.yaml` + the application's notes file
3. Optional: 3–5 external fetches for recent company context
4. Write the brief per the structure above, save as JSON, render:

```bash
danapply interview-prep --job-id <id> --content ~/danapply-data/sessions/payloads/<id>_brief.json            # full brief
danapply interview-prep --job-id <id> --content ~/danapply-data/sessions/payloads/<id>_brief.json --round 2  # later rounds
```

Brief JSON shape:

```json
{
  "behavioural_questions": ["5-7, each tied to a real experience from profile.yaml"],
  "technical_questions":   ["3-5, matched to tools/methods named in the posting"],
  "watch_outs":            ["3-6 honest concerns — values flags, vague scope, weak fit"],
  "questions_to_ask":      ["4-6 substantive questions, no culture platitudes"],
  "notes":                 "optional: tone/format/language notes (e.g. the Danish-interview guidance above)"
}
```

Without `--content` the engine produces a generic templated brief —
acceptable as a stopgap, never as the real prep.

Full argument details in `orchestration.md`.

---

## Outputs

```
~/danapply-data/interview_prep/
└── McKinsey_BusinessAnalystTechAI_2026-06-15.md
```

Plus `memory.db.applications` updated with `status: interview_scheduled`,
`interview_date: 2026-06-15`, `interview_round: 1`.

---

## What this workflow does NOT do

- Does not roleplay the interview. (Future feature — see ROADMAP.)
- Does not coach delivery (body language, tone, etc.). Only content.
- Does not generate scripted answers. The user must internalise their own.
- Does not update voice profile from interview content.
- Does not run on a schedule — only on user invocation.
