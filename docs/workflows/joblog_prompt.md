# Workflow: joblog_prompt

Generate a ready-to-paste prompt for Claude in Chrome that automates filling
Jobnet's "Opret Joblog" form. This is the DK-specific automation that
satisfies the dagpenge weekly application requirement.

The workflow does **not** submit anything to Jobnet directly. It produces a
prompt the user pastes into Claude in Chrome, which then fills the form.
The user still clicks "Gem" (Save) themselves.

---

## Metadata

| Field | Value |
|---|---|
| Trigger | User says "log to Jobnet", "I applied", "joblog for today", or finishes a `tailor` workflow and accepts the offered next step |
| Estimated duration | < 30 sec |
| Pause/resume | Not needed (single-shot generation) |
| Outputs | `joblog_prompts/jobnet_joblog_YYYY-MM-DD.md`, status updates in `memory.db` |
| Prereqs | Jobs already in `memory.db` with `status: tailored` or `applied`; ideally dagpenge.yaml exists |

---

## Selection logic — which jobs go in the prompt

Default scope: all jobs from the current session that scored **≥ 60** and are
not already logged to Jobnet.

Override modes:

| User says | Behaviour |
|---|---|
| "Log everything I tailored today" | All `tailored` jobs from today, regardless of score |
| "Joblog for [company]" | Just that one job |
| "Joblog for top 3" | The 3 highest-scoring tailored jobs from today |
| "Joblog the ones I just applied to" | Whichever jobs the user names explicitly |
| (No override) | Default: today's tailored jobs scoring ≥ 60 |

If selected jobs would push the prompt to > 12 entries, suggest splitting:

> *"15 entries is a lot to fill in one go in Claude in Chrome. Want me to
> split into two prompts (8 + 7) so you can take a break between them, or
> generate one long prompt?"*

---

## The supplement-file pattern

**Critical rule:** once a dated joblog prompt has been generated for a given
date, **never regenerate or modify it**. Subsequent additions go into a
supplement file:

- First prompt: `joblog_prompts/jobnet_joblog_2026-06-07.md`
- Second prompt same day: `joblog_prompts/jobnet_joblog_2026-06-07_supplement_1.md`
- Third: `joblog_prompts/jobnet_joblog_2026-06-07_supplement_2.md`
- (or named per company: `jobnet_joblog_2026-06-07_BNPParibas.md`)

Reason: audit trail integrity. Once the user has pasted a prompt into Claude
in Chrome, that prompt is now part of the historical record. Modifying it
later would silently rewrite history.

---

## Prompt structure

Every generated file has three sections:

### Section 1 — Opening block (verbatim)

```
You are going to create N entries in the Jobnet "Opret Joblog" form that 
is currently open in this tab. I am giving you blanket permission upfront 
for this session: you may click "Gem" to save each joblog and reopen 
"Opret Joblog" between entries — do NOT pause to ask for confirmation 
between fields or between the jobs. Only stop and ask if a field is 
genuinely ambiguous or the page throws a validation error you can't 
resolve.

Do NOT upload any files. Skip the "Upload jobansøgning", "Upload CV", and 
"Upload jobannonce" sections entirely — leave them empty.

For every entry:
- Skip the "Skriv evt. noter om jobbet" notes section — leave it empty.
- "Hvor langt er du med at søge dette job?" → Søgt
- "Hvordan fandt du jobbet?" → Opslået stilling
- "Hvordan søger du jobbet?" → Digitalt
- Arbejdstid → Fuldtid (unless I note otherwise below)
- After filling everything, click "Gem" to save. Then click "Opret Joblog" 
  again (or reopen it from the menu) and start the next entry.
```

Replace `N` with actual count. If batch contains part-time roles or
fixed-term contracts, the Arbejdstid default note is adjusted (e.g.
"Fuldtid unless I note otherwise below" → "varies per entry — see notes").

### Section 2 — Per-entry blocks

For each job:

```
ENTRY {n} — {CompanyName}
- Stilling: {JobTitle}
- Ansøgningsfrist: {YYYY-MM-DD or "leave blank (rolling)"}
- Arbejdstid: {Fuldtid | Deltid (N t/uge) | Tidsbegrænset (N måneder)}
- Virksomhedens navn: {CompanyName + legal form if known, e.g. "A/S"}
- Adresse: {street + number, or "leave blank"}
- Land: Danmark (or other country if relevant)
- Postnummer og by: {NNNN City, or "leave blank — tick 'Jeg kender hverken postnummer eller by'"}
- Kontaktperson: {name, or "leave blank"}
- Telefonnummer: {phone, or "leave blank"}
- E-mail: {email, or "leave blank"}
- Link til jobannonce: {canonical posting URL}
```

