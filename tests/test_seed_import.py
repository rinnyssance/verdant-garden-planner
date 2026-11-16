"""Candidate inventory import: primary garden only, flagged, idempotent, no plantings."""

from verdant.persistence import SQLiteRepository
from verdant.services.garden_service import GardenService
from verdant.services.inventory import import_initial_inventory, load_crop_reference, load_initial_inventory

ME = "local-operator"


def test_import_into_one_garden_only():
    service = GardenService(SQLiteRepository())
    service.ensure_user(ME)
    mine = service.create_garden(ME, "My Garden")
    moms = service.create_garden(ME, "Mom's Garden")
    result = import_initial_inventory(service, ME, mine.id)
    entries = load_initial_inventory()["entries"]
    assert result == {"added": len(entries), "skipped": 0} and len(entries) == 26
    assert service.inventory(ME, moms.id) == []
    assert service.plantings(ME, mine.id) == [] and service.tasks(ME, mine.id) == []
    again = import_initial_inventory(service, ME, mine.id)
    assert again == {"added": 0, "skipped": 26}
    assert len(service.inventory(ME, mine.id)) == 26


def test_uncertain_names_are_flagged_and_nothing_invented():
    service = GardenService(SQLiteRepository())
    service.ensure_user(ME)
    garden = service.create_garden(ME, "My Garden")
    import_initial_inventory(service, ME, garden.id)
    varieties = {v.label: v for _, v in service.inventory(ME, garden.id)}
    for label in ("Spinach 'Corenta Hybrid'", "Cauliflower 'Snowball X'", "Cucumber 'Straight Eight'",
                  "Watermelon 'Jubilee'", "Kale", "Bunching onion"):
        assert varieties[label].verification_status == "needs_review"
    for variety in varieties.values():
        assert variety.brand is None and variety.germination_days_min is None
        assert variety.maturity_days_min is None and variety.requirements_source is None
    items = [item for item, _ in service.inventory(ME, garden.id)]
    assert all(i.packet_count is None and i.acquired_on is None for i in items)


def test_every_imported_crop_has_reference_row():
    crops = load_crop_reference()["crops"]
    assert {e["crop_key"] for e in load_initial_inventory()["entries"]} <= set(crops)
    assert {row["frost_sensitivity"] for row in crops.values()} <= {"tender", "tolerant", "unknown"}
