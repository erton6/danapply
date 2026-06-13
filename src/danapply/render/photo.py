"""Profile-photo preparation.

The CV template circle-crops the photo top-right, so the ideal input is a
square, face-centred headshot. ``prepare_profile_photo`` normalises
whatever the user supplies: centre-crops to a square, resizes to a
render-optimal edge length, and saves a clean JPEG at the profile path.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image as PILImage
from PIL import UnidentifiedImageError

# 800 px across a ~2.8 cm circle ≈ 700+ dpi — comfortably print-sharp.
TARGET_PX = 800

# Below this source edge the circle looks visibly soft in print.
MIN_SIDE_SHARP = 300


class PhotoError(Exception):
    """Raised when the source file can't be used as a profile photo."""


@dataclass
class PhotoReport:
    source: Path
    dest: Path
    original_size: tuple[int, int]
    final_px: int
    upscaled_avoided: bool
    """True when the source was smaller than TARGET_PX and we kept its
    native resolution instead of upscaling."""

    @property
    def too_small_for_print(self) -> bool:
        return self.final_px < MIN_SIDE_SHARP


def prepare_profile_photo(
    source: Path, dest: Path, target_px: int = TARGET_PX
) -> PhotoReport:
    """Centre-crop ``source`` to a square, resize, save as JPEG at ``dest``.

    Never upscales — a small source stays at its native edge length (and
    the report flags it so the caller can warn). Raises ``PhotoError``
    with a readable message for missing/unreadable files.
    """
    source = source.expanduser().resolve()
    if not source.exists():
        raise PhotoError(f"No such file: {source}")

    try:
        im = PILImage.open(source)
        im.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise PhotoError(
            f"Can't read {source.name} as an image ({exc}). "
            f"JPEG or PNG works best."
        ) from exc

    im = im.convert("RGB")
    w, h = im.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    square = im.crop((left, top, left + side, top + side))

    final_px = min(target_px, side)
    if final_px != side:
        square = square.resize((final_px, final_px), PILImage.LANCZOS)

    dest.parent.mkdir(parents=True, exist_ok=True)
    square.save(dest, format="JPEG", quality=90)

    return PhotoReport(
        source=source,
        dest=dest,
        original_size=(w, h),
        final_px=final_px,
        upscaled_avoided=side < target_px,
    )
