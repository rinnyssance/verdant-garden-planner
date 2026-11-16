"""Forecasts through a provider interface, cached per garden, never invented.

Open-Meteo (https://open-meteo.com/) needs no API key for non-commercial use.
Verify its current terms before any commercial deployment.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Protocol

from verdant.domain import WeatherSnapshot
from verdant.domain.common import utcnow

log = logging.getLogger("verdant.weather")
USER_AGENT = "Verdant-garden-planner/0.1"


class WeatherUnavailable(Exception):
    """The provider could not return a usable forecast."""


class WeatherProvider(Protocol):
    name: str

    def daily_forecast(self, latitude: float, longitude: float, timezone: str, days: int) -> list[dict]:
        """Return dicts with keys forecast_for (date), temperature, min_temperature,
        precipitation_probability, precipitation_amount, wind_speed, sunshine_duration (hours)."""


def _get_json(url: str, timeout: float) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as error:  # network, HTTP, JSON: all mean "unavailable"
        raise WeatherUnavailable(f"{type(error).__name__}: {error}") from error


class OpenMeteoProvider:
    name = "Open-Meteo"
    units = "imperial"
    DAILY = ("temperature_2m_max,temperature_2m_min,precipitation_probability_max,"
             "precipitation_sum,wind_speed_10m_max,sunshine_duration")

    def __init__(self, base_url: str | None = None, timeout: float = 10):
        self.base_url = base_url or os.getenv("OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1/forecast")
        self.timeout = timeout

    def build_url(self, latitude, longitude, timezone, days) -> str:
        query = urllib.parse.urlencode({
            "latitude": latitude, "longitude": longitude, "daily": self.DAILY, "timezone": timezone,
            "forecast_days": days, "temperature_unit": "fahrenheit", "wind_speed_unit": "mph",
            "precipitation_unit": "inch"})
        return f"{self.base_url}?{query}"

    def daily_forecast(self, latitude, longitude, timezone, days=7) -> list[dict]:
        return self.parse(_get_json(self.build_url(latitude, longitude, timezone, days), self.timeout))

    @staticmethod
    def parse(payload: dict) -> list[dict]:
        daily = payload.get("daily")
        if not isinstance(daily, dict) or not daily.get("time"):
            raise WeatherUnavailable("Response has no daily forecast.")

        def column(key, i):
            values = daily.get(key) or []
            return values[i] if i < len(values) else None

        rows = []
        for i, day in enumerate(daily["time"]):
            sunshine = column("sunshine_duration", i)
            rows.append({
                "forecast_for": date.fromisoformat(day),
                "temperature": column("temperature_2m_max", i),
                "min_temperature": column("temperature_2m_min", i),
                "precipitation_probability": column("precipitation_probability_max", i),
                "precipitation_amount": column("precipitation_sum", i),
                "wind_speed": column("wind_speed_10m_max", i),
                "sunshine_duration": round(sunshine / 3600, 1) if sunshine is not None else None,
            })
        return rows


class OpenMeteoGeocoder:
    """City / postal-code search so people never need to type coordinates."""

    def __init__(self, base_url: str | None = None, timeout: float = 10):
        self.base_url = base_url or os.getenv("OPEN_METEO_GEOCODING_URL",
                                              "https://geocoding-api.open-meteo.com/v1/search")
        self.timeout = timeout

    def search(self, name: str, count: int = 5) -> list[dict]:
        if not name or not name.strip():
            return []
        query = urllib.parse.urlencode({"name": name.strip(), "count": count, "language": "en", "format": "json"})
        payload = _get_json(f"{self.base_url}?{query}", self.timeout)
        return [{"city": r.get("name", ""), "region": r.get("admin1", ""), "country": r.get("country", ""),
                 "latitude": r["latitude"], "longitude": r["longitude"],
                 "timezone": r.get("timezone") or "UTC"}
                for r in payload.get("results") or [] if "latitude" in r and "longitude" in r]


@dataclass
class ForecastResult:
    status: str                      # fresh | cached | stale | unavailable
    snapshots: list = field(default_factory=list)
    message: str = ""
    provider: str | None = None
    fetched_at: datetime | None = None

    @property
    def usable(self) -> bool:
        """Only fresh or within-TTL data feeds advisories; stale data is shown, not acted on."""
        return self.status in ("fresh", "cached") and bool(self.snapshots)


class WeatherService:
    def __init__(self, repo, provider: WeatherProvider | None = None, ttl: timedelta = timedelta(hours=3),
                 days: int = 7):
        self.repo = repo
        self.provider = provider or OpenMeteoProvider()
        self.ttl = ttl
        self.days = days

    def cached(self, garden_id: str) -> list[WeatherSnapshot]:
        return sorted(self.repo.list(WeatherSnapshot, garden_id), key=lambda s: s.forecast_for)

    def clear(self, garden_id: str) -> None:
        """Forget cached forecasts, e.g. after the garden's location changes."""
        self.repo.delete_where(WeatherSnapshot, garden_id)

    def forecast(self, garden, now: datetime | None = None, refresh: bool = False) -> ForecastResult:
        now = now or utcnow()
        cache = self.cached(garden.id)
        if cache and not refresh and now < cache[0].expires_at:
            return ForecastResult("cached", cache, "", cache[0].provider, cache[0].fetched_at)
        if not garden.has_coordinates:
            return ForecastResult("unavailable", [], "Weather unavailable: set this garden's location in Settings.")
        try:
            rows = self.provider.daily_forecast(garden.latitude, garden.longitude, garden.timezone, self.days)
        except WeatherUnavailable as error:
            log.warning("weather fetch failed garden=%s: %s", garden.id, error)
            if cache:
                return ForecastResult("stale", cache, f"Weather update failed; showing the forecast fetched "
                                      f"{cache[0].fetched_at:%Y-%m-%d %H:%M} UTC. Advisories paused.",
                                      cache[0].provider, cache[0].fetched_at)
            reason = str(error).split(":")[0] or "error"
            return ForecastResult("unavailable", [], f"Weather unavailable right now ({reason}). "
                                  "No conditions are assumed.")
        expires = now + self.ttl
        units = getattr(self.provider, "units", "imperial")
        snapshots = [WeatherSnapshot(garden.id, self.provider.name, now, expires, units=units, **row)
                     for row in rows]
        with self.repo.transaction():
            self.repo.delete_where(WeatherSnapshot, garden.id)
            for snap in snapshots:
                self.repo.save(snap)
        log.info("weather fetched garden=%s days=%d provider=%s", garden.id, len(snapshots), self.provider.name)
        return ForecastResult("fresh", snapshots, "", self.provider.name, now)
