"""Sanity tests for the Claude Code plugin files in ``skills/danapply/``.

These verify that the files exist, parse cleanly, and reference real CLI
commands. They don't verify that Claude Code itself behaves correctly —
that's an end-to-end test that requires Claude Code installed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

# Repo root for tests — work from this file's parent's parent
REPO_ROOT = Path(__file__).parent.parent
SKILL_DIR = REPO_ROOT / "skills" / "danapply"


# ---------------------------------------------------------------------------
# Skill files exist
# ---------------------------------------------------------------------------
def test_skill_dir_exists() -> None:
    assert SKILL_DIR.is_dir(), f"Missing skill dir: {SKILL_DIR}"


@pytest.mark.parametrize("filename", [
    "SKILL.md",
    "orchestration.md",
    "tone_spec.md",
    "danish_register_guide.md",
    "push_back_library.md",
    "triggers.yaml",
])
def test_core_skill_file_present(filename: str) -> None:
    p = SKILL_DIR / filename
    assert p.is_file(), f"Missing: {p}"
    assert p.stat().st_size > 100, f"Suspiciously small: {p}"


@pytest.mark.parametrize("workflow", [
    "onboarding.md",
    "cv_session.md",
    "process_new.md",
    "tailor.md",
    "voice_capture.md",
    "joblog_prompt.md",
    "interview_prep.md",
    "log_outcome.md",
    "dagpenge_check.md",
    "update_profile.md",
])
def test_workflow_spec_present(workflow: str) -> None:
    p = SKILL_DIR / "workflows" / workflow
    assert p.is_file(), f"Missing workflow spec: {p}"


# ---------------------------------------------------------------------------
# SKILL.md frontmatter
# ---------------------------------------------------------------------------
def _split_frontmatter(text: str) -> tuple[dict | None, str]:
    """Split a markdown file's YAML frontmatter from its body."""
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return None, text
    fm_text = text[4:end]
    body = text[end + 5:]
    try:
        fm = yaml.safe_load(fm_text)
    except yaml.YAMLError:
        return None, body
    return fm if isinstance(fm, dict) else None, body


def test_skill_md_has_valid_yaml_frontmatter() -> None:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    fm, _ = _split_frontmatter(text)
    assert fm is not None, "SKILL.md is missing YAML frontmatter"
    assert fm.get("name") == "danapply"
    assert isinstance(fm.get("description"), str) and fm["description"].strip()
    assert "Bash" in fm.get("allowed-tools", [])


def test_skill_description_mentions_dk_market() -> None:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    fm, _ = _split_frontmatter(text)
    assert "Denmark" in fm["description"] or "Danish" in fm["description"]


# ---------------------------------------------------------------------------
# triggers.yaml parses cleanly
# ---------------------------------------------------------------------------
def test_triggers_yaml_parses() -> None:
    text = (SKILL_DIR / "triggers.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    assert isinstance(data, dict)
    assert len(data) > 0


# ---------------------------------------------------------------------------
# orchestration.md references real CLI commands
# ---------------------------------------------------------------------------
EXPECTED_CLI_COMMANDS = (
    "danapply init",
    "danapply onboard",
    "danapply voice set",
    "danapply parse",
    "danapply ingest",
    "danapply show",
    "danapply score",
    "danapply tailor",
    "danapply joblog",
    "danapply outcome",
    "danapply dagpenge",
    "danapply interview-prep",
    "danapply list",
    "danapply db",
    "danapply version",
)


@pytest.mark.parametrize("cmd", EXPECTED_CLI_COMMANDS)
def test_orchestration_references_real_command(cmd: str) -> None:
    text = (SKILL_DIR / "orchestration.md").read_text(encoding="utf-8")
    assert cmd in text, f"orchestration.md missing reference to: {cmd}"


@pytest.mark.parametrize("cmd", EXPECTED_CLI_COMMANDS)
def test_skill_md_references_real_command(cmd: str) -> None:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert cmd in text, f"SKILL.md missing reference to: {cmd}"


# ---------------------------------------------------------------------------
# Operating rules section is present
# ---------------------------------------------------------------------------
def test_skill_md_lists_six_non_negotiable_rules() -> None:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert "Never fabricate" in text
    assert "Never auto-submit" in text
    assert "Never fetch the web" in text
    assert "Respect the user's voice" in text
    assert "Push back as a question" in text
    assert "Degrade gracefully" in text


def test_no_phantom_cli_commands_in_skill_docs() -> None:
    """Skill docs must not reference commands/flags the engine doesn't have."""
    phantom = (
        "--confirm-logged",
        "dagpenge-check",
        "dagpenge-set",
        "danapply watchlist",
        "danapply enrich",
        "--dedupe",
        "danapply discover",
        "--update-mode",
        "--calibrate-cv",
        "--extract-voice",
        "--tagline-stats",
        "python -m danapply",
    )
    files = [SKILL_DIR / "SKILL.md", SKILL_DIR / "orchestration.md"]
    files += sorted((SKILL_DIR / "workflows").glob("*.md"))
    for f in files:
        text = f.read_text(encoding="utf-8")
        for needle in phantom:
            assert needle not in text, f"{f.name} references phantom CLI: {needle}"
