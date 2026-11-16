"""Scenario harness for the Verdant advisory engine.

Run from the project root:  python scripts/evaluate_recommendations.py
Runs offline with scripted forecasts and an in-memory database, then prints
one line per scenario plus guardrail checks and a summary. Exit code 1 if
anything fails.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from verdant.domain import SeedVariety  # noqa: E402
from verdant.persistence import SQLiteRepository  # noqa: E402
from verdant.services.fakes import FailingWeatherProvider, FixedWeatherProvider  # noqa: E402
from verdant.services.garden_service import GardenService  # noqa: E402
from verdant.services.recommendation_engine import build_context, evaluate  # noqa: E402
from verdant.services.weather import WeatherService  # noqa: E402

DAY = date(2026, 11, 16)
NOW = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)
ME = "evaluator"


@dataclass
class Scenario:
    name: str
    plants: list            # (crop_key, name, setting, stage)
    provider: object
    expected: set           # {(category, severity, suitability)}
    spaces: list = field(default_factory=list)   # extra spaces: dict of GrowingSpace kwargs
    water_task: bool = False


def lows(*values, rain=None):
    return FixedWeatherProvider(DAY, list(values), rain_pct=rain)


SCENARIOS = [
    Scenario("Tender basil outdoors, low 31F", [("basil", "Basil", "outdoor", "seedling")], lows(45, 31, 40),
             {("frost_risk", "action", "needs_adjustment")}),
    Scenario("Tender tomato under cover, low 35F", [("tomato", "Tomato", "covered", "vegetative")], lows(35, 50, 50),
             {("frost_risk", "watch", "needs_adjustment")}),
    Scenario("Boundary: low exactly 36F", [("pepper", "Pepper", "outdoor", "seedling")], lows(36, 50, 50),
             {("frost_risk", "watch", "needs_adjustment")}),
    Scenario("Boundary: low 37F (no alert)", [("pepper", "Pepper", "outdoor", "seedling")], lows(37, 50, 50), set()),
    Scenario("Indoor basil, low 25F (not exposed)", [("basil", "Basil", "indoor", "seedling")], lows(25, 25, 25), set()),
    Scenario("Frost-tolerant kale, low 30F", [("kale", "Kale", "outdoor", "vegetative")], lows(30, 30, 30), set()),
    Scenario("Unknown sensitivity (rosemary), low 30F", [("rosemary", "Rosemary", "outdoor", "vegetative")],
             lows(30, 30, 30), {("frost_risk", "info", "insufficient_data")}),
    Scenario("Planned pepper not yet sown, low 28F", [("pepper", "Pepper", "outdoor", "planned")], lows(28, 28, 28),
             set()),
    Scenario("Rain 80% on outdoor beans with watering task", [("bean", "Bean", "outdoor", "seedling")],
             lows(55, 55, rain=[80, 0]), {("rain_soil_check", "info", "needs_adjustment")}, water_task=True),
    Scenario("Rain 80% in a greenhouse", [("bean", "Bean", "greenhouse", "seedling")], lows(55, 55, rain=[80, 0]),
             set()),
    Scenario("Grow light without PPFD", [], lows(55),
             {("grow_light", "info", "insufficient_data")},
             spaces=[dict(name="Shelf", setting="indoor", light_source="grow_light", grow_light_hours=14)]),
    Scenario("Weather outage with outdoor basil", [("basil", "Basil", "outdoor", "seedling")],
             FailingWeatherProvider(), {("data_quality", "watch", "insufficient_data")}),
]


def run(scenario: Scenario):
    service = GardenService(SQLiteRepository())
    service.ensure_user(ME)
    garden = service.create_garden(ME, "Eval garden", latitude=37.5, longitude=-77.4)
    for extra in scenario.spaces:
        extra = dict(extra)
        service.add_space(ME, garden.id, extra.pop("name"), **extra)
    for crop, name, setting, stage in scenario.plants:
        space = service.add_space(ME, garden.id, f"{name} space", setting=setting)
        item = service.add_seed(ME, garden.id, SeedVariety(name, "vegetable", crop_key=crop))
        service.start_planting(ME, garden.id, item.id, space.id, growth_stage=stage,
                               sown_on=None if stage == "planned" else DAY)
        if scenario.water_task:
            service.add_task(ME, garden.id, f"Water {name}", DAY, growing_space_id=space.id)
    tasks_before = service.tasks(ME, garden.id)
    weather = WeatherService(service.repo, scenario.provider)
    recs = evaluate(build_context(service, weather, ME, garden.id, DAY, NOW))
    again = evaluate(build_context(service, weather, ME, garden.id, DAY, NOW))
    got = {(r.category, r.severity, r.suitability) for r in recs}
    guardrails = {
        "deterministic": [r.rule_key for r in recs] == [r.rule_key for r in again],
        "no tasks changed": service.tasks(ME, garden.id) == tasks_before,
        "evidence or insufficient_data": all(r.evidence or r.suitability == "insufficient_data" for r in recs),
        "unknowns stated": all(r.unknowns for r in recs),
    }
    return got, guardrails


def main() -> int:
    print(f"Verdant advisory evaluation - {len(SCENARIOS)} scenarios, fixed date {DAY}\n")
    passed = guard_fail = 0
    for i, scenario in enumerate(SCENARIOS, 1):
        got, guardrails = run(scenario)
        ok = got == scenario.expected
        passed += ok
        bad = [name for name, good in guardrails.items() if not good]
        guard_fail += bool(bad)
        shown = ", ".join(sorted(f"{c}/{s}/{u}" for c, s, u in got)) or "no advice"
        print(f"{i:2}. {'PASS' if ok else 'FAIL'}  {scenario.name:46} -> {shown}"
              + (f"   GUARDRAIL FAIL: {', '.join(bad)}" if bad else ""))
        if not ok:
            expected = ", ".join(sorted(f"{c}/{s}/{u}" for c, s, u in scenario.expected)) or "no advice"
            print(f"      expected: {expected}")
    print(f"\nSummary: {passed}/{len(SCENARIOS)} scenarios matched expected advice; "
          f"{len(SCENARIOS) - guard_fail}/{len(SCENARIOS)} passed all guardrails "
          "(deterministic, no automatic task changes, evidence present, unknowns stated).")
    return 0 if passed == len(SCENARIOS) and guard_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
