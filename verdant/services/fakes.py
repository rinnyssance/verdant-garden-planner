"""Offline weather providers for tests, demos and the evaluation harness."""

from __future__ import annotations

from datetime import date, timedelta

from .weather import WeatherUnavailable


class FixedWeatherProvider:
    """Returns the same scripted forecast every time (no network)."""

    name = "Scripted test forecast"
    units = "imperial"

    def __init__(self, start: date, lows, highs=None, rain_pct=None, rain_in=None):
        self.start = start
        self.lows = list(lows)
        self.highs = list(highs or [low + 20 for low in self.lows])
        self.rain_pct = list(rain_pct or [0] * len(self.lows))
        self.rain_in = list(rain_in or [0.0] * len(self.lows))
        self.calls = 0

    def daily_forecast(self, latitude, longitude, timezone, days=7):
        self.calls += 1
        return [{"forecast_for": self.start + timedelta(days=i), "temperature": self.highs[i],
                 "min_temperature": self.lows[i], "precipitation_probability": self.rain_pct[i],
                 "precipitation_amount": self.rain_in[i], "wind_speed": 5.0, "sunshine_duration": 6.0}
                for i in range(min(days, len(self.lows)))]


class FailingWeatherProvider:
    name = "Unavailable provider"
    units = "imperial"

    def daily_forecast(self, latitude, longitude, timezone, days=7):
        raise WeatherUnavailable("simulated outage")
