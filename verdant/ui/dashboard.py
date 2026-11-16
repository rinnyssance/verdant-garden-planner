"""Dashboard: forecast, today's care, advisories and data-quality warnings."""

from __future__ import annotations

import streamlit as st

from verdant.services.recommendation_engine import build_context, evaluate
from verdant.domain.common import utcnow

from .common import Page, ago, badge, esc, notify, run_safely
from .calendar import task_row


def forecast_panel(page: Page):
    snapshots = page.weather.cached(page.gid)
    st.subheader("Forecast")
    if not page.garden.has_coordinates:
        st.info("Weather unavailable: set this garden's location in Settings to see a forecast.")
        return
    if not snapshots:
        st.info("No forecast fetched yet. Use **Check weather & advice** below.")
        return
    first = snapshots[0]
    stale = utcnow() >= first.expires_at
    st.caption(f"{first.provider} · fetched {ago(first.fetched_at)} · °{first.temp_unit}, {first.precip_unit}, "
               f"{first.wind_unit}" + (" · **out of date**" if stale else ""))
    rows = [{"Day": f"{s.forecast_for:%a %b %d}",
             "Low": "—" if s.min_temperature is None else f"{s.min_temperature:.0f}°",
             "High": "—" if s.temperature is None else f"{s.temperature:.0f}°",
             "Rain chance": "—" if s.precipitation_probability is None else f"{s.precipitation_probability:.0f}%",
             "Rain": "—" if s.precipitation_amount is None else f"{s.precipitation_amount:.2f} {s.precip_unit}",
             "Wind": "—" if s.wind_speed is None else f"{s.wind_speed:.0f} {s.wind_unit}"}
            for s in snapshots[:5]]
    st.dataframe(rows, hide_index=True)


def advisory_card(page: Page, rec):
    with st.container(border=True):
        st.markdown(badge(rec.severity.title(), rec.severity) + badge(rec.suitability.replace("_", " "), "info"),
                    unsafe_allow_html=True)
        st.markdown(f"**{esc(rec.title)}**")
        st.write(rec.explanation)
        with st.expander("Why? Evidence and limits"):
            if rec.evidence:
                st.dataframe([{"What": e.get("type", "").replace("_", " "), "Value": f"{e.get('value')} {e.get('unit', '')}".strip(),
                               "Origin": e.get("origin", ""), "Source": e.get("source", ""),
                               "For": e.get("for_date", "")} for e in rec.evidence],
                             hide_index=True)
            if rec.unknowns:
                st.markdown("**Unknown:** " + ", ".join(esc(u) for u in rec.unknowns))
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
    st.markdown(f"### {esc(g.display_name)}")
    st.caption(f"{g.location_label} · today is {page.today:%A, %B %d}")
    inventory = page.service.inventory(page.user_id, page.gid)
    plantings = page.service.plantings(page.user_id, page.gid)
    schedule = page.service.schedule(page.user_id, page.gid)
    today_tasks = schedule.tasks(on_date=page.today)
    c1, c2, c3 = st.columns(3)
    c1.metric("Seeds in library", len(inventory))
    c2.metric("Active plantings", len(plantings))
    c3.metric("Care tasks today", sum(not t.completed for t in today_tasks))

    forecast_panel(page)
    if st.button("Check weather & advice", key=page.key("refresh"), type="primary",
                 help="Fetches the forecast if the cached one has expired, then re-runs the advisory rules."):
        now = utcnow()
        ctx = build_context(page.service, page.weather, page.user_id, page.gid, page.today, now)
        stored = page.service.store_recommendations(page.user_id, page.gid, evaluate(ctx))
        message = ctx.forecast.message or f"Forecast {ctx.forecast.status}."
        notify(f"{message} {len(stored)} advisory item(s).", "info" if ctx.forecast.usable else "warning")

    st.subheader("Advice")
    recs = page.service.recommendations(page.user_id, page.gid)
    if not recs:
        st.caption("No open advice. Advice appears after a weather check and never changes your tasks on its own.")
    for rec in recs:
        advisory_card(page, rec)

    st.subheader("Today's care")
    for warning in schedule.conflicts(page.today):
        st.warning(warning)
    overdue = schedule.overdue(page.today)
    if overdue:
        st.warning(f"{len(overdue)} overdue task(s). Open Calendar to complete or reschedule them.")
    if not today_tasks:
        st.caption("Nothing scheduled today.")
    for task in today_tasks:
        task_row(page, task, "dash")

    st.subheader("Data quality")
    issues = []
    review = sum(1 for _, v in inventory if v.verification_status == "needs_review")
    if review:
        issues.append(f"{review} seed record(s) need review (uncertain names or cultivars).")
    expired = sum(1 for item, _ in inventory if item.is_expired(page.today))
    if expired:
        issues.append(f"{expired} seed packet(s) are past their expiry date.")
    if not g.has_coordinates:
        issues.append("No location coordinates, so forecasts and weather advice are off.")
    spaces = page.service.spaces(page.user_id, page.gid)
    unknown_exposure = [s.name for s in spaces if s.light_source != "grow_light" and s.exposure == "unknown"]
    if unknown_exposure:
        issues.append("Sun exposure unknown for: " + ", ".join(unknown_exposure) + ".")
    for issue in issues:
        st.markdown(f"- {esc(issue)}")
    if not issues:
        st.caption("No data-quality warnings.")
