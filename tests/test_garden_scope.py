"""The PawPal adapter keeps original scheduling semantics and stays inside one garden."""

from datetime import date, timedelta

import pytest

from verdant.domain import Garden, GardenTask
from verdant.scheduling import GardenSchedule

DAY = date(2026, 11, 16)


@pytest.fixture
def gardens():
    return Garden("My Garden", "u1"), Garden("Mom's Garden", "u1")


def test_conflicts_never_mix_gardens(gardens):
    mine, moms = gardens
    a = GardenTask(mine.id, "Water tomatoes", DAY, "08:00", 30)
    b = GardenTask(moms.id, "Water roses", DAY, "08:00", 30)
    assert GardenSchedule(mine, [a]).conflicts(DAY) == []
    with pytest.raises(ValueError):
        GardenSchedule(mine, [a, b])


def test_overlaps_within_garden_use_group_labels(gardens):
    mine, _ = gardens
    tasks = [GardenTask(mine.id, "Water", DAY, "08:00", 30, planting_id="p1"),
             GardenTask(mine.id, "Harvest", DAY, "08:15", 30, growing_space_id="s1")]
    labels = {"p1": "Basil", "s1": "Sunny bed"}
    warnings = GardenSchedule(mine, tasks, labels.get).conflicts(DAY)
    assert len(warnings) == 1 and "Basil" in warnings[0] and "Sunny bed" in warnings[0]


@pytest.mark.parametrize("recurrence,delta", [("daily", 1), ("weekly", 7)])
def test_recurring_completion_preserves_history_and_context(gardens, recurrence, delta):
    mine, _ = gardens
    task = GardenTask(mine.id, "Mist seedlings", DAY, "07:00", 5, "high", recurrence,
                      planting_id="p1", source="suggested", recommendation_id="r1", idempotency_key="rec:r1")
    schedule = GardenSchedule(mine, [task])
    done, following = schedule.complete(task.id, DAY)
    assert done.completed and done.completed_at is not None and done.id == task.id
    assert following.due_date == DAY + timedelta(days=delta) and not following.completed
    assert (following.planting_id, following.priority, following.start_time) == ("p1", "high", "07:00")
    assert following.idempotency_key is None and following.id != task.id
    assert schedule.complete(task.id, DAY) == (done, None)  # idempotent
    assert len(schedule.tasks()) == 2


def test_once_task_has_no_follow_up(gardens):
    mine, _ = gardens
    task = GardenTask(mine.id, "Sow peas", DAY)
    assert GardenSchedule(mine, [task]).complete(task.id, DAY)[1] is None


def test_plan_and_edit_follow_pawpal_rules(gardens):
    mine, _ = gardens
    tasks = [GardenTask(mine.id, "Low overlap", DAY, "08:00", 30, "low"),
             GardenTask(mine.id, "High", DAY, "08:10", 20, "high"),
             GardenTask(mine.id, "Fits", DAY, "10:00", 10, "low")]
    schedule = GardenSchedule(mine, tasks)
    plan = schedule.plan(DAY, 30, "07:00", "19:00")
    assert [t.description for t in plan.selected] == ["High", "Fits"]
    assert plan.total_minutes == 30 and plan.skipped[0][0].description == "Low overlap"
    updated = schedule.update(tasks[0].id, start_time="11:00", recurrence="weekly")
    assert (updated.start_time, updated.recurrence, updated.id) == ("11:00", "weekly", tasks[0].id)
    with pytest.raises(ValueError):
        schedule.update(tasks[0].id, start_time="bad")
    schedule.complete(tasks[1].id, DAY)
    with pytest.raises(ValueError):
        schedule.update(tasks[1].id, start_time="12:00")  # history is read-only


def test_overdue_and_unknown_task(gardens):
    mine, _ = gardens
    old = GardenTask(mine.id, "Thin carrots", DAY - timedelta(days=2))
    schedule = GardenSchedule(mine, [old])
    assert schedule.overdue(DAY) == [old]
    with pytest.raises(ValueError):
        schedule.complete("missing")
