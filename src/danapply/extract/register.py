"""Danish-mode register calibration (rule-based).

Deterministic substring swaps + regex replacements that strip
overclaiming, replace US-power verbs with calibrated alternatives, and
remove filler phrases. Runs over the **templated** tailoring path only.

When Claude Code writes cover-letter prose in-conversation, the register
rules live in ``skills/danapply/danish_register_guide.md`` and are part
of the writing instructions — no post-processing pass runs over
Claude-written text.

Returns a ``RegisterResult`` with the original text, the calibrated
text, a categorised diff log, and a register score (1-10) where
10 = strong Danish mode. Keep the swap tables in sync with
``danish_register_guide.md``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from danapply.extract.voice import VoiceProfile

ChangeCategory = Literal[
    "superlative", "intensifier", "filler", "power_verb", "self_promotion"
]


@dataclass
class RegisterChange:
    category: ChangeCategory
    before: str
    after: str


@dataclass
class RegisterResult:
    original: str
    calibrated: str
    changes: list[RegisterChange] = field(default_factory=list)
    register_score: float = 5.0
    """1-10 scale; 10 = strong Danish mode."""

    method: Literal["rules", "llm"] = "rules"

    def summary(self) -> str:
        """Short audit-line for logs."""
        n = len(self.changes)
        by_cat: dict[str, int] = {}
        for c in self.changes:
            by_cat[c.category] = by_cat.get(c.category, 0) + 1
        cats = ", ".join(f"{k}={v}" for k, v in sorted(by_cat.items())) or "none"
        return f"Register {self.register_score:.1f}/10 via {self.method}: {n} change(s) ({cats})"


# ---------------------------------------------------------------------------
# Swap tables — keep these in sync with docs/danish_register_guide.md
# ---------------------------------------------------------------------------

# Words to strip entirely (or with a one-word swap). Word-boundary aware.
_SUPERLATIVES = {
    "exceptional": "",
    "outstanding": "",
    "proven": "",
    "extensive": "",
    "remarkable": "",
    "extraordinary": "",
    "world-class": "",
    "best-in-class": "",
    "top-tier": "",
    "elite": "",
    "invaluable": "",
    "unparalleled": "",
    "groundbreaking": "",
    "cutting-edge": "",
}

_INTENSIFIERS = {
    "highly": "",
    "truly": "",
    "extraordinarily": "",
    "incredibly": "",
    "vastly": "",
    "tremendously": "",
    "deeply": "",
    "absolutely": "",
}

# Phrases to delete entirely — they contribute zero information.
_FILLER_PHRASES = [
    "self-starter",
    "team player",
    "results-driven",
    "results driven",
    "highly motivated",
    "detail-oriented",
    "detail oriented",
    "goal-oriented",
    "goal oriented",
    "passionate about",
    "excellent communication skills",
    "strong work ethic",
    "quick learner",
    "problem-solver",
    "problem solver",
    "dynamic professional",
    "out-of-the-box thinker",
    "go-getter",
]

# US-power verbs → DK-appropriate equivalents
_POWER_VERB_SWAPS = {
    "spearheaded": "co-led",
    "pioneered": "built",
    "championed": "supported",
    "orchestrated": "coordinated",
    "transformed": "redesigned",
    "catalysed": "initiated",
    "catalyzed": "initiated",
    "revolutionised": "redesigned",
    "revolutionized": "redesigned",
    "mastered": "developed expertise in",
    "synergised": "collaborated with",
    "synergized": "collaborated with",
    "crushed": "exceeded",
    "slashed": "reduced",
    "skyrocketed": "grew significantly",
}

# Self-promotion patterns: (regex, replacement)
_SELF_PROMOTION_PATTERNS = [
    (re.compile(r"\bI am skilled at\b", re.I), "experience with"),
    (re.compile(r"\bI am an expert in\b", re.I), "experience with"),
    (re.compile(r"\bI excel at\b", re.I), "experience with"),
    (re.compile(r"\bI am highly experienced in\b", re.I), "experience with"),
    (re.compile(r"\bI have a proven track record of\b", re.I), "delivered"),
    (re.compile(r"\bI successfully completed\b", re.I), "completed"),
    (re.compile(r"\bI am uniquely positioned to\b", re.I), ""),
]


# ---------------------------------------------------------------------------
# Rule-based calibration
# ---------------------------------------------------------------------------
def apply_register_rules(text: str) -> RegisterResult:
    """Apply the deterministic Danish-mode swap tables. Always succeeds."""
    if not text:
        return RegisterResult(original=text, calibrated=text, method="rules",
                              register_score=10.0)

    calibrated = text
    changes: list[RegisterChange] = []

    # 1) Strip superlatives (preserve word boundaries)
    for word, replacement in _SUPERLATIVES.items():
        pattern = re.compile(rf"\b{re.escape(word)}\b", re.I)
        for m in pattern.finditer(calibrated):
            changes.append(RegisterChange("superlative", m.group(0), replacement))
        calibrated = pattern.sub(replacement, calibrated)

    # 2) Strip intensifiers
    for word, replacement in _INTENSIFIERS.items():
        pattern = re.compile(rf"\b{re.escape(word)}\b", re.I)
        for m in pattern.finditer(calibrated):
            changes.append(RegisterChange("intensifier", m.group(0), replacement))
        calibrated = pattern.sub(replacement, calibrated)

    # 3) Delete filler phrases (case-insensitive, word-bounded)
    for phrase in _FILLER_PHRASES:
        pattern = re.compile(rf"\b{re.escape(phrase)}\b", re.I)
        for m in pattern.finditer(calibrated):
            changes.append(RegisterChange("filler", m.group(0), ""))
        calibrated = pattern.sub("", calibrated)

    # 4) Swap US-power verbs
    for verb, replacement in _POWER_VERB_SWAPS.items():
        # Match the verb word with any standard suffix (-ed, -ing, -s)
        # but keep the swap simple — match exact verb only for clarity.
        pattern = re.compile(rf"\b{re.escape(verb)}\b", re.I)
        for m in pattern.finditer(calibrated):
            changes.append(RegisterChange("power_verb", m.group(0), replacement))
        calibrated = pattern.sub(replacement, calibrated)

    # 5) Rewrite self-promotion structures
    for pattern, replacement in _SELF_PROMOTION_PATTERNS:
        for m in pattern.finditer(calibrated):
            changes.append(RegisterChange("self_promotion", m.group(0), replacement))
        calibrated = pattern.sub(replacement, calibrated)

    # Clean up artefacts from deletions: collapse multiple spaces, leading
    # spaces before punctuation, double commas, etc.
    calibrated = _post_clean(calibrated)

    register_score = _compute_register_score(calibrated, changes)
    return RegisterResult(
        original=text, calibrated=calibrated, changes=changes,
        method="rules", register_score=register_score,
    )


def _post_clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r",\s*,", ",", text)
    text = re.sub(r"\s+'", "'", text)
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    return text.strip()


def _compute_register_score(text: str, changes: list[RegisterChange]) -> float:
    """Rough 1-10 score of how Danish-mode the output reads.

    Heuristic: more remaining superlatives/intensifiers → lower score.
    Made deterministic so callers can assert on it.
    """
    text_lower = text.lower()
    remaining = 0
    for word in (*_SUPERLATIVES.keys(), *_INTENSIFIERS.keys()):
        if re.search(rf"\b{re.escape(word)}\b", text_lower):
            remaining += 1
    # Start at 10, drop 1.5 per remaining issue, floor at 1
    score = 10.0 - 1.5 * remaining
    return max(1.0, min(10.0, score))


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def apply_register(
    text: str,
    voice_profile: VoiceProfile | None = None,
) -> RegisterResult:
    """Apply Danish-mode register calibration (deterministic rules).

    Used as the safety net on the templated tailoring path. When Claude
    writes the prose in-conversation, register rules are part of its
    instructions (``danish_register_guide.md``) — this filter does not run
    over Claude-written text.

    ``voice_profile`` is accepted for interface stability; the rule-based
    pass is voice-neutral (it only strips and swaps; it never rewrites).
    """
    return apply_register_rules(text)
