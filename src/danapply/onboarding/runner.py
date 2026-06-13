"""Interactive runner — walks chapters, prompts user, saves state.

Designed to work with ``input()`` and ``print()`` so it's testable by
swapping ``stdin``/``stdout``. The :class:`Runner` accepts injected
``read`` / ``write`` callables so tests can drive it programmatically.

Flow:

  1. Resume from saved state if any (or start fresh)
  2. For each chapter in order:
     - Skip if already completed (unless ``replay_all=True``)
     - Print pre_amble, ask each question, record answer
     - Save state after the chapter finishes
  3. Special chapters:
     - ``reality_check`` prints a synthesised summary before its question
     - ``existing_cv`` runs the Danish-mode register check on the supplied file
     - ``voice_exercise`` calls extract.voice on the supplied file
  4. After the wrap-up chapter, build the profile yaml files and clear state

The runner never raises on user-side errors — it re-prompts. It does
raise on hard environment errors (e.g. cannot write state file).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from danapply import paths
from danapply.onboarding import state as state_mod
from danapply.onboarding.chapters import CHAPTERS, chapter_index
from danapply.onboarding.models import Chapter, Question
from danapply.onboarding.profile_builder import (
    build_profile_files,
    render_reality_check_summary,
)
from danapply.onboarding.state import OnboardingState

ReadFn = Callable[[str], str]
WriteFn = Callable[[str], None]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def run_onboarding(
    resume: bool = False,
    reset: bool = False,
    read: ReadFn | None = None,
    write: WriteFn | None = None,
) -> OnboardingState:
    """Run the interactive interview. Returns the final OnboardingState.

    Args:
        resume: If True and state exists, pick up from the last
            un-answered chapter. If False, restart from the top
            (existing state is OVERWRITTEN — caller decides).
        reset: If True, deletes any saved state before starting.
        read: Callable taking a prompt string, returning user input.
            Defaults to ``input``.
        write: Callable taking a string to display. Defaults to ``print``.
    """
    read = read or input
    write = write or _print

    if reset:
        state_mod.clear_state()

    state = state_mod.load_state() if resume else None
    if state is None:
        state = OnboardingState()

    runner = Runner(state=state, read=read, write=write)
    runner.run()
    return state


def _print(text: str) -> None:
    print(text)  # noqa: T201 — print IS the contract for the default writer


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
@dataclass
class Runner:
    state: OnboardingState
    read: ReadFn
    write: WriteFn
    replay_all: bool = False
    """If True, ignore already-completed chapters and re-ask them."""

    abort: bool = field(default=False, init=False)

    def run(self) -> None:
        for chapter in CHAPTERS:
            if self.abort:
                return
            if (
                not self.replay_all
                and self.state.chapter_completed(chapter.id)
                and chapter.id not in {"wrap_up"}
            ):
                # Skip chapters we already have answers for
                continue
            self._run_chapter(chapter)

        # End of interview: write the profile files + clear state
        if not self.abort:
            written = build_profile_files(self.state)
            self.write("")
            self.write("Saved:")
            for kind, p in written.items():
                self.write(f"  ✓ {kind:<8} {p}")
            self.write("")
            state_mod.clear_state()

    # -----------------------------------------------------------------------
    # Chapter dispatch
    # -----------------------------------------------------------------------
    def _run_chapter(self, chapter: Chapter) -> None:
        idx = chapter_index(chapter.id)
        total = len(CHAPTERS)
        self.write("")
        self.write(f"─── Chapter {idx + 1}/{total}: {chapter.title} ───")
        if chapter.intent:
            self.write(f"({chapter.intent})")
        if chapter.pre_amble:
            self.write("")
            self.write(chapter.pre_amble)

        # Special chapter: reality_check renders synthesis before its question
        if chapter.id == "reality_check":
            self.write(render_reality_check_summary(self.state))

        # Collect answers for each question
        answers: dict[str, Any] = {}
        for q in chapter.questions:
            answer = self._ask(q)
            if answer is _ABORT:
                self.abort = True
                self.write("\nInterview aborted. Resume later with "
                           "`danapply onboard --resume`.")
                return
            answers[q.id] = answer

        # Chapter-specific side effects
        if chapter.id == "existing_cv":
            self._handle_cv_chapter(answers)
        elif chapter.id == "voice_exercise":
            self._handle_voice_chapter(answers)
        elif chapter.id == "reality_check":
            confirmed = bool(answers.get("confirm", True))
            if not confirmed:
                self.write("\nNo confirmation — exiting before saving. "
                           "Run `danapply onboard --reset` to restart, "
                           "or `--resume` to continue editing answers.")
                self.abort = True
                return

        self.state.record(chapter.id, answers)
        state_mod.save_state(self.state)

        if chapter.post_amble:
            self.write("")
            self.write(chapter.post_amble)

    # -----------------------------------------------------------------------
    # Question prompts
    # -----------------------------------------------------------------------
    def _ask(self, q: Question) -> Any:
        """Ask a single question. Returns the parsed answer or :const:`_ABORT`."""
        while True:
            prompt = self._format_prompt(q)
            try:
                raw = self.read(prompt)
            except (EOFError, KeyboardInterrupt):
                return _ABORT

            raw = (raw or "").strip()

            # Empty answer handling
            if not raw:
                if q.default is not None:
                    return q.default
                if not q.required:
                    return ""
                self.write("  (answer required)")
                continue

            # Parse based on type
            parsed = self._parse_answer(q, raw)
            if parsed is _PARSE_ERROR:
                continue  # _parse_answer already wrote the error
            return parsed

    def _format_prompt(self, q: Question) -> str:
        parts = [q.prompt]
        if q.choices:
            parts.append(f"  [{' | '.join(q.choices)}]")
        if q.answer_type == "bool":
            parts.append("  [y/n]")
        if q.default is not None and q.default != "":
            parts.append(f"  (default: {q.default})")
        if q.help_text:
            parts.append(f"  {q.help_text}")
        return "\n".join(parts) + "\n> "

    def _parse_answer(self, q: Question, raw: str) -> Any:
        t = q.answer_type
        if t in ("text", "long_text"):
            return raw

        if t == "choice":
            if q.choices is None or raw in q.choices:
                return raw
            self.write(f"  (must be one of: {', '.join(q.choices)})")
            return _PARSE_ERROR

        if t == "multi_choice":
            picked = [s.strip() for s in raw.split(",") if s.strip()]
            if q.choices:
                bad = [p for p in picked if p not in q.choices]
                if bad:
                    self.write(f"  (unknown choices: {', '.join(bad)})")
                    return _PARSE_ERROR
            return picked

        if t == "number":
            try:
                # Try int first; fall back to float
                return int(raw)
            except ValueError:
                try:
                    return float(raw)
                except ValueError:
                    self.write("  (must be a number)")
                    return _PARSE_ERROR

        if t == "bool":
            lowered = raw.lower()
            if lowered in ("y", "yes", "true", "1"):
                return True
            if lowered in ("n", "no", "false", "0"):
                return False
            self.write("  (must be y/n)")
            return _PARSE_ERROR

        if t == "file_path":
            p = Path(raw).expanduser()
            if not p.exists():
                self.write(f"  (no such file: {p})")
                return _PARSE_ERROR
            return str(p.resolve())

        return raw

    # -----------------------------------------------------------------------
    # Side effects for special chapters
    # -----------------------------------------------------------------------
    def _handle_cv_chapter(self, answers: dict[str, Any]) -> None:
        """If a CV path was supplied, copy to cv_content.md and run register check."""
        cv_path = answers.get("cv_sample_path")
        if not cv_path:
            return

        from danapply.extract.register import apply_register_rules

        try:
            raw = Path(cv_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            self.write(f"  (couldn't read CV file: {exc} — skipping)")
            return

        target = paths.cv_content_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(raw, encoding="utf-8")
        self.write(f"  ✓ saved CV content to {target}")

        result = apply_register_rules(raw)
        if result.changes:
            self.write(
                f"  Danish-mode check: {len(result.changes)} potential "
                f"adjustments (register {result.register_score:.1f}/10). "
                f"See `danapply tailor` output for per-section calibration."
            )
        else:
            self.write(
                f"  Danish-mode check: clean ({result.register_score:.1f}/10) — "
                f"no overclaiming flagged."
            )

    def _handle_voice_chapter(self, answers: dict[str, Any]) -> None:
        sample_path = answers.get("voice_sample_path")
        if not sample_path:
            return

        from danapply.extract.voice import extract_voice, save_voice_profile

        try:
            text = Path(sample_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            self.write(f"  (couldn't read voice sample: {exc} — skipping)")
            return

        self.write(f"  Extracting voice from {Path(sample_path).name}…")
        profile = extract_voice(text)
        yaml_path, md_path = save_voice_profile(profile, paths.profile_dir())
        self.write(f"  ✓ {yaml_path}")
        self.write(f"  ✓ {md_path}")
        if profile.extraction_method == "templated":
            self.write(
                f"  (saved templated default — {profile.notes.splitlines()[0]})"
            )


# Sentinel values used internally
_ABORT = object()
_PARSE_ERROR = object()
