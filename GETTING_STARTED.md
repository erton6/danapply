# Getting started with DanApply

**New to this? You're in the right place.** This guide takes you from
nothing installed to a finished, tailored job application — in plain
language, no technical background assumed. Budget about an hour for the
one-time setup and your first run; everything after that takes minutes.

---

## Why use DanApply?

Job hunting in Denmark means writing a fresh, well-judged CV and cover
letter for every role — in a register Danish employers actually respond
to (understated, evidence-led, no American-style overclaiming). That's
slow, and generic AI tools make it worse: every letter reads like every
other AI letter, and recruiters spot it instantly.

DanApply fixes that:

- **It sounds like you.** It learns your writing voice from one sample
  you provide, then writes every cover letter against it — not like a
  template.
- **It's calibrated for Denmark.** No "exceptional / proven / world-class",
  no inflated power-verbs. Just the factual, modest register that works here.
- **It does the busywork, not the thinking-for-you.** Paste a posting; it
  scores the fit, drafts the CV and letter, renders clean ATS-friendly
  PDFs, and prepares your Jobnet log — you review and submit.
- **It's private.** Everything stays on your computer. No accounts to
  feed your data to, no separate AI service, no web tracking.
- **It helps with dagpenge.** Weekly application tracking and one-click
  Jobnet "Opret Joblog" prompts.

You stay in control of every application. DanApply is the prepared
assistant; you're the one who decides what goes out.

---

## What you'll need