### Section 3 — Closing block (verbatim)

```
When all are saved, give me a short summary of what was created and flag 
anything you had to skip or guess.
```

### Footer — audit notes

After the closing block, two subsections:

```
---

## Footer — jobs excluded from this prompt (audit trail)

- [Company X] — [reason for exclusion: below threshold / already logged / etc.]
- [Company Y] — [reason]

## Note on guessed fields

- [Field 1]: [explanation of what was inferred vs. confirmed]
- [Field 2]: [explanation]
- Contact persons and phone numbers were not in the postings, so left 
  blank rather than invented.
```

---

## Field-population rules

### From the parsed job data (no guessing)

| Jobnet field | Source |
|---|---|
| Stilling | `memory.db.applications.title` |
| Ansøgningsfrist | `memory.db.applications.deadline`, or "leave blank (rolling)" if null |
| Virksomhedens navn | `memory.db.applications.company` (exactly as stored — never guess legal suffixes) |
| Land | Default Danmark; override per posting |
| Link til jobannonce | `memory.db.applications.url` |

### From research notes (high confidence)

| Jobnet field | Source |
|---|---|
| Adresse | `research_notes/<slug>.md` if address present in posting; else "leave blank" |
| Postnummer og by | Same |
| Kontaktperson | Same — only if explicit name in posting |
| Telefonnummer | Same |
| E-mail | Same |

### From inference (use cautiously, document in footer)

| Jobnet field | Inference allowed? |
|---|---|
| Adresse | Yes for well-known company HQs (e.g. McKinsey CPH, BNP Paribas CPH, UNOPS Marmorvej) — **always flag in footer for sanity-check** |
| Postnummer og by | Yes if city is in research notes — look up standard postal code |
| Contact person | **No** — never invent |
| Phone number | **No** — never invent |
| Email | **No** — never invent |

The principle: **address/postal can be inferred from public info; people contacts cannot.** People-data fabrication is dishonest and creates Jobnet records that don't match reality.

---

## Arbejdstid handling

The default is Fuldtid. Override when:

