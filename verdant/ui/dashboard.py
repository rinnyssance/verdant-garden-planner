"""Overview: welcome, metrics, weather, growing plants, care and explained recommendations."""

from __future__ import annotations

from datetime import timedelta

import streamlit as st

from verdant.domain import SeedVariety
from verdant.domain.common import utcnow
from verdant.domain.plantings import GROWTH_STAGES
from verdant.services.recommendation_engine import FROST_WATCH_F, build_context, evaluate

from .calendar import task_row
from .common import STAGE_LABELS, Page, ago, days_ago, garden_now, html, notify, plant_photo, run_safely
from .theme import (SETTING_ICON, SETTING_LABEL, chip, empty_state, esc, illustration, metric, page_header,
                    section, stage_bar, table, weather_strip)

MAX_PLANT_CARDS = 6


def greeting(hour: int) -> str:
    return "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"


def environment_chip(space) -> str:
    if space is None:
        return ""
    tone = "" if space.setting in ("indoor", "greenhouse") else "warm"
    return chip(f"{SETTING_LABEL[space.setting]} · {space.name}", tone, SETTING_ICON[space.setting])


def weather_panel(page: Page, spaces, plantings):
    html(section("Weather", "sun"))
    snapshots = page.weather.cached(page.gid)
    exposed = sum(1 for p in plantings if p.is_live and spaces.get(p.growing_space_id)
                  and spaces[p.growing_space_id].exposed_to_outdoor_temperature)
    sheltered = sum(1 for p in plantings if p.is_live and spaces.get(p.growing_space_id)
                    and not spaces[p.growing_space_id].exposed_to_outdoor_temperature)
    if not page.garden.has_coordinates:
        html(empty_state("Weather is off for this garden",
                         " Set the garden's location in Settings to see a forecast and weather-aware advice.", "cloud"))
    elif not snapshots:
        html(empty_state("No forecast yet",
                         " Use Check weather & advice to fetch the forecast for this garden.", "cloud"))
    else:
        first = snapshots[0]
        stale = utcnow() >= first.expires_at
        html(f'<div class="vd-sub">{esc(first.provider)} · fetched {esc(ago(first.fetched_at))} · '
             f'°{first.temp_unit}, {first.precip_unit}, {first.wind_unit}'
             + (' · <b style="color:var(--terracotta)">out of date — refresh before relying on it</b>' if stale else "")
             + '</div>')
        upcoming = [s for s in snapshots if s.forecast_for >= page.today][:7]
        if upcoming:
            html(weather_strip(upcoming, page.today, FROST_WATCH_F))
        else:
            html(empty_state("This forecast has run out", " Refresh to see the coming days.", "cloud"))
    note = (f"{exposed} plant{'s' if exposed != 1 else ''} outdoors or under cover can be affected by this weather; "
            f"{sheltered} indoor or greenhouse planting{'s are' if sheltered != 1 else ' is'} sheltered from outdoor rain and frost.")
    html(f'<div class="vd-sub" style="margin-top:.6rem">{esc(note)}</div>')
    if st.button("Check weather & advice", key=page.key("refresh"), type="primary", icon=":material/refresh:",
                 help="Fetches the forecast if the cached one has expired, then re-runs the advisory rules."):
        now = utcnow()
        ctx = build_context(page.service, page.weather, page.user_id, page.gid, page.today, now)
        stored = page.service.store_recommendations(page.user_id, page.gid, evaluate(ctx))
        message = ctx.forecast.message or f"Forecast {ctx.forecast.status}."
        notify(f"{message} {len(stored)} advisory item(s).", "info" if ctx.forecast.usable else "warning")


