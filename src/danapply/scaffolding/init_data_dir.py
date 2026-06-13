"""Create the user's ``~/danapply-data/`` directory and seed it.

By default the profile files are seeded from a **blank template** so a new
user starts from an empty profile that onboarding fills in. Pass
``example=True`` (``danapply init --example``) to seed the fictional
"Sofia Almeida" demo persona instead — useful for trying the renderer.

Idempotent: running ``danapply init`` again is safe. Existing files are
never overwritten — only missing files are created.
"""

from __future__ import annotations

import shutil
from importlib.resources import files
from pathlib import Path

from danapply import paths

# Profile files seeded on init, mapped to their destination paths. The same
# filenames exist under both the ``blank`` and ``example`` scaffold dirs.
SEED_FILES = [
    ("profile.yaml", paths.profile_yaml_path),
    ("targets.yaml", paths.targets_yaml_path),
    ("cv_content.md", paths.cv_content_path),
    ("voice_profile.md", paths.voice_profile_path),
]

# The demo persona ships a placeholder photo; a blank profile deliberately
# starts WITHOUT one — the CV session asks the user for a real headshot
# (`danapply photo set`), and seeding a placeholder would silence that ask.
EXAMPLE_ONLY_SEED_FILES = [
    ("photo.jpeg", lambda: paths.profile_dir() / "photo.jpeg"),
]


def init_data_dir(force: bool = False, example: bool = False) -> dict[str, str]:
    """Scaffold the data directory.

    ``example=False`` (default) seeds a blank profile template; ``example=True``
    seeds the fictional demo persona.

    Returns a dict mapping each created file/dir to its status:
    ``"created"`` if newly created, ``"exists"`` if it was already there,
    ``"overwritten"`` if ``force=True`` replaced an existing file.
    """
    report: dict[str, str] = {}

    # Directories first
    for d in paths.all_data_subdirs():
        if d.exists():
            report[str(d)] = "exists"
        else:
            d.mkdir(parents=True, exist_ok=True)
            report[str(d)] = "created"

    # Profile files — blank template by default, demo persona if example=True
    seed_subdir = "example" if example else "blank"
    seed_root = files("danapply.scaffolding").joinpath(seed_subdir)
    seed_files = SEED_FILES + (EXAMPLE_ONLY_SEED_FILES if example else [])
    for filename, target_fn in seed_files:
        target: Path = target_fn()
        source = seed_root.joinpath(filename)

        existed_before = target.exists()
        if existed_before and not force:
            report[str(target)] = "exists"
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as src_fh, target.open("wb") as dst_fh:
            shutil.copyfileobj(src_fh, dst_fh)
        report[str(target)] = "overwritten" if existed_before else "created"

    return report
