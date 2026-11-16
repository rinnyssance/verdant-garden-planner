"""Drive the real Verdant Streamlit app (offline weather, temporary database)."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from verdant.persistence import SQLiteRepository
from verdant.services.garden_service import LOCAL_OPERATOR_ID, GardenService

APP = str(Path(__file__).resolve().parents[1] / "verdant_app.py")


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("VERDANT_DB_PATH", str(tmp_path / "verdant.db"))
    monkeypatch.setenv("VERDANT_PHOTO_DIR", str(tmp_path / "photos"))
    monkeypatch.setenv("VERDANT_WEATHER", "offline")
    return tmp_path


def start():
    app = AppTest.from_file(APP, default_timeout=60).run()
    assert not app.exception, app.exception
    return app


def click(app, label, index=0):
    [item for item in app.button if item.label == label][index].click().run()
    assert not app.exception, app.exception
    return app


def onboard():
    app = start()
    click(app, "Create gardens")
    return app


def go(app, section):
    app.session_state["vd_nav"] = section
    app.run()
    assert not app.exception, app.exception
    return app


def gardens(tmp_path):
    repo = SQLiteRepository(tmp_path / "verdant.db")
    try:
        return GardenService(repo).gardens(LOCAL_OPERATOR_ID)
    finally:
        repo.close()


def test_onboarding_creates_two_separate_gardens(env):
    app = onboard()
    assert [g.display_name for g in gardens(env)] == ["My Garden", "Mom's Garden"]
    assert app.selectbox(key="vd_garden").options == ["My Garden", "Mom's Garden"]
    go(app, "Seed Library")
    assert any("seed library is empty" in i.value for i in app.info)


def test_import_only_into_selected_garden_and_reload(env):
    app = onboard()
    gid = app.session_state["vd_garden"]
    go(app, "Settings")
    app.checkbox(key=f"{gid}:import_confirm").check().run()
    click(app, "Import packet list")
    assert any("Imported 26" in s.value for s in app.success)
    assert app.session_state["vd_nav"] == "Settings"  # stays on the same screen after saving
    go(app, "Seed Library")
    assert any("Showing 26 of 26" in c.value for c in app.caption)
    # A fresh session on the same database sees the same data (durable storage).
    again = go(start(), "Seed Library")
    assert any("Showing 26 of 26" in c.value for c in again.caption)
    # Mom's garden is untouched.
    other = [g.id for g in gardens(env) if g.id != gid][0]
    again.session_state["vd_garden"] = other
    again.run()
    assert not again.exception and again.session_state["vd_garden"] == other
    assert any("seed library is empty" in i.value for i in again.info)


def test_space_planting_task_and_recurrence(env):
    app = onboard()
    gid = app.session_state["vd_garden"]
    go(app, "Garden Spaces")
    app.text_input(key=f"{gid}:new_space_name").input("Seed shelf")
    app.selectbox(key=f"{gid}:new_space_Setting").set_value("indoor")
    app.selectbox(key=f"{gid}:new_space_Light source").set_value("grow_light")
    app.number_input(key=f"{gid}:new_space_glh").set_value(14.0)
    click(app, "Add space")
    go(app, "Seed Library")
    app.text_input(key=f"{gid}:seed_name").input("Basil")
    app.selectbox(key=f"{gid}:seed_crop").set_value("basil")
    click(app, "Add to library")
    click(app, "Start planting")
    assert any("Planting started" in s.value for s in app.success)
    go(app, "Calendar")
    app.text_input(key=f"{gid}:new_desc").input("Mist basil")
    app.selectbox(key=f"{gid}:new_rep").set_value("daily")
    click(app, "Add task")
    completes = [b for b in app.button if b.label == "Complete"]
    assert completes
    completes[0].click().run()
    assert not app.exception
    assert any("Next:" in s.value for s in app.success)


def test_offline_advice_is_explicit_and_accept_adds_task(env):
    app = onboard()
    gid = app.session_state["vd_garden"]
    go(app, "Garden Spaces")
    app.text_input(key=f"{gid}:new_space_name").input("Grow station")
    app.selectbox(key=f"{gid}:new_space_Light source").set_value("grow_light")
    app.selectbox(key=f"{gid}:new_space_Setting").set_value("indoor")
    click(app, "Add space")
    go(app, "Dashboard")
    click(app, "Check weather & advice")
    assert any("Weather unavailable" in w.value for w in app.warning)
    assert any("Add grow-light details" in m.value for m in app.markdown)
    click(app, "Add suggested task")
    assert any("Added to calendar" in s.value for s in app.success)
    assert not [m for m in app.markdown if "Add grow-light details" in m.value]


def test_sample_gardens_button_for_visitors(env):
    app = start()
    click(app, "Load sample gardens")
    names = [g.display_name for g in gardens(env)]
    assert names == ["My Garden (sample)", "Mom's Garden (sample)"]
    assert any("Sample gardens loaded" in s.value for s in app.success)
    go(app, "My Plants")
    assert any("Sweet basil" in m.value for m in app.markdown)
    # Mom's sample garden has its own task and no seeds.
    moms = [g.id for g in gardens(env)][1]
    app.session_state["vd_garden"] = moms
    go(app, "Seed Library")
    assert any("seed library is empty" in i.value for i in app.info)
