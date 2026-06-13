# Danish-Mode Register Guide

The full calibration reference for adjusting CVs and cover letters to Danish
business-communication norms. Read this when generating any artefact for a
DK employer — it's loaded by both the `tailor` workflow and the onboarding
CV-calibration step.

The underlying principle: **let evidence do the bragging, not adjectives.**
Janteloven shapes professional writing in DK even when no one consciously
invokes it. Overclaiming makes recruiters calibrate downward; understatement
signals real confidence.

---

## When to apply Danish mode

| Letter / CV language | Target employer | Mode |
|---|---|---|
| Danish | Any DK employer | **Full Danish mode** |
| English | Danish-founded DK employer (Novo Nordisk, Maersk, LEGO, Carlsberg, Danfoss, Vestas, Coloplast, etc.) | **Full Danish mode** — they read EN application but evaluate by DK norms |
| English | International / foreign-owned DK employer (McKinsey, Uber, BNP Paribas, Trustpilot HQ etc.) | **Soft mode** — keep US-power-verb strictness but allow slightly warmer tone |
| English | Non-DK employer | User's natural register (no Danish mode applied) |
| Hungarian / German / etc. | Any | User's natural register; flag for human review (v1 doesn't fully calibrate other languages) |

DanApply detects DK-founded employers via a list in `voice/dk_founded_employers.yaml`.

---

## The four marker categories

When scanning a CV or cover letter, DanApply counts and surfaces four
marker categories:

### 1. Superlatives & intensifiers

Words that *claim* excellence without proving it. Examples:

`exceptional`, `outstanding`, `proven`, `extensive`, `remarkable`,
`highly`, `truly`, `extraordinarily`, `incredibly`, `vastly`, `tremendously`,
`world-class`, `best-in-class`, `top-tier`, `elite`, `invaluable`,
`unparalleled`, `unique`, `groundbreaking`, `cutting-edge`

**Default action:** strip entirely. Replace with concrete evidence.

| ❌ Before | ✅ After |
|---|---|
| "Exceptional track record" | (delete; replace with the actual track record) |
| "Highly motivated analyst" | "Analyst with…" |
| "Proven expertise in Python" | "Python: applied to [specific projects from cv_content]" |
| "Outstanding communication skills" | "Communication: 40+ executive interviews, 200+ published analyses" |

### 2. Filler phrases

Phrases that contribute zero information. Danish recruiters skip these
lines without reading them, then read your CV as 4 lines shorter than it is.

`self-starter`, `team player`, `results-driven`, `highly motivated`,
`detail-oriented`, `goal-oriented`, `passionate about`, `excellent
communication skills`, `strong work ethic`, `quick learner`,
`problem-solver`, `dynamic professional`, `out-of-the-box thinker`,
`go-getter`, `synergistic`, `dedicated professional`

**Default action:** delete entirely. Don't replace — use the space for
one more concrete fact.

| ❌ Before | ✅ After |
|---|---|
| "I am a self-starter and team player with strong work ethic" | (delete entirely; you have 3 lines back) |
| "Passionate about driving results in fast-paced environments" | (delete entirely) |

### 3. US-power verbs

Verbs the US CV industry has trained candidates to use. Land too aggressively
in DK; the calibrated equivalents are quieter.

| ❌ US power verb | ✅ DK-appropriate equivalent |
|---|---|
| Spearheaded | Co-led / led |
| Pioneered | Built / developed |
| Championed | Supported / advocated for |
| Drove (revenue, growth, etc.) | Contributed to / delivered / helped grow |
| Orchestrated | Coordinated / organised |
| Transformed | Restructured / improved / redesigned |
| Catalysed | Initiated / started |
| Revolutionised | Changed / redesigned |
| Mastered | Learned / developed expertise in |
| Synergised | Worked with / collaborated with |
| Engineered (when not literal engineering) | Designed / built |
| Architected (when not literal architecture) | Designed / structured |
| Crushed (results, goals) | Met / exceeded |
| Slashed (costs, time) | Reduced |
| Skyrocketed (growth, sales) | Grew significantly |
| Wowed (clients, etc.) | (delete; let outcome speak) |

**Default action:** swap, keep the rest of the bullet intact.

### 4. Self-promotion structures

Sentence patterns that frame the user as the hero of the story. The
Danish-mode alternative shifts to third-party voice or factual structure.

