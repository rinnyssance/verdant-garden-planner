"""Run a reproducible CLI demonstration with: python main.py."""

from datetime import date
from pawpal_system import Owner, Pet, Task, Scheduler


def demo_owner(day: date) -> Owner:
    """Create two pets with out-of-order tasks and a deliberate conflict."""
    owner = Owner("Jordan")
    mochi, luna = Pet("Mochi", "dog"), Pet("Luna", "cat")
    owner.add_pet(mochi)
    owner.add_pet(luna)
    mochi.add_task(Task("Evening walk", "18:00", day, 30, "medium", "daily"))
    mochi.add_task(Task("Morning walk", "08:00", day, 30, "high", "daily"))
    luna.add_task(Task("Breakfast", "08:00", day, 10, "high", "daily"))
    luna.add_task(Task("Brush coat", "09:00", day, 15, "low", "weekly"))
    return owner


def main():
    """Show sorting, filtering, conflicts, constrained planning, and recurrence."""
    day = date(2026, 10, 18)
    owner = demo_owner(day)
    scheduler = Scheduler(owner)
    print(f"Today's Schedule - {day} (fixed demo date)")
    for pet, task in scheduler.sort_by_time():
        print(f"  {task.time}-{task.end_time} | {pet.name:5} | {task.description:13} | {task.priority}")
    print("\nConflict warnings:")
    for warning in scheduler.detect_conflicts(day):
        print(f"  WARNING: {warning}")
    print("\nLuna's pending tasks:")
    for _, task in scheduler.filter_tasks(pet_id=owner.pets[1].id, completed=False):
        print(f"  {task.time} {task.description}")
    plan = scheduler.build_plan(day, 45, "07:00", "20:00")
    print(f"\nPriority plan - {plan.total_minutes}/45 minutes:")
    for pet, task in plan.selected:
        print(f"  {task.time} {pet.name}: {task.description} ({task.priority})")
    for pet, task, reason in plan.skipped:
        print(f"  SKIPPED {pet.name}: {task.description} - {reason}")
    pet, task = plan.selected[0]
    following = scheduler.mark_task_complete(pet.id, task.id, completed_on=day)
    print(f"\nCompleted {task.description}; next occurrence: {following.due_date} {following.time}")
    print(f"Completed tasks: {len(scheduler.filter_tasks(completed=True))}")


if __name__ == "__main__":
    main()
