"""Verdant Streamlit app. Run with: python -m streamlit run verdant_app.py

The original PawPal+ app (app.py) is unchanged and still runs on its own.
"""

from __future__ import annotations

import logging
import os

import streamlit as st

from verdant.persistence import SQLiteRepository
from verdant.services.fakes import FailingWeatherProvider
from verdant.services.garden_service import LOCAL_OPERATOR_ID, GardenService
from verdant.services.weather import OpenMeteoGeocoder, OpenMeteoProvider, WeatherService
from verdant.ui import calendar, dashboard, journal, plantings, seeds, settings, spaces
from verdant.ui.common import STYLE, Page, esc, garden_today, notify, run_safely, show_notice

logging.basicConfig(level=os.getenv("VERDANT_LOG_LEVEL", "INFO"),
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")

st.set_page_config(page_title="Verdant · Garden planner", page_icon="🌿", layout="wide")
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

st.markdown('<div class="vd-brand"><span class="vd-title">🌿 Verdant</span>'
            '<span class="vd-tag">Grow with knowledge. Care with confidence.</span></div>', unsafe_allow_html=True)
show_notice()

gardens = service.gardens(USER)
if not gardens:
    st.subheader("Set up your gardens")
    st.write("Each garden keeps its own seeds, spaces, plants, tasks and forecast. "
             "You can manage a family member's garden without them needing an account.")
    with st.form("vd_onboarding"):
        first = st.text_input("Your garden", "My Garden", key="vd_first_name")
        first_city = st.text_input("Its city (optional)", key="vd_first_city")
        second = st.text_input("Second garden (optional)", "Mom's Garden", key="vd_second_name")
        second_city = st.text_input("Its city (optional)", key="vd_second_city")
        if st.form_submit_button("Create gardens", type="primary"):
            def create():
                made = [service.create_garden(USER, first, city=first_city)]
                if second.strip():
                    made.append(service.create_garden(USER, second, city=second_city))
                return made
            made = run_safely(create)
            if made:
                st.session_state["vd_garden"] = made[0].id
                notify("Gardens created. Add a location in Settings to turn on weather.")
    st.stop()

ids = [g.id for g in gardens]
names = {g.id: g.display_name for g in gardens}
if st.session_state.get("vd_garden_next") in ids:
    st.session_state["vd_garden"] = st.session_state.pop("vd_garden_next")
if st.session_state.get("vd_garden") not in ids:
    st.session_state["vd_garden"] = ids[0]
garden_id = st.selectbox("Garden", ids, format_func=names.get, key="vd_garden",
                         help="Everything below — seeds, plants, tasks, weather and advice — belongs to this garden.")
garden = service.garden(USER, garden_id)
page = Page(service, weather, USER, garden, garden_today(garden))
st.caption(f"Viewing **{esc(garden.display_name)}** · {esc(garden.location_label)}")

# A stateful selector (unlike st.tabs) keeps you on the same screen after every save.
SECTIONS = {
    "Dashboard": dashboard.render,
    "Seed Library": seeds.render,
    "My Plants": plantings.render,
    "Garden Spaces": spaces.render,
    "Calendar": calendar.render,
    "Field Journal": journal.render,
    "Settings": lambda p: settings.render(p, geocoder),
}
if st.session_state.get("vd_nav") not in SECTIONS:
    st.session_state["vd_nav"] = "Dashboard"
section = st.segmented_control("Section", list(SECTIONS), key="vd_nav", required=True,
                               label_visibility="collapsed")
st.divider()
SECTIONS[section or "Dashboard"](page)
