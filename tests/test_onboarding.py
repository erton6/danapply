"""Tests for the onboarding interview flow."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

from danapply.onboarding.chapters import CHAPTERS, chapter_index, get_chapter
from danapply.onboarding.profile_builder import (
    build_profile_files,
    render_reality_check_summary,
)
from danapply.onboarding.runner import Runner
from danapply.onboarding.state import (
    OnboardingState,
    clear_state,
    load_state,
    save_state,
    state_exists,
    state_path,
)


@pytest.fixture(autouse=True)
def _isolated_data_dir(tmp_path: Path):
    os.environ["DANAPPLY_DATA_DIR"] = str(tmp_path)
    yield tmp_path
    os.environ.pop("DANAPPLY_DATA_DIR", None)


# ---------------------------------------------------------------------------
# Chapter library — sanity checks
# ---------------------------------------------------------------------------
def test_all_chapters_have_unique_ids() -> None:
    ids = [c.id for c in CHAPTERS]
    assert len(ids) == len(set(ids))


def test_all_chapters_have_titles_and_intents() -> None:
    for c in CHAPTERS:
        assert c.title.strip()
        assert c.intent.strip()


def test_chapter_index_lookup() -> None:
    assert chapter_index("welcome") == 0
    assert chapter_index("wrap_up") == len(CHAPTERS) - 1
    assert chapter_index("nonexistent") == -1


def test_get_chapter() -> None:
    assert get_chapter("welcome") is not None
    assert get_chapter("nonexistent") is None


def test_chapters_cover_full_design_doc_set() -> None:
    """The 10 chapters from docs/workflows/onboarding.md must all be present."""
    expected = {
        "welcome", "situation", "story", "targets", "constraints",
        "self_assessment", "reality_check", "dk_admin",
        "existing_cv", "voice_exercise", "wrap_up",
    }
    actual = {c.id for c in CHAPTERS}
    assert expected.issubset(actual)


# ---------------------------------------------------------------------------
# State — save / load / clear
# ---------------------------------------------------------------------------
def test_state_does_not_exist_initially() -> None:
    assert state_exists() is False
    assert load_state() is None


def test_save_and_load_state_roundtrip() -> None:
    s = OnboardingState()
    s.record("welcome", {"ready": True})
    s.record("situation", {"name": "Sofia Almeida"})
    save_state(s)

    assert state_exists() is True
    loaded = load_state()
    assert loaded is not None
    assert loaded.chapter_completed("welcome")
    assert loaded.chapter_completed("situation")
    assert loaded.get_answer("situation", "name") == "Sofia Almeida"


def test_state_records_timestamps_on_record() -> None:
    s = OnboardingState()
    first_ts = s.last_updated_at
    s.record("welcome", {"ready": True})
    assert s.last_updated_at >= first_ts


def test_clear_state_removes_file() -> None:
    s = OnboardingState()
    save_state(s)
    assert state_exists()
    clear_state()
    assert not state_exists()


def test_clear_state_idempotent_when_missing() -> None:
    clear_state()  # no error
    clear_state()


def test_load_state_returns_none_on_malformed_yaml() -> None:
    state_path().parent.mkdir(parents=True, exist_ok=True)
    state_path().write_text("not: valid: yaml: [", encoding="utf-8")
    assert load_state() is None


# ---------------------------------------------------------------------------
# Profile builder — translation rules
# ---------------------------------------------------------------------------
def _make_state(**chapter_answers) -> OnboardingState:
    s = OnboardingState()
    for chapter_id, answers in chapter_answers.items():
        s.record(chapter_id, answers)
    return s


def test_build_profile_files_writes_profile_and_targets() -> None:
    s = _make_state(
        situation={
            "name": "Sofia Almeida",
            "location_city": "Aarhus",
            "employment_status": "unemployed",
        },
        targets={
            "tier_a_titles": "Business Analyst, Insights Analyst",
            "tier_b_titles": "Associate Consultant",
            "geography_primary": "Aarhus, Copenhagen",
            "arrangement": "hybrid",
            "remote_ok": True,
            "salary_floor_dkk": 40000,
        },
        constraints={
            "visa_status": "eu_eea",
            "danish_level": "B1",
            "english_level": "fluent",
            "excluded_industries": "tobacco, gambling",
            "max_commute_minutes": 60,
        },
    )
    written = build_profile_files(s)
    assert "profile" in written
    assert "targets" in written
    assert "dagpenge" not in written  # not on dagpenge

    profile = yaml.safe_load(written["profile"].read_text())
    assert profile["name"] == "SOFIA ALMEIDA"
    assert profile["contact"]["location"] == "Aarhus, Denmark"
    lang_names = {lang["name"] for lang in profile["languages"]}
    assert "English" in lang_names
    assert "Danish" in lang_names

    targets = yaml.safe_load(written["targets"].read_text())
    assert targets["roles"]["tier_a_titles"] == ["Business Analyst", "Insights Analyst"]
    assert targets["roles"]["tier_b_titles"] == ["Associate Consultant"]
    assert targets["geography"]["primary"] == ["Aarhus", "Copenhagen"]
    assert targets["geography"]["remote_ok"] is True
    assert targets["arrangement"] == "hybrid"
    assert targets["salary_floor_monthly_dkk"] == 40000
    assert targets["constraints"]["excluded_industries"] == ["tobacco", "gambling"]
    assert targets["constraints"]["max_commute_minutes_one_way"] == 60


def test_build_profile_files_writes_dagpenge_when_on_benefits() -> None:
    s = _make_state(
        situation={"name": "A", "location_city": "X"},
        targets={"tier_a_titles": "Analyst"},
        constraints={"visa_status": "eu_eea", "danish_level": "B2",
                     "english_level": "fluent"},
        dk_admin={
            "on_dagpenge": True,
            "a_kasse": "Akademikernes A-kasse",
            "my_plan_field": "Analyst, Researcher",
            "weekly_threshold": 2,
        },
    )
    written = build_profile_files(s)
    assert "dagpenge" in written
    dag = yaml.safe_load(written["dagpenge"].read_text())
    assert dag["on_dagpenge"] is True
    assert dag["a_kasse"] == "Akademikernes A-kasse"
    assert dag["weekly_threshold"] == 2


def test_build_profile_files_skips_dagpenge_when_not_on_benefits() -> None:
    s = _make_state(
        situation={"name": "A", "location_city": "X"},
        targets={"tier_a_titles": "Analyst"},
        constraints={"visa_status": "eu_eea", "danish_level": "B1",
                     "english_level": "fluent"},
        dk_admin={"on_dagpenge": False},
    )
    written = build_profile_files(s)
    assert "dagpenge" not in written


def test_build_profile_files_merges_with_existing_profile() -> None:
    """Existing hand-edited fields must survive a merge."""
    from danapply import paths

    paths.profile_yaml_path().parent.mkdir(parents=True, exist_ok=True)
    existing = {
        "name": "OLD NAME",
        "tagline_default": "My Hand-Edited Tagline | Don't Overwrite Me",
        "contact": {"phone": "+45 11 22 33 44", "email": "hand@edited.example",
                    "location": "Old Place"},
    }
    paths.profile_yaml_path().write_text(yaml.safe_dump(existing), encoding="utf-8")

    s = _make_state(
        situation={"name": "New Name", "location_city": "Aarhus"},
        targets={"tier_a_titles": "Analyst"},
        constraints={"visa_status": "eu_eea", "danish_level": "B1",
                     "english_level": "fluent"},
    )
    build_profile_files(s)
    merged = yaml.safe_load(paths.profile_yaml_path().read_text())

    # Name + location updated (interview answers won)
    assert merged["name"] == "NEW NAME"
    assert merged["contact"]["location"] == "Aarhus, Denmark"
    # Phone + email NOT in updates — should survive
    assert merged["contact"]["phone"] == "+45 11 22 33 44"
    assert merged["contact"]["email"] == "hand@edited.example"
    # Tagline NOT in updates — should survive
    assert merged["tagline_default"] == "My Hand-Edited Tagline | Don't Overwrite Me"


def test_render_reality_check_summary_contains_key_fields() -> None:
    s = _make_state(
        situation={"name": "Alice", "location_city": "Aarhus",
                   "employment_status": "unemployed",
                   "search_duration_months": 3, "stress_level": 2},
        targets={"tier_a_titles": "Business Analyst",
                 "geography_primary": "Aarhus",
                 "arrangement": "hybrid", "remote_ok": True,
                 "salary_floor_dkk": 38000},
        constraints={"visa_status": "eu_eea", "danish_level": "B1",
                     "english_level": "fluent",
                     "excluded_industries": "tobacco"},
    )
    summary = render_reality_check_summary(s)
    assert "Alice" in summary
    assert "Aarhus" in summary
    assert "unemployed" in summary
    assert "Business Analyst" in summary
    assert "tobacco" in summary


# ---------------------------------------------------------------------------
# Runner — drive with scripted inputs
# ---------------------------------------------------------------------------
class _ScriptedIO:
    """Stand-in for input() / print() that records and replays."""

    def __init__(self, answers: list[str]) -> None:
        self._iter: Iterator[str] = iter(answers)
        self.output: list[str] = []

    def read(self, prompt: str) -> str:
        self.output.append(prompt)
        try:
            return next(self._iter)
        except StopIteration as exc:
            raise EOFError from exc

    def write(self, text: str) -> None:
        self.output.append(text)


def test_runner_skips_completed_chapters() -> None:
    state = OnboardingState()
    state.record("welcome", {"ready": True})
    state.record("situation", {"name": "A", "employment_status": "employed",
                               "search_duration_months": 0, "stress_level": 1,
                               "location_city": "Aarhus"})

    io = _ScriptedIO([
        # Story chapter — 4 questions
        "Brief career story.", "Built a thing.", "Building things.", "",
        # Targets — 6 questions
        "Business Analyst", "", "Aarhus", "hybrid", "y", "0",
        # Constraints — 5 questions
        "eu_eea", "B1", "fluent", "", "0",
        # Self-assessment — 3 questions
        "Analysis", "", "",
        # Reality check — 1 question
        "y",
        # DK admin — 4 questions
        "n", "", "", "0",
        # Existing CV — 1 question (skip)
        "",
        # Voice exercise — 1 question (skip)
        "",
        # Wrap-up — 0 questions (no input needed)
    ])

    runner = Runner(state=state, read=io.read, write=io.write)
    runner.run()

    # Welcome + situation were skipped (already in state); story onward asked
    prompts = "\n".join(io.output)
    assert "Welcome" not in prompts  # chapter header for already-done
    assert "Your story so far" in prompts


def test_runner_handles_choice_validation() -> None:
    state = OnboardingState()
    state.record("welcome", {"ready": True})
    state.record("situation", {"name": "A", "employment_status": "employed",
                               "search_duration_months": 0, "stress_level": 1,
                               "location_city": "Aarhus"})
    state.record("story", {"career_summary": "x", "proudest_achievement": "y",
                           "best_energy_source": "z", "biggest_drain": ""})
    state.record("targets", {"tier_a_titles": "Analyst",
                             "tier_b_titles": "",
                             "geography_primary": "Aarhus",
                             "arrangement": "hybrid", "remote_ok": True,
                             "salary_floor_dkk": 0})

    # Now the constraints chapter — make it reject an invalid choice once
    io = _ScriptedIO([
        "GARBAGE_VISA",  # invalid — rejected
        "eu_eea",        # valid
        "B1",
        "fluent",
        "",
        "0",
        "Analysis",     # self_assessment
        "", "",
        "y",            # reality_check confirm
        "n", "", "", "0",  # dk_admin (off dagpenge)
        "",             # existing_cv skip
        "",             # voice_exercise skip
    ])
    runner = Runner(state=state, read=io.read, write=io.write)
    runner.run()
    assert any("must be one of" in line for line in io.output)


def test_runner_handles_bool_yes_no() -> None:
    state = OnboardingState()
    io = _ScriptedIO([
        "n"  # ready? No → still recorded as False; next chapter would follow
    ])
    runner = Runner(state=state, read=io.read, write=io.write)
    # Just run the welcome chapter manually
    runner._run_chapter(get_chapter("welcome"))
    assert state.get_answer("welcome", "ready") is False


def test_runner_eof_aborts_cleanly() -> None:
    state = OnboardingState()
    io = _ScriptedIO([])  # no inputs at all → EOF immediately
    runner = Runner(state=state, read=io.read, write=io.write)
    runner.run()
    assert runner.abort is True
    # No chapter should be marked complete
    assert state.completed_chapters() == []


def test_runner_reality_check_no_confirmation_aborts() -> None:
    state = OnboardingState()
    # Pre-populate enough state for the summary to render
    state.record("situation", {"name": "A", "location_city": "X",
                               "employment_status": "employed",
                               "search_duration_months": 0,
                               "stress_level": 1})
    state.record("targets", {"tier_a_titles": "Analyst"})
    state.record("constraints", {"visa_status": "eu_eea", "danish_level": "B1",
                                 "english_level": "fluent"})
    io = _ScriptedIO(["n"])  # user says "no" to reality check
    runner = Runner(state=state, read=io.read, write=io.write)
    runner._run_chapter(get_chapter("reality_check"))
    assert runner.abort is True
    # The reality_check answer should NOT be recorded as completed when aborted
    assert not state.chapter_completed("reality_check")


def test_runner_uses_default_on_empty_input() -> None:
    """Pressing enter on a question with a default accepts that default."""
    state = OnboardingState()
    io = _ScriptedIO([""])  # empty — should accept default (True)
    runner = Runner(state=state, read=io.read, write=io.write)
    runner._run_chapter(get_chapter("welcome"))
    assert state.get_answer("welcome", "ready") is True


def test_runner_rejects_invalid_number_then_accepts() -> None:
    state = OnboardingState()
    io = _ScriptedIO([
        # situation: name, employment_status, search_duration_months,
        # stress_level, location_city
        "Test User",
        "unemployed",
        "not a number",  # invalid → rejected
        "3",             # valid
        "2",
        "Aarhus",
    ])
    runner = Runner(state=state, read=io.read, write=io.write)
    runner._run_chapter(get_chapter("situation"))
    assert state.get_answer("situation", "search_duration_months") == 3
    assert any("must be a number" in line for line in io.output)
