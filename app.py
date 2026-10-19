"""Streamlit interface; scheduling rules live in pawpal_system.py."""

from datetime import date, time
import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler, FREQUENCIES, PRIORITIES
from main import demo_owner

st.set_page_config(page_title="PawPal+ | Daily care", page_icon="🐾", layout="wide")
if "owner" not in st.session_state:
    st.session_state.owner = Owner("Jordan")
owner = st.session_state.owner
scheduler = Scheduler(owner)


def notify(message):
    """Keep feedback across the rerun that refreshes the schedule."""
    st.session_state.notice = message
    st.rerun()


def task_fields(prefix, task=None):
    """Render shared controls for creating and editing tasks."""
    description = st.text_input("Task description", value=task.description if task else "",
                                key=f"{prefix}_description")
    first, second = st.columns(2)
    with first:
        due = st.date_input("Due date", value=task.due_date if task else date.today(), key=f"{prefix}_date")
        at = st.time_input("Start time", value=time.fromisoformat(task.time) if task else time(8), key=f"{prefix}_time")
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=1440,
                                  value=task.duration_minutes if task else 20, key=f"{prefix}_duration")
    with second:
        priority = st.selectbox("Priority", list(PRIORITIES),
                               index=list(PRIORITIES).index(task.priority) if task else 1, key=f"{prefix}_priority")
        frequency = st.selectbox("Repeat", FREQUENCIES,
                                index=FREQUENCIES.index(task.frequency) if task else 0, key=f"{prefix}_frequency")
    return dict(description=description, time=at.strftime("%H:%M"), due_date=due,
                duration_minutes=int(duration), priority=priority, frequency=frequency)


with st.sidebar:
    st.title("🐾 PawPal+")
    st.caption("A little planning. A lot of care.")
    with st.form("owner_form"):
        name = st.text_input("Owner name", value=owner.name)
        if st.form_submit_button("Save owner"):
            try:
                owner.name = Owner(name).name
                notify("Owner updated.")
            except ValueError as error:
                st.error(str(error))
    st.subheader("Your pets")
    for pet in owner.pets:
        st.write(f"{pet.name} · {pet.species}")
    with st.expander("Add a pet", expanded=not owner.pets):
        with st.form("pet_form", clear_on_submit=True):
            pet_name = st.text_input("Pet name")
            species = st.selectbox("Species", ["dog", "cat", "bird", "rabbit", "other"])
            if st.form_submit_button("Add pet"):
                try:
                    owner.add_pet(Pet(pet_name, species))
                    notify(f"Added {pet_name.strip()}.")
                except ValueError as error:
                    st.error(str(error))
    if not owner.pets and st.button("Load demo household"):
        st.session_state.owner = demo_owner(date.today())
        notify("Loaded Mochi and Luna with sample tasks.")
    st.divider()
    st.caption("Data stays in this browser session. Refreshing or closing the session may reset it.")

st.title("Their day, thoughtfully planned.")
st.write(f"Welcome, {owner.name}. Keep every pet's care in one place.")
if "notice" in st.session_state:
    st.success(st.session_state.pop("notice"))
schedule_tab, tasks_tab, plan_tab = st.tabs(["Daily schedule", "Manage tasks", "Build a plan"])

with schedule_tab:
    first, second, third = st.columns(3)
    with first:
        chosen_date = st.date_input("Schedule date", date.today())
    with second:
        pet_options = {pet.id: f"{pet.name} ({pet.species})" for pet in owner.pets}
        chosen_pet = st.selectbox("Filter by pet", [None, *pet_options],
                                  format_func=lambda value: "All pets" if value is None else pet_options[value])
    with third:
        status = st.selectbox("Status", ["All", "Pending", "Completed"])
    completed = {"All": None, "Pending": False, "Completed": True}[status]
    day_tasks = scheduler.filter_tasks(on_date=chosen_date)
    left, middle, right = st.columns(3)
    left.metric("Tasks today", len(day_tasks))
    middle.metric("Completed", sum(task.completed for _, task in day_tasks))
    right.metric("Pending care", f"{sum(task.duration_minutes for _, task in day_tasks if not task.completed)} min")
    for warning in scheduler.detect_conflicts(chosen_date):
        st.warning(warning)
    st.caption("Conflict warnings include all pets because they share your time.")
    overdue = [(pet, task) for pet, task in scheduler.filter_tasks(completed=False) if task.due_date < date.today()]
    if overdue:
        st.warning(f"{len(overdue)} overdue task(s). Open Manage tasks to complete or reschedule them.")
    visible = scheduler.sort_by_time(scheduler.filter_tasks(pet_id=chosen_pet, completed=completed, on_date=chosen_date))
    if not visible:
        st.info("No tasks match these filters. Add a pet and a task, or choose another date.")
    for pet, task in visible:
        with st.container(border=True):
            details, action = st.columns([5, 1])
            with details:
                st.subheader(f"{task.time}–{task.end_time} · {task.description}")
                st.write(f"{pet.name} · {task.duration_minutes} min · {task.priority.upper()} priority · {task.frequency}")
            with action:
                if task.completed:
                    st.success("Completed")
                elif st.button("Complete", key=f"complete_{task.id}"):
                    following = scheduler.mark_task_complete(pet.id, task.id)
                    notify("Task completed." + (f" Next occurrence: {following.due_date} at {following.time}." if following else ""))

