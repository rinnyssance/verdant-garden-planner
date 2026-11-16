"""Import the candidate seed inventory and load crop reference data."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

from verdant.domain import SeedInventoryItem, SeedVariety

SEED_DATA = Path(__file__).resolve().parents[1] / "seed_data"
log = logging.getLogger("verdant.inventory")


def load_initial_inventory(path: Path | None = None) -> dict:
    return json.loads((path or SEED_DATA / "initial_seed_inventory.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_crop_reference() -> dict:
    return json.loads((SEED_DATA / "crop_reference.json").read_text(encoding="utf-8"))


def import_initial_inventory(service, user_id: str, garden_id: str, path: Path | None = None) -> dict:
    """Add the candidate packets to one garden's seed library.

    Idempotent: entries already imported into this garden (same import key)
    are skipped. Creates no plantings and no tasks.
    """
    data = load_initial_inventory(path)
    existing = {item.import_key for item, _ in service.inventory(user_id, garden_id) if item.import_key}
    keys = [entry["key"] for entry in data["entries"]]
    if len(keys) != len(set(keys)):
        raise ValueError("Seed inventory file contains duplicate keys.")
    added, skipped = 0, 0
    with service.repo.transaction():
        for entry in data["entries"]:
            if entry["key"] in existing:
                skipped += 1
                continue
            variety = SeedVariety(
                common_name=entry["common_name"], category=entry["category"], cultivar=entry.get("cultivar"),
                crop_key=entry.get("crop_key"), packet_label=entry.get("packet_label"),
                verification_status=entry["verification_status"], planting_notes=entry.get("note", ""),
                requirements_source=None)
            service.add_seed(user_id, garden_id, variety, import_key=entry["key"],
                             notes=f"Imported from: {data['source']}")
            added += 1
    log.info("seed import garden=%s added=%d skipped=%d", garden_id, added, skipped)
    return {"added": added, "skipped": skipped}
