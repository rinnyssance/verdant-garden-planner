"""Weather snapshots and explainable recommendations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from .common import choice, new_id, text, utcnow

SEVERITIES = ("info", "watch", "action")
SUITABILITY = ("suitable", "needs_adjustment", "unsuitable", "insufficient_data")
REC_STATUSES = ("new", "accepted", "dismissed")


@dataclass
class WeatherSnapshot:
    """One forecast day for one garden, exactly as the provider reported it."""

    garden_id: str
    provider: str
    fetched_at: datetime
    expires_at: datetime
    forecast_for: date
    temperature: float | None = None          # daily maximum
    min_temperature: float | None = None      # daily minimum
    precipitation_probability: float | None = None
    precipitation_amount: float | None = None
    wind_speed: float | None = None
    sunshine_duration: float | None = None    # hours
    units: str = "imperial"
    raw_reference: str | None = None
    id: str = field(default_factory=new_id)

    def __post_init__(self):
        choice(self.units, ("imperial", "metric"), "Units")

    @property
    def temp_unit(self) -> str:
        return "F" if self.units == "imperial" else "C"

    @property
    def precip_unit(self) -> str:
        return "in" if self.units == "imperial" else "mm"

    @property
    def wind_unit(self) -> str:
        return "mph" if self.units == "imperial" else "km/h"


@dataclass
class Recommendation:
    garden_id: str
    category: str
    severity: str
    suitability: str
    title: str
    explanation: str
    rule_key: str
    planting_id: str | None = None
    growing_space_id: str | None = None
    evidence: list = field(default_factory=list)
    unknowns: list = field(default_factory=list)
    limitations: str = ""
    suggested_task: dict | None = None
    generated_at: datetime = field(default_factory=utcnow)
    expires_at: datetime | None = None
    status: str = "new"
    id: str = field(default_factory=new_id)

    def __post_init__(self):
        choice(self.severity, SEVERITIES, "Severity")
        choice(self.suitability, SUITABILITY, "Suitability")
        choice(self.status, REC_STATUSES, "Status")
        self.title = text(self.title, "Title")
        self.explanation = text(self.explanation, "Explanation")
        if not self.evidence and self.suitability != "insufficient_data":
            raise ValueError("A recommendation needs evidence unless it reports insufficient data.")

    @property
    def requires_user_approval(self) -> bool:
        return self.suggested_task is not None

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at is not None and now >= self.expires_at
