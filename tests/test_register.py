"""Tests for the Danish-mode register filter."""

from __future__ import annotations

from danapply.extract.register import (
    _compute_register_score,
    apply_register,
    apply_register_rules,
)
from danapply.extract.voice import VoiceProfile


# ---------------------------------------------------------------------------
# Rule-based — superlatives
# ---------------------------------------------------------------------------
def test_strip_superlatives() -> None:
    text = "I have exceptional skills and a proven track record."
    result = apply_register_rules(text)
    assert "exceptional" not in result.calibrated.lower()
    assert "proven" not in result.calibrated.lower()
    assert any(c.category == "superlative" for c in result.changes)


def test_strip_world_class() -> None:
    text = "World-class engineer with outstanding results."
    result = apply_register_rules(text)
    assert "world-class" not in result.calibrated.lower()
    assert "outstanding" not in result.calibrated.lower()


def test_strip_intensifiers() -> None:
    text = "I am highly motivated and incredibly passionate."
    result = apply_register_rules(text)
    assert "highly" not in result.calibrated.lower()
    assert "incredibly" not in result.calibrated.lower()


# ---------------------------------------------------------------------------
# Rule-based — filler phrases
# ---------------------------------------------------------------------------
def test_strip_self_starter_filler() -> None:
    text = "I am a self-starter with great work ethic."
    result = apply_register_rules(text)
    assert "self-starter" not in result.calibrated.lower()
    assert any(c.category == "filler" for c in result.changes)


def test_strip_passionate_about() -> None:
    text = "Passionate about driving results in the team."
    result = apply_register_rules(text)
    assert "passionate about" not in result.calibrated.lower()


def test_strip_results_driven_with_or_without_hyphen() -> None:
    for text in ("Results-driven professional.", "Results driven approach."):
        result = apply_register_rules(text)
        assert "results-driven" not in result.calibrated.lower()
        assert "results driven" not in result.calibrated.lower()


# ---------------------------------------------------------------------------
# Rule-based — US power verbs
# ---------------------------------------------------------------------------
def test_spearheaded_swapped_to_co_led() -> None:
    text = "I spearheaded the initiative."
    result = apply_register_rules(text)
    assert "spearheaded" not in result.calibrated.lower()
    assert "co-led" in result.calibrated.lower()
    assert any(c.category == "power_verb" for c in result.changes)


def test_pioneered_swapped_to_built() -> None:
    result = apply_register_rules("She pioneered a new framework.")
    assert "pioneered" not in result.calibrated.lower()
    assert "built" in result.calibrated.lower()


def test_synergised_and_synergized_both_swapped() -> None:
    for text in ("Synergised teams.", "Synergized teams."):
        result = apply_register_rules(text)
        assert "synerg" not in result.calibrated.lower()
        assert "collaborat" in result.calibrated.lower()


# ---------------------------------------------------------------------------
# Rule-based — self-promotion structures
# ---------------------------------------------------------------------------
def test_i_am_skilled_at_rewritten() -> None:
    text = "I am skilled at Python and SQL."
    result = apply_register_rules(text)
    assert "i am skilled at" not in result.calibrated.lower()
    assert "experience with" in result.calibrated.lower()
    assert any(c.category == "self_promotion" for c in result.changes)


def test_proven_track_record_rewritten() -> None:
    text = "I have a proven track record of strong results."
    result = apply_register_rules(text)
    # Both 'proven' (superlative) and 'I have a proven track record of'
    # (self_promotion) match. Either swap is acceptable as long as the
    # phrase is gone.
    assert "proven track record" not in result.calibrated.lower()


# ---------------------------------------------------------------------------
# Rule-based — edge cases
# ---------------------------------------------------------------------------
def test_empty_text_returns_max_score() -> None:
    result = apply_register_rules("")
    assert result.register_score == 10.0
    assert result.calibrated == ""


def test_clean_text_unchanged() -> None:
    text = "I worked at Iberia Insights for two years."
    result = apply_register_rules(text)
    assert result.calibrated == text
    assert result.changes == []
    assert result.register_score == 10.0


def test_case_insensitive_match() -> None:
    text = "EXCEPTIONAL skills with WORLD-CLASS results."
    result = apply_register_rules(text)
    assert "exceptional" not in result.calibrated.lower()
    assert "world-class" not in result.calibrated.lower()


def test_word_boundary_respected() -> None:
    """'extension' contains 'extens' but not the word 'extensive'."""
    text = "The extension method was helpful."
    result = apply_register_rules(text)
    assert "extension" in result.calibrated
    assert result.changes == []  # nothing stripped


def test_post_clean_removes_double_spaces() -> None:
    text = "I am highly motivated and truly passionate."
    result = apply_register_rules(text)
    assert "  " not in result.calibrated


# ---------------------------------------------------------------------------
# Register score
# ---------------------------------------------------------------------------
def test_register_score_drops_for_remaining_issues() -> None:
    text_with_issues = "Outstanding incredibly proven."
    score = _compute_register_score(text_with_issues, changes=[])
    # 3 remaining issues × 1.5 = 4.5 deduction → 5.5. Lower than max.
    assert score < 7.0


def test_register_score_max_for_clean_text() -> None:
    assert _compute_register_score("Plain factual text.", changes=[]) == 10.0


def test_result_summary_is_a_human_string() -> None:
    text = "Exceptional incredibly highly results-driven."
    result = apply_register_rules(text)
    summary = result.summary()
    assert "Register" in summary
    assert "via rules" in summary
    assert "change" in summary


# ---------------------------------------------------------------------------
# apply_register — public entry point
# ---------------------------------------------------------------------------
def test_apply_register_uses_rules() -> None:
    result = apply_register("An exceptional analyst.")
    assert result.method == "rules"
    assert "exceptional" not in result.calibrated.lower()


def test_apply_register_accepts_voice_profile_for_interface_stability() -> None:
    voice = VoiceProfile()
    result = apply_register("A truly proven leader.", voice_profile=voice)
    assert result.method == "rules"
