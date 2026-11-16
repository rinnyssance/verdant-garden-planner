"""Field Journal: dated observations; charts only when there is enough real data."""

from __future__ import annotations

from datetime import datetime, time, timezone

import streamlit as st

from verdant.domain import SeedVariety
from verdant.domain.observations import MOISTURE
from verdant.services.photos import photo_belongs_to, save_photo

from .common import Page, esc, optional, run_safely

MIN_CHART_POINTS = 3


def render(page: Page):
    plantings = page.service.plantings(page.user_id, page.gid)
    if not plantings:
        st.info("Start a planting first; journal entries belong to a planting.")
        return
    names = {p.id: p.nickname or page.service.repo.get(SeedVariety, p.seed_variety_id).label for p in plantings}
    chosen = st.selectbox("Planting", list(names), format_func=names.get, key=page.key("journal_planting"))
    with st.expander("Add an entry", expanded=True):
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
    if len(heights) >= MIN_CHART_POINTS:
        st.line_chart({"Height (cm)": [h for _, h in heights]}, x_label="Entry", y_label="cm")
        st.caption("Chart shows only recorded heights; days without entries are not filled in.")
    else:
        st.caption(f"A height chart appears after {MIN_CHART_POINTS} height entries (currently {len(heights)}).")
    if not observations:
        st.info("No journal entries for this planting yet.")
    for obs in reversed(observations):
        with st.container(border=True):
            label = "measured" if obs.data_origin == "instrument_measured" else "observed"
            st.markdown(f"**{obs.observed_at:%Y-%m-%d %H:%M}** · {label}")
            facts = []
            facts += [f"height {obs.height_cm:g} cm"] if obs.height_cm is not None else []
            facts += [f"{obs.leaf_count} leaves"] if obs.leaf_count is not None else []
            facts += [f"soil {obs.moisture_assessment.replace('_', ' ')}"] if obs.moisture_assessment else []
            if facts:
                st.caption(" · ".join(facts))
            for label_text, value in (("Symptoms", obs.symptoms), ("Light", obs.light_notes)):
                if value:
                    st.markdown(f"*{label_text}:* {esc(value)}")
            if obs.notes:
                st.write(obs.notes)
            if photo_belongs_to(obs.photo_path, page.gid):
                st.image(obs.photo_path, width=260)