- A **Mac (macOS 13+)**, **Windows 10+**, or **Linux** computer.
- A **paid Claude plan** (Pro, Max, Team, or Enterprise). Claude Code —
  the app DanApply plugs into — is not included in the free Claude.ai
  plan. ([See plans](https://claude.com/pricing).)
- About **20 minutes of terminal copy-pasting** for the one-time setup,
  and **30–45 minutes** for the first guided interview.
- Handy for the interview: your **current CV**, one **piece of writing
  you wrote yourself** (an old cover letter, a blog post, a long
  email — 500+ words is ideal), and a **headshot photo** if you want one
  on your CV (Danish CVs usually have one).

> **The "terminal"** is the plain text app where you type commands. On a
> Mac it's called **Terminal** (find it with Spotlight: press `⌘ + Space`,
> type "Terminal", hit Enter). On Windows it's **PowerShell**. You'll
> paste a few lines into it — that's all.

---

## Step 1 — Install Claude Code

Claude Code is the assistant DanApply runs inside. Two ways to install it:

### Easiest: the Desktop app (no terminal)
Download and run the installer, then sign in with your Claude account:
- **Mac:** [download the Desktop app](https://claude.ai/api/desktop/darwin/universal/dmg/latest/redirect)
- **Windows:** [download the Desktop app](https://claude.com/download)

### Or: the terminal version
Open your terminal and paste **one** of these:

```bash
# Mac / Linux
curl -fsSL https://claude.ai/install.sh | bash
```
```powershell
# Windows (PowerShell)
irm https://claude.ai/install.ps1 | iex
```

Then start it and sign in:
```bash
claude
```
The first time, it opens your browser to log in. Done — type `/exit` to
leave for now, or leave it open for Step 3.

> Full, always-current install help (every OS): the official
> [Claude Code setup guide](https://code.claude.com/docs/en/setup) and,
> if the terminal is new to you, the gentle
> [terminal guide](https://code.claude.com/docs/en/terminal-guide).

---

## Step 2 — Install `uv` (DanApply's engine helper)

DanApply has a small built-in engine that does the mechanical work
(reading PDFs, scoring, making the PDF files). It runs through a free
tool called **uv**, which also sets up everything else it needs
automatically. Install it with one line:

```bash
# Mac / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```
```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**After it finishes, close the terminal window and open a fresh one** so
the new tool is recognised. That's the only thing to remember here.

> You do **not** need to install Python or anything else — uv handles it
> the first time DanApply runs.

---

## Step 3 — Install the DanApply plugin

In your terminal, paste these two lines:

```bash
claude plugin marketplace add erton6/danapply
claude plugin install danapply@danapply
```

The first line tells Claude Code where to find DanApply; the second
installs it. That's it — DanApply is now part of Claude Code.

---

## Step 4 — Launch and set up your profile

Start Claude Code (open the Desktop app, or type `claude` in the
terminal), then type:

```
/danapply
```

The **very first time**, DanApply notices you don't have a profile yet
and starts a friendly **onboarding interview** — it asks about your
situation, your background, what roles you're after, and your constraints.
It takes 30–45 minutes and **you can pause and come back anytime**.

During onboarding it will:
1. Ask you to **paste or point to your current CV** (so it learns your
   real experience — it never invents anything).
2. Walk you through writing **one cover letter in your own words** — this
   is how it learns your voice. Write it like *you*, not "professionally";
   it fixes grammar later, never your voice.
3. Ask whether you want a **photo** on your CV, and let you pick the
   **style** (classic / minimal / modern / creative — all clean and
   ATS-safe) and an **accent colour**.

When it's done, you have a ready CV and your first cover letter as **PDF
files**, plus a saved profile. Everything lives in a folder called
`danapply-data` in your home directory.

> The engine builds itself the first time you use it (a few seconds,
> one time only) — that's `uv` doing its job. You don't have to do
> anything.

---

## Step 5 — Everyday use

Once you're set up, a normal session is quick. Start Claude Code, type
`/danapply`, and just talk to it. Some things you can say:

| You say | DanApply does |
|---|---|
| *"Here's a job posting"* (paste the text, drop a PDF, or paste a screenshot) | Reads it, scores how well it fits you, adds it to your pipeline |
| *"Tailor my CV and cover letter for this one"* | Writes both in your voice, Danish-calibrated, and renders fresh PDFs |
| *"Make the CV one page"* / *"try a navy colour"* / *"more minimal"* | Adjusts the formatting and re-renders — nothing is set in stone |
| *"Prep me for the interview at [company]"* | Builds a tailored interview brief |
| *"Log this to Jobnet"* | Generates the "Opret Joblog" prompt for your dagpenge count |
| *"Where am I?"* | Shows your pipeline, recent activity, and weekly application status |

**A golden rule:** DanApply never submits anything for you. It prepares;
you open the PDFs, read them, ask for any changes, and send them yourself.

> **One important note about job links:** DanApply doesn't open web links.
> If you have a posting as a URL, copy the **text** of the posting and
> paste that instead. This is on purpose — it keeps everything on your
> machine and private.

---

## Where your things are kept

Everything DanApply makes is in one folder in your home directory:
`danapply-data/`

```
danapply-data/
├── profile/          ← who you are: your CV facts, voice, photo, settings
├── resume_drafts/    ← your generated CV PDFs
├── cover_letters/    ← your generated cover-letter PDFs
├── raw_searches/     ← drop job-posting files here for batch processing
└── memory.db         ← the list of jobs you've worked on
```

Nothing leaves this folder. No cloud, no tracking, no other AI service —
your CV, your writing, and your applications stay with you.

---

## If something goes wrong

- **`/danapply` says the engine isn't available, or a command fails with
  "uv: command not found".** `uv` (Step 2) either isn't installed or the
  terminal hasn't picked it up yet. Close every terminal window, open a
  fresh one, and try again. If it still fails, re-run the Step 2 install
  line.
- **`claude: command not found`.** Claude Code (Step 1) isn't installed,
  or you need a fresh terminal window. Reopen the terminal; if needed,
  re-run the Step 1 install line, then `claude doctor` to check.
- **`/danapply` does nothing / isn't recognised.** The plugin didn't
  install. Re-run the two lines in Step 3, then restart Claude Code.
- **Need a paid plan.** If Claude Code won't let you log in, confirm your
  account is on Pro, Max, Team, or Enterprise — the free plan doesn't
  include Claude Code.
- **Still stuck?** Run `claude doctor` (it diagnoses common problems) or
  open an issue at
  [github.com/erton6/danapply/issues](https://github.com/erton6/danapply/issues).

---

## Keeping it up to date

```bash
claude plugin update danapply@danapply
```
Claude Code itself updates on its own in the background.

---

That's everything. Once you've done the one-time setup, landing the next
application is: open Claude Code → `/danapply` → paste a posting → review
the PDFs → send. Good luck with the search. 🍀
