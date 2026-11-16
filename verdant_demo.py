"""Reproducible end-to-end Verdant demo (offline, temporary database).

Run: python verdant_demo.py
Uses a scripted forecast so the output is identical on every machine.
"""

from __future__ import annotations

import json
import logging
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

from verdant.persistence import SQLiteRepository
from verdant.services.fakes import FixedWeatherProvider
from verdant.services.garden_service import LOCAL_OPERATOR_ID as ME, GardenService
from verdant.services.inventory import import_initial_inventory
from verdant.services.recommendation_engine import build_context, evaluate
from verdant.services.weather import WeatherService

logging.disable(logging.CRITICAL)
DAY = date(2026, 11, 16)
NOW = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        service = GardenService(SQLiteRepository(Path(tmp) / "demo.db"))
        service.ensure_user(ME)
        mine = service.create_garden(ME, "My Garden", city="Richmond", region="VA", latitude=37.55, longitude=-77.46)
        moms = service.create_garden(ME, "Mom's Garden", city="Norfolk", region="VA", latitude=36.85, longitude=-76.29)

        print("1) Import the packet list into My Garden only")
        print("  ", import_initial_inventory(service, ME, mine.id))
        review = [v.label for _, v in service.inventory(ME, mine.id) if v.verification_status == "needs_review"]
        print(f"   My Garden seeds: {len(service.inventory(ME, mine.id))} ({len(review)} need review, e.g. {review[0]})")
        print(f"   Mom's Garden seeds: {len(service.inventory(ME, moms.id))}   plantings anywhere: "
              f"{len(service.plantings(ME, mine.id)) + len(service.plantings(ME, moms.id))}")

        print("\n2) Spaces and a planting (inventory stays separate)")
        bed = service.add_space(ME, mine.id, "Sunny raised bed", setting="outdoor", exposure="full_sun")
        shelf = service.add_space(ME, mine.id, "Seed shelf", setting="indoor", light_source="grow_light",
                                  grow_light_hours=14)
        inventory = {v.label: i for i, v in service.inventory(ME, mine.id)}
        basil = service.start_planting(ME, mine.id, inventory["Sweet basil"].id, bed.id, 3,
                                       growth_stage="seedling", sown_on=date(2026, 10, 20))
        service.start_planting(ME, mine.id, inventory["Kale"].id, bed.id, 4, growth_stage="vegetative",
                               sown_on=date(2026, 9, 15))
        print(f"   Active plantings: {len(service.plantings(ME, mine.id))}; seed records still: {len(inventory)}")

        print("\n3) Recurring care through the original PawPal+ scheduler")
        water = service.add_task(ME, mine.id, "Water raised bed", DAY, start_time="08:00", recurrence="daily",
                                 growing_space_id=bed.id)
        service.add_task(ME, mine.id, "Mist basil", DAY, start_time="08:10", duration_minutes=10, planting_id=basil.id)
        for warning in service.schedule(ME, mine.id).conflicts(DAY):
            print("   WARNING:", warning)
        done, following = service.complete_task(ME, mine.id, water.id, DAY)
        print(f"   Completed '{done.description}' -> next occurrence {following.due_date} {following.start_time}")

        print("\n4) Weather + advisory rules (scripted forecast: lows 45, 31, 40 F; 80% rain today)")
        weather = WeatherService(service.repo, FixedWeatherProvider(DAY, [45, 31, 40], rain_pct=[80, 10, 0]))
        ctx = build_context(service, weather, ME, mine.id, DAY, NOW)
        recs = service.store_recommendations(ME, mine.id, evaluate(ctx))
        for rec in recs:
            print(f"   [{rec.severity:6}] {rec.suitability:17} {rec.title}")
        frost = next(r for r in recs if r.category == "frost_risk")
        print("\n   Frost advisory as JSON (response contract):")
        print("   " + json.dumps({"garden_id": "<id>", "planting_id": "<id>", "suitability": frost.suitability,
                                  "severity": frost.severity, "title": frost.title,
                                  "explanation": frost.explanation,
                                  "evidence": frost.evidence[:1], "unknowns": frost.unknowns,
                                  "suggested_task": {k: frost.suggested_task[k] for k in ("description", "priority")},
                                  "requires_user_approval": frost.requires_user_approval},
                                 indent=2, ensure_ascii=False).replace("\n", "\n   "))

        print("\n5) Nothing changes until the user decides")
        before = len(service.tasks(ME, mine.id))
        task = service.accept_recommendation(ME, mine.id, frost.id)
        service.accept_recommendation(ME, mine.id, frost.id)  # second click: no duplicate
        print(f"   Tasks before accept: {before}; after accepting twice: {len(service.tasks(ME, mine.id))} "
              f"(new: '{task.description}', source={task.source})")
        print(f"   Mom's Garden tasks: {len(service.tasks(ME, moms.id))}; advice: "
              f"{len(service.recommendations(ME, moms.id, now=NOW))}")
        service.repo.close()


if __name__ == "__main__":
    main()
