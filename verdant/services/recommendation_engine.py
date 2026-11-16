"""Deterministic, explainable garden advisories.

Each rule reads only stored facts (spaces, plantings, seed varieties, crop
reference rows, cached forecast) and returns Recommendation objects that
carry their evidence, unknowns and limitations. Rules never create, move or
complete tasks; a suggested task waits for explicit user approval.

Thresholds below are configurable advisory defaults, not validated agronomic
limits. They are deliberately conservative because forecast air temperature
is not plant-level temperature.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from verdant.domain import Recommendation

from .inventory import load_crop_reference

log = logging.getLogger("verdant.recommendations")

FROST_WATCH_F = 36.0      # tender crops: watch at or below this forecast low
FROST_ACTION_F = 32.0     # tender crops: action at or below freezing
RAIN_PROBABILITY_PCT = 60.0
RAIN_AMOUNT_IN = 0.25
LOOKAHEAD_DAYS = 3        # today + next two days


@dataclass
class GardenContext:
    garden: object
    spaces: list
    plantings: list
    varieties: dict          # seed_variety_id -> SeedVariety
    tasks: list
    forecast: object         # ForecastResult
    today: date
    now: datetime


def _f(value: float, units: str) -> float:
    return value if units == "imperial" else value * 9 / 5 + 32


def _end_of(day: date) -> datetime:
    return datetime.combine(day + timedelta(days=1), time(0), tzinfo=timezone.utc)


def _forecast_evidence(snap, kind, value, unit):
    return {"type": kind, "value": value, "unit": unit, "for_date": snap.forecast_for.isoformat(),
            "source": snap.provider, "fetched_at": snap.fetched_at.isoformat(), "origin": "forecast"}


def _window(ctx: GardenContext):
    last = ctx.today + timedelta(days=LOOKAHEAD_DAYS - 1)
    return [s for s in ctx.forecast.snapshots if ctx.today <= s.forecast_for <= last]


def _plant_name(planting, variety) -> str:
    return planting.nickname or (variety.label if variety else "this planting")


# -- rule 1: frost risk ---------------------------------------------------
def frost_risk(ctx: GardenContext) -> list[Recommendation]:
    if not ctx.forecast.usable:
        return []
    window = [s for s in _window(ctx) if s.min_temperature is not None]
    if not window:
        return []
    coldest = min(window, key=lambda s: s.min_temperature)
    low_f = round(_f(coldest.min_temperature, coldest.units), 1)
    if low_f > FROST_WATCH_F:
        return []
    reference = load_crop_reference()
    spaces = {s.id: s for s in ctx.spaces}
    recs = []
    for planting in ctx.plantings:
        space = spaces.get(planting.growing_space_id)
        if not planting.is_live or space is None or not space.exposed_to_outdoor_temperature:
            continue
        variety = ctx.varieties.get(planting.seed_variety_id)
        row = reference["crops"].get(variety.crop_key if variety else None, {})
        sensitivity = row.get("frost_sensitivity", "unknown")
        name = _plant_name(planting, variety)
        evidence = [
            _forecast_evidence(coldest, "forecast_low", low_f, "F"),
            {"type": "space_setting", "value": space.setting, "source": f"Garden space '{space.name}'",
             "origin": "user_entered"},
            {"type": "frost_sensitivity", "value": sensitivity, "source": reference["citation"],
             "origin": "reference", "verification_status": reference["verification_status"]},
        ]
        unknowns = ["actual plant-level temperature", "microclimate around the plant"]
        limitations = ("Forecast lows are area estimates for air about 2 m above ground. "
                       f"Thresholds ({FROST_WATCH_F:g}°F watch, {FROST_ACTION_F:g}°F action) are configurable "
                       "advisory defaults, not validated limits. Crop sensitivity table is pending verification.")
        if space.setting == "covered":
            limitations += " A cover may keep the space warmer than the forecast; how much is unknown."
        key = f"frost:{planting.id}:{coldest.forecast_for.isoformat()}"
        expires = _end_of(coldest.forecast_for)
        if sensitivity == "tender":
            severity = "action" if low_f <= FROST_ACTION_F else "watch"
            recs.append(Recommendation(
                ctx.garden.id, "frost_risk", severity, "needs_adjustment",
                f"Check cold protection for {name}",
                f"The forecast low for {coldest.forecast_for:%a %b %d} is {low_f:g}°F. {name} is listed as "
                f"frost-tender and is in '{space.name}' ({space.setting}), which is exposed to outdoor temperatures.",
                key, planting_id=planting.id, growing_space_id=space.id, evidence=evidence, unknowns=unknowns,
                limitations=limitations, expires_at=expires,
                suggested_task={"description": f"Check cold protection for {name}",
                                "due_date": min(ctx.today, coldest.forecast_for).isoformat(),
                                "start_time": "17:00", "duration_minutes": 15,
                                "priority": "high" if severity == "action" else "medium"}))
        elif sensitivity == "unknown":
            recs.append(Recommendation(
                ctx.garden.id, "frost_risk", "info", "insufficient_data",
                f"Frost sensitivity unknown for {name}",
                f"The forecast low for {coldest.forecast_for:%a %b %d} is {low_f:g}°F, but Verdant has no frost "
                f"sensitivity on record for {name}, so it cannot say whether protection is needed.",
                key, planting_id=planting.id, growing_space_id=space.id, evidence=evidence,
                unknowns=unknowns + ["frost tolerance of this crop or cultivar"], limitations=limitations,
                expires_at=expires))
        # 'tolerant' crops: no advisory at these thresholds.
    return recs


# -- rule 2: rain -> check soil before watering ---------------------------
def rain_soil_check(ctx: GardenContext) -> list[Recommendation]:
    if not ctx.forecast.usable:
        return []
    candidates = [s for s in ctx.forecast.snapshots if s.forecast_for in (ctx.today, ctx.today + timedelta(days=1))]
    wet = [s for s in candidates if (s.precipitation_probability or 0) >= RAIN_PROBABILITY_PCT
           or (s.precipitation_amount or 0) >= (RAIN_AMOUNT_IN if s.units == "imperial" else RAIN_AMOUNT_IN * 25.4)]
    if not wet:
        return []
    snap = wet[0]
    live_spaces = {p.growing_space_id for p in ctx.plantings if p.is_live}
    recs = []
    for space in ctx.spaces:
        if not space.exposed_to_outdoor_weather or space.id not in live_spaces:
            continue  # indoor, greenhouse and covered spaces do not get rain
        evidence = []
        if snap.precipitation_probability is not None:
            evidence.append(_forecast_evidence(snap, "precipitation_probability", snap.precipitation_probability, "%"))
        if snap.precipitation_amount is not None:
            evidence.append(_forecast_evidence(snap, "precipitation_amount", snap.precipitation_amount,
                                               snap.precip_unit))
        evidence.append({"type": "space_setting", "value": "outdoor", "source": f"Garden space '{space.name}'",
                         "origin": "user_entered"})
        watering = [t for t in ctx.tasks if not t.completed and t.due_date == snap.forecast_for
                    and "water" in t.description.lower()
                    and (t.growing_space_id == space.id or t.planting_id in
                         {p.id for p in ctx.plantings if p.growing_space_id == space.id})]
        for task in watering:
            evidence.append({"type": "pending_task", "value": f"{task.description} at {task.start_time}",
                             "source": "Verdant calendar", "origin": "user_entered"})
        note = (" Your watering task stays scheduled and is not marked done; decide after checking." if watering
                else "")
        recs.append(Recommendation(
            ctx.garden.id, "rain_soil_check", "info", "needs_adjustment",
            f"Check soil moisture in {space.name} before watering",
            f"Rain is forecast for {snap.forecast_for:%a %b %d}. Rain can reduce or replace watering for outdoor "
            f"beds, but how much reaches the roots depends on the soil and the plants.{note}",
            f"rain:{space.id}:{snap.forecast_for.isoformat()}", growing_space_id=space.id, evidence=evidence,
            unknowns=["actual rainfall at the garden", "current soil moisture"],
            limitations="Forecast precipitation is an area estimate. Verdant does not prescribe watering amounts.",
            expires_at=_end_of(snap.forecast_for),
            suggested_task={"description": f"Check soil moisture in {space.name}",
                            "due_date": snap.forecast_for.isoformat(), "start_time": "08:00",
                            "duration_minutes": 10, "priority": "medium"}))
    return recs


# -- rule 3: grow-light data completeness ----------------------------------
def grow_light_data(ctx: GardenContext) -> list[Recommendation]:
    recs = []
    for space in ctx.spaces:
        if not space.uses_grow_light:
            continue
        missing = [label for label, value in (("light intensity (PPFD)", space.grow_light_ppfd),
                                              ("daily light hours", space.grow_light_hours)) if value is None]
        if not missing:
            continue
        evidence = [{"type": "light_source", "value": space.light_source, "source": f"Garden space '{space.name}'",
                     "origin": "user_entered"}]
        if space.grow_light_hours is not None:
            evidence.append({"type": "grow_light_hours", "value": space.grow_light_hours, "unit": "h/day",
                             "source": f"Garden space '{space.name}'", "origin": "user_entered"})
        recs.append(Recommendation(
            ctx.garden.id, "grow_light", "info", "insufficient_data",
            f"Add grow-light details for {space.name}",
            f"Verdant cannot judge whether the grow light in '{space.name}' is sufficient without "
            f"{' and '.join(missing)}. Hours alone do not tell how much light plants receive.",
            f"growlight:{space.id}:{'+'.join(missing)}", growing_space_id=space.id, evidence=evidence,
            unknowns=missing,
            limitations="PPFD should come from a light meter or the fixture's published data at the plant's distance.",
            suggested_task={"description": f"Record grow-light PPFD and hours for {space.name}",
                            "due_date": ctx.today.isoformat(), "start_time": "19:00", "duration_minutes": 10,
                            "priority": "low"}))
    return recs


# -- rule 4: data quality --------------------------------------------------
def weather_data_quality(ctx: GardenContext) -> list[Recommendation]:
    outdoor_live = any(p.is_live for p in ctx.plantings
                       for s in ctx.spaces if s.id == p.growing_space_id and s.exposed_to_outdoor_temperature)
    if ctx.forecast.usable or not outdoor_live:
        return []
    return [Recommendation(
        ctx.garden.id, "data_quality", "watch", "insufficient_data",
        "Weather checks are paused",
        f"{ctx.forecast.message} Frost and rain advisories need a current forecast, so none were generated.",
        f"weather-missing:{ctx.today.isoformat()}", unknowns=["current forecast"],
        limitations="No weather conditions are assumed when the forecast is missing or stale.",
        expires_at=_end_of(ctx.today))]


RULES = (frost_risk, rain_soil_check, grow_light_data, weather_data_quality)


def evaluate(ctx: GardenContext) -> list[Recommendation]:
    """Run every rule for one garden. Same inputs always give the same output."""
    recs = []
    for rule in RULES:
        produced = rule(ctx)
        for rec in produced:
            if rec.garden_id != ctx.garden.id:
                raise ValueError("Rule produced advice for another garden.")
            rec.generated_at = ctx.now
        log.info("rule=%s garden=%s produced=%d keys=%s", rule.__name__, ctx.garden.id, len(produced),
                 [r.rule_key for r in produced])
        recs.extend(produced)
    return recs


def build_context(service, weather_service, user_id: str, garden_id: str, today: date,
                  now: datetime, refresh_weather: bool = False) -> GardenContext:
    garden = service.garden(user_id, garden_id)
    plantings = service.plantings(user_id, garden_id)
    varieties = {v.id: v for _, v in service.inventory(user_id, garden_id)}
    from verdant.domain import SeedVariety
    for p in plantings:
        if p.seed_variety_id not in varieties:
            varieties[p.seed_variety_id] = service.repo.get(SeedVariety, p.seed_variety_id)
    forecast = weather_service.forecast(garden, now, refresh_weather)
    return GardenContext(garden, service.spaces(user_id, garden_id), plantings, varieties,
                         service.tasks(user_id, garden_id), forecast, today, now)
