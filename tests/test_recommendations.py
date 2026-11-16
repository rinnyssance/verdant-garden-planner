"""Deterministic advisory rules and explicit accept/dismiss."""

from datetime import date, datetime, timezone

import pytest

from verdant.domain import SeedVariety
from verdant.persistence import SQLiteRepository
from verdant.services.fakes import FailingWeatherProvider, FixedWeatherProvider
from verdant.services.garden_service import GardenService
from verdant.services.recommendation_engine import build_context, evaluate
from verdant.services.weather import WeatherService

DAY = date(2026, 11, 16)
NOW = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)
ME = "local-operator"


@pytest.fixture
def garden_setup():
    service = GardenService(SQLiteRepository())
    service.ensure_user(ME)
    garden = service.create_garden(ME, "My Garden", latitude=37.5, longitude=-77.4)
    return service, garden


def plant(service, garden, crop_key, name, setting="outdoor", stage="seedling", **space_attrs):
    space = service.add_space(ME, garden.id, f"{name} space", setting=setting, **space_attrs)
    item = service.add_seed(ME, garden.id, SeedVariety(name, "vegetable", crop_key=crop_key))
    sown = DAY if stage != "planned" else None
    return service.start_planting(ME, garden.id, item.id, space.id, growth_stage=stage, sown_on=sown), space


def run(service, garden, provider):
    ctx = build_context(service, WeatherService(service.repo, provider), ME, garden.id, DAY, NOW)
    return evaluate(ctx)


def by_category(recs, category):
    return [r for r in recs if r.category == category]


def test_frost_alert_for_tender_outdoor_crop_only(garden_setup):
    service, garden = garden_setup
    basil, _ = plant(service, garden, "basil", "Sweet basil")
    plant(service, garden, "kale", "Kale")                                    # tolerant
    plant(service, garden, "tomato", "Indoor tomato", setting="indoor")       # not exposed
    plant(service, garden, "pepper", "Planned pepper", stage="planned")      # not in the ground
    recs = by_category(run(service, garden, FixedWeatherProvider(DAY, [45, 31, 40])), "frost_risk")
    assert len(recs) == 1
    rec = recs[0]
    assert rec.planting_id == basil.id and rec.severity == "action" and rec.suitability == "needs_adjustment"
    low = next(e for e in rec.evidence if e["type"] == "forecast_low")
    assert (low["value"], low["unit"], low["for_date"], low["source"]) == (31, "F", "2026-11-17",
                                                                           "Scripted test forecast")
    assert "actual plant-level temperature" in rec.unknowns and "not validated" in rec.limitations
    assert rec.suggested_task["priority"] == "high"


def test_frost_watch_band_and_no_alert_when_mild(garden_setup):
    service, garden = garden_setup
    plant(service, garden, "tomato", "Tomato", setting="covered")
    [rec] = by_category(run(service, garden, FixedWeatherProvider(DAY, [35, 50, 50])), "frost_risk")
    assert rec.severity == "watch" and "cover may keep" in rec.limitations
    service.repo.conn.execute("DELETE FROM weather_snapshots")
    assert by_category(run(service, garden, FixedWeatherProvider(DAY, [37, 50, 50])), "frost_risk") == []


def test_unknown_sensitivity_reports_insufficient_data(garden_setup):
    service, garden = garden_setup
    plant(service, garden, "rosemary", "Rosemary")
    [rec] = by_category(run(service, garden, FixedWeatherProvider(DAY, [30, 30, 30])), "frost_risk")
    assert rec.suitability == "insufficient_data" and rec.suggested_task is None


def test_rain_suggests_checking_soil_and_never_completes_watering(garden_setup):
    service, garden = garden_setup
    _, bed = plant(service, garden, "bean", "Bean")
    plant(service, garden, "basil", "Indoor basil", setting="indoor")
    water = service.add_task(ME, garden.id, "Water bean bed", DAY, growing_space_id=bed.id)
    recs = by_category(run(service, garden, FixedWeatherProvider(DAY, [50, 50], rain_pct=[80, 0])),
                       "rain_soil_check")
    assert len(recs) == 1 and recs[0].growing_space_id == bed.id
    assert any(e["type"] == "pending_task" for e in recs[0].evidence)
    assert "not marked done" in recs[0].explanation
    assert service.tasks(ME, garden.id) == [water]  # untouched


def test_grow_light_without_ppfd_is_insufficient_data(garden_setup):
    service, garden = garden_setup
    service.add_space(ME, garden.id, "Seed shelf", setting="indoor", light_source="grow_light", grow_light_hours=14)
    service.add_space(ME, garden.id, "Measured shelf", setting="indoor", light_source="grow_light",
                      grow_light_hours=14, grow_light_ppfd=250)
    [rec] = by_category(run(service, garden, FixedWeatherProvider(DAY, [50])), "grow_light")
    assert rec.suitability == "insufficient_data" and rec.unknowns == ["light intensity (PPFD)"]
    assert "Seed shelf" in rec.title


def test_outage_pauses_weather_rules_and_says_so(garden_setup):
    service, garden = garden_setup
    plant(service, garden, "basil", "Basil")
    recs = run(service, garden, FailingWeatherProvider())
    assert [r.category for r in recs] == ["data_quality"]
    assert recs[0].suitability == "insufficient_data"


def test_evaluation_is_deterministic(garden_setup):
    service, garden = garden_setup
    plant(service, garden, "basil", "Basil")
    provider = FixedWeatherProvider(DAY, [30, 30, 30], rain_pct=[90, 0, 0])
    first = [(r.rule_key, r.title, r.explanation, r.evidence) for r in run(service, garden, provider)]
    second = [(r.rule_key, r.title, r.explanation, r.evidence) for r in run(service, garden, provider)]
    assert first == second and len(first) == 2


def test_accept_creates_one_task_dismiss_is_remembered(garden_setup):
    service, garden = garden_setup
    plant(service, garden, "basil", "Basil")
    provider = FixedWeatherProvider(DAY, [30, 30, 30], rain_pct=[90, 0, 0])
    stored = service.store_recommendations(ME, garden.id, run(service, garden, provider))
    assert service.tasks(ME, garden.id) == []  # nothing created automatically
    frost = next(r for r in stored if r.category == "frost_risk")
    rain = next(r for r in stored if r.category == "rain_soil_check")
    task = service.accept_recommendation(ME, garden.id, frost.id)
    again = service.accept_recommendation(ME, garden.id, frost.id)
    assert task.id == again.id and task.source == "suggested" and task.recommendation_id == frost.id
    assert len(service.tasks(ME, garden.id)) == 1
    service.dismiss_recommendation(ME, garden.id, rain.id)
    regenerated = service.store_recommendations(ME, garden.id, run(service, garden, provider))
    assert regenerated == []  # answered advice is not raised again
    assert service.recommendations(ME, garden.id, now=NOW) == []
    assert {r.status for r in service.recommendations(ME, garden.id, status=None)} == {"accepted", "dismissed"}


def test_other_garden_cannot_accept(garden_setup):
    service, garden = garden_setup
    other = service.create_garden(ME, "Mom's Garden")
    plant(service, garden, "basil", "Basil")
    [rec] = service.store_recommendations(ME, garden.id,
                                          by_category(run(service, garden, FixedWeatherProvider(DAY, [30])),
                                                      "frost_risk"))
    with pytest.raises(ValueError):
        service.accept_recommendation(ME, other.id, rec.id)
