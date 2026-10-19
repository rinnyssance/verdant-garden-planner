"""Exercise real Streamlit forms and session-state behavior."""

from pathlib import Path
from datetime import date, timedelta
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def button(app, label):
    return next(item for item in app.button if item.label == label)


def test_create_pet_task_plan_and_complete():
    app = AppTest.from_file(APP, default_timeout=30).run()
    assert not app.exception
    next(item for item in app.text_input if item.label == "Pet name").set_value("Biscuit")
    button(app, "Add pet").click().run()
    assert not app.exception
    assert app.session_state.owner.pets[0].name == "Biscuit"
    app.text_input(key="new_description").set_value("Morning walk")
    app.selectbox(key="new_frequency").set_value("daily")
    button(app, "Add task").click().run()
    assert not app.exception
    pet = app.session_state.owner.pets[0]
    assert len(pet.tasks) == 1
    button(app, "Generate schedule").click().run()
    assert not app.exception
    assert len(app.table) == 1
    button(app, "Complete").click().run()
    assert not app.exception
    pet = app.session_state.owner.pets[0]
    assert len(pet.tasks) == 2
    assert pet.tasks[0].completed
    assert pet.tasks[1].due_date == date.today() + timedelta(days=1)
    # A rerun must preserve the household and not create another recurrence.
    app.run()
    assert len(app.session_state.owner.pets[0].tasks) == 2


def test_demo_conflicts_filters_and_edit():
    app = AppTest.from_file(APP, default_timeout=30).run()
    button(app, "Load demo household").click().run()
    assert not app.exception
    assert any("overlaps" in item.value for item in app.warning)
    pet = app.session_state.owner.pets[1]
    next(item for item in app.selectbox if item.label == "Filter by pet").set_value(pet.id).run()
    assert len([item for item in app.button if item.label == "Complete"]) == 2
    task = pet.tasks[0]
    app.text_input(key=f"{task.id}_description").set_value("Breakfast updated")
    # Submit the edit form belonging to this specific occurrence.
    app.button(key=f"FormSubmitter:edit_{task.id}-Save changes").click().run()
    assert not app.exception
    assert app.session_state.owner.pets[1].tasks[0].description == "Breakfast updated"


def test_blank_pet_validation():
    app = AppTest.from_file(APP, default_timeout=30).run()
    button(app, "Add pet").click().run()
    assert not app.exception
    assert app.session_state.owner.pets == []
    assert any("cannot be blank" in item.value for item in app.error)
