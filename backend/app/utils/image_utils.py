"""Image helper utilities.

Future versions may add dimension checks, EXIF stripping, and thumbnail generation.
"""

from __future__ import annotations

from pathlib import Path


def is_image_path(path: Path) -> bool:
    """Return True when the path looks like a supported image file."""
    return path.suffix.lower().lstrip(".") in {"jpg", "jpeg", "png", "webp"}


def build_upload_url(filename: str) -> str:
    """Build the public URL path for an uploaded file."""
    return f"/uploads/{filename}"


# TODO: Add async image dimension inspection (Pillow / pure-Python).
# TODO: Add EXIF stripping before storing production uploads.
# TODO: Add thumbnail generation for library previews.
