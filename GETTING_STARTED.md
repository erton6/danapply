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
- About **20 minutes** for the one-time setup, and **30–45 minutes** for
  the first guided interview.
- Handy for the interview: your **current CV**, one **piece of writing
  you wrote yourself** (an old cover letter, a blog post, a long
  email — 500+ words is ideal), and a **headshot photo** if you want one
  on your CV (Danish CVs usually have one).

> ### ⚠️ Important: the setup happens in the terminal
> Installing DanApply means pasting a few commands into a terminal. The
> Claude **Desktop app on its own is not enough** — the install steps
> below need the `claude` *command*, which comes from the terminal
> installer in Step 2. (You can still use the Desktop app for everyday
> work later, once setup is done.)
>
> **The "terminal"** is the plain text app where you type commands:
> - **Windows:** **PowerShell** (click Start, type "PowerShell", open it).
> - **Mac:** **Terminal** (press `⌘ + Space`, type "Terminal", Enter).
>
> You'll paste lines into it and press Enter. After installing each tool,
> **close the terminal and open a new one** so it gets recognised.

---

## The setup: 4 tools, then the plugin

You'll install three small tools (**Git**, **Claude Code**, **uv**), then
the DanApply plugin itself. Do them in order. After each install, open a
**fresh** terminal window before the next step.

---

### Step 1 — Install Git

Git is what lets Claude Code download plugins. Without it you'll see
*"Command 'git' not found"*.

**Windows:**
- Download and run **[Git for Windows](https://git-scm.com/downloads/win)**
  (click through the installer with the default options), **or** in
  PowerShell run:
  ```powershell
  winget install --id Git.Git -e
  ```

**Mac:** Git usually comes pre-installed. To make sure, run this — if Git
is missing, a macOS box pops up offering to install it; click **Install**:
```bash
xcode-select --install
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt update && sudo apt install git
```

**Then close the terminal and open a fresh one.** Check it worked:
```bash
git --version
```
You should see a version number (e.g. `git version 2.43.0`).

---

### Step 2 — Install Claude Code

Claude Code is the assistant DanApply runs inside. Install the version
that gives you the `claude` **command** in your terminal:

**Windows (PowerShell):**
```powershell
irm https://claude.ai/install.ps1 | iex
```
**Mac / Linux:**
```bash
curl -fsSL https://claude.ai/install.sh | bash
```

**Close the terminal, open a fresh one**, then sign in:
```bash
claude
```
The first time, it opens your browser to log in with your Claude account.
Once you see it start, type `/exit` to come back to the terminal.

> Prefer a window with buttons for daily use? You can *also* install the
> [Desktop app](https://code.claude.com/docs/en/desktop-quickstart) — but
> the install steps in this guide still need the `claude` command above.
> Full, always-current install help for every system:
> [code.claude.com/docs/en/setup](https://code.claude.com/docs/en/setup).

---

### Step 3 — Install uv (DanApply's engine helper)

DanApply has a small built-in engine (it reads PDFs, scores jobs, makes
the PDF files). It runs through a free tool called **uv**, which also
sets up everything else it needs — including Python — automatically.

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
**Mac / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Close the terminal and open a fresh one** so uv is recognised. You do
**not** need to install Python separately — uv handles it.

---

### Step 4 — Install the DanApply plugin

With Git, Claude Code, and uv all installed, paste these two lines:

```bash
claude plugin marketplace add erton6/danapply
claude plugin install danapply@danapply
```

The first line points Claude Code at DanApply on GitHub (this is the step
that needs Git); the second installs it. That's it — DanApply is now part
of Claude Code.

---

### Step 5 — Launch and set up your profile

Start Claude Code by typing `claude` in the terminal, then type:

```
/danapply
```

The **very first time**, DanApply notices you don't have a profile yet
and starts a friendly **onboarding interview** — your situation, your
background, the roles you want, your constraints. It takes 30–45 minutes
and **you can pause and come back anytime**.

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

> The engine builds itself the first time you use it (a few seconds, one
> time only) — that's `uv` doing its job. You don't have to do anything.

---

### Step 6 — Everyday use

Once you're set up, a normal session is quick. Start Claude Code (`claude`),
type `/danapply`, and just talk to it:

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

> **One note about job links:** DanApply doesn't open web links. If you
> have a posting as a URL, copy the **text** of the posting and paste
> that instead. This is on purpose — it keeps everything on your machine
> and private.

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

- **`'claude' is not recognized` / `claude: command not found`.** Claude
  Code (Step 2) isn't installed, or your terminal hasn't picked it up
  yet. Close every terminal window, open a fresh one, and try again. If
  it still fails, re-run the Step 2 install line, then check with
  `claude --version`.
- **`Failed to add marketplace: Command 'git' not found`.** Git (Step 1)
  isn't installed, or the terminal needs restarting. Install Git, **open
  a fresh terminal**, confirm with `git --version`, then re-run the Step 4
  commands.
- **`/danapply` says the engine isn't available, or `uv: command not
  found`.** uv (Step 3) isn't installed or the terminal hasn't picked it
  up. Close all terminals, open a fresh one, and try again; re-run the
  Step 3 line if needed.
- **`/danapply` does nothing / isn't recognised.** The plugin didn't
  install. Re-run the two lines in Step 4, then restart Claude Code.
- **Can't log in to Claude Code.** Confirm your account is on a paid plan
  (Pro / Max / Team / Enterprise) — the free plan doesn't include Claude
  Code.
- **Still stuck?** Run `claude doctor` (it diagnoses common problems) or
  open an issue at
  [github.com/erton6/danapply/issues](https://github.com/erton6/danapply/issues).

> **The golden rule for almost every "not recognized / not found" error:**
> after installing a tool, **close the terminal and open a new one.** New
> tools are only picked up by terminal windows opened *after* they're
> installed.

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
