"""Calendar: day/week tasks, recurring care, overlaps and the PawPal time-budget plan."""

from __future__ import annotations

from datetime import time, timedelta

import streamlit as st

from pawpal_system import FREQUENCIES, PRIORITIES

from .common import Page, esc, notify, run_safely


def target_options(page: Page) -> dict:
    options = {"": "General garden care"}
    for space in page.service.spaces(page.user_id, page.gid):
        options[f"space:{space.id}"] = f"Space · {space.name}"
    labels = {v.id: v.label for _, v in page.service.inventory(page.user_id, page.gid)}
    for p in page.service.plantings(page.user_id, page.gid):
        options[f"planting:{p.id}"] = f"Plant · {p.nickname or labels.get(p.seed_variety_id, 'Planting')}"
    return options


def task_row(page: Page, task, context: str):
    with st.container(border=True):
        details, action = st.columns([4, 2])
        details.markdown(f"**{esc(task.start_time)} · {esc(task.description)}**")
        extra = " · suggested" if task.source == "suggested" else ""
        details.caption(f"{task.due_date:%a %b %d} · {task.duration_minutes} min · {task.priority} priority · "
                        f"{task.recurrence}{extra}")
        if task.completed:
            action.success("Done")
        elif action.button("Complete", key=page.key(f"{context}_done_{task.id}")):
            _, following = page.service.complete_task(page.user_id, page.gid, task.id, page.today)
            notify("Task completed." + (f" Next: {following.due_date} at {following.start_time}." if following else ""))


def task_fields(page: Page, prefix: str, task=None, default_date=None):
    description = st.text_input("Task", value=task.description if task else "", key=page.key(f"{prefix}_desc"),
                                placeholder="e.g. Water seed trays")
    left, right = st.columns(2)
    due = left.date_input("Date", value=task.due_date if task else (default_date or page.today),
                          key=page.key(f"{prefix}_date"))
    at = left.time_input("Start time", value=time.fromisoformat(task.start_time) if task else time(8),
                         key=page.key(f"{prefix}_time"))
    duration = left.number_input("Minutes", min_value=1, max_value=1440, value=task.duration_minutes if task else 15,
                                 key=page.key(f"{prefix}_dur"))
    priority = right.selectbox("Priority", list(PRIORITIES), index=list(PRIORITIES).index(task.priority) if task else 1,
                               key=page.key(f"{prefix}_prio"))
    recurrence = right.selectbox("Repeat", FREQUENCIES, index=FREQUENCIES.index(task.recurrence) if task else 0,
                                 key=page.key(f"{prefix}_rep"))
    return dict(description=description, due_date=due, start_time=at.strftime("%H:%M"),
                duration_minutes=int(duration), priority=priority, recurrence=recurrence)


def render(page: Page):
    schedule = page.service.schedule(page.user_id, page.gid)
    left, right = st.columns([2, 2])
    day = left.date_input("Show", page.today, key=page.key("cal_day"))
    view = right.radio("View", ["Day", "Week"], horizontal=True, key=page.key("cal_view"))
    overdue = schedule.overdue(page.today)
    if overdue:
        st.warning(f"{len(overdue)} overdue task(s): " + ", ".join(f"{t.description} ({t.due_date})" for t in overdue[:5]))
    days = [day] if view == "Day" else [day + timedelta(days=i) for i in range(7)]
    for current in days:
        tasks = schedule.tasks(on_date=current)
        if view == "Week":
            st.markdown(f"**{current:%A %b %d}**")
        for warning in schedule.conflicts(current):
            st.warning(warning)
        if not tasks:
            st.caption("No tasks." if view == "Week" else "No tasks on this day.")
        for task in tasks:
            task_row(page, task, f"cal{current.isoformat()}")
    st.caption("Overlap warnings cover this garden only. Completed tasks stay as history; "
               "repeating tasks create their next occurrence when completed.")

    st.subheader("Add a task")
    options = target_options(page)
    with st.form(page.key("add_task"), clear_on_submit=True):
        target = st.selectbox("For", list(options), format_func=options.get, key=page.key("new_target"))
        values = task_fields(page, "new", default_date=day)
        if st.form_submit_button("Add task", type="primary"):
            if target.startswith("space:"):
                values["growing_space_id"] = target.split(":", 1)[1]
            elif target.startswith("planting:"):
                values["planting_id"] = target.split(":", 1)[1]
            run_safely(lambda: page.service.add_task(page.user_id, page.gid, **values), "Task added.")

    pending = [t for t in schedule.tasks(completed=False) if t.due_date in days or t in overdue]
    if pending:
        st.subheader("Edit pending tasks")
    for task in pending:
        with st.expander(f"{task.due_date} · {task.start_time} · {task.description}"):
            with st.form(page.key(f"edit_{task.id}")):
                edits = task_fields(page, f"edit_{task.id}", task)
                if st.form_submit_button("Save changes"):
                    run_safely(lambda: page.service.update_task(page.user_id, page.gid, task.id, **edits),
                               "Task updated.")
            if st.button("Delete task", key=page.key(f"del_{task.id}")):
                run_safely(lambda: page.service.delete_task(page.user_id, page.gid, task.id), "Task deleted.")

    st.subheader("Plan my time")
    st.caption("Uses the PawPal+ planner: higher priority first, no overlaps, within your hours and minutes. "
               "It only suggests; nothing is moved or completed.")
    with st.form(page.key("plan")):
        plan_day = st.date_input("Plan date", day, key=page.key("plan_day"))
        budget = st.number_input("Minutes available", 0, 1440, 60, key=page.key("plan_budget"))
        a, b = st.columns(2)
        start = a.time_input("From", time(7), key=page.key("plan_from"))
        end = b.time_input("Until", time(21), key=page.key("plan_until"))
        submitted = st.form_submit_button("Build plan")
    if submitted:
        plan = run_safely(lambda: schedule.plan(plan_day, int(budget), start.strftime("%H:%M"), end.strftime("%H:%M")))
        if plan is not None:
            st.metric("Planned care", f"{plan.total_minutes} / {int(budget)} min")
            if plan.selected:
                st.table([{"Time": t.start_time, "Task": t.description, "Priority": t.priority,
                           "Minutes": t.duration_minutes} for t in plan.selected])
            else:
                st.info("No pending tasks fit this plan.")
            for task, reason in plan.skipped:
                st.warning(f"{task.description} ({task.priority}) — {reason}")
