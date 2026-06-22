# Installing DanApply

DanApply is a **Claude Code plugin**. Claude is the interface and the
writer; a bundled Python engine does the mechanical work (parsing,
scoring, PDF rendering, SQLite memory). There is **no API key to
configure** — all language work happens inside your Claude Code session.

> **Not very technical?** This page is the concise/technical reference.
> For a plain-language, hand-held walkthrough, use
> **[GETTING_STARTED.md](GETTING_STARTED.md)** instead.

---

## Requirements

- **[Claude Code](https://code.claude.com/docs/en/setup) CLI** (the `claude`
  command in your terminal), with a paid Claude plan (Pro / Max / Team /
  Enterprise). The desktop app alone does not provide the `claude plugin`
  commands used below.
- **[Git](https://git-scm.com/downloads)** — required: `claude plugin
  marketplace add <github-repo>` clones this repo with Git. On Windows,
  install [Git for Windows](https://git-scm.com/downloads/win).
- **[uv](https://docs.astral.sh/uv/)** — runs the engine (`uv run`) and
  provides Python 3.11+ automatically
- ~50 MB disk
- macOS, Linux, or Windows (native or WSL)

---

## Install

### As a plugin (recommended)

```bash
# Add the repo as a marketplace, then install:
claude plugin marketplace add erton6/danapply
claude plugin install danapply@danapply
```

Or from a local clone:

```bash
git clone https://github.com/erton6/danapply.git
claude plugin marketplace add ./danapply
claude plugin install danapply@danapply
```

That's it — the engine's Python environment is built automatically the
first time DanApply runs a command (`uv run` syncs it on demand, into the
installed plugin directory). You don't need to run `uv sync` yourself.

> Prefer to pre-build it (e.g. to surface any setup error up front)? From
> a local clone you can run `uv sync` inside the cloned `danapply/` folder.

### First session

Start Claude Code anywhere and type:

```
/danapply
```

On a fresh machine the skill detects there's no profile and walks you
through onboarding (~30–45 min, resumable). After that, every session
starts with a short status greeting.

You can also just talk to it — "find me new jobs", "tailor the top 3",
"I got an interview at Pleo" — the skill triggers on intent, no slash
command needed.

---

## What setup actually involves

1. **Onboarding interview** — builds `profile.yaml` (who you are),
   `targets.yaml` (what you're hunting), `cv_content.md` (your facts —
   the grounding source for every generated letter), and optionally
   `dagpenge.yaml`.
2. **Voice capture** — share a writing sample you wrote yourself (an old
   cover letter, a blog post; 500+ words ideal). Claude analyses it
   in-conversation and saves your voice profile. This is what makes
   generated letters sound like you.

Both are one-time. Everything lives in `~/danapply-data/`.

---

## Using the engine directly (optional)

The Python engine is a normal CLI you can run yourself:

```bash
cd danapply
uv run danapply version          # → DanApply 0.5.3
uv run danapply init             # scaffold ~/danapply-data/
uv run danapply render-sample    # smoke test: produces two sample PDFs
uv run danapply list             # browse your pipeline
```

Without Claude, generation commands (`tailor`, `interview-prep`) fall
back to honest templated output — useful for smoke tests, not for real
applications. The conversational layer is the product.

---

## Data directory

All DanApply data lives at `~/danapply-data/` — profile, parsed jobs
(SQLite), generated PDFs, Jobnet prompts. To relocate:

```bash
export DANAPPLY_DATA_DIR=/path/to/your/data
```

Nothing ever leaves this directory — the engine makes no network
requests at all.

---

## Updating

```bash
claude plugin update danapply
# or, from a local clone:
git -C danapply pull && (cd danapply && uv sync)
```

Schema migrations run automatically on the next engine invocation —
existing memory.db files are upgraded in-place without data loss.

---

## Uninstalling

```bash
claude plugin uninstall danapply

# Optional: remove your data
rm -rf ~/danapply-data
```
