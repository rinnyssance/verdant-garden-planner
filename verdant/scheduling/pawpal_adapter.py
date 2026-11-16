"""Run garden tasks through the original, unmodified PawPal+ scheduler.

Mapping:
    one Garden           -> one PawPal Owner (whose time is shared)
    planting / space /
    general garden care  -> one PawPal Pet-shaped task group
    GardenTask           -> PawPal Task with the same id

Only tasks of a single garden are ever loaded into one Owner, so overlap
warnings and plans are scoped to that garden.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime
from typing import Callable, Iterable

from pawpal_system import Owner, Pet, Scheduler, Task

from verdant.domain.common import utcnow

GENERAL = "general"


def to_pawpal_task(garden_task) -> Task:
    """Build (and therefore validate) the PawPal task for a garden task."""
    return Task(description=garden_task.description, time=garden_task.start_time,
                due_date=garden_task.due_date, duration_minutes=garden_task.duration_minutes,
                priority=garden_task.priority, frequency=garden_task.recurrence,
                completed=garden_task.completed, id=garden_task.id)


def group_key(garden_task) -> str:
    return garden_task.planting_id or garden_task.growing_space_id or GENERAL


@dataclass
class GardenPlan:
    selected: list = field(default_factory=list)
    skipped: list = field(default_factory=list)   # (GardenTask, reason)

    @property
    def total_minutes(self) -> int:
        return sum(task.duration_minutes for task in self.selected)


class GardenSchedule:
    """PawPal scheduling for exactly one garden."""

    def __init__(self, garden, tasks: Iterable, label_for: Callable[[str], str] | None = None):
        self.garden = garden
        self.owner = Owner(garden.display_name)
        self._garden_tasks: dict[str, object] = {}
        self._groups: dict[str, Pet] = {}
        for garden_task in tasks:
            if garden_task.garden_id != garden.id:
                raise ValueError("A garden schedule cannot include another garden's tasks.")
            key = group_key(garden_task)
            if key not in self._groups:
                name = (label_for(key) if label_for else None) or (
                    "General garden care" if key == GENERAL else "Garden care")
                pet = Pet(name, "garden care")
                pet.id = key
                self._groups[key] = pet
                self.owner.add_pet(pet)
            self._groups[key].add_task(to_pawpal_task(garden_task))
            self._garden_tasks[garden_task.id] = garden_task
        self.scheduler = Scheduler(self.owner)

    def _wrap(self, pairs) -> list:
        return [self._garden_tasks[task.id] for _, task in pairs]

    def tasks(self, *, on_date: date | None = None, completed: bool | None = None) -> list:
        """Chronological garden tasks using PawPal filtering and sorting."""
        return self._wrap(self.scheduler.sort_by_time(
            self.scheduler.filter_tasks(completed=completed, on_date=on_date)))

    def overdue(self, today: date) -> list:
        return [t for t in self.tasks(completed=False) if t.due_date < today]

    def conflicts(self, on_date: date | None = None) -> list[str]:
        return self.scheduler.detect_conflicts(on_date)

    def plan(self, on_date: date, available_minutes: int, start_time: str = "00:00",
             end_time: str = "24:00") -> GardenPlan:
        plan = self.scheduler.build_plan(on_date, available_minutes, start_time, end_time)
        return GardenPlan(selected=self._wrap(plan.selected),
                          skipped=[(self._garden_tasks[task.id], reason)
                                   for _, task, reason in plan.skipped])

    def complete(self, task_id: str, completed_on: date | None = None,
                 completed_at: datetime | None = None):
        """Complete via PawPal; return (completed task, next occurrence or None).

        Calling it again for an already completed task returns (task, None) and
        creates nothing, matching PawPal's idempotent completion.
        """
        garden_task = self._find(task_id)
        if garden_task.completed:
            return garden_task, None
        next_task = self.scheduler.mark_task_complete(group_key(garden_task), task_id, completed_on)
        done = replace(garden_task, completed=True, completed_at=completed_at or utcnow())
        self._garden_tasks[task_id] = done
        following = None
        if next_task is not None:
            following = replace(garden_task, id=next_task.id, due_date=next_task.due_date,
                                completed=False, completed_at=None, idempotency_key=None)
            self._garden_tasks[following.id] = following
        return done, following

    def update(self, task_id: str, **changes):
        """Edit a pending task with PawPal's atomic validation; history stays read-only."""
        mapping = {"start_time": "time", "recurrence": "frequency"}
        garden_task = self._find(task_id)
        pawpal_changes = {mapping.get(k, k): v for k, v in changes.items()}
        updated = self.scheduler.update_task(group_key(garden_task), task_id, **pawpal_changes)
        result = replace(garden_task, description=updated.description, start_time=updated.time,
                         due_date=updated.due_date, duration_minutes=updated.duration_minutes,
                         priority=updated.priority, recurrence=updated.frequency)
        self._garden_tasks[task_id] = result
        return result

    def _find(self, task_id: str):
        if task_id not in self._garden_tasks:
            raise ValueError("Task not found in this garden.")
        return self._garden_tasks[task_id]
