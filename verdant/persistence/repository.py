"""Storage interface. SQLite today; a Supabase implementation can follow (Phase 3)."""

from __future__ import annotations

from typing import Protocol, TypeVar

from verdant.domain import (Garden, GardenMembership, GardenTask, GrowingSpace, Observation, Planting,
                            Recommendation, SeedInventoryItem, SeedVariety, User, WeatherSnapshot)

T = TypeVar("T")

TABLES: dict[type, str] = {
    User: "users",
    Garden: "gardens",
    GardenMembership: "garden_memberships",
    GrowingSpace: "growing_spaces",
    SeedVariety: "seed_varieties",
    SeedInventoryItem: "seed_inventory",
    Planting: "plantings",
    GardenTask: "garden_tasks",
    Observation: "observations",
    WeatherSnapshot: "weather_snapshots",
    Recommendation: "recommendations",
}

# Records that belong to exactly one garden. Listing them always requires a garden_id.
GARDEN_SCOPED = {GrowingSpace, SeedInventoryItem, Planting, GardenTask, Observation,
                 WeatherSnapshot, Recommendation}


class Repository(Protocol):
    def save(self, obj) -> None: ...
    def get(self, cls: type[T], id: str) -> T | None: ...
    def list(self, cls: type[T], garden_id: str | None = None, **filters) -> list[T]: ...
    def delete(self, cls: type, id: str) -> None: ...
    def delete_where(self, cls: type, garden_id: str, **filters) -> int: ...
    def transaction(self): ...
