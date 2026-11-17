"""Verdant Streamlit app. Run with: python -m streamlit run verdant_app.py

The original PawPal+ app (app.py) is unchanged and still runs on its own.
"""

from __future__ import annotations

import logging
import os
from datetime import date

import streamlit as st

from verdant.persistence import SQLiteRepository
from verdant.services.demo import load_demo
from verdant.services.fakes import FailingWeatherProvider
from verdant.services.garden_service import LOCAL_OPERATOR_ID, GardenService
from verdant.services.weather import OpenMeteoGeocoder, OpenMeteoProvider, WeatherService
from verdant.ui import calendar, dashboard, journal, plantings, seeds, settings, spaces
from verdant.ui.common import STYLE, Page, esc, garden_today, html, notify, run_safely, show_notice
from verdant.ui.theme import illustration, logo, page_header

logging.basicConfig(level=os.getenv("VERDANT_LOG_LEVEL", "INFO"),
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")

st.set_page_config(page_title="Verdant · Garden planner", page_icon="🌿", layout="wide",
                   initial_sidebar_state="auto")
st.markdown(STYLE, unsafe_allow_html=True)


@st.cache_resource
def services(db_path: str, weather_mode: str):
    repo = SQLiteRepository(db_path)
    service = GardenService(repo)
    service.ensure_user(LOCAL_OPERATOR_ID, "Garden operator")
    provider = FailingWeatherProvider() if weather_mode == "offline" else OpenMeteoProvider()
    return service, WeatherService(repo, provider)


DB_PATH = os.getenv("VERDANT_DB_PATH", "data/verdant.db")
WEATHER_MODE = os.getenv("VERDANT_WEATHER", "open-meteo")
service, weather = services(DB_PATH, WEATHER_MODE)
geocoder = OpenMeteoGeocoder() if WEATHER_MODE != "offline" else type(
    "OfflineGeocoder", (), {"search": lambda self, name, count=5: []})()
USER = LOCAL_OPERATOR_ID

# Section name -> (Material icon, render function). Icons are Streamlit's built-in Material Symbols.
SECTIONS = {
    "Overview": (":material/dashboard:", dashboard.render),
    "My Plants": (":material/potted_plant:", plantings.render),
    "Seed Library": (":material/inventory_2:", seeds.render),
    "Garden Spaces": (":material/yard:", spaces.render),
    "Calendar": (":material/calendar_month:", calendar.render),
    "Field Journal": (":material/menu_book:", journal.render),
    "Settings": (":material/settings:", lambda p: settings.render(p, geocoder)),
}

with st.sidebar:
    html(f'<div style="display:flex;gap:.7rem;align-items:center;margin-top:.2rem">{logo(38)}'
         '<div><div class="vd-brand-name">Verdant</div>'
         '<div class="vd-brand-tag">Grow with knowledge. Care with confidence.</div></div></div>')

gardens = service.gardens(USER)
if not gardens:
    with st.sidebar:
        html('<div class="vd-side-foot">Create a garden or load the sample gardens to begin.</div>')
    show_notice()
    html(page_header("Welcome", "Your garden companion",
                     "Keep each garden's seeds, growing spaces, plants, care and weather in one calm place. "
                     "Advice is explained, cites its evidence, and never changes your plans without you."))
    left, right = st.columns([3, 2], gap="large")
    with right:
        html(illustration("herb", "basil", "welcome", "a young basil plant"))
    with left:
        html('<div class="vd-h2">Take a quick tour</div><div class="vd-sub">Two sample gardens in Richmond and '
             'Norfolk, Virginia, with seeds, spaces, plants, tasks and a journal entry. Then open '
             'Overview → Check weather &amp; advice for live, explained advice.</div>')
        if st.button("Load sample gardens", type="primary", key="vd_demo", icon=":material/eco:"):
            made = load_demo(service, USER, date.today())
            if made:
                st.session_state["vd_garden_next"] = made[0].id
            notify("Sample gardens loaded. Try Overview → Check weather & advice.")
    html('<div class="vd-h2">Or set up your own gardens</div><div class="vd-sub">Each garden keeps its own seeds, '
         "spaces, plants, tasks and forecast. You can manage a family member's garden without them needing an account.</div>")
    with st.form("vd_onboarding"):
        a, b = st.columns(2)
        first = a.text_input("Your garden", "My Garden", key="vd_first_name")
        first_city = b.text_input("Its city (optional)", key="vd_first_city")
        second = a.text_input("Second garden (optional)", "Mom's Garden", key="vd_second_name")
        second_city = b.text_input("Its city (optional)", key="vd_second_city")
        if st.form_submit_button("Create gardens", type="primary"):
            def create():
                made = [service.create_garden(USER, first, city=first_city)]
                if second.strip():
                    made.append(service.create_garden(USER, second, city=second_city))
                return made
            made = run_safely(create)
            if made:
                st.session_state["vd_garden_next"] = made[0].id
                notify("Gardens created. Add a location in Settings to turn on weather.")
    st.stop()

ids = [g.id for g in gardens]
names = {g.id: g.display_name for g in gardens}
if st.session_state.get("vd_garden_next") in ids:
    st.session_state["vd_garden"] = st.session_state.pop("vd_garden_next")
if st.session_state.get("vd_garden") not in ids:
    st.session_state["vd_garden"] = ids[0]
if st.session_state.get("vd_nav") not in SECTIONS:
    st.session_state["vd_nav"] = "Overview"

with st.sidebar:
    html('<div class="vd-side-label">Garden</div>')
    garden_id = st.selectbox("Garden", ids, format_func=names.get, key="vd_garden", label_visibility="collapsed",
                             help="Everything — seeds, plants, tasks, weather and advice — belongs to this garden.")
    garden = service.garden(USER, garden_id)
    html(f'<div class="vd-brand-tag">{esc(garden.location_label)}</div>')
    html('<div class="vd-side-label">Navigate</div>')
    section = st.radio("Navigate", list(SECTIONS), key="vd_nav", label_visibility="collapsed",
                       format_func=lambda name: f"{SECTIONS[name][0]}  {name}")
    html('<div class="vd-side-foot">Advice is rule-based and cites its evidence. '
         'Forecasts by Open-Meteo.com. Nothing in your calendar changes until you accept it.</div>')

page = Page(service, weather, USER, garden, garden_today(garden))
html(f'<div class="vd-mobilebar"><span>↖ Menu</span><span>{esc(section)} · <b>{esc(garden.display_name)}</b></span></div>')
show_notice()
SECTIONS[section][1](page)
