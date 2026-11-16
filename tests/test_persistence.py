"""Garden data survives a reload and stays isolated per garden."""

from datetime import date, datetime, timezone

import pytest

from verdant.domain import GardenTask, Recommendation, SeedVariety
from verdant.persistence import SQLiteRepository
from verdant.services.garden_service import GardenService

DAY = date(2026, 11, 16)
ME = "local-operator"


def make(path):
    service = GardenService(SQLiteRepository(path))
    service.ensure_user(ME)
    return service


def test_full_round_trip_after_reopen(tmp_path):
    db = tmp_path / "verdant.db"
    service = make(db)
    garden = service.create_garden(ME, "My Garden", city="Richmond", region="VA", latitude=37.5, longitude=-77.4)
    space = service.add_space(ME, garden.id, "Sunny bed", setting="outdoor", exposure="full_sun",
                              estimated_direct_sun_hours=7.5)
    item = service.add_seed(ME, garden.id, SeedVariety("Basil", "herb", cultivar="Genovese"), packet_count=1)
    planting = service.start_planting(ME, garden.id, item.id, space.id, 4, growth_stage="sown", sown_on=DAY)
    task = service.add_task(ME, garden.id, "Water basil", DAY, start_time="08:00", recurrence="daily",
                            planting_id=planting.id)
    service.complete_task(ME, garden.id, task.id, DAY)
    service.add_observation(ME, garden.id, planting.id, height_cm=2.5,
                            observed_at=datetime(2026, 11, 16, 14, tzinfo=timezone.utc))
    service.repo.close()

    reopened = make(db)
    [g] = reopened.gardens(ME)
    assert (g.display_name, g.latitude, g.location_label) == ("My Garden", 37.5, "Richmond, VA")
    assert reopened.spaces(ME, g.id)[0].estimated_direct_sun_hours == 7.5
    [(inv, variety)] = reopened.inventory(ME, g.id)
    assert inv.packet_count == 1 and variety.label == "Basil 'Genovese'"
    [p] = reopened.plantings(ME, g.id)
    assert p.sown_on == DAY and p.quantity == 4
    tasks = reopened.tasks(ME, g.id)
    assert [t.completed for t in tasks] == [True, False]
    assert tasks[0].completed_at is not None and tasks[1].due_date == date(2026, 11, 17)
    [obs] = reopened.observations(ME, g.id)
    assert obs.height_cm == 2.5 and obs.observed_at.tzinfo is not None


def test_migration_is_idempotent(tmp_path):
    repo = SQLiteRepository(tmp_path / "v.db")
    assert repo.migrate() == 1 and repo.migrate() == 1


def test_listing_scoped_records_requires_garden(tmp_path):
    repo = SQLiteRepository(tmp_path / "v.db")
    with pytest.raises(ValueError):
        repo.list(GardenTask)
    with pytest.raises(ValueError):
        repo.delete_where(GardenTask, None)


def test_transaction_rolls_back_on_error(tmp_path):
    service = make(tmp_path / "v.db")
    garden = service.create_garden(ME, "My Garden")
    with pytest.raises(RuntimeError):
        with service.repo.transaction():
            service.repo.save(GardenTask(garden.id, "Should vanish", DAY))
            raise RuntimeError("boom")
    assert service.tasks(ME, garden.id) == []


def test_json_fields_round_trip(tmp_path):
    service = make(tmp_path / "v.db")
    garden = service.create_garden(ME, "My Garden")
    rec = Recommendation(garden.id, "frost", "watch", "needs_adjustment", "T", "E", "frost:x",
                         evidence=[{"type": "forecast_low", "value": 34.0}], unknowns=["plant temp"],
                         suggested_task={"description": "Cover", "due_date": "2026-11-16"})
    service.store_recommendations(ME, garden.id, [rec])
    [back] = service.recommendations(ME, garden.id, now=datetime(2026, 11, 16, tzinfo=timezone.utc))
    assert back.evidence[0]["value"] == 34.0 and back.unknowns == ["plant temp"]
    assert back.suggested_task["description"] == "Cover"


def test_two_gardens_do_not_cross_contaminate(tmp_path):
    service = make(tmp_path / "v.db")
    mine = service.create_garden(ME, "My Garden", city="Richmond")
    moms = service.create_garden(ME, "Mom's Garden", city="Norfolk")
    mine_space = service.add_space(ME, mine.id, "Bed")
    service.add_seed(ME, mine.id, SeedVariety("Carrot", "vegetable"))
    service.add_task(ME, mine.id, "Weed", DAY)
    assert service.inventory(ME, moms.id) == []
    assert service.tasks(ME, moms.id) == [] and service.spaces(ME, moms.id) == []
    [(item, _)] = service.inventory(ME, mine.id)
    with pytest.raises(ValueError):  # a seed from my garden cannot be planted in Mom's
        service.start_planting(ME, moms.id, item.id, mine_space.id)
    with pytest.raises(ValueError):  # a task cannot point at another garden's space
        service.add_task(ME, moms.id, "Water", DAY, growing_space_id=mine_space.id)
