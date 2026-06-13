# Workflow: voice_capture

Capture the user's writing voice from a sample **you analyse yourself,
in this conversation**. No API call, no subprocess doing the reading —
you read the sample with the Read tool, analyse it against the rules
below, and hand the engine a structured JSON payload to validate and save.

This is the moat. Without it, generated cover letters sound like every
other AI-written application. With it, they sound like the user.

---

## Metadata

| Field | Value |
|---|---|
| Trigger | "capture my voice", "I have a cover letter sample", onboarding chapter, or user shares any self-written text |
| Estimated duration | 2-3 min |
| Outputs | `profile/voice_profile.yaml` + `profile/voice_profile.md` |
| Prereqs | A writing sample the user actually wrote — 500+ words ideal, 50 minimum |

---

## The flow

1. **Get the sample.** A real cover letter draft, journal entry, blog
   post, long email — something the user wrote themselves, unedited by
   AI. Ask for 500+ words; accept less but say what it costs (thinner
   profile, weaker pattern anchors).

2. **Read it** with the Read tool (or take it from the conversation if
   pasted).

3. **Analyse** per the principles below and build the payload.

4. **Save** — write the JSON to a temp file, then:

   ```bash
   danapply voice set ~/danapply-data/sessions/payloads/voice_<date>.json [--force]
   ```

   Validation errors are printed verbatim; fix the JSON and retry.

5. **Show the user** what you captured (rhythm, formality, a couple of
   the characteristic phrases) and tell them the YAML is hand-editable.

---

## Analysis principles

1. **Be specific.** "Uses concrete examples" is useless; "uses two-clause
   sentences with a colon between them" is useful.
2. **Be honest about what's there.** If the sample is short or generic,
   say so in `notes` rather than fabricating quirks.
3. **Preserve characteristic phrases verbatim.** They're pattern anchors
   for every future cover letter.
4. **vocabulary_preferences are distinctive** — not stopwords. Look for
   adjectives, verbs, and connectors the user reaches for that another
   writer might not.
5. **vocabulary_avoidances are conspicuous absences.** If the sample is
   800 words about applying for a job and "passionate" never appears,
   that's a signal. Common AI/corporate phrases to check: "passionate
   about", "reach out", "circle back", "leverage", "world-class",
   "incredibly".

---

## Payload schema

```json
{
  "avg_sentence_length_words": 18,
  "sentence_rhythm": "balanced",
  "formality_register": "neutral",
  "opening_style": "claim",
  "closing_style": "warm-confident",
  "vocabulary_preferences": ["5-15 distinctive words/phrases actually used"],
  "vocabulary_avoidances": ["5-10 phrases conspicuously absent"],
  "characteristic_phrases": ["5-10 verbatim full sentences from the sample"],
  "superlatives_per_100_words": 0.5,
  "intensifiers_per_100_words": 1.0,
  "notes": "one paragraph of free-text observations — quirks, tics, anything to preserve",
  "sample_word_count": 812
}
```

Enums (must match exactly):

| Field | Allowed values |
|---|---|
| `sentence_rhythm` | `short and punchy` · `balanced` · `long and flowing` |
| `formality_register` | `formal` · `neutral` · `warm-conversational` |
| `opening_style` | `anecdote` · `claim` · `question` · `observation` · `quote` |
| `closing_style` | `formal` · `warm` · `confident` · `reflective` · `warm-confident` |

`superlatives_per_100_words` / `intensifiers_per_100_words`: count them
honestly — lower = already close to Danish-mode, which matters when
calibrating later (a naturally modest writer needs almost no register
adjustment; sandpapering them further would erase the voice).

---

## Edge cases

- **Sample under 50 words** — don't save junk. Ask for more text.
- **Sample is clearly AI-written** (uniform rhythm, em-dash addiction,
  "delve", flawless parallelism) — say so gently and ask for something
  rawer: an old email thread, a journal entry. A fake voice profile is
  worse than none.
- **Profile already exists** — `voice set` refuses without `--force`.
  Ask the user whether to overwrite or keep; suggest backing up the YAML
  if they've hand-edited it.
- **Sample in Danish, applications mostly English (or vice versa)** —
  capture anyway; rhythm and structural fingerprints transfer across
  languages. Note the sample language in `notes`.

---

## What this workflow does NOT do

- Does not change `cv_content.md` or `profile.yaml`.
- Does not run any rule-based filter over the sample.
- Does not send the sample anywhere — it stays in this conversation and
  on the user's disk.
