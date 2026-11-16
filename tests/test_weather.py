"""Weather lookups: cached, timestamped, scoped per garden, and never invented."""

from datetime import date, datetime, timedelta, timezone

import pytest

from verdant.persistence import SQLiteRepository
from verdant.services.fakes import FailingWeatherProvider, FixedWeatherProvider
from verdant.services.garden_service import GardenService
from verdant.services.weather import OpenMeteoProvider, WeatherService, WeatherUnavailable

DAY = date(2026, 11, 16)
NOW = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)
ME = "local-operator"


@pytest.fixture
def service():
    s = GardenService(SQLiteRepository())
    s.ensure_user(ME)
    return s


def test_fetch_then_cache_then_refresh(service):
    garden = service.create_garden(ME, "My Garden", latitude=37.5, longitude=-77.4)
    provider = FixedWeatherProvider(DAY, [40, 41, 42])
    weather = WeatherService(service.repo, provider)
    first = weather.forecast(garden, NOW)
    assert first.status == "fresh" and first.provider == "Scripted test forecast" and first.fetched_at == NOW
    assert [s.forecast_for for s in first.snapshots] == [DAY, DAY + timedelta(1), DAY + timedelta(2)]
    second = weather.forecast(garden, NOW + timedelta(hours=1))
    assert second.status == "cached" and provider.calls == 1
    third = weather.forecast(garden, NOW + timedelta(hours=4))
    assert third.status == "fresh" and provider.calls == 2
    assert len(weather.cached(garden.id)) == 3  # old rows replaced, not duplicated


def test_missing_location_and_outage_degrade_gracefully(service):
    nowhere = service.create_garden(ME, "No location")
    result = WeatherService(service.repo, FixedWeatherProvider(DAY, [40])).forecast(nowhere, NOW)
    assert result.status == "unavailable" and "location" in result.message and not result.usable
    garden = service.create_garden(ME, "My Garden", latitude=37.5, longitude=-77.4)
    down = WeatherService(service.repo, FailingWeatherProvider()).forecast(garden, NOW)
    assert down.status == "unavailable" and down.snapshots == [] and "No conditions are assumed" in down.message


def test_outage_with_old_cache_is_stale_not_usable(service):
    garden = service.create_garden(ME, "My Garden", latitude=37.5, longitude=-77.4)
    WeatherService(service.repo, FixedWeatherProvider(DAY, [40])).forecast(garden, NOW)
    stale = WeatherService(service.repo, FailingWeatherProvider()).forecast(garden, NOW + timedelta(hours=5))
    assert stale.status == "stale" and stale.snapshots and not stale.usable
    assert "Advisories paused" in stale.message


def test_forecasts_are_per_garden(service):
    mine = service.create_garden(ME, "My Garden", latitude=37.5, longitude=-77.4)
    moms = service.create_garden(ME, "Mom's Garden", latitude=36.85, longitude=-76.29)
    WeatherService(service.repo, FixedWeatherProvider(DAY, [30])).forecast(mine, NOW)
    weather = WeatherService(service.repo, FixedWeatherProvider(DAY, [50]))
    assert weather.forecast(moms, NOW).snapshots[0].min_temperature == 50
    assert weather.cached(mine.id)[0].min_temperature == 30


def test_open_meteo_parsing_and_url():
    payload = {"daily": {"time": ["2026-11-16", "2026-11-17"], "temperature_2m_max": [60.1, 58.0],
                         "temperature_2m_min": [35.2, None], "precipitation_probability_max": [80, 10],
                         "precipitation_sum": [0.4, 0.0], "wind_speed_10m_max": [12.0, 8.0],
                         "sunshine_duration": [18000.0, None]}}
    rows = OpenMeteoProvider.parse(payload)
    assert rows[0]["min_temperature"] == 35.2 and rows[0]["sunshine_duration"] == 5.0
    assert rows[1]["min_temperature"] is None and rows[1]["sunshine_duration"] is None
    with pytest.raises(WeatherUnavailable):
        OpenMeteoProvider.parse({"error": True, "reason": "bad"})
    url = OpenMeteoProvider("https://example.test/forecast").build_url(37.5, -77.4, "America/New_York", 7)
    assert "temperature_unit=fahrenheit" in url and "latitude=37.5" in url
