"""Tests for the utility CLI commands: photo set, status, delete."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image as PILImage
from typer.testing import CliRunner

from danapply.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolated_data_dir(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DANAPPLY_DATA_DIR", str(tmp_path / "data"))
    yield tmp_path / "data"


def _make_image(path: Path, width: int, height: int) -> Path:
    PILImage.new("RGB", (width, height), color=(120, 90, 60)).save(path)
    return path


# ---------------------------------------------------------------------------
# photo set
# ---------------------------------------------------------------------------
def test_photo_set_crops_and_installs(tmp_path: Path) -> None:
    source = _make_image(tmp_path / "headshot.png", 1000, 600)
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["photo", "set", str(source)])
    assert result.exit_code == 0, result.output

    dest = tmp_path / "data" / "profile" / "photo.jpeg"
    assert dest.exists()
    im = PILImage.open(dest)
    assert im.size == (600, 600)  # square, native resolution (no upscale)

    profile_text = (tmp_path / "data" / "profile" / "profile.yaml").read_text()
    assert 'photo_path: "photo.jpeg"' in profile_text


def test_photo_set_resizes_large_sources(tmp_path: Path) -> None:
    source = _make_image(tmp_path / "big.jpg", 2400, 2400)
    result = runner.invoke(app, ["photo", "set", str(source)])
    assert result.exit_code == 0, result.output
    im = PILImage.open(tmp_path / "data" / "profile" / "photo.jpeg")
    assert im.size == (800, 800)


def test_photo_set_warns_on_tiny_source(tmp_path: Path) -> None:
    source = _make_image(tmp_path / "tiny.png", 200, 200)
    result = runner.invoke(app, ["photo", "set", str(source)])
    assert result.exit_code == 0
    assert "soft in print" in result.output


def test_photo_set_rejects_non_image(tmp_path: Path) -> None:
    bogus = tmp_path / "not_a_photo.txt"
    bogus.write_text("hello")
    result = runner.invoke(app, ["photo", "set", str(bogus)])
    assert result.exit_code == 1
    assert "Can't read" in result.output


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------
def test_status_without_profile_points_to_onboarding() -> None:
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "none — run onboarding" in result.output


def test_status_shows_profile_and_pipeline(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "--example"])
    from danapply import memory
    from danapply.models import Job

    memory.init_db()
    memory.upsert_job(Job(title="Analyst", company="Acme", description_raw="d"))

    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.output
    assert "SOFIA ALMEIDA" in result.output
    assert "Pipeline: 1 job(s)" in result.output
    assert "parsed" in result.output


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------
def test_delete_requires_force(tmp_path: Path) -> None:
    runner.invoke(app, ["init"])
    data_dir = tmp_path / "data"
    result = runner.invoke(app, ["delete"])
    assert result.exit_code == 1
    assert "no undo" in result.output
    assert data_dir.exists()


def test_delete_force_removes_everything(tmp_path: Path) -> None:
    runner.invoke(app, ["init"])
    data_dir = tmp_path / "data"
    assert data_dir.exists()
    result = runner.invoke(app, ["delete", "--force"])
    assert result.exit_code == 0, result.output
    assert not data_dir.exists()


def test_delete_when_nothing_exists() -> None:
    result = runner.invoke(app, ["delete"])
    assert result.exit_code == 0
    assert "Nothing to delete" in result.output


# ---------------------------------------------------------------------------
# init photo seeding policy
# ---------------------------------------------------------------------------
def test_blank_init_does_not_seed_photo(tmp_path: Path) -> None:
    """A blank profile must start photo-less so the CV session's explicit
    photo ask actually fires."""
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert not (tmp_path / "data" / "profile" / "photo.jpeg").exists()


def test_example_init_seeds_placeholder_photo(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", "--example"])
    assert result.exit_code == 0
    assert (tmp_path / "data" / "profile" / "photo.jpeg").exists()
