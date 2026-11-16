"""Private, per-garden photo storage on local disk (Supabase Storage in Phase 3)."""

from __future__ import annotations

import os
from pathlib import Path

from verdant.domain.common import new_id

MAX_BYTES = 5 * 1024 * 1024
SIGNATURES = {
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpg": (b"\xff\xd8\xff",),
    "webp": (b"RIFF",),
}


def photo_root() -> Path:
    return Path(os.getenv("VERDANT_PHOTO_DIR", "data/photos"))


def detect_type(data: bytes) -> str | None:
    for kind, signatures in SIGNATURES.items():
        if any(data.startswith(sig) for sig in signatures):
            if kind == "webp" and data[8:12] != b"WEBP":
                continue
            return kind
    return None


def save_photo(garden_id: str, data: bytes, root: Path | None = None) -> str:
    """Validate by content (not file name) and size, then store under the garden's folder."""
    if not data:
        raise ValueError("The photo is empty.")
    if len(data) > MAX_BYTES:
        raise ValueError("Photos must be 5 MB or smaller.")
    kind = detect_type(data)
    if kind is None:
        raise ValueError("Photos must be PNG, JPEG or WebP images.")
    folder = (root or photo_root()) / garden_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{new_id()}.{kind}"
    path.write_bytes(data)
    return str(path)


def photo_belongs_to(path: str | None, garden_id: str, root: Path | None = None) -> bool:
    """Only show a stored photo inside the garden that owns it."""
    if not path:
        return False
    try:
        resolved = Path(path).resolve()
        return resolved.parent == ((root or photo_root()) / garden_id).resolve() and resolved.exists()
    except OSError:
        return False