- **Deltid (part-time)**: posting specifies hours/week (e.g. Group Online's 15h/week). Write `Deltid (15 t/uge)`.
- **Tidsbegrænset (fixed-term)**: posting specifies contract length (e.g. Danfoss M&A's 12 months, Circle K's 12 months, UNOPS' IICA Regular). Write `Tidsbegrænset (12 måneder)`.
- **Both**: rare, combine.

These get flagged in the opening block's Arbejdstid default line so Claude in Chrome doesn't blanket-set everything to Fuldtid.

---

## Dagpenge alignment check

Before generating the prompt, read `dagpenge.yaml`:

- Check the user's `my_plan_field`
- For each job in the proposed prompt, check whether the job title/field
  aligns with `my_plan_field`
- If any don't align, surface to the user **before** generating the prompt:

> *"One thing worth flagging before I generate this: your My Plan field is
> 'Analyst, Economist, Business Researcher'. The Flying Tiger job is a
> Business & Pricing Analyst — fits. The Imbox role is Strategy & PMO
> Associate — fits, but the 'PMO' label might be questioned by your
> caseworker. Want to include it anyway, or skip?"*

This is dagpenge-protective: Jobnet caseworkers can challenge logged jobs that don't match your declared field, and rejected logs don't count toward the weekly threshold.

---

## Selection presentation

Before generating, Claude shows the selected jobs and offers a quick confirm:

```
"I'll generate the joblog prompt for 4 jobs:

 1. UNOPS — AI Business Analyst (88) — closes 21 Jun
 2. Flying Tiger — Business & Pricing Analyst (71) — rolling
 3. PwC — Associate Strategy& Deals (65) — closes 15 Jun ⚠️
 4. BNP Paribas — Graduate Analyst FX & EM (45 — you applied despite low score)

 BNP scored below your usual threshold — including because you submitted.
 Anything to exclude before I generate?"
```

If user says "skip BNP" or "yes generate" → proceed.

---

## Generation

```bash
danapply joblog --job-ids <id1>,<id2>      # explicit selection
danapply joblog --threshold 60             # or: auto-pick scored ≥ 60, not yet logged
```

Output: a single markdown file at `joblog_prompts/jobnet_joblog_YYYY-MM-DD.md`
(or a supplement if today's file already exists).

After writing the file, Claude shows the path and a brief summary:

```
"Joblog prompt written to:

  joblog_prompts/jobnet_joblog_2026-06-07.md

 4 entries. 3 with confidence-high addresses (UNOPS Marmorvej 51, Flying
 Tiger Strandgade 71-73, BNP Paribas Sundkrogsgade 7). 1 with 'leave
 blank' on the address (PwC — I didn't have a confirmed HQ for the
 Strategy& Deals team's Copenhagen office).

 Paste this into Claude in Chrome on the Jobnet form when you're ready
 to log them."
```

---

## After the user submits (in Claude in Chrome)

The user comes back later and says they've logged the entries. Two updates happen:

1. **`memory.db.applications`** — for each logged job, `jobnet_logged_at` gets stamped and early-stage statuses advance to `applied`. This prevents re-inclusion in future joblog prompts.

2. **Dagpenge compliance tracker** — `danapply dagpenge` will count these toward the week's threshold next time it runs.

The user signals this with phrasings like "logged them all", "submitted to Jobnet", or "joblog done". DanApply confirms which jobs and runs:

```bash
danapply joblog --mark-logged --job-ids <id1>,<id2>,<id3>
```

This stamps only — it never generates a new prompt file. If the user
signals partial success ("logged 3 of 4 — the 4th had an issue"), pass
just the ids that were actually saved.

---

## Push-back triggers

### When user wants to log a job that's already been logged

> *"That one's already in your Jobnet log from 2026-06-03. Logging the
> same job twice can trigger questions from your a-kasse. Want to log
> a different application stage (interview, follow-up) instead?"*

### When user wants to log all jobs regardless of score

> *"You've got 8 jobs from today, but only 4 scored ≥ 60. The lower-score
> ones (Netcompany 46, Uber 32, Danfoss 45) are likely to feel like
> stretches to a caseworker, and they don't help your weekly count if
> they get questioned. Want to include them anyway, or stick to the
> 4 strong fits?"*

### When the user is behind on dagpenge

> *"This brings you to 3 of the required 2 applications this week —
> you're in good shape for compliance."*

Or, if still behind:

> *"This brings you to 1 of the required 2 this week — you'll need 1 more
> by Sunday to stay compliant. Want me to look at what's still unapplied
> in your pipeline, or do you have new postings to process?"*

---

## Operational rules

1. **Never modify a previously generated joblog prompt.** Use supplement files.

2. **Never invent contact people, phones, or emails.** Address/postal can be inferred from public info (with sanity-check note); people-data cannot.

3. **Always flag inferred fields in the footer.** The user must be able to spot what to double-check.

4. **Never include jobs already logged to Jobnet.** Check `memory.db` first.

5. **Never generate without the user's confirmation.** Show the proposed selection, ask for confirmation, then write the file.

6. **Always update `memory.db` after the user confirms they've logged.** Otherwise future joblog prompts re-include jobs the user has already logged.

---

## Edge cases

### User asks for joblog for a job not yet tailored

> *"That job is in the pipeline as 'parsed' but not yet tailored. Want
> me to tailor first, then generate the joblog? Or did you skip the
> tailoring and just want to log the application directly?"*

Branch on user's answer:
- Tailor first → chain to `tailor` workflow
- Log directly → proceed, but flag in notes: `tailored: false`

### User asks for joblog when raw_searches is empty and memory.db has nothing

> *"You don't have any jobs in your pipeline yet — nothing to log to
> Jobnet. Paste a posting or drop some job files into raw_searches and
> we'll start there."*

### User asks for a joblog prompt in Danish (not English)

The joblog prompt structure is bilingual — instructions in English (for Claude in Chrome), Jobnet field labels and values in Danish (since the form is in Danish). This is the right hybrid; no need to translate the wrapper.

---

## CLI calls used in this workflow

```bash
danapply joblog                                  # generate, default scope (score ≥ 60, not yet logged)
danapply joblog --threshold 70                   # custom threshold
danapply joblog --job-ids <id1>,<id2>            # explicit selection
danapply joblog --mark-logged --job-ids <ids>    # stamp after the user saved in Jobnet (no file generated)
```

To see what's still unlogged, use `danapply list --json` and filter on
`jobnet_logged_at == null`. Full argument details in `orchestration.md`.

---

## What this workflow does NOT do

- Does not interact with Jobnet directly. Only generates the Claude-in-Chrome prompt.
- Does not click "Gem" on the user's behalf — that's the user's call.
- Does not modify previously generated prompts. Use supplements.
- Does not invent contact data. Only address/postal can be inferred (with notes).
- Does not run automatically. Only on user request or end-of-tailor offer.
