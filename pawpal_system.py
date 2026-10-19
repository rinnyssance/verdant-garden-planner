"""UI-independent pet care models and deterministic scheduling algorithms."""

from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from uuid import uuid4
import re

PRIORITIES = {"high": 0, "medium": 1, "low": 2}
FREQUENCIES = ("once", "daily", "weekly")


def minutes(value: str) -> int:
    """Validate a 24-hour HH:MM string and return minutes since midnight."""
    if not isinstance(value, str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
        raise ValueError("Time must use 24-hour HH:MM format, such as 08:30.")
    hour, minute = map(int, value.split(":"))
    return hour * 60 + minute


def nonblank(value: str, label: str) -> str:
    """Return trimmed text or reject a missing name or description."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} cannot be blank.")
    return value.strip()


@dataclass
class Task:
    """One dated occurrence; completion preserves its history."""

    description: str
    time: str
    due_date: date = field(default_factory=date.today)
    duration_minutes: int = 20
    priority: str = "medium"
    frequency: str = "once"
    completed: bool = False
    id: str = field(default_factory=lambda: uuid4().hex)

    def __post_init__(self):
        """Reject malformed tasks before they reach the scheduler."""
        self.description = nonblank(self.description, "Task description")
        start = minutes(self.time)
        if type(self.due_date) is not date:
            raise ValueError("Due date must be a date.")
        if type(self.duration_minutes) is not int or not 1 <= self.duration_minutes <= 1440:
            raise ValueError("Duration must be a whole number from 1 to 1440 minutes.")
        if start + self.duration_minutes > 1440:
            raise ValueError("Tasks must finish by midnight; split overnight tasks into two.")
        if self.priority not in PRIORITIES:
            raise ValueError("Priority must be high, medium, or low.")
        if self.frequency not in FREQUENCIES:
            raise ValueError("Frequency must be once, daily, or weekly.")

    @property
    def end_time(self) -> str:
        """Return the end of this occurrence, allowing 24:00 for midnight."""
        end = minutes(self.time) + self.duration_minutes
        return f"{end // 60:02d}:{end % 60:02d}"

    def mark_complete(self, completed_on: date | None = None) -> "Task | None":
        """Complete once and return a fresh next occurrence for recurring tasks."""
        if self.completed:
            return None
        next_task = None
        if self.frequency != "once":
            base = max(self.due_date, completed_on or date.today())
            next_date = base + timedelta(days=1 if self.frequency == "daily" else 7)
            next_task = replace(self, due_date=next_date, completed=False, id=uuid4().hex)
        self.completed = True
        return next_task


@dataclass
class Pet:
    """A pet and its independent collection of task occurrences."""

    name: str
    species: str
    tasks: list[Task] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid4().hex)

    def __post_init__(self):
        """Validate identifying details."""
        self.name = nonblank(self.name, "Pet name")
        self.species = nonblank(self.species, "Species")

    def add_task(self, task: Task) -> None:
        """Attach a task once, rejecting duplicate occurrence IDs."""
        if any(existing.id == task.id for existing in self.tasks):
            raise ValueError("This task is already attached to the pet.")
        self.tasks.append(task)


@dataclass
class Owner:
    """An owner whose time is shared across all of their pets."""

    name: str
    pets: list[Pet] = field(default_factory=list)

    def __post_init__(self):
        """Validate the owner's name."""
        self.name = nonblank(self.name, "Owner name")

    def add_pet(self, pet: Pet) -> None:
        """Attach a pet while keeping pet IDs unique."""
        if any(existing.id == pet.id for existing in self.pets):
            raise ValueError("This pet is already attached to the owner.")
        self.pets.append(pet)

    def get_all_tasks(self) -> list[tuple[Pet, Task]]:
        """Return all tasks with their pet context, across every owned pet."""
        return [(pet, task) for pet in self.pets for task in pet.tasks]


@dataclass
class Plan:
    """Selected tasks and explicit reasons for every scheduling decision."""

    selected: list[tuple[Pet, Task]] = field(default_factory=list)
    skipped: list[tuple[Pet, Task, str]] = field(default_factory=list)

    @property
    def total_minutes(self) -> int:
        """Return the care time consumed by the selected tasks."""
        return sum(task.duration_minutes for _, task in self.selected)


class Scheduler:
    """Read tasks through Owner; never silently change their requested times."""

    def __init__(self, owner: Owner):
        """Keep a reference to the owner so later additions are visible."""
        self.owner = owner

    def filter_tasks(self, *, pet_id: str | None = None, completed: bool | None = None,
                     on_date: date | None = None) -> list[tuple[Pet, Task]]:
        """Filter by pet identity, status, and date; None means no restriction."""
        return [(pet, task) for pet, task in self.owner.get_all_tasks()
                if (pet_id is None or pet.id == pet_id)
                and (completed is None or task.completed == completed)
                and (on_date is None or task.due_date == on_date)]

    def sort_by_time(self, tasks=None) -> list[tuple[Pet, Task]]:
        """Return a stable chronological copy without changing stored order."""
        source = self.owner.get_all_tasks() if tasks is None else tasks
        return sorted(source, key=lambda item: (item[1].due_date, minutes(item[1].time)))

    def sort_by_priority(self, tasks=None) -> list[tuple[Pet, Task]]:
        """Rank high before medium before low, then by date and time."""
        source = self.owner.get_all_tasks() if tasks is None else tasks
        return sorted(source, key=lambda item: (PRIORITIES[item[1].priority],
                                               item[1].due_date, minutes(item[1].time)))

    @staticmethod
    def overlaps(first: Task, second: Task) -> bool:
        """Detect intersecting intervals on the same day; touching ends are valid."""
        return (first.due_date == second.due_date
                and minutes(first.time) < minutes(second.time) + second.duration_minutes
                and minutes(second.time) < minutes(first.time) + first.duration_minutes)

    def detect_conflicts(self, on_date: date | None = None) -> list[str]:
        """Warn about every overlapping pending pair, including different pets."""
        tasks = self.sort_by_time(self.filter_tasks(completed=False, on_date=on_date))
        warnings = []
        for index, (pet, task) in enumerate(tasks):
            for other_pet, other in tasks[index + 1:]:
                if self.overlaps(task, other):
                    warnings.append(
                        f"{task.due_date}: {pet.name} / {task.description} "
                        f"({task.time}-{task.end_time}) overlaps {other_pet.name} / "
                        f"{other.description} ({other.time}-{other.end_time}).")
        return warnings

    def mark_task_complete(self, pet_id: str, task_id: str,
                           completed_on: date | None = None) -> Task | None:
        """Complete an owned task and attach its next occurrence exactly once."""
        for pet, task in self.owner.get_all_tasks():
            if pet.id == pet_id and task.id == task_id:
                next_task = task.mark_complete(completed_on)
                if next_task is not None:
                    pet.add_task(next_task)
                return next_task
        raise ValueError("Task not found for this pet.")

    def update_task(self, pet_id: str, task_id: str, **changes) -> Task:
        """Validate an edit before replacing a pending task; retain its identity."""
        allowed = {"description", "time", "due_date", "duration_minutes", "priority", "frequency"}
        if not set(changes) <= allowed:
            raise ValueError("Only task details can be edited.")
        for pet in self.owner.pets:
            if pet.id == pet_id:
                for index, task in enumerate(pet.tasks):
                    if task.id == task_id:
                        if task.completed:
                            raise ValueError("Completed tasks are kept as history and cannot be edited.")
                        updated = replace(task, **changes)
                        pet.tasks[index] = updated
                        return updated
        raise ValueError("Task not found for this pet.")

    def build_plan(self, on_date: date, available_minutes: int,
                   start_time: str = "00:00", end_time: str = "24:00") -> Plan:
        """Greedily select pending tasks by priority, respecting budget and availability."""
        if type(available_minutes) is not int or not 0 <= available_minutes <= 1440:
            raise ValueError("Available time must be a whole number from 0 to 1440 minutes.")
        start = minutes(start_time)
        end = 1440 if end_time == "24:00" else minutes(end_time)
        if start >= end:
            raise ValueError("Availability must end after it starts on the same day.")
        plan = Plan()
        for pet, task in self.sort_by_priority(self.filter_tasks(completed=False, on_date=on_date)):
            reason = ""
            if minutes(task.time) < start or minutes(task.time) + task.duration_minutes > end:
                reason = "Outside your available hours."
            elif any(self.overlaps(task, chosen) for _, chosen in plan.selected):
                reason = "Overlaps a task selected first by priority, time, or insertion order."
            elif plan.total_minutes + task.duration_minutes > available_minutes:
                reason = "Does not fit the remaining care-time budget."
            if reason:
                plan.skipped.append((pet, task, reason))
            else:
                plan.selected.append((pet, task))
        plan.selected = self.sort_by_time(plan.selected)
        return plan