def plant_card(page: Page, planting, variety, space, tasks, observations):
    name = planting.nickname or (variety.label if variety else "Planting")
    with page.card(f"plant-{planting.id}"):
        photo = plant_photo(page, planting.id)
        if photo:
            st.image(photo, caption="Latest journal photo")
        else:
            html(illustration(variety.category if variety else None, variety.crop_key if variety else None,
                              planting.id[:8], name))
        pending = sorted((t for t in tasks if t.planting_id == planting.id and not t.completed),
                         key=lambda t: (t.due_date, t.start_time))
        indicators = [environment_chip(space)]
        if pending:
            nxt = pending[0]
            tone = "warm" if nxt.due_date < page.today else ""
            when = "overdue" if nxt.due_date < page.today else days_ago(nxt.due_date, page.today)
            indicators.append(chip(f"{nxt.description} · {when}", tone, "task"))
        if observations:
            last = observations[-1]
            indicators.append(chip(f"Journal {days_ago(last.observed_at.date(), page.today)}", "out", "book"))
            if last.moisture_assessment:
                indicators.append(chip(f"Soil {last.moisture_assessment.replace('_', ' ')}", "ink", "drop"))
        else:
            indicators.append(chip("No journal entries yet", "out", "book"))
        sown = f"Sown {planting.sown_on:%b %d}" if planting.sown_on else "Sowing date not recorded"
        html(f'<div class="vd-title">{esc(name)}</div>'
             f'<div class="vd-meta">{planting.quantity} plant{"s" if planting.quantity != 1 else ""} · {esc(sown)}</div>'
             f'{stage_bar(planting.growth_stage, GROWTH_STAGES)}'
             f'<div class="vd-stagecap">{STAGE_LABELS[planting.growth_stage]}</div>'
             f'<div class="vd-indicators">{"".join(indicators)}</div>')


def growing_garden(page: Page, plantings, varieties, spaces, tasks):
    html(section("My growing garden", "sprout", "Your active plantings, their stage and what they need next."))
    live = [p for p in plantings if p.status == "active"]
    if not live:
        html(empty_state("Nothing planted yet",
                         " Open the Seed Library and choose Start planting on a seed. Owning seeds is not the same "
                         "as growing them, so plants only appear here once you record them.", "sprout"))
        return
    cols = st.columns(3, gap="medium")
    for index, planting in enumerate(live[:MAX_PLANT_CARDS]):
        with cols[index % 3]:
            plant_card(page, planting, varieties.get(planting.seed_variety_id), spaces.get(planting.growing_space_id),
                       tasks, page.service.observations(page.user_id, page.gid, planting.id))
    if len(live) > MAX_PLANT_CARDS:
        html(f'<div class="vd-sub">Showing {MAX_PLANT_CARDS} of {len(live)} plantings. See them all in My Plants.</div>')


def advisory_card(page: Page, rec, spaces):
    space = spaces.get(rec.growing_space_id)
    with page.card(f"rec-{rec.id}"):
        chips = chip(rec.severity.title(), f"vd-sev-{rec.severity}") + chip(rec.suitability.replace("_", " "), "out")
        if space:
            chips += environment_chip(space)
        html(f'<div>{chips}</div><div class="vd-title" style="margin:.45rem 0 .25rem">{esc(rec.title)}</div>'
             f'<div class="vd-meta" style="color:var(--ink);font-size:.9rem">{esc(rec.explanation)}</div>')
        with st.expander("Why? Evidence and limits"):
            if rec.evidence:
                html(table([{"What": e.get("type", "").replace("_", " "),
                             "Value": f"{e.get('value')} {e.get('unit', '')}".strip(),
                             "Origin": e.get("origin", ""), "Source": e.get("source", ""),
                             "For": e.get("for_date", "")} for e in rec.evidence]))
            if rec.unknowns:
                html('<div class="vd-meta"><b>Unknown:</b> ' + ", ".join(esc(u) for u in rec.unknowns) + "</div>")
            if rec.limitations:
                st.caption(rec.limitations)
        left, right = st.columns(2)
        label = "Add suggested task" if rec.suggested_task else "Got it"
        if left.button(label, key=page.key(f"accept_{rec.id}"), type="primary"):
            task = run_safely(lambda: page.service.accept_recommendation(page.user_id, page.gid, rec.id))
            if task is not None or not rec.suggested_task:
                notify(f"Added to calendar: {task.description} ({task.due_date})." if task else "Noted.")
        if right.button("Dismiss", key=page.key(f"dismiss_{rec.id}")):
            page.service.dismiss_recommendation(page.user_id, page.gid, rec.id)
            notify("Advice dismissed. It will not be raised again for the same conditions.", "info")