| ❌ Self-promotion pattern | ✅ Danish-mode alternative |
|---|---|
| "I am skilled at X" | "Experience with X, Y, Z" |
| "I am an expert in X" | "Worked with X in [context from cv_content]" |
| "I excel at X" | (delete; let the actual experience demonstrate) |
| "I am highly experienced in Y" | "Y: [specific years, projects, or scale]" |
| "I have a proven track record of Z" | "Delivered Z: [actual outcomes]" |
| "My CCO described me as exceptional" | "My CCO recognised the work for [specific quality]" |
| "I successfully completed X" | "Completed X: [outcome]" |
| "I am uniquely positioned to..." | (delete; rewrite the sentence without the framing) |

---

## Scanning rules (for the CV calibration pass)

During onboarding Chapter 8, **you** scan the user's CV against these
rules and present the findings as a structured report:

```json
{
  "superlatives_found": [
    {"word": "exceptional", "location": "summary, sentence 1"},
    {"word": "proven", "location": "skills paragraph, line 2"}
  ],
  "filler_phrases_found": [
    {"phrase": "self-starter", "location": "summary, sentence 3"}
  ],
  "us_power_verbs_found": [
    {"verb": "spearheaded", "location": "NordRetail bullet 1"}
  ],
  "self_promotion_structures": [
    {"pattern": "I am skilled at...", "location": "summary, sentence 2"}
  ],
  "concrete_facts_count": 12,
  "third_party_attributions": 1,
  "register_score": 6.5
}
```

`register_score` is on a 1–10 scale where:
- 1–3: heavily American-mode (lots of overclaiming, low evidence density)
- 4–6: mixed (somewhere between US and DK norms)
- 7–9: well-calibrated Danish mode (evidence-led, low filler)
- 10: extreme understatement (rare; might be selling self short)

Target: **7 or higher** after calibration.

---

## The calibration conversation (Chapter 8)

After the scan, Claude leads an interactive walkthrough. Always
**show the user their own sentences** — never rewrite without their input.

### Example exchange

```
Claude: "I scanned your CV. Here's what I found:

         - 5 superlatives: 'exceptional', 'proven', 'outstanding',
           'highly', 'extensive'
         - 3 filler phrases: 'self-starter', 'results-driven',
           'team player'
         - 2 US-power verbs: 'spearheaded', 'pioneered'

         Register score: 4/10 — leaning American.

         Want to walk through them one at a time, or batch-fix the
         filler phrases (which are easy) and then go sentence-by-sentence
         on the rest?"

User: "Let's batch-fix the filler."

Claude: "OK. Showing the three sentences containing filler:

         1. 'I am a self-starter with strong analytical skills' →
            (delete entire sentence; you'll save 1 line and the
            'strong analytical' framing is overclaiming anyway)

         2. 'Results-driven professional with extensive experience' →
            (delete entire sentence; replace with: 'Analyst with 4 years
            of experience at...')

         3. 'Team player who thrives in fast-paced environments' →
            (delete entire sentence; this contributes zero information)

         All three deletions in one go?"

User: "Yes."

[Claude updates cv_content.md, recalculates register_score, continues]

Claude: "Done. Register score: 6/10. Now the superlatives — start with
        'exceptional' or 'proven'?"
```

---

## Examples from real DanApply outputs

### CV summary (good Danish mode)

```
Marketing analyst with hands-on commercial analytics from a recent
internship at NordRetail A/S (2024), editorial and consumer-trends
research at Lisbon Media Group (2020–2022, data-backed reporting for a
business audience), and prior analyst experience at Iberia Insights
supporting market sizing and competitive research. MSc in Business
Administration from Copenhagen Business School with focus on marketing
analytics and quantitative methods.
```

