"""Tests for the voice profile — persistence + Claude-payload validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from danapply.extract.voice import (
    VoiceProfile,
    load_voice_profile,
    save_voice_profile,
    voice_profile_from_payload,
)


# ---------------------------------------------------------------------------
# Persistence — yaml + md roundtrip
# ---------------------------------------------------------------------------
def test_save_and_load_voice_profile_roundtrip(tmp_path: Path) -> None:
    original = VoiceProfile(
        avg_sentence_length_words=22,
        sentence_rhythm="long and flowing",
        formality_register="warm-conversational",
        opening_style="observation",
        closing_style="warm-confident",
        vocabulary_preferences=["genuinely", "alongside", "drawn from"],
        vocabulary_avoidances=["passionate about", "reach out"],
        characteristic_phrases=[
            "Frankly, it's the only reason I'm writing.",
            "Two years in, I still find it the most interesting problem.",
        ],
        notes="Uses dashes generously; rarely uses exclamation marks.",
        sample_word_count=812,
        extraction_method="claude",
    )
    yaml_path, md_path = save_voice_profile(original, tmp_path)

    assert yaml_path.exists()
    assert md_path.exists()
    assert yaml_path.name == "voice_profile.yaml"
    assert md_path.name == "voice_profile.md"

    loaded = load_voice_profile(tmp_path)
    assert loaded is not None
    assert loaded.avg_sentence_length_words == 22
    assert loaded.sentence_rhythm == "long and flowing"
    assert loaded.characteristic_phrases == original.characteristic_phrases


def test_load_voice_profile_returns_none_when_missing(tmp_path: Path) -> None:
    assert load_voice_profile(tmp_path) is None


def test_load_voice_profile_returns_none_on_malformed_yaml(tmp_path: Path) -> None:
    (tmp_path / "voice_profile.yaml").write_text("not: valid: yaml: [", encoding="utf-8")
    assert load_voice_profile(tmp_path) is None


def test_voice_md_contains_human_readable_sections(tmp_path: Path) -> None:
    profile = VoiceProfile(
        vocabulary_preferences=["honestly", "alongside"],
        vocabulary_avoidances=["world-class"],
        characteristic_phrases=["This is a real sentence I wrote."],
        sample_word_count=600,
    )
    _, md_path = save_voice_profile(profile, tmp_path)
    md = md_path.read_text(encoding="utf-8")
    assert "# Voice profile" in md
    assert "honestly" in md
    assert "world-class" in md
    assert "This is a real sentence" in md


# ---------------------------------------------------------------------------
# Claude-payload validation
# ---------------------------------------------------------------------------
def _valid_payload() -> dict:
    return {
        "avg_sentence_length_words": 17,
        "sentence_rhythm": "balanced",
        "formality_register": "neutral",
        "opening_style": "claim",
        "closing_style": "confident",
        "vocabulary_preferences": ["in practice", "concretely"],
        "vocabulary_avoidances": ["passionate", "world-class"],
        "characteristic_phrases": ["The work was harder than I expected."],
        "superlatives_per_100_words": 0.2,
        "intensifiers_per_100_words": 0.4,
        "notes": "Sober, direct.",
        "sample_word_count": 720,
    }


def test_voice_profile_from_payload_validates_and_stamps_provenance() -> None:
    profile = voice_profile_from_payload(_valid_payload())
    assert profile.extraction_method == "claude"
    assert profile.avg_sentence_length_words == 17
    assert "in practice" in profile.vocabulary_preferences
    assert profile.extracted_at  # stamped at validation time


def test_voice_profile_from_payload_rejects_non_dict() -> None:
    with pytest.raises(ValueError, match="JSON object"):
        voice_profile_from_payload(["not", "a", "dict"])  # type: ignore[arg-type]


def test_voice_profile_from_payload_rejects_bad_types() -> None:
    bad = _valid_payload()
    bad["avg_sentence_length_words"] = "lots"
    with pytest.raises(ValueError, match="failed validation"):
        voice_profile_from_payload(bad)


def test_voice_profile_from_payload_roundtrips_through_disk(tmp_path: Path) -> None:
    profile = voice_profile_from_payload(_valid_payload())
    save_voice_profile(profile, tmp_path)
    loaded = load_voice_profile(tmp_path)
    assert loaded is not None
    assert loaded.extraction_method == "claude"
    assert loaded.characteristic_phrases == profile.characteristic_phrases
