"""Field Journal: an editorial notebook of dated observations; charts only with enough real data."""

from __future__ import annotations

from datetime import datetime, time, timezone

import streamlit as st

from verdant.domain import SeedVariety
from verdant.domain.observations import MOISTURE
from verdant.services.photos import photo_belongs_to, save_photo

from .common import Page, html, optional, run_safely
from .theme import FOREST, chip, empty_state, esc, page_header, section

MIN_CHART_POINTS = 3


def entry(page: Page, obs):
    with page.card(f"obs-{obs.id}"):
        has_photo = photo_belongs_to(obs.photo_path, page.gid)
        text_col, photo_col = st.columns([3, 2], gap="medium") if has_photo else (st.container(), None)
        with text_col:
            origin = chip("measured with an instrument", "ink", "ruler") if obs.data_origin == "instrument_measured" \
                else chip("observed by you", "out", "book")
            facts = ""
            if obs.height_cm is not None:
                facts += chip(f"{obs.height_cm:g} cm tall", "", "ruler")
            if obs.leaf_count is not None:
                facts += chip(f"{obs.leaf_count} leaves", "", "leaf")
            if obs.moisture_assessment:
                facts += chip(f"soil {obs.moisture_assessment.replace('_', ' ')}", "ink", "drop")
            body = ""
            if obs.notes:
                body += f'<div class="vd-note-text">{esc(obs.notes)}</div>'
            for label, value in (("Symptoms", obs.symptoms), ("Light", obs.light_notes)):
                if value:
                    body += f'<div class="vd-meta"><b>{label}:</b> {esc(value)}</div>'
            html(f'<div class="vd-entry"><div class="vd-date"><div class="mm">{obs.observed_at:%b}</div>'
                 f'<div class="dd">{obs.observed_at:%d}</div><div class="tt">{obs.observed_at:%Y · %H:%M}</div></div>'
                 f'<div><div>{origin}{facts}</div><div style="margin-top:.5rem">{body}</div></div></div>')
        if photo_col is not None:
            with photo_col:
                st.image(obs.photo_path, caption=f"{obs.observed_at:%b %d, %Y}")


def render(page: Page):
    html(page_header("Field Journal", "Notes from the garden",
                     "Dated observations and photos. Your estimates and instrument readings stay clearly labelled."))
    plantings = page.service.plantings(page.user_id, page.gid)
    if not plantings:
        st.info("Start a planting first; journal entries belong to a planting.")
        return
    names = {p.id: p.nickname or page.service.repo.get(SeedVariety, p.seed_variety_id).label for p in plantings}
    chosen = st.selectbox("Planting", list(names), format_func=names.get, key=page.key("journal_planting"))
    with st.expander("Write an entry", expanded=False, icon=":material/edit_note:"):
        with st.form(page.key("add_obs"), clear_on_submit=True):
            a, b = st.columns(2)
            day = a.date_input("Date", page.today, key=page.key("obs_day"))
            at = b.time_input("Time", time(9), key=page.key("obs_time"))
            height = a.number_input("Height (cm, optional)", 0.0, 2000.0, value=None, step=0.5, key=page.key("obs_h"))
            leaves = b.number_input("Leaf count (optional)", 0, 100000, value=None, step=1, key=page.key("obs_leaves"))
            moisture = a.selectbox("Soil moisture (your judgement)", ["", *MOISTURE],
                                   format_func=lambda m: m.replace("_", " ") or "Not checked", key=page.key("obs_moist"))
            origin = b.radio("These values are", ["user_observed", "instrument_measured"],
                             format_func=lambda o: "observed / estimated by me" if o == "user_observed" else "measured with an instrument",
                             key=page.key("obs_origin"))
            symptoms = st.text_input("Symptoms (optional)", key=page.key("obs_symptoms"),
                                     help="Describe what you see. Verdant does not diagnose plant disease.")
            light = st.text_input("Light notes (optional)", key=page.key("obs_light"))
            notes = st.text_area("Notes", key=page.key("obs_notes"))
            photo = st.file_uploader("Photo (optional)", type=["png", "jpg", "jpeg", "webp"], key=page.key("obs_photo"))
            if st.form_submit_button("Save entry", type="primary"):
                def add():
                    path = save_photo(page.gid, photo.getvalue()) if photo else None
                    return page.service.add_observation(
                        page.user_id, page.gid, chosen,
                        observed_at=datetime.combine(day, at).replace(tzinfo=timezone.utc), height_cm=height,
                        leaf_count=None if leaves is None else int(leaves), moisture_assessment=optional(moisture),
                        light_notes=optional(light), symptoms=optional(symptoms), notes=notes, photo_path=path,
                        data_origin=origin)
                run_safely(add, "Journal entry saved.")

    observations = page.service.observations(page.user_id, page.gid, chosen)
    heights = [(o.observed_at, o.height_cm) for o in observations if o.height_cm is not None]
    html(section("Growth", "ruler"))
    if len(heights) >= MIN_CHART_POINTS:
        st.line_chart({"Date": [t.date() for t, _ in heights], "Height (cm)": [h for _, h in heights]},
                      x="Date", y="Height (cm)", x_label="Date", y_label="cm", color=FOREST)
        st.caption("Chart shows only recorded heights; days without entries are not filled in.")
    else:
        html(empty_state("Not enough measurements for a chart yet",
                         f" A height chart appears after {MIN_CHART_POINTS} height entries (currently {len(heights)}).", "ruler"))
    html(section("Entries", "book", f"{len(observations)} for {names[chosen]}, newest first."))
    if not observations:
        st.info("No journal entries for this planting yet.")
    for obs in reversed(observations):
        entry(page, obs)
