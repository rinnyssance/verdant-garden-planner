"""Garden Spaces: beds, containers, shelves and grow-light setups, with explicit light and exposure."""

from __future__ import annotations

import streamlit as st

from verdant.domain import SeedVariety
from verdant.domain.gardens import EXPOSURES, GROWING_METHODS, LIGHT_SOURCES, SETTINGS

from .common import Page, html, optional, run_safely
from .theme import METHOD_ICON, SETTING_ICON, SETTING_LABEL, chip, empty_state, esc, page_header, space_illustration

PRETTY = lambda value: value.replace("_", " ")  # noqa: E731


def space_fields(page: Page, prefix: str, space=None) -> dict:
    name = st.text_input("Name", space.name if space else "", placeholder="e.g. Sunny raised bed",
                         key=page.key(f"{prefix}_name"))
    a, b = st.columns(2)
    pick = lambda label, options, current, k: (a if k % 2 == 0 else b).selectbox(  # noqa: E731
        label, options, index=options.index(current) if current else 0, format_func=PRETTY,
        key=page.key(f"{prefix}_{label}"))
    setting = pick("Setting", SETTINGS, space.setting if space else "outdoor", 0)
    method = pick("Growing method", GROWING_METHODS, space.growing_method if space else "bed", 1)
    light = pick("Light source", LIGHT_SOURCES, space.light_source if space else "natural", 2)
    exposure = pick("Exposure", EXPOSURES, space.exposure if space else "unknown", 3)
    sun = a.number_input("Direct sun hours (estimate, optional)", 0.0, 24.0,
                         value=space.estimated_direct_sun_hours if space else None, step=0.5,
                         key=page.key(f"{prefix}_sun"))
    hours = b.number_input("Grow-light hours per day (optional)", 0.0, 24.0,
                           value=space.grow_light_hours if space else None, step=0.5, key=page.key(f"{prefix}_glh"))
    ppfd = a.number_input("Grow-light PPFD, µmol/m²/s (optional)", 0.0, 3000.0,
                          value=space.grow_light_ppfd if space else None, step=10.0, key=page.key(f"{prefix}_ppfd"),
                          help="From a light meter or the fixture's published data at plant height. "
                               "Leave empty if unknown; Verdant will not guess it.")
    soil = b.text_input("Soil / medium (optional)", (space.soil_medium or "") if space else "",
                        key=page.key(f"{prefix}_soil"))
    irrigation = a.text_input("Watering method (optional)", (space.irrigation_method or "") if space else "",
                              key=page.key(f"{prefix}_irr"))
    notes = st.text_area("Notes", space.notes if space else "", key=page.key(f"{prefix}_notes"))
    return dict(name=name, setting=setting, growing_method=method, light_source=light, exposure=exposure,
                estimated_direct_sun_hours=sun, grow_light_hours=hours, grow_light_ppfd=ppfd,
                soil_medium=optional(soil), irrigation_method=optional(irrigation), notes=notes)


def space_card(page: Page, space, plants: list[str]):
    with page.card(f"space-{space.id}"):
        html(space_illustration(space, space.id[:8]))
        weather_note = ("Gets outdoor rain and frost" if space.setting == "outdoor"
                        else "Sheltered from rain; outdoor cold can reach it" if space.setting == "covered"
                        else "Sheltered from outdoor rain and frost")
        chips = (chip(SETTING_LABEL[space.setting], "" if space.setting in ("indoor", "greenhouse") else "warm",
                      SETTING_ICON[space.setting])
                 + chip(PRETTY(space.growing_method), "ink", METHOD_ICON[space.growing_method])
                 + chip(PRETTY(space.exposure), "out", "sun"))
        light = PRETTY(space.light_source)
        if space.uses_grow_light:
            light += (f" · {space.grow_light_hours:g} h/day" if space.grow_light_hours is not None else " · hours unknown")
            light += (f" · PPFD {space.grow_light_ppfd:g}" if space.grow_light_ppfd is not None else " · PPFD unknown")
        rows = {"Light": light, "Weather": weather_note}
        if space.estimated_direct_sun_hours is not None:
            rows["Direct sun"] = f"~{space.estimated_direct_sun_hours:g} h (your estimate)"
        if space.soil_medium:
            rows["Medium"] = space.soil_medium
        if space.irrigation_method:
            rows["Watering"] = space.irrigation_method
        rows["Growing here"] = ", ".join(plants) if plants else "nothing yet"
        html(f'<div class="vd-title">{esc(space.name)}</div><div style="margin-top:.35rem">{chips}</div>'
             '<dl class="vd-kv">' + "".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in rows.items()) + "</dl>"
             + (f'<div class="vd-meta">{esc(space.notes)}</div>' if space.notes else ""))
        with st.expander("Edit space", icon=":material/edit:"):
            with st.form(page.key(f"edit_space_{space.id}")):
                values = space_fields(page, f"edit_{space.id}", space)
                if st.form_submit_button("Save space", type="primary"):
                    run_safely(lambda: page.service.update_space(page.user_id, page.gid, space.id, **values),
                               "Space updated.")


def render(page: Page):
    spaces = page.service.spaces(page.user_id, page.gid)
    html(page_header("Garden Spaces", "Where things grow",
                     "Beds, containers, shelves and grow-light setups. Setting and light decide which weather advice applies."))
    with st.expander("Add a growing space", expanded=not spaces, icon=":material/add:"):
        with st.form(page.key("add_space"), clear_on_submit=True):
            values = space_fields(page, "new_space")
            if st.form_submit_button("Add space", type="primary"):
                name = values.pop("name")
                run_safely(lambda: page.service.add_space(page.user_id, page.gid, name, **values), "Space added.")
    if not spaces:
        html(empty_state("No spaces yet", " Add an indoor shelf, grow-light station, sunny bed or shaded porch.", "bed"))
        return
    plants: dict[str, list[str]] = {}
    for p in page.service.plantings(page.user_id, page.gid):
        variety = page.service.repo.get(SeedVariety, p.seed_variety_id)
        plants.setdefault(p.growing_space_id, []).append(p.nickname or (variety.label if variety else "Planting"))
    cols = st.columns(3, gap="medium")
    for index, space in enumerate(spaces):
        with cols[index % 3]:
            space_card(page, space, plants.get(space.id, []))
