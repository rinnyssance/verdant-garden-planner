"""Behavior tests for the assignment requirements and important edge cases."""

from datetime import date
import pytest
from pawpal_system import Owner, Pet, Task, Scheduler

DAY = date(2026, 10, 18)


@pytest.fixture
def household():
    owner = Owner("Jordan")
    for name, species in [("Mochi", "dog"), ("Luna", "cat")]:
        owner.add_pet(Pet(name, species))
    return owner, Scheduler(owner)


def test_task_completion():
    task = Task("Feed", "08:00", DAY)
    assert task.mark_complete(DAY) is None
    assert task.completed


def test_add_task_and_independent_lists():
    first, second = Pet("Mochi", "dog"), Pet("Luna", "cat")
    first.add_task(Task("Feed", "08:00", DAY))
    assert len(first.tasks) == 1
    assert second.tasks == []


def test_owner_aggregates_multiple_pets(household):
    owner, scheduler = household
    for pet in owner.pets:
        pet.add_task(Task("Feed", "08:00", DAY))
    assert len(scheduler.sort_by_time()) == 2
    assert {pet.name for pet, _ in owner.get_all_tasks()} == {"Mochi", "Luna"}


def test_chronological_sort_does_not_mutate(household):
    owner, scheduler = household
    for time in ["18:00", "08:00", "12:00"]:
        owner.pets[0].add_task(Task("Care", time, DAY))
    assert [task.time for _, task in scheduler.sort_by_time()] == ["08:00", "12:00", "18:00"]
    assert owner.pets[0].tasks[0].time == "18:00"
    assert scheduler.sort_by_time([]) == []


def test_filters_combine_date_identity_and_status(household):
    owner, scheduler = household
    first, second = owner.pets
    second.name = first.name  # Identity must not rely on unique names.
    first.add_task(Task("Done", "08:00", DAY, completed=True))
    first.add_task(Task("Tomorrow", "08:00", date(2026, 10, 19)))
    second.add_task(Task("Pending", "08:00", DAY))
    assert len(scheduler.filter_tasks(completed=True)) == 1
    assert scheduler.filter_tasks(pet_id=first.id, completed=False, on_date=DAY) == []
    assert len(scheduler.filter_tasks(pet_id=second.id, completed=False, on_date=DAY)) == 1


@pytest.mark.parametrize("frequency,next_day", [("daily", date(2026, 11, 1)),
                                               ("weekly", date(2026, 11, 7))])
def test_recurrence_preserves_details_and_is_idempotent(household, frequency, next_day):
    owner, scheduler = household
    pet = owner.pets[0]
    task = Task("Care", "08:00", date(2026, 10, 31), 10, "high", frequency)
    pet.add_task(task)
    following = scheduler.mark_task_complete(pet.id, task.id, date(2026, 10, 31))
    assert task.completed and not following.completed
    assert following.due_date == next_day
    assert following.id != task.id
    assert (following.description, following.time, following.priority, following.duration_minutes) == (
        "Care", "08:00", "high", 10)
    assert scheduler.mark_task_complete(pet.id, task.id, DAY) is None
    assert len(pet.tasks) == 2


def test_late_recurrence_uses_completion_day():
    task = Task("Feed", "08:00", DAY, frequency="daily")
    assert task.mark_complete(date(2026, 10, 22)).due_date == date(2026, 10, 23)


def test_duplicate_times_across_pets_warn(household):
    owner, scheduler = household
    for pet in owner.pets:
        pet.add_task(Task("Feed", "08:00", DAY))
    warnings = scheduler.detect_conflicts(DAY)
    assert len(warnings) == 1
    assert "Mochi" in warnings[0] and "Luna" in warnings[0]


def test_partial_overlaps_but_not_touching_or_other_dates(household):
    owner, scheduler = household
    pet = owner.pets[0]
    for time, day in [("08:00", DAY), ("08:10", DAY), ("08:30", DAY),
                       ("08:00", date(2026, 10, 19))]:
        pet.add_task(Task("Care", time, day, 20))
    assert len(scheduler.detect_conflicts()) == 1
    pet.tasks[0].mark_complete(DAY)
    assert scheduler.detect_conflicts() == []


def test_empty_household(household):
    _, scheduler = household
    assert scheduler.sort_by_time() == []
    assert scheduler.detect_conflicts() == []
    assert scheduler.build_plan(DAY, 30).total_minutes == 0


def test_priority_plan_respects_overlap_budget_and_hours(household):
    owner, scheduler = household
    pet = owner.pets[0]
    for task in [Task("Low overlapping", "08:00", DAY, 30, "low"),
                 Task("High", "08:10", DAY, 20, "high"),
                 Task("Too long", "09:00", DAY, 40, "medium"),
                 Task("Fits", "10:00", DAY, 10, "low"),
                 Task("Outside", "20:00", DAY, 10, "high")]:
        pet.add_task(task)
    plan = scheduler.build_plan(DAY, 30, "07:00", "19:00")
    assert [task.description for _, task in plan.selected] == ["High", "Fits"]
    assert plan.total_minutes == 30
    assert len(plan.skipped) == 3
    assert all(reason for _, _, reason in plan.skipped)
    assert all(not task.completed for task in pet.tasks)


def test_zero_budget_and_completed_tasks(household):
    owner, scheduler = household
    owner.pets[0].add_task(Task("Done", "08:00", DAY, completed=True))
    owner.pets[0].add_task(Task("Pending", "09:00", DAY))
    plan = scheduler.build_plan(DAY, 0)
    assert plan.selected == [] and len(plan.skipped) == 1


def test_edit_is_atomic_and_preserves_id(household):
    owner, scheduler = household
    pet = owner.pets[0]
    task = Task("Care", "08:00", DAY)
    pet.add_task(task)
    with pytest.raises(ValueError):
        scheduler.update_task(pet.id, task.id, time="bad")
    assert pet.tasks[0] is task
    updated = scheduler.update_task(pet.id, task.id, time="09:00", priority="high")
    assert updated.id == task.id and updated.time == "09:00"
    scheduler.mark_task_complete(pet.id, task.id, DAY)
    with pytest.raises(ValueError):
        scheduler.update_task(pet.id, task.id, time="10:00")


@pytest.mark.parametrize("changes", [{"time": "25:00"}, {"time": "8:00"},
    {"description": " "}, {"duration_minutes": 0}, {"duration_minutes": -1},
    {"duration_minutes": 1.5}, {"priority": "urgent"}, {"frequency": "monthly"},
    {"time": "23:59", "duration_minutes": 2}])
def test_invalid_task_rejected(changes):
    values = dict(description="Care", time="08:00", due_date=DAY)
    values.update(changes)
    with pytest.raises(ValueError):
        Task(**values)


def test_invalid_budget_and_window(household):
    _, scheduler = household
    with pytest.raises(ValueError):
        scheduler.build_plan(DAY, -1)
    with pytest.raises(ValueError):
        scheduler.build_plan(DAY, 30, "18:00", "08:00")


def test_wrong_pet_cannot_complete_task(household):
    owner, scheduler = household
    task = Task("Care", "08:00", DAY)
    owner.pets[0].add_task(task)
    with pytest.raises(ValueError):
        scheduler.mark_task_complete(owner.pets[1].id, task.id)
    assert not task.completed


def test_midnight_boundary(household):
    owner, scheduler = household
    task = Task("Care", "23:50", DAY, 10)
    owner.pets[0].add_task(task)
    assert task.end_time == "24:00"
    assert scheduler.build_plan(DAY, 10, "23:00", "24:00").total_minutes == 10
