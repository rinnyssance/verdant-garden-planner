"""Calendar: day/week tasks, recurring care, overlaps and the PawPal time-budget plan."""

from __future__ import annotations

from datetime import time, timedelta

import streamlit as st

from pawpal_system import FREQUENCIES, PRIORITIES

from .common import Page, html, notify, run_safely
from .theme import chip, empty_state, esc, page_header, section, table

PRIORITY_TONE = {"high": "warm", "medium": "gold", "low": "out"}


def target_options(page: Page) -> dict:
    options = {"": "General garden care"}
    for space in page.service.spaces(page.user_id, page.gid):
        options[f"space:{space.id}"] = f"Space · {space.name}"
    labels = {v.id: v.label for _, v in page.service.inventory(page.user_id, page.gid)}
    for p in page.service.plantings(page.user_id, page.gid):
        options[f"planting:{p.id}"] = f"Plant · {p.nickname or labels.get(p.seed_variety_id, 'Planting')}"
    return options


def task_row(page: Page, task, context: str):
    with page.card(f"task-{context}-{task.id}"):
        details, action = st.columns([5, 2], vertical_alignment="center")
        chips = chip(f"{task.priority} priority", PRIORITY_TONE[task.priority])
        if task.recurrence != "once":
            chips += chip(task.recurrence, "ink", "clock")
        if task.source == "suggested":
            chips += chip("from advice", "", "spark")
        if not task.completed and task.due_date < page.today:
            chips += chip("overdue", "warm", "alert")
        details.markdown(
            f'<div style="display:flex;gap:.8rem;align-items:center"><div class="vd-when">{task.due_date:%a}'
            f'<b>{esc(task.start_time)}</b></div><div><div class="vd-title" style="font-size:1.02rem">'
            f'{esc(task.description)}</div><div class="vd-meta" style="margin:.1rem 0 .2rem">{task.due_date:%b %d} · '
            f'{task.duration_minutes} min</div>{chips}</div></div>', unsafe_allow_html=True)
        if task.completed:
            action.markdown(chip("Done", "", "check"), unsafe_allow_html=True)
        elif action.button("Complete", key=page.key(f"{context}_done_{task.id}"), icon=":material/check:"):
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


def week_strip(schedule, day, today) -> str:
    start = day - timedelta(days=day.weekday())
    cells = []
    for i in range(7):
        current = start + timedelta(days=i)
        pending = sum(not t.completed for t in schedule.tasks(on_date=current))
        cls = "wd sel" if current == day else "wd"
        label = "Today" if current == today else f"{current:%a}"
        dot = f'<div class="dot">{pending}</div>' if pending else '<div style="height:1.15rem"></div>'
        cells.append(f'<div class="{cls}" title="{pending} pending">{label}<b>{current:%d}</b>{dot}</div>')
    return f'<div class="vd-week" aria-label="Week overview">{"".join(cells)}</div>'


def render(page: Page):
    schedule = page.service.schedule(page.user_id, page.gid)
    html(page_header("Calendar", "Care & planting schedule",
                     "Recurring care, overlaps and a plan that fits your time. Times you set are never moved for you."))
    left, right = st.columns([2, 2])
    day = left.date_input("Show", page.today, key=page.key("cal_day"))
    view = right.radio("View", ["Day", "Week"], horizontal=True, key=page.key("cal_view"))
    html(week_strip(schedule, day, page.today))
    overdue = schedule.overdue(page.today)
    if overdue:
        st.warning(f"{len(overdue)} overdue task(s): " + ", ".join(f"{t.description} ({t.due_date})" for t in overdue[:5]))
    days = [day] if view == "Day" else [day + timedelta(days=i) for i in range(7)]
    if overdue and page.today in days:
        html('<div class="vd-h2" style="font-size:1.1rem;margin-top:.4rem">Overdue</div>')
        for task in overdue:
            task_row(page, task, "overdue")
    for current in days:
        tasks = schedule.tasks(on_date=current)
        if view == "Week":
            html(f'<div class="vd-h2" style="font-size:1.1rem;margin-top:1rem">{current:%A, %B %d}</div>')
        for warning in schedule.conflicts(current):
            st.warning(warning)
        if not tasks:
            if view == "Day":
                html(empty_state("No tasks on this day", " Add one below, or accept a recommendation on the Overview.", "calendar"))
            else:
                st.caption("No tasks.")
        for task in tasks:
            task_row(page, task, f"cal{current.isoformat()}")
    st.caption("Overlap warnings cover this garden only. Completed tasks stay as history; "
               "repeating tasks create their next occurrence when completed.")

    html(section("Add a task", "task"))
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
        html(section("Edit pending tasks", "clock"))
    for task in pending:
        with st.expander(f"{task.due_date:%a %b %d} · {task.start_time} · {task.description}"):
            with st.form(page.key(f"edit_{task.id}")):
                edits = task_fields(page, f"edit_{task.id}", task)
                if st.form_submit_button("Save changes"):
                    run_safely(lambda: page.service.update_task(page.user_id, page.gid, task.id, **edits),
                               "Task updated.")
            if st.button("Delete task", key=page.key(f"del_{task.id}")):
                run_safely(lambda: page.service.delete_task(page.user_id, page.gid, task.id), "Task deleted.")

    html(section("Plan my time", "clock", "The PawPal+ planner: higher priority first, no overlaps, within your hours "
                 "and minutes. It only suggests; nothing is moved or completed."))
    with st.form(page.key("plan")):
        a, b, c, d = st.columns(4)
        plan_day = a.date_input("Plan date", day, key=page.key("plan_day"))
        budget = b.number_input("Minutes available", 0, 1440, 60, key=page.key("plan_budget"))
        start = c.time_input("From", time(7), key=page.key("plan_from"))
        end = d.time_input("Until", time(21), key=page.key("plan_until"))
        submitted = st.form_submit_button("Build plan", type="primary")
    if submitted:
        plan = run_safely(lambda: schedule.plan(plan_day, int(budget), start.strftime("%H:%M"), end.strftime("%H:%M")))
        if plan is not None:
            html(f'<div class="vd-sub"><b>{plan.total_minutes} of {int(budget)} minutes</b> planned for {plan_day:%A, %B %d}.</div>')
            if plan.selected:
                html(table([{"Time": t.start_time, "Task": t.description, "Priority": t.priority,
                             "Minutes": t.duration_minutes} for t in plan.selected]))
            else:
                html(empty_state("Nothing fits this plan", " Check the date, hours and minutes available.", "clock"))
            for task, reason in plan.skipped:
                st.warning(f"{task.description} ({task.priority}) — {reason}")