def render(page: Page):
    g = page.garden
    now = garden_now(g)
    inventory = page.service.inventory(page.user_id, page.gid)
    plantings = page.service.plantings(page.user_id, page.gid)
    spaces = {s.id: s for s in page.service.spaces(page.user_id, page.gid)}
    varieties = {v.id: v for _, v in inventory}
    for p in plantings:
        if p.seed_variety_id not in varieties:
            varieties[p.seed_variety_id] = page.service.repo.get(SeedVariety, p.seed_variety_id)
    schedule = page.service.schedule(page.user_id, page.gid)
    tasks = page.service.tasks(page.user_id, page.gid)
    today_tasks = schedule.tasks(on_date=page.today)
    overdue = schedule.overdue(page.today)
    recs = page.service.recommendations(page.user_id, page.gid)

    where = f" in {g.city}" if g.city else ""
    html(page_header(f"{page.today:%A, %B %d}", f"{greeting(now.hour)}.",
                     f"Here's how {g.display_name} is growing{where}."))

    review = sum(1 for _, v in inventory if v.verification_status == "needs_review")
    indoor = sum(1 for p in plantings if spaces.get(p.growing_space_id)
                 and not spaces[p.growing_space_id].exposed_to_outdoor_temperature)
    outstanding = sum(not t.completed for t in today_tasks) + len(overdue)
    html('<div class="vd-metrics">'
         + metric(len(inventory), "Seeds in library", "seed", f"{review} need review" if review else "")
         + metric(len(plantings), "Active plants", "sprout",
                  f"{indoor} sheltered · {len(plantings) - indoor} exposed" if plantings else "", "")
         + metric(outstanding, "Care tasks outstanding", "task", f"{len(overdue)} overdue" if overdue else "", "warm")
         + metric(len(recs), "Open recommendations", "spark", "", "gold")
         + "</div>")

    weather_panel(page, spaces, plantings)
    growing_garden(page, plantings, varieties, spaces, tasks)

    left, right = st.columns([1, 1], gap="large")
    with left:
        html(section("Today's care", "task"))
        for warning in schedule.conflicts(page.today):
            st.warning(warning)
        if overdue:
            st.warning(f"{len(overdue)} overdue task(s), listed first. Complete them here or reschedule in Calendar.")
        if not today_tasks and not overdue:
            html(empty_state("Nothing scheduled today", " Add care tasks in the Calendar.", "check"))
        for task in overdue + today_tasks:
            task_row(page, task, "dash")

        html(section("Upcoming tasks", "calendar", "The next seven days."))
        upcoming = [t for t in schedule.tasks(completed=False)
                    if page.today < t.due_date <= page.today + timedelta(days=7)]
        if not upcoming:
            html(empty_state("A quiet week ahead", " No pending tasks in the next seven days.", "calendar"))
        else:
            items = "".join(f'<li><div class="vd-when">{t.due_date:%a}<b>{t.due_date:%d}</b></div>'
                            f'<div><b>{esc(t.description)}</b><div class="vd-meta" style="margin:0">{esc(t.start_time)} · '
                            f'{t.duration_minutes} min · {esc(t.priority)} · {esc(t.recurrence)}</div></div></li>'
                            for t in upcoming[:8])
            html(f'<div class="vd-card"><ul class="vd-list">{items}</ul></div>')

    with right:
        html(section("Seasonal & weather recommendations", "spark",
                     "Rule-based, with evidence. Indoor and greenhouse plants are not given outdoor rain or frost advice."))
        if not recs:
            html(empty_state("No open recommendations",
                             " Run Check weather & advice. Advice never changes your tasks on its own.", "spark"))
        for rec in recs:
            advisory_card(page, rec, spaces)
        html('<div class="vd-sub" style="margin-top:.8rem">Planting-window advice (“can I sow this now?”) '
             'needs cited local frost dates and is not available yet.</div>')

    issues = []
    if review:
        issues.append(f"{review} seed record(s) need review (uncertain names or cultivars).")
    expired = sum(1 for item, _ in inventory if item.is_expired(page.today))
    if expired:
        issues.append(f"{expired} seed packet(s) are past their expiry date.")
    if not g.has_coordinates:
        issues.append("No location coordinates, so forecasts and weather advice are off.")
    unknown_exposure = [s.name for s in spaces.values() if s.light_source != "grow_light" and s.exposure == "unknown"]
    if unknown_exposure:
        issues.append("Sun exposure unknown for: " + ", ".join(unknown_exposure) + ".")
    html(section("Data quality", "alert"))
    if issues:
        html('<div class="vd-card"><ul class="vd-list">' + "".join(f"<li>{esc(i)}</li>" for i in issues) + "</ul></div>")
    else:
        html(empty_state("Records look complete", " No data-quality warnings for this garden.", "check"))
