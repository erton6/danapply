# Workflow: cv_session

Build the user's **base CV** — the step that comes *after* the first cover
letter. The cover letter teaches DanApply the user's voice; this session turns
that, plus the onboarding answers, into a rendered CV. You write the content;
the engine renders the PDF.

---

## Metadata

| Field | Value |
|---|---|
| Trigger | Right after the first cover letter (onboarding Phase B), or "build my CV" / "make my CV" |
| Estimated duration | 5–10 min |
| Pause/resume | Yes |
| Outputs | Updated `profile.yaml` (LinkedIn, optional Portfolio, `cv_style`, `accent_color`), `profile/photo.jpeg`, `cv_content.md` (short summary), rendered `base_cv.pdf` via `danapply render-base` |
| Prereqs | Onboarding answers captured; voice profile ideally already set from the cover letter |

---

## Why it runs after the cover letter

The cover letter is where DanApply captures voice. The CV should sound like the
same person, so build it once the voice profile exists. Order: **cover letter →
cv_session**.

---

## The flow

### Step 1 — Collect the header essentials

Ask for these and store each in the right place. Keep it light — one short
message, not an interrogation.

1. **LinkedIn** — *"What's your LinkedIn URL? Most DK recruiters look for it."*
   → write to `profile.yaml` → `contact.linkedin_url`. Skippable, but ask.
