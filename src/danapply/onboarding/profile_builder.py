"""Translate onboarding answers into ``profile.yaml`` + ``targets.yaml`` (+
optional ``dagpenge.yaml``).

The translation is intentionally narrow: only fields the interview directly
captures. Other fields keep their defaults from the example profile that
``danapply init`` already wrote.

When an existing ``profile.yaml`` is present, the builder merges — it never
overwrites a hand-edited field with an empty interview answer.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from danapply import paths
from danapply.onboarding.state import OnboardingState


def build_profile_files(state: OnboardingState) -> dict[str, Path]:
    """Translate state → yaml files.

    Returns a dict mapping each output kind (``profile``, ``targets``,
    ``dagpenge``) to the file path written.
    """
    written: dict[str, Path] = {}

    profile_path = paths.profile_yaml_path()
    targets_path = paths.targets_yaml_path()
    dagpenge_path = paths.profile_dir() / "dagpenge.yaml"

    profile_path.parent.mkdir(parents=True, exist_ok=True)

    # ---- profile.yaml ----
    existing_profile = _load_yaml(profile_path)
    profile_updates = _build_profile_updates(state)
    new_profile = _deep_merge(existing_profile, profile_updates)
    profile_path.write_text(
        yaml.safe_dump(new_profile, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    written["profile"] = profile_path

    # ---- targets.yaml ----
    existing_targets = _load_yaml(targets_path)
    target_updates = _build_target_updates(state)
    new_targets = _deep_merge(existing_targets, target_updates)
    targets_path.write_text(
        yaml.safe_dump(new_targets, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    written["targets"] = targets_path

    # ---- dagpenge.yaml (only if on dagpenge) ----
    dk = state.answers.get("dk_admin", {})
    if dk.get("on_dagpenge"):
        dagpenge_data = {
            "on_dagpenge": True,
            "a_kasse": dk.get("a_kasse") or "",
            "my_plan_field": dk.get("my_plan_field") or "",
            "weekly_threshold": int(dk.get("weekly_threshold") or 2),
            "joblog_auto_generate": True,
        }
        dagpenge_path.write_text(
            yaml.safe_dump(dagpenge_data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        written["dagpenge"] = dagpenge_path

    return written


def render_reality_check_summary(state: OnboardingState) -> str:
    """Multi-line summary printed to the user at the reality-check step.

    Pulls answers from every prior chapter and lays them out so the user
    can confirm what was heard.
    """
    a = state.answers
    situation = a.get("situation", {})
    story = a.get("story", {})
    targets = a.get("targets", {})
    constraints = a.get("constraints", {})
    self_assess = a.get("self_assessment", {})

    lines = [
        "",
        "─────── Reality check ───────",
        "",
        f"  Name:           {situation.get('name', '?')}",
        f"  Location:       {situation.get('location_city', '?')}",
        f"  Status:         {situation.get('employment_status', '?')} "
        f"({situation.get('search_duration_months', 0)} mo searching)",
        f"  Stress level:   {situation.get('stress_level', '?')}/5",
        "",
        "  Targets:",
        f"    Tier A:       {targets.get('tier_a_titles', '?')}",
    ]
    if targets.get("tier_b_titles"):
        lines.append(f"    Tier B:       {targets.get('tier_b_titles')}")
    lines.extend([
        f"    Geography:    {targets.get('geography_primary', '?')}",
        f"    Arrangement:  {targets.get('arrangement', '?')} "
        f"(remote ok: {targets.get('remote_ok', '?')})",
    ])
    salary = targets.get("salary_floor_dkk", 0)
    if salary:
        lines.append(f"    Salary floor: DKK {salary:,}/month")

    lines.extend([
        "",
        "  Constraints:",
        f"    Visa:         {constraints.get('visa_status', '?')}",
        f"    Danish:       {constraints.get('danish_level', '?')}",
        f"    English:      {constraints.get('english_level', '?')}",
    ])
    excluded = constraints.get("excluded_industries", "")
    if excluded:
        lines.append(f"    Excluded:     {excluded}")

    if story.get("career_summary"):
        lines.extend([
            "",
            "  Story:",
            "    " + story.get("career_summary").replace("\n", "\n    "),
        ])
    if self_assess.get("real_strengths"):
        lines.append("")
        lines.append(f"  Real strengths: {self_assess.get('real_strengths')}")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _build_profile_updates(state: OnboardingState) -> dict[str, Any]:
    """Map state answers to profile.yaml shape (partial — only fields touched)."""
    situation = state.answers.get("situation", {})
    constraints = state.answers.get("constraints", {})

    updates: dict[str, Any] = {}

    name = situation.get("name")
    if name and isinstance(name, str):
        updates["name"] = name.upper().strip()

    contact_updates: dict[str, Any] = {}
    loc = situation.get("location_city")
    if loc and isinstance(loc, str):
        contact_updates["location"] = f"{loc.strip()}, Denmark"
    if contact_updates:
        updates["contact"] = contact_updates

    # Languages
    danish_level = constraints.get("danish_level")
    english_level = constraints.get("english_level")
    langs: list[dict[str, str]] = []
    if english_level:
        langs.append({"name": "English", "level": _english_label(english_level)})
    if danish_level and danish_level != "none":
        langs.append({"name": "Danish", "level": _danish_label(danish_level)})
    if langs:
        updates["languages"] = langs

    return updates


def _english_label(level: str) -> str:
    return {
        "intermediate": "Intermediate",
        "advanced": "Advanced",
        "fluent": "Fluent",
        "native": "Native",
    }.get(level, level)


def _danish_label(level: str) -> str:
    if level == "native":
        return "Native (mother tongue)"
    if level in ("A1", "A2"):
        return f"Beginner ({level})"
    if level in ("B1", "B2"):
        return f"Intermediate ({level})"
    if level in ("C1", "C2"):
        return f"Advanced ({level})"
    return level


def _build_target_updates(state: OnboardingState) -> dict[str, Any]:
    targets = state.answers.get("targets", {})
    constraints = state.answers.get("constraints", {})

    updates: dict[str, Any] = {}

    roles: dict[str, list[str]] = {}
    tier_a_raw = targets.get("tier_a_titles") or ""
    if isinstance(tier_a_raw, str) and tier_a_raw.strip():
        roles["tier_a_titles"] = _csv_to_list(tier_a_raw)
    tier_b_raw = targets.get("tier_b_titles") or ""
    if isinstance(tier_b_raw, str) and tier_b_raw.strip():
        roles["tier_b_titles"] = _csv_to_list(tier_b_raw)
    if roles:
        updates["roles"] = roles

    geo_raw = targets.get("geography_primary") or ""
    if isinstance(geo_raw, str) and geo_raw.strip():
        updates["geography"] = {
            "primary": _csv_to_list(geo_raw),
            "remote_ok": bool(targets.get("remote_ok", True)),
        }

    if targets.get("arrangement"):
        updates["arrangement"] = targets["arrangement"]

    salary = targets.get("salary_floor_dkk")
    if salary:
        try:
            salary_int = int(salary)
            if salary_int > 0:
                updates["salary_floor_monthly_dkk"] = salary_int
        except (ValueError, TypeError):
            pass

    excluded_raw = constraints.get("excluded_industries") or ""
    commute = constraints.get("max_commute_minutes")
    constraints_block: dict[str, Any] = {}
    if isinstance(excluded_raw, str) and excluded_raw.strip():
        constraints_block["excluded_industries"] = _csv_to_list(excluded_raw)
    if commute:
        try:
            c_int = int(commute)
            if c_int > 0:
                constraints_block["max_commute_minutes_one_way"] = c_int
        except (ValueError, TypeError):
            pass
    if constraints_block:
        updates["constraints"] = constraints_block

    return updates


def _csv_to_list(raw: str) -> list[str]:
    return [s.strip() for s in raw.split(",") if s.strip()]


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _deep_merge(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    """Merge ``updates`` into ``base``. updates win on scalars, nested dicts
    recurse, lists are fully replaced (not appended)."""
    merged = dict(base)
    for key, val in updates.items():
        if isinstance(val, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], val)
        else:
            merged[key] = val
    return merged