with tasks_tab:
    st.subheader("Make room for every routine")
    if not owner.pets:
        st.info("Add your first pet in the sidebar, or load the demo household.")
    else:
        pet_map = {pet.id: pet for pet in owner.pets}
        with st.form("add_task", clear_on_submit=True):
            task_pet = st.selectbox("Pet", list(pet_map), format_func=lambda value: f"{pet_map[value].name} ({pet_map[value].species})")
            values = task_fields("new")
            if st.form_submit_button("Add task", type="primary"):
                try:
                    pet_map[task_pet].add_task(Task(**values))
                    notify("Task added to the schedule.")
                except ValueError as error:
                    st.error(str(error))
        st.subheader("Edit pending tasks")
        pending = scheduler.sort_by_time(scheduler.filter_tasks(completed=False))
        if not pending:
            st.caption("No pending tasks yet.")
        for pet, task in pending:
            with st.expander(f"{task.due_date} · {task.time} · {pet.name}: {task.description}"):
                with st.form(f"edit_{task.id}"):
                    edits = task_fields(task.id, task)
                    if st.form_submit_button("Save changes"):
                        try:
                            scheduler.update_task(pet.id, task.id, **edits)
                            notify("Task updated.")
                        except ValueError as error:
                            st.error(str(error))
                if st.button("Mark complete", key=f"manage_complete_{task.id}"):
                    following = scheduler.mark_task_complete(pet.id, task.id)
                    notify("Task completed." + (f" Next occurrence: {following.due_date}." if following else ""))
        st.caption("Completed tasks stay in the daily schedule as history. Recurring tasks create their next occurrence when completed.")

with plan_tab:
    st.subheader("A plan that fits your day")
    st.write("Choose your available hours and care-time budget. Higher priorities come first; ties use the earlier time and then insertion order.")
    with st.form("plan_form"):
        plan_date = st.date_input("Plan date", date.today())
        budget = st.number_input("Available care time (minutes)", min_value=0, max_value=1440, value=60)
        left, right = st.columns(2)
        with left:
            start = st.time_input("Available from", time(7))
        with right:
            end = st.time_input("Available until", time(22))
        if st.form_submit_button("Generate schedule", type="primary"):
            st.session_state.plan_request = (plan_date, int(budget), start.strftime("%H:%M"), end.strftime("%H:%M"))
    if "plan_request" in st.session_state:
        requested_date, requested_budget, requested_start, requested_end = st.session_state.plan_request
        try:
            plan = scheduler.build_plan(requested_date, requested_budget, requested_start, requested_end)
            st.caption(f"Plan for {requested_date} · {requested_start}–{requested_end}")
            st.metric("Care time selected", f"{plan.total_minutes} / {requested_budget} min")
            if plan.selected:
                st.table([{"Time": f"{task.time}–{task.end_time}", "Pet": pet.name,
                           "Task": task.description, "Priority": task.priority,
                           "Why included": "Fits your hours and budget with no selected-task overlap."}
                          for pet, task in plan.selected])
            else:
                st.info("No pending tasks fit this plan. Check the date, hours, and time budget.")
            if plan.skipped:
                st.subheader("Needs your attention")
                for pet, task, reason in plan.skipped:
                    st.warning(f"{pet.name}: {task.description} ({task.priority}) — {reason}")
            st.caption("This is a suggestion. Skipped tasks stay pending; edit them to resolve conflicts. Tasks are never automatically moved or completed.")
        except ValueError as error:
            st.error(str(error))
