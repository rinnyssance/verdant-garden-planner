"""Validation rules for the Verdant domain models."""

from datetime import date, datetime, timezone

import pytest

from verdant.domain import (Garden, GardenTask, GrowingSpace, Observation, Planting, Recommendation,
                            SeedInventoryItem, SeedVariety)

DAY = date(2026, 11, 16)


def test_garden_rounds_coordinates_and_requires_pairs():
    garden = Garden("My Garden", "u1", city="Richmond", region="VA", latitude=37.54123, longitude=-77.43611)
    assert (garden.latitude, garden.longitude) == (37.54, -77.44)
    assert garden.location_label == "Richmond, VA"
    with pytest.raises(ValueError):
        Garden("Bad", "u1", latitude=37.5)
    with pytest.raises(ValueError):
        Garden("Bad", "u1", zone_label="7b")  # zone without a source


def test_growing_space_does_not_invent_light_values():
    space = GrowingSpace("g", "Seed shelf", setting="indoor", light_source="grow_light", grow_light_hours=14)
    assert space.grow_light_ppfd is None and space.uses_grow_light
    assert not space.exposed_to_outdoor_weather
    with pytest.raises(ValueError):
        GrowingSpace("g", "Bed", light_source="natural", grow_light_hours=12)
    with pytest.raises(ValueError):
        GrowingSpace("g", "Bed", exposure="sunny")
    with pytest.raises(ValueError):
        GrowingSpace("g", "Bed", estimated_direct_sun_hours=30)
    covered = GrowingSpace("g", "Porch", setting="covered")
    assert covered.exposed_to_outdoor_temperature and not covered.exposed_to_outdoor_weather


def test_seed_facts_require_a_source():
    with pytest.raises(ValueError):
        SeedVariety("Basil", "herb", germination_days_min=5)
    variety = SeedVariety("Basil", "herb", cultivar="Genovese", germination_days_min=5,
                          germination_days_max=10, requirements_source="seed packet")
    assert variety.label == "Basil 'Genovese'"
    with pytest.raises(ValueError):
        SeedVariety("Basil", "herb", germination_days_min=12, germination_days_max=5,
                    requirements_source="seed packet")


def test_inventory_dates_and_counts():
    item = SeedInventoryItem("g", "v", packet_count=2, expiry_on=date(2026, 1, 1))
    assert item.is_expired(DAY)
    with pytest.raises(ValueError):
        SeedInventoryItem("g", "v", packet_count=-1)
    with pytest.raises(ValueError):
        SeedInventoryItem("g", "v", acquired_on=DAY, expiry_on=date(2026, 1, 1))


def test_planting_lifecycle_rules():
    assert not Planting("g", "s", "v").is_live  # planned: nothing in the ground yet
    live = Planting("g", "s", "v", growth_stage="seedling", sown_on=DAY)
    assert live.is_live
    with pytest.raises(ValueError):
        Planting("g", "s", "v", growth_stage="sown")  # no sowing date
    with pytest.raises(ValueError):
        Planting("g", "s", "v", sown_on=DAY, germinated_on=date(2026, 11, 1), growth_stage="germinating")
    with pytest.raises(ValueError):
        Planting("g", "s", "v", quantity=0)


def test_observation_needs_content_and_labels_origin():
    obs = Observation("g", "p", height_cm=4.5)
    assert obs.data_origin == "user_observed"
    with pytest.raises(ValueError):
        Observation("g", "p")
    with pytest.raises(ValueError):
        Observation("g", "p", notes="x", data_origin="sensor_guess")


def test_garden_task_reuses_pawpal_validation():
    task = GardenTask("g", "  Water bed ", DAY, "08:00")
    assert task.description == "Water bed"
    for bad in [dict(start_time="25:00"), dict(priority="urgent"), dict(recurrence="monthly"),
                dict(duration_minutes=0), dict(description=" ")]:
        values = dict(garden_id="g", description="Water", due_date=DAY)
        values.update(bad)
        with pytest.raises(ValueError):
            GardenTask(**values)
    with pytest.raises(ValueError):
        GardenTask("g", "Water", DAY, completed_at=datetime.now(timezone.utc))


def test_recommendation_requires_evidence_unless_insufficient():
    with pytest.raises(ValueError):
        Recommendation("g", "frost", "watch", "needs_adjustment", "T", "E", "k")
    rec = Recommendation("g", "grow_light", "info", "insufficient_data", "T", "E", "k")
    assert not rec.requires_user_approval
