"""Users, gardens, memberships and growing spaces.

A garden is not a user. Mom's garden is a garden the operator manages; she
needs no account until she is invited.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .common import choice, new_id, optional_number, optional_text, text

ROLES = ("owner", "editor", "viewer")
SETTINGS = ("indoor", "outdoor", "greenhouse", "covered")
GROWING_METHODS = ("bed", "raised_bed", "container", "tray", "other")
LIGHT_SOURCES = ("natural", "grow_light", "mixed")
EXPOSURES = ("full_sun", "partial_sun", "partial_shade", "full_shade", "unknown")


@dataclass
class User:
    display_name: str
    id: str = field(default_factory=new_id)

    def __post_init__(self):
        self.display_name = text(self.display_name, "Name")


@dataclass
class Garden:
    display_name: str
    owner_user_id: str
    city: str = ""
    region: str = ""
    country: str = ""
    postal_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    timezone: str = "America/New_York"
    zone_label: str | None = None
    zone_source: str | None = None
    id: str = field(default_factory=new_id)

    def __post_init__(self):
        self.display_name = text(self.display_name, "Garden name")
        self.owner_user_id = text(self.owner_user_id, "Garden owner")
        self.city, self.region, self.country = (str(v or "").strip() for v in
                                                (self.city, self.region, self.country))
        self.postal_code = optional_text(self.postal_code)
        self.zone_label = optional_text(self.zone_label)
        self.zone_source = optional_text(self.zone_source)
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Provide both latitude and longitude, or neither.")
        if self.latitude is not None:
            # About 1 km precision: enough for a forecast, not a street address.
            self.latitude = round(optional_number(self.latitude, "Latitude", minimum=-90, maximum=90), 2)
            self.longitude = round(optional_number(self.longitude, "Longitude", minimum=-180, maximum=180), 2)
        if self.zone_label and not self.zone_source:
            raise ValueError("Record where the hardiness zone came from.")

    @property
    def location_label(self) -> str:
        parts = [p for p in (self.city, self.region, self.country) if p]
        return ", ".join(parts) or "Location not set"

    @property
    def has_coordinates(self) -> bool:
        return self.latitude is not None and self.longitude is not None


@dataclass
class GardenMembership:
    garden_id: str
    user_id: str
    role: str = "viewer"
    id: str = field(default_factory=new_id)

    def __post_init__(self):
        choice(self.role, ROLES, "Role")


@dataclass
class GrowingSpace:
    garden_id: str
    name: str
    setting: str = "outdoor"
    growing_method: str = "bed"
    light_source: str = "natural"
    exposure: str = "unknown"
    estimated_direct_sun_hours: float | None = None
    grow_light_hours: float | None = None
    grow_light_ppfd: float | None = None
    soil_medium: str | None = None
    irrigation_method: str | None = None
    notes: str = ""
    id: str = field(default_factory=new_id)

    def __post_init__(self):
        self.name = text(self.name, "Space name")
        choice(self.setting, SETTINGS, "Setting")
        choice(self.growing_method, GROWING_METHODS, "Growing method")
        choice(self.light_source, LIGHT_SOURCES, "Light source")
        choice(self.exposure, EXPOSURES, "Exposure")
        self.estimated_direct_sun_hours = optional_number(
            self.estimated_direct_sun_hours, "Direct sun hours", maximum=24)
        self.grow_light_hours = optional_number(self.grow_light_hours, "Grow-light hours", maximum=24)
        # PPFD is recorded only when measured or published for the fixture; never inferred from hours.
        self.grow_light_ppfd = optional_number(self.grow_light_ppfd, "Grow-light PPFD", maximum=3000)
        if self.light_source == "natural" and (self.grow_light_hours or self.grow_light_ppfd):
            raise ValueError("A naturally lit space cannot have grow-light settings; choose 'mixed'.")
        self.soil_medium = optional_text(self.soil_medium)
        self.irrigation_method = optional_text(self.irrigation_method)
        self.notes = (self.notes or "").strip()

    @property
    def uses_grow_light(self) -> bool:
        return self.light_source in ("grow_light", "mixed")

    @property
    def exposed_to_outdoor_weather(self) -> bool:
        """Rain reaches only open outdoor spaces; frost can reach covered ones too."""
        return self.setting == "outdoor"

    @property
    def exposed_to_outdoor_temperature(self) -> bool:
        return self.setting in ("outdoor", "covered")