What works:
- No superlatives. (No "exceptional", "proven", "highly".)
- No filler. (No "self-starter", "results-driven".)
- Every claim has a number or anchor. (200+, 40+, MSc, "supporting the
  launch of", etc.)
- Verbs are descriptive, not heroic. ("with", "from", "supporting".)

### CV summary (bad — American mode)

```
Highly motivated, results-driven analytical professional with exceptional
hands-on experience and a proven track record of delivering outstanding
outcomes in fast-paced environments. Truly passionate about turning data
into insight.
```

Failures: 4 superlatives, 2 filler phrases, zero facts, no anchors. A DK
recruiter would mentally adjust the real candidate level *downward* on
reading this.

### Cover-letter opener (good Danish mode)

```
In my view, the greatest value in sustainability reporting comes not from
the volume of data collected, but from how cleanly that data is structured,
validated, and translated into analyses that decision-makers can act on.
As regulatory frameworks like CSRD and the Greenhouse Gas Protocol move
ESG data closer to the rigour of financial reporting, the work of building
data quality and clear narratives around it becomes genuinely strategic.
This is exactly the kind of work I want to deepen, which is why I am
applying for the Sustainability Data Analyst position at Fertin Pharma.
```

What works:
- Opens with an observation, not a self-claim
- References specific regulations (CSRD, GHG Protocol — both in the
  posting) rather than vague enthusiasm
- The "want to deepen" framing is honest about a growth area, which lands
  better in DK than claiming pre-existing expertise

### Cover-letter opener (bad — American mode)

```
I am incredibly excited to apply for the Sustainability Data Analyst
position at Fertin Pharma. As a passionate, results-driven analyst with
extensive experience in driving data-driven outcomes, I would be an
invaluable asset to your team. My proven track record speaks for itself.
```

Failures: 3 superlatives, 2 filler phrases, zero facts, generic
substitutable-for-any-job tone. Would be in the reject pile in 5 seconds.

---

## Bullet-level calibration

For bullet points (in CV experience sections), the calibration is lighter
but still applies. Each bullet should:

1. Start with a descriptive verb (not a US-power verb)
2. Include a number or concrete outcome where possible
3. Not include personal qualifiers ("successfully", "effectively", "expertly")
4. Be 1–2 lines max

| ❌ American-mode bullet | ✅ Danish-mode bullet |
|---|---|
| "Successfully spearheaded a transformative UK market entry initiative that achieved exceptional results" | "Reframed a UK market entry brief around commercial objectives; delivered a Digital Profile concept and go-to-market campaign setup — research to execution in 7 weeks" |
| "Effectively orchestrated cross-functional collaboration with senior stakeholders" | "Conducted 40+ executive interviews; co-organised four industry conferences" |
| "Pioneered innovative analytical methodologies" | "Applied causal-inference and PSM methods to business outcome evaluation (MSc thesis)" |

The Danish-mode bullet is often *longer* than the American-mode bullet
because the evidence is in the bullet itself, not in adjectives. Length is
fine — substance is the trade.

---

## What stays the same regardless of register

These are facts, not register choices:

- Job titles, company names, dates
- Education content
- Numerical achievements (results, scale, outcomes)
- Tool/technology lists (Python, R, SQL, Power BI, etc.)
- References (names + emails)
- The user's name, contact, links

Calibration only touches the **adjectives, structure, and verbs** —
never the substance.

---

## The "voice profile takes precedence" rule

If the user's `voice_profile.md` shows that they naturally use a slightly
warmer register than strict Danish mode, the voice profile wins.

Example: a user whose voice profile shows they often write "I genuinely
enjoy" instead of "I am interested in" — that's their authentic voice.
DanApply preserves it. It still strips the most egregious overclaiming
(no "exceptional" or "world-class"), but doesn't sandpaper the user into
a uniform DK register.

The rule: **calibration adjusts overclaiming, not personality.**

---

## Edge cases

### User wants to apply to a Danish company with a US-style CV

(Common scenario: user came from US/UK, has a US-style CV they're proud of.)

```
Claude: "Your CV is well-calibrated for US markets. For DK applications,
        the register would shift the response rate noticeably — and not
        in a good way. Want me to walk through the swaps and let you
        decide which to keep, or just leave it as-is and accept the
        US-market positioning?"
```

Respect the user's choice. They might want to keep US-style for specific
US-headquartered DK roles.

### User writes a cover letter in fluent Danish but with English structure

(Common for L2 speakers who think in English and translate.)

```
Claude: "Your Danish grammar is clean, but the structure reads as
        translated-from-English — e.g. 'Jeg er passioneret omkring...'
        (English calque) instead of 'Jeg er motiveret af...' (natural
        Danish). Want to walk through the patterns?"
```

This is style-coaching that goes beyond register — flag but don't force.

### User is applying to a tobacco / nicotine company despite the exclusion in profile.yaml

(Edge case from real-life: Fertin Pharma's PMI parent.)

```
Claude: "Just flagging: Fertin Pharma is owned by Philip Morris
        International. Your profile.yaml excludes tobacco. Want to
        include this one anyway, or skip?"
```

Don't auto-apply or auto-skip; let the user decide on the spot.

---

## The closing principle

DK business writing rewards substance over style. The candidate who lists
their actual outcomes and lets the reader draw conclusions ranks higher
than the candidate who tells the reader what to think.

DanApply's job in the calibration step is to free the substance from
under the adjectives. Most users have done the actual work — they've just
been trained to bury it under "exceptional" and "proven". Strip that
layer, and the real CV emerges underneath.
