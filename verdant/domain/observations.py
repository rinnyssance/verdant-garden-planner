"""Field-journal observations. User estimates and instrument readings stay labelled."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .common import choice, new_id, optional_number, optional_text, utcnow

DATA_ORIGINS = ("user_observed", "instrument_measured")
MOISTURE = ("dry", "slightly_dry", "moist", "wet", "waterlogged")


@dataclass
class Observation:
    garden_id: str
    planting_id: str
    observed_at: datetime = field(default_factory=utcnow)
    height_cm: float | None = None
    leaf_count: int | None = None
    moisture_assessment: str | None = None
    light_notes: str | None = None
    symptoms: str | None = None
    notes: str = ""
    photo_path: str | None = None
    data_origin: str = "user_observed"
    id: str = field(default_factory=new_id)

    def __post_init__(self):
        if type(self.observed_at) is not datetime:
            raise ValueError("Observation time must be a date and time.")
        self.height_cm = optional_number(self.height_cm, "Height (cm)", maximum=2000)
        self.leaf_count = optional_number(self.leaf_count, "Leaf count", maximum=100000, integer=True)
        if self.moisture_assessment is not None:
            choice(self.moisture_assessment, MOISTURE, "Moisture assessment")
        choice(self.data_origin, DATA_ORIGINS, "Data origin")
        self.light_notes = optional_text(self.light_notes)
        self.symptoms = optional_text(self.symptoms)
        self.photo_path = optional_text(self.photo_path)
        self.notes = (self.notes or "").strip()
        if not any(v not in (None, "") for v in (self.height_cm, self.leaf_count, self.moisture_assessment,
                                                 self.light_notes, self.symptoms, self.notes, self.photo_path)):
            raise ValueError("An observation needs at least one measurement, note or photo.")
