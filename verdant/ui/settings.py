"""Settings: garden details and location, add gardens, import the packet list."""

from __future__ import annotations

import streamlit as st

from verdant.services.inventory import import_initial_inventory, load_initial_inventory
from verdant.services.weather import WeatherUnavailable

from .common import Page, notify, optional, run_safely


def location_search(page: Page, geocoder):
    st.markdown("**Find location**")
    st.caption("Search by city (or city and region). Coordinates are rounded to about 1 km and only used for "
               "forecasts; they are not shown elsewhere in the app.")
    a, b = st.columns([3, 1])
    query = a.text_input("City", key=page.key("geo_q"), placeholder="e.g. Richmond, Virginia",
                         label_visibility="collapsed")
    if b.button("Search", key=page.key("geo_go")):
        try:
            st.session_state[page.key("geo_results")] = geocoder.search(query.split(",")[0])
        except WeatherUnavailable:
            st.error("Location search is unavailable right now. You can enter the city by hand below.")
    results = st.session_state.get(page.key("geo_results"))
    if results == []:
        st.caption("No matches.")
    if results:
        labels = [f"{r['city']}, {r['region']}, {r['country']}" for r in results]
        index = st.selectbox("Matches", range(len(results)), format_func=labels.__getitem__, key=page.key("geo_pick"))
        if st.button("Use this location", key=page.key("geo_use"), type="primary"):
            r = results[index]
            page.service.update_garden(page.user_id, page.gid, city=r["city"], region=r["region"],
                                       country=r["country"], latitude=r["latitude"], longitude=r["longitude"],
                                       timezone=r["timezone"])
            page.weather.clear(page.gid)
            st.session_state.pop(page.key("geo_results"), None)
            notify(f"Location set to {labels[index]}. Forecast cache cleared.")


def render(page: Page, geocoder):
    g = page.garden
    st.subheader("This garden")
    with st.form(page.key("garden_form")):
        name = st.text_input("Garden name", g.display_name, key=page.key("g_name"))
        a, b = st.columns(2)
        city = a.text_input("City", g.city, key=page.key("g_city"))
        region = b.text_input("State / region", g.region, key=page.key("g_region"))
        country = a.text_input("Country", g.country, key=page.key("g_country"))
        postal = b.text_input("ZIP / postal code (optional)", g.postal_code or "", key=page.key("g_postal"))
        tz = a.text_input("Time zone", g.timezone, key=page.key("g_tz"), help="IANA name, e.g. America/New_York")
        zone = b.text_input("Hardiness zone (optional)", g.zone_label or "", key=page.key("g_zone"),
                            help="Used for perennial winter survival only, never to set sowing dates.")
        zone_source = st.text_input("Zone source (required if a zone is entered)", g.zone_source or "",
                                    key=page.key("g_zone_src"), placeholder="e.g. USDA Plant Hardiness Zone Map lookup")
        if st.form_submit_button("Save garden"):
            run_safely(lambda: page.service.update_garden(
                page.user_id, page.gid, display_name=name, city=city, region=region, country=country,
                postal_code=optional(postal), timezone=tz.strip() or g.timezone, zone_label=optional(zone),
                zone_source=optional(zone_source)), "Garden saved.")
    st.caption("Forecast location: " + ("set" if g.has_coordinates else "not set — weather is off for this garden"))
    location_search(page, geocoder)

    st.subheader("Packet list import")
    entries = load_initial_inventory()["entries"]
    st.write(f"Adds the {len(entries)} candidate seed packets transcribed from your photos to **{g.display_name}**. "
             "Uncertain names are flagged *Needs review*. Nothing is planted and no tasks are created. "
             "Intended for your own garden; Mom's garden starts empty.")
    confirm = st.checkbox(f"Yes, import into {g.display_name}", key=page.key("import_confirm"))
    if st.button("Import packet list", key=page.key("import_go"), disabled=not confirm):
        result = import_initial_inventory(page.service, page.user_id, page.gid)
        notify(f"Imported {result['added']} seed record(s); {result['skipped']} already present.")

    st.subheader("Add another garden")
    with st.form("vd_add_garden", clear_on_submit=True):
        new_name = st.text_input("Garden name", placeholder="e.g. Mom's Garden", key="vd_new_garden_name")
        new_city = st.text_input("City (optional)", key="vd_new_garden_city")
        if st.form_submit_button("Create garden"):
            garden = run_safely(lambda: page.service.create_garden(page.user_id, new_name, city=new_city))
            if garden:
                st.session_state["vd_garden_next"] = garden.id  # applied before the selector renders
                notify(f"Created {garden.display_name}.")

    st.subheader("Privacy")
    st.caption("Data is stored on this computer in a local SQLite database. Photos are kept in a per-garden "
               "folder and are only shown inside that garden. Sign-in and sharing with family members are planned "
               "for a later phase.")
