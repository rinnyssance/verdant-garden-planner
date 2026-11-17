"""My Plants: plant cards with growth timeline, environment, care history and stage updates."""

from __future__ import annotations

import streamlit as st

from verdant.domain import SeedVariety
from verdant.domain.plantings import GROWTH_STAGES

from .common import STAGE_LABELS, Page, days_ago, html, notify, plant_photo, run_safely
from .theme import (SETTING_ICON, SETTING_LABEL, chip, empty_state, esc, illustration, page_header, section,
                    stage_bar, table)


def timeline(planting, today) -> str:
    steps = [("Sown", planting.sown_on), ("Germinated", planting.germinated_on),
             ("Transplanted", planting.transplanted_on)]
    parts = []
    for label, day in steps:
        state = "done" if day else ""
        when = f"{day:%b %d}" if day else "not recorded"
        parts.append(f'<div class="step {state}"><b>{label}</b>{when}</div>')
    parts.append(f'<div class="step done"><b>Now</b>{STAGE_LABELS[planting.growth_stage]}</div>')
    return f'<div class="vd-timeline">{"".join(parts)}</div>'


def environment(space) -> str:
    if space is None:
        return ""
    rows = {"Setting": SETTING_LABEL[space.setting], "Method": space.growing_method.replace("_", " "),
            "Light": space.light_source.replace("_", " "), "Exposure": space.exposure.replace("_", " ")}
    if space.estimated_direct_sun_hours is not None:
        rows["Direct sun"] = f"~{space.estimated_direct_sun_hours:g} h (your estimate)"
    if space.uses_grow_light:
        rows["Grow light"] = (f"{space.grow_light_hours:g} h/day" if space.grow_light_hours is not None else "hours unknown") + \
            (f" · PPFD {space.grow_light_ppfd:g}" if space.grow_light_ppfd is not None else " · PPFD unknown")
    if space.soil_medium:
        rows["Medium"] = space.soil_medium
    return '<dl class="vd-kv">' + "".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in rows.items()) + "</dl>"


def render(page: Page):
    html(page_header("My Plants", "What's growing",
                     "Each planting with its stage, growing conditions, care history and journal notes."))
    show_archived = st.toggle("Show archived", key=page.key("show_archived"))
    plantings = page.service.plantings(page.user_id, page.gid, status=None if show_archived else "active")
    if not plantings:
        st.info("No plantings yet. Open the Seed Library and choose **Start planting** on a seed.")
        return
    spaces = {s.id: s for s in page.service.spaces(page.user_id, page.gid)}
    space_names = {sid: s.name for sid, s in spaces.items()}
    tasks = page.service.tasks(page.user_id, page.gid)
    for p in plantings:
        variety = page.service.repo.get(SeedVariety, p.seed_variety_id)
        name = p.nickname or variety.label
        space = spaces.get(p.growing_space_id)
        observations = page.service.observations(page.user_id, page.gid, p.id)
        history = [t for t in tasks if t.planting_id == p.id]
        with page.card(f"planting-{p.id}"):
            art, body = st.columns([2, 5], gap="medium")
            with art:
                photo = plant_photo(page, p.id)
                if photo:
                    st.image(photo, caption="Latest journal photo")
                else:
                    html(illustration(variety.category, variety.crop_key, p.id[:8], name))
            with body:
                chips = chip(STAGE_LABELS[p.growth_stage])
                if space:
                    chips += chip(f"{SETTING_LABEL[space.setting]} · {space.name}",
                                  "" if space.setting in ("indoor", "greenhouse") else "warm", SETTING_ICON[space.setting])
                if p.status == "archived":
                    chips += chip("archived", "out")
                cultivar = f'<div class="vd-cultivar">{esc(variety.cultivar)}</div>' if variety.cultivar and p.nickname else ""
                html(f'<div class="vd-title" style="font-size:1.35rem">{esc(name)}</div>{cultivar}'
                     f'<div style="margin-top:.35rem">{chips}</div>'
                     f'<div class="vd-meta">{p.quantity} plant{"s" if p.quantity != 1 else ""} · '
                     f'{len(observations)} journal entr{"y" if len(observations) == 1 else "ies"} · '
                     f'{sum(t.completed for t in history)} care task(s) done</div>'
                     f'{stage_bar(p.growth_stage, GROWTH_STAGES)}{timeline(p, page.today)}')
            if p.notes:
                html(f'<div class="vd-note-text" style="margin-top:.6rem">“{esc(p.notes)}”</div>')
            env_col, care_col = st.columns(2, gap="large")
            with env_col:
                html(section("Growing conditions", "sun"))
                html(environment(space) or empty_state("No space recorded", "", "bed"))
            with care_col:
                html(section("Recent care", "task"))
                if history:
                    html(table([{"Date": f"{t.due_date:%b %d}", "Task": t.description,
                                 "Status": "done" if t.completed else "pending"} for t in history[-5:]]))
                else:
                    html(empty_state("No care recorded", " Add tasks for this plant in the Calendar.", "task"))
                if observations:
                    last = observations[-1]
                    html(f'<div class="vd-meta">Last journal entry {days_ago(last.observed_at.date(), page.today)}'
                         + (f" · height {last.height_cm:g} cm" if last.height_cm is not None else "")
                         + (f" · soil {last.moisture_assessment.replace('_', ' ')}" if last.moisture_assessment else "")
                         + "</div>")
            if p.status == "archived":
                continue
            with st.expander("Update this planting", icon=":material/edit:"):
                with st.form(page.key(f"stage_{p.id}")):
                    a, b = st.columns(2)
                    stage = a.selectbox("Stage", GROWTH_STAGES, index=GROWTH_STAGES.index(p.growth_stage),
                                        format_func=STAGE_LABELS.get, key=page.key(f"stage_sel_{p.id}"))
                    sown = b.date_input("Sown on", p.sown_on, key=page.key(f"sown_{p.id}"))
                    germ = a.date_input("Germinated on", p.germinated_on, key=page.key(f"germ_{p.id}"))
                    trans = b.date_input("Transplanted on", p.transplanted_on, key=page.key(f"trans_{p.id}"))
                    space_id = st.selectbox("Space", list(space_names), index=list(space_names).index(p.growing_space_id),
                                            format_func=space_names.get, key=page.key(f"space_{p.id}"))
                    notes = st.text_area("Notes", p.notes, key=page.key(f"notes_{p.id}"))
                    if st.form_submit_button("Save", type="primary"):
                        run_safely(lambda: page.service.update_planting(
                            page.user_id, page.gid, p.id, growth_stage=stage, sown_on=sown, germinated_on=germ,
                            transplanted_on=trans, growing_space_id=space_id, notes=notes), "Planting updated.")
                c1, c2 = st.columns(2)
                if c1.button("Mark finished", key=page.key(f"finish_{p.id}")):
                    page.service.archive_planting(page.user_id, page.gid, p.id, finished=True)
                    notify(f"{name} finished and archived.")
                if c2.button("Archive", key=page.key(f"archive_{p.id}")):
                    page.service.archive_planting(page.user_id, page.gid, p.id, finished=False)
                    notify(f"{name} archived.")
