"""Tests for the Claude-facing CLI commands: ingest + show."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from danapply.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolated_data_dir(tmp_path: Path):
    """Point DANAPPLY_DATA_DIR at a temp dir for each test."""
    os.environ["DANAPPLY_DATA_DIR"] = str(tmp_path / "data")
    yield
    os.environ.pop("DANAPPLY_DATA_DIR", None)


def _job_record(**overrides) -> dict:
    record = {
        "title": "Market Analyst",
        "company": "ACME A/S",
        "location": "Aarhus, Denmark",
        "language": "EN",
        "description_raw": "Analyse markets. Python required.",
        "requirements": ["Python", "Market research"],
        "source": "claude:screenshot",
    }
    record.update(overrides)
    return record


def test_ingest_single_record(tmp_path: Path) -> None:
    payload = tmp_path / "job.json"
    payload.write_text(json.dumps(_job_record()), encoding="utf-8")

    result = runner.invoke(app, ["ingest", str(payload)])
    assert result.exit_code == 0
    assert "Ingested 1 job(s) — 1 new to memory." in result.output
    assert "ACME A/S" in result.output


def test_ingest_list_of_records(tmp_path: Path) -> None:
    payload = tmp_path / "jobs.json"
    payload.write_text(
        json.dumps([_job_record(), _job_record(title="Insights Analyst", company="Beta ApS")]),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["ingest", str(payload), "--json"])
    assert result.exit_code == 0
    out = json.loads(result.output)
    assert out["ingested"] == 2
    assert out["new_to_db"] == 2
    assert all(j["job_id"] for j in out["jobs"])


def test_ingest_dedupes_on_reingest(tmp_path: Path) -> None:
    payload = tmp_path / "job.json"
    payload.write_text(json.dumps(_job_record()), encoding="utf-8")

    first = runner.invoke(app, ["ingest", str(payload), "--json"])
    second = runner.invoke(app, ["ingest", str(payload), "--json"])
    assert json.loads(first.output)["new_to_db"] == 1
    assert json.loads(second.output)["new_to_db"] == 0


def test_ingest_rejects_invalid_record(tmp_path: Path) -> None:
    payload = tmp_path / "bad.json"
    payload.write_text(json.dumps({"title": "X", "language": 42}), encoding="utf-8")

    result = runner.invoke(app, ["ingest", str(payload)])
    assert result.exit_code == 1
    assert "failed validation" in result.output


def test_ingest_rejects_malformed_json(tmp_path: Path) -> None:
    payload = tmp_path / "broken.json"
    payload.write_text("{not json", encoding="utf-8")

    result = runner.invoke(app, ["ingest", str(payload)])
    assert result.exit_code == 1
    assert "Invalid JSON" in result.output


def test_show_dumps_full_record(tmp_path: Path) -> None:
    payload = tmp_path / "job.json"
    payload.write_text(json.dumps(_job_record()), encoding="utf-8")
    ingest = runner.invoke(app, ["ingest", str(payload), "--json"])
    job_id = json.loads(ingest.output)["jobs"][0]["job_id"]

    result = runner.invoke(app, ["show", "--job-id", job_id])
    assert result.exit_code == 0
    record = json.loads(result.output)
    assert record["title"] == "Market Analyst"
    assert record["description_raw"]  # full text included for Claude to write from
    assert record["requirements"] == ["Python", "Market research"]


def test_show_errors_on_unknown_id() -> None:
    result = runner.invoke(app, ["show", "--job-id", "nope-123"])
    assert result.exit_code == 1
    assert "No job with id" in result.output
