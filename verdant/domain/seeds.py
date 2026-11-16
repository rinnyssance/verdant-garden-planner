"""Seed varieties (what a packet is) and inventory (what a garden owns).

Owning seeds never means they are growing: plantings are separate records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .common import choice, new_id, optional_number, optional_text, text

CATEGORIES = ("vegetable", "herb", "flower", "microgreen", "fruit", "other")
VERIFICATION_STATUSES = ("verified", "transcribed", "needs_review", "user_entered")
SUNLIGHT = ("full_sun", "partial_sun", "partial_shade", "full_shade", "unknown")


@dataclass
class SeedVariety:
    common_name: str
    category: str = "other"
    cultivar: str | None = None
    scientific_name: str | None = None
    crop_key: str | None = None
    brand: str | None = None
    packet_label: str | None = None
    source_url: str | None = None
    requirements_source: str | None = None
    germination_days_min: int | None = None
    germination_days_max: int | None = None
    maturity_days_min: int | None = None
    maturity_days_max: int | None = None
    sunlight_requirement: str = "unknown"
    preferred_temperature_range: str | None = None
    planting_notes: str = ""
    image_path: str | None = None
    verification_status: str = "user_entered"
    id: str = field(default_factory=new_id)

    def __post_init__(self):
        self.common_name = text(self.common_name, "Common name")
        choice(self.category, CATEGORIES, "Category")
        choice(self.sunlight_requirement, SUNLIGHT, "Sunlight requirement")
        choice(self.verification_status, VERIFICATION_STATUSES, "Verification status")
        for name in ("cultivar", "scientific_name", "crop_key", "brand", "packet_label",
                     "source_url", "requirements_source", "preferred_temperature_range", "image_path"):
            setattr(self, name, optional_text(getattr(self, name)))
        for low, high, label in (("germination_days_min", "germination_days_max", "Germination days"),
                                 ("maturity_days_min", "maturity_days_max", "Days to maturity")):
            lo = optional_number(getattr(self, low), label, maximum=730, integer=True)
            hi = optional_number(getattr(self, high), label, maximum=730, integer=True)
            if lo is not None and hi is not None and lo > hi:
                raise ValueError(f"{label}: minimum cannot exceed maximum.")
            setattr(self, low, lo)
            setattr(self, high, hi)
        has_facts = any(v is not None for v in (self.germination_days_min, self.germination_days_max,
                                                 self.maturity_days_min, self.maturity_days_max,
                                                 self.preferred_temperature_range))
        if has_facts and not self.requirements_source:
            raise ValueError("Record where growing requirements came from (e.g. 'seed packet').")
        self.planting_notes = (self.planting_notes or "").strip()

    @property
    def label(self) -> str:
        return f"{self.common_name} '{self.cultivar}'" if self.cultivar else self.common_name


@dataclass
class SeedInventoryItem:
    garden_id: str
    seed_variety_id: str
    packet_count: int | None = None
    approximate_seed_count: int | None = None
    acquired_on: date | None = None
    expiry_on: date | None = None
    notes: str = ""
    packet_photo_path: str | None = None
    import_key: str | None = None
    id: str = field(default_factory=new_id)

    def __post_init__(self):
        self.packet_count = optional_number(self.packet_count, "Packet count", integer=True)
        self.approximate_seed_count = optional_number(self.approximate_seed_count, "Seed count", integer=True)
        for name in ("acquired_on", "expiry_on"):
            value = getattr(self, name)
            if value is not None and type(value) is not date:
                raise ValueError("Dates must be calendar dates.")
        if self.acquired_on and self.expiry_on and self.expiry_on < self.acquired_on:
            raise ValueError("Expiry cannot be before the acquisition date.")
        self.notes = (self.notes or "").strip()
        self.packet_photo_path = optional_text(self.packet_photo_path)
        self.import_key = optional_text(self.import_key)

    def is_expired(self, today: date) -> bool:
        return self.expiry_on is not None and self.expiry_on < today
