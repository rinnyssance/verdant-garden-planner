"""Garden care tasks. Scheduling rules are delegated to PawPal's Task via the adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from .common import choice, new_id, optional_text

TASK_SOURCES = ("manual", "suggested")


@dataclass
class GardenTask:
    garden_id: str
    description: str
    due_date: date
    start_time: str = "08:00"
    duration_minutes: int = 15
    priority: str = "medium"
    recurrence: str = "once"
    completed: bool = False
    completed_at: datetime | None = None
    planting_id: str | None = None
    growing_space_id: str | None = None
    recommendation_id: str | None = None
    source: str = "manual"
    idempotency_key: str | None = None
    id: str = field(default_factory=new_id)

    def __post_init__(self):
        choice(self.source, TASK_SOURCES, "Task source")
        self.idempotency_key = optional_text(self.idempotency_key)
        if self.completed_at is not None and not self.completed:
            raise ValueError("Only completed tasks have a completion time.")
        # Re-use PawPal's validation so the original rules stay the single source of truth.
        from verdant.scheduling.pawpal_adapter import to_pawpal_task
        validated = to_pawpal_task(self)
        self.description = validated.description