2. **Portfolio — always ask explicitly, never assume either way.**
   *"Do you have a portfolio — a personal site, a project collection, or
   even a single good piece (a case study, a dashboard, a report you're
   proud of)? If you have a link, paste it — it gets a highlighted,
   clickable block near the top of both the CV and the cover letter."*

   - **If yes** → write to `profile.yaml` → `portfolio.display` (clean
     label, e.g. `yourname.com`) and `portfolio.href` (full URL). The
     renderer shows the PORTFOLIO block with the clickable link.
   - **If no** → remove / comment out the `portfolio` block entirely.
     The section is **omitted from the PDFs completely** — no empty box,
     no placeholder. (The engine also treats blank display/href as "no
     portfolio".)
   - **If no, nudge once — friendly, not pushy.** A portfolio
     genuinely moves the needle in DK hiring: it gives the
     interviewer something concrete to ask about, and it shows
     initiative without overclaiming. Offer concrete, low-effort ideas
     matched to their field:
       - Analysts: one anonymised case study (problem → method →
         result) as a Notion page or PDF; a Tableau Public / Power BI
         dashboard; a tidy GitHub repo with one well-documented
         analysis.
       - Writers/communicators: 2–3 published pieces on a simple
         personal page or LinkedIn Featured section.
       - Anything works as a start — even one good piece with a link
         beats nothing. *"Want me to note it as a to-do? When it's
         live, say 'add my portfolio' and I'll re-render."*
     If they decline, drop it — never block the render on it.
3. **Photo — always ask, and push for a usable one.** *"Most Danish CVs
   include a photo, top-right. Want to add one? Best results: a recent
   headshot, roughly square, face centred, at least 400×400 px — it gets
   circle-cropped, so nothing important near the corners."*

   When the user provides a file, run:

   ```bash
   danapply photo set <path-they-gave-you>
   ```

   The engine validates it, centre-crops to a square, resizes to the
   render-optimal size, and saves `profile/photo.jpeg` — it reports the
   final dimensions. If the source is too small (< 300 px on a side),
   it warns; tell the user it will look soft in print and ask for a
   bigger one. Photo is optional — if they skip, that's fine, the CV
   header renders text-only. But ask explicitly; never silently skip.

Never invent a LinkedIn/portfolio URL. If the user doesn't have one, leave it
blank.

### Step 1b — Ask the design questions (never skip, never assume)

Three explicit questions before anything renders. All answers go to
`profile.yaml`. Every option is ATS-friendly — single column, real text,
standard section headers; the presets only vary restrained design touches.
Say that out loud so the user knows nothing here costs them a parser.

1. **Style — match the work environment they're applying to.**
   *"How should the CV feel? Think about the places you're applying:
   - **classic** — serious, traditional (ministries, banks, big corporates)
   - **minimal** — minimalistic, colour only in the details
   - **modern** — smart, contemporary (tech, consultancies, scale-ups)
   - **creative** — slightly more colour presence (agencies, media, NGOs)
   All of them stay clean and ATS-friendly — nothing overdecorated."*
   → `profile.yaml` → `cv_style`.

2. **Base colour — ask explicitly, never silently keep the default.**
   *"The accent colour is currently dark green (`#1F4737`) — it shows in
   your name, the section headers, the photo ring, and the links. Want to
   keep it, or pick another? Navy `#1F3A5F`, burgundy `#5F1F2E`, charcoal
   `#333333`, or any hex you like."*
   → `profile.yaml` → `accent_color`.

3. **Cover letter — match or diverge?**
   *"Should your cover letters use the same style as the CV? Most people
   say yes — they're usually read together."*
   → If yes (the default), leave `cover_letter_style` unset — it follows
   `cv_style` automatically. If no, write their choice to
   `profile.yaml` → `cover_letter_style`.

### Step 2 — Write a SHORT summary

The CV summary is **4–6 sentences, ~80–110 words — short enough to read in one
glance.** Do not exceed ~110 words. Structure:

- Lead with the strongest facet for the user's target roles.
- Name 1–2 concrete proofs (a role, a result, a degree) — evidence, not adjectives.
- Close with one forward-looking line if it fits naturally.

Apply the Danish-mode register (strip superlatives/filler) and the user's voice
profile. Every claim must trace to `cv_content.md` / the onboarding answers —
never fabricate. Write it to `cv_content.md` → `## Summary`.

> Length calibration: aim for the size of a single dense paragraph — roughly
> five lines on screen. If it spills past ~110 words, cut it.

### Step 3 — Build experience & education in profile.yaml

The renderer draws the CV body **directly from `profile.yaml`** —
`experience:` and `education:` lists. Pull the raw material from the
onboarding answers / `cv_content.md`, confirm dates, titles, and the top
2–3 bullets per role with the user, then write the entries:

```yaml
experience:
  - role: "Job Title"
    company: "Employer"
    dates: "2020–2022"
    location: "City, Country"
    bullets:
      - "Concrete, factual statement of what they did."
education:
  - degree: "MSc in ..."
    school: "University"
    dates: "2018–2020"
    bullets: []
```

Rephrase existing bullets for the target roles if useful — never invent
new history. Danish-mode register applies to bullets too.

### Step 4 — Render

Render the base CV with:

```bash
danapply render-base
```

It uses everything you just wrote — the **real summary from
`cv_content.md`**, photo, links, experience, education, skills, and the
style + colour the user picked in Step 1b. Output:
`resume_drafts/base_cv.pdf`.

**Never use `render-sample` here** — that command exists only to
smoke-test the renderer and fills the summary with placeholder text. If
`render-base` errors with "no summary found", go back to Step 2 — the
summary was never written to `cv_content.md`.

Per-job CVs come later via `danapply tailor --job-id <id> --content …`.
The cover letter is always a **single page**; the CV is two pages max.

### Step 5 — Show it and get a verdict (never skip)

Point the user at the rendered PDF and ask explicitly:

> *"Open it and tell me honestly — does it look right? Photo placement,
> the summary, the order of your roles, anything you'd change?"*

**Tell them the formatting is adjustable — nothing is written in
stone:** style preset, accent colour, and font size are all one-line
profile.yaml edits plus a re-render. `render-base` prints a ⚠ when the
CV spills only a line or two onto an extra page — propose the fix
yourself rather than waiting: *"Page 2 only holds a couple of lines — I
can shrink the font slightly (`cv_font_scale: 0.95`) or trim a bullet
so it sits cleanly. Want me to?"*

Iterate: edit `profile.yaml` / the summary, re-render, ask again, until
they're happy. Remind them `profile.yaml` and `cv_content.md` stay
hand-editable.

---

## Storage map

| Asked for | Stored in |
|---|---|
| LinkedIn URL | `profile.yaml` → `contact.linkedin_url` |
| Portfolio link (optional) | `profile.yaml` → `portfolio.display` + `portfolio.href` |
| Photo | `profile/photo.jpeg` |
| CV style (classic / minimal / modern / creative) | `profile.yaml` → `cv_style` |
| Accent / base colour | `profile.yaml` → `accent_color` |
| Cover letter style (only if diverging from CV) | `profile.yaml` → `cover_letter_style` |
| Short summary | `cv_content.md` → `## Summary` |
| Experience / education | `cv_content.md` (confirmed with the user) |

---

## What this workflow does NOT do

- Does not capture voice — that's `voice_capture.md` (the cover letter).
- Does not invent links, photos, or history.
- Does not make the cover letter longer than one page — the renderer enforces that.
