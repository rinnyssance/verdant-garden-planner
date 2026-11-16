"""Plantings: seeds that were actually sown or planted in a growing space."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .common import choice, new_id, optional_text

GROWTH_STAGES = ("planned", "sown", "germinating", "seedling", "vegetative",
                 "flowering", "fruiting", "harvesting", "finished")
PLANTING_STATUSES = ("active", "archived")
# Stages where a living plant (or seed in soil) can be affected by weather.
LIVE_STAGES = GROWTH_STAGES[1:-1]


@dataclass
class Planting:
    garden_id: str
    growing_space_id: str
    seed_variety_id: str
    quantity: int = 1
    nickname: str | None = None
    sown_on: date | None = None
    germinated_on: date | None = None
    transplanted_on: date | None = None
    growth_stage: str = "planned"
    status: str = "active"
    notes: str = ""
    id: str = field(default_factory=new_id)

    def __post_init__(self):
        if isinstance(self.quantity, bool) or not isinstance(self.quantity, int) or self.quantity < 1:
            raise ValueError("Quantity must be a whole number of at least 1.")
        choice(self.growth_stage, GROWTH_STAGES, "Growth stage")
        choice(self.status, PLANTING_STATUSES, "Status")
        self.nickname = optional_text(self.nickname)
        for name in ("sown_on", "germinated_on", "transplanted_on"):
            value = getattr(self, name)
            if value is not None and type(value) is not date:
                raise ValueError("Dates must be calendar dates.")
        if self.sown_on and self.germinated_on and self.germinated_on < self.sown_on:
            raise ValueError("Germination cannot be recorded before sowing.")
        if self.sown_on and self.transplanted_on and self.transplanted_on < self.sown_on:
            raise ValueError("Transplanting cannot be recorded before sowing.")
        if self.growth_stage != "planned" and self.sown_on is None and self.transplanted_on is None:
            raise ValueError("Record a sowing or transplant date once a planting is past 'planned'.")
        self.notes = (self.notes or "").strip()

    @property
    def is_live(self) -> bool:
        return self.status == "active" and self.growth_stage in LIVE_STAGES
