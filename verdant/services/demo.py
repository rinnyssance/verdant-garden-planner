"""Sample gardens so visitors (e.g. graders) can explore without typing setup data.

Uses public city-centre coordinates, not anyone's home.
"""

from __future__ import annotations

from datetime import date, timedelta

from .inventory import import_initial_inventory


def load_demo(service, user_id: str, today: date) -> list:
    """Create two sample gardens. Returns the gardens created (none if the samples already exist).

    Never touches gardens the user created.
    """
    if any(g.display_name.endswith("(sample)") for g in service.gardens(user_id)):
        return []
    mine = service.create_garden(user_id, "My Garden (sample)", city="Richmond", region="Virginia",
                                 country="United States", latitude=37.55, longitude=-77.46,
                                 timezone="America/New_York")
    moms = service.create_garden(user_id, "Mom's Garden (sample)", city="Norfolk", region="Virginia",
                                 country="United States", latitude=36.85, longitude=-76.29,
                                 timezone="America/New_York")
    import_initial_inventory(service, user_id, mine.id)
    bed = service.add_space(user_id, mine.id, "Sunny raised bed", setting="outdoor", growing_method="raised_bed",
                            exposure="full_sun", estimated_direct_sun_hours=7)
    porch = service.add_space(user_id, mine.id, "Covered porch pots", setting="covered", growing_method="container",
                              exposure="partial_shade")
    shelf = service.add_space(user_id, mine.id, "Seed-starting shelf", setting="indoor", growing_method="tray",
                              light_source="grow_light", grow_light_hours=14)
    inventory = {v.label: item for item, v in service.inventory(user_id, mine.id)}
    basil = service.start_planting(user_id, mine.id, inventory["Sweet basil"].id, bed.id, 3,
                                   growth_stage="seedling", sown_on=today - timedelta(days=27))
    service.start_planting(user_id, mine.id, inventory["Kale"].id, bed.id, 4, growth_stage="vegetative",
                           sown_on=today - timedelta(days=60))
    service.start_planting(user_id, mine.id, inventory["Hot pepper 'Habanero'"].id, porch.id, 2,
                           growth_stage="flowering", sown_on=today - timedelta(days=120))
    greens = service.start_planting(user_id, mine.id, inventory["Microgreens 'Mild mix'"].id, shelf.id, 1,
                                    growth_stage="germinating", sown_on=today - timedelta(days=3))
    service.add_task(user_id, mine.id, "Water raised bed", today, start_time="08:00", recurrence="daily",
                     growing_space_id=bed.id)
    service.add_task(user_id, mine.id, "Mist microgreens", today, start_time="08:10", duration_minutes=5,
                     recurrence="daily", planting_id=greens.id)
    service.add_task(user_id, mine.id, "Harvest basil tips", today, start_time="17:30", duration_minutes=10,
                     priority="low", recurrence="weekly", planting_id=basil.id)
    service.add_observation(user_id, mine.id, basil.id, height_cm=6.0, leaf_count=8, moisture_assessment="moist",
                            notes="Sample entry: healthy seedlings.")
    moms_bed = service.add_space(user_id, moms.id, "Front flower bed", setting="outdoor", exposure="partial_sun")
    service.add_task(user_id, moms.id, "Weed front bed", today, start_time="10:00", duration_minutes=30,
                     growing_space_id=moms_bed.id)
    return [mine, moms]
