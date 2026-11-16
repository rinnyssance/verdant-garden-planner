"""The single entry point the UI uses. Every call names a user and a garden,
checks membership first, and only touches records belonging to that garden."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import date, datetime

from verdant.domain import (Garden, GardenMembership, GardenTask, GrowingSpace, Observation, Planting,
                            Recommendation, SeedInventoryItem, SeedVariety, User)
from verdant.domain.common import utcnow
from verdant.scheduling import GardenSchedule

from .access import AccessDenied, gardens_for, require_role

log = logging.getLogger("verdant.service")

LOCAL_OPERATOR_ID = "local-operator"
EDITABLE_TASK_FIELDS = {"description", "start_time", "due_date", "duration_minutes", "priority", "recurrence"}


class GardenService:
    def __init__(self, repo):
        self.repo = repo

    # -- users and gardens ------------------------------------------------
    def ensure_user(self, user_id: str = LOCAL_OPERATOR_ID, display_name: str = "Garden operator") -> User:
        user = self.repo.get(User, user_id)
        if user is None:
            user = User(display_name, id=user_id)
            self.repo.save(user)
        return user

    def create_garden(self, user_id: str, display_name: str, **location) -> Garden:
        garden = Garden(display_name, user_id, **location)
        with self.repo.transaction():
            self.repo.save(garden)
            self.repo.save(GardenMembership(garden.id, user_id, "owner"))
        log.info("garden created id=%s", garden.id)
        return garden

    def gardens(self, user_id: str) -> list[Garden]:
        return gardens_for(self.repo, user_id)

    def garden(self, user_id: str, garden_id: str) -> Garden:
        return require_role(self.repo, user_id, garden_id)

    def update_garden(self, user_id: str, garden_id: str, **changes) -> Garden:
        garden = require_role(self.repo, user_id, garden_id, "owner")
        changes.pop("id", None)
        changes.pop("owner_user_id", None)
        updated = replace(garden, **changes)
        self.repo.save(updated)
        return updated

    def grant_access(self, user_id: str, garden_id: str, member_user_id: str, role: str) -> GardenMembership:
        """Owner-only. Used for the future invitation flow (e.g. Mom gets 'editor')."""
        require_role(self.repo, user_id, garden_id, "owner")
        existing = self.repo.list(GardenMembership, garden_id=garden_id, user_id=member_user_id)
        member = replace(existing[0], role=role) if existing else GardenMembership(garden_id, member_user_id, role)
        self.repo.save(member)
        return member

    # -- growing spaces ---------------------------------------------------
    def add_space(self, user_id: str, garden_id: str, name: str, **attrs) -> GrowingSpace:
        require_role(self.repo, user_id, garden_id, "editor")
        space = GrowingSpace(garden_id, name, **attrs)
        self.repo.save(space)
        return space

    def update_space(self, user_id: str, garden_id: str, space_id: str, **changes) -> GrowingSpace:
        require_role(self.repo, user_id, garden_id, "editor")
        space = self._owned(GrowingSpace, garden_id, space_id)
        changes.pop("garden_id", None)
        changes.pop("id", None)
        updated = replace(space, **changes)
        self.repo.save(updated)
        return updated

    def spaces(self, user_id: str, garden_id: str) -> list[GrowingSpace]:
        require_role(self.repo, user_id, garden_id)
        return self.repo.list(GrowingSpace, garden_id)

    # -- seed library -----------------------------------------------------
    def add_seed(self, user_id: str, garden_id: str, variety: SeedVariety, **inventory) -> SeedInventoryItem:
        require_role(self.repo, user_id, garden_id, "editor")
        with self.repo.transaction():
            if self.repo.get(SeedVariety, variety.id) is None:
                self.repo.save(variety)
            item = SeedInventoryItem(garden_id, variety.id, **inventory)
            self.repo.save(item)
        return item

    def inventory(self, user_id: str, garden_id: str) -> list[tuple[SeedInventoryItem, SeedVariety]]:
        require_role(self.repo, user_id, garden_id)
        items = self.repo.list(SeedInventoryItem, garden_id)
        pairs = [(item, self.repo.get(SeedVariety, item.seed_variety_id)) for item in items]
        return sorted(pairs, key=lambda pair: (pair[1].category, pair[1].common_name.lower(),
                                               (pair[1].cultivar or "").lower()))

    def update_inventory_item(self, user_id: str, garden_id: str, item_id: str, **changes) -> SeedInventoryItem:
        require_role(self.repo, user_id, garden_id, "editor")
        item = self._owned(SeedInventoryItem, garden_id, item_id)
        for key in ("garden_id", "id", "seed_variety_id", "import_key"):
            changes.pop(key, None)
        updated = replace(item, **changes)
        self.repo.save(updated)
        return updated

    def update_variety(self, user_id: str, garden_id: str, variety_id: str, **changes) -> SeedVariety:
        """Varieties are edited through a garden that holds them in inventory."""
        require_role(self.repo, user_id, garden_id, "editor")
        if not self.repo.list(SeedInventoryItem, garden_id, seed_variety_id=variety_id):
            raise AccessDenied("That seed is not in this garden's library.")
        variety = self.repo.get(SeedVariety, variety_id)
        changes.pop("id", None)
        updated = replace(variety, **changes)
        self.repo.save(updated)
        return updated

    # -- plantings --------------------------------------------------------
    def start_planting(self, user_id: str, garden_id: str, inventory_item_id: str, growing_space_id: str,
                       quantity: int = 1, **details) -> Planting:
        """Create a planting from a seed in this garden's inventory. Inventory is left unchanged."""
        require_role(self.repo, user_id, garden_id, "editor")
        item = self._owned(SeedInventoryItem, garden_id, inventory_item_id)
        self._owned(GrowingSpace, garden_id, growing_space_id)
        planting = Planting(garden_id, growing_space_id, item.seed_variety_id, quantity, **details)
        self.repo.save(planting)
        log.info("planting started garden=%s planting=%s", garden_id, planting.id)
        return planting

    def plantings(self, user_id: str, garden_id: str, status: str | None = "active") -> list[Planting]:
        require_role(self.repo, user_id, garden_id)
        filters = {} if status is None else {"status": status}
        return self.repo.list(Planting, garden_id, **filters)

    def update_planting(self, user_id: str, garden_id: str, planting_id: str, **changes) -> Planting:
        require_role(self.repo, user_id, garden_id, "editor")
        planting = self._owned(Planting, garden_id, planting_id)
        for key in ("garden_id", "id", "seed_variety_id"):
            changes.pop(key, None)
        if "growing_space_id" in changes:
            self._owned(GrowingSpace, garden_id, changes["growing_space_id"])
        updated = replace(planting, **changes)
        self.repo.save(updated)
        return updated

    def archive_planting(self, user_id: str, garden_id: str, planting_id: str, finished: bool = True) -> Planting:
        changes = {"status": "archived"}
        if finished:
            changes["growth_stage"] = "finished"
        return self.update_planting(user_id, garden_id, planting_id, **changes)

    # -- tasks (via the PawPal adapter) ----------------------------------
    def add_task(self, user_id: str, garden_id: str, description: str, due_date: date, **details) -> GardenTask:
        require_role(self.repo, user_id, garden_id, "editor")
        self._check_targets(garden_id, details.get("planting_id"), details.get("growing_space_id"))
        task = GardenTask(garden_id, description, due_date, **details)
        self.repo.save(task)
        return task

    def tasks(self, user_id: str, garden_id: str) -> list[GardenTask]:
        require_role(self.repo, user_id, garden_id)
        return self.repo.list(GardenTask, garden_id)

    def schedule(self, user_id: str, garden_id: str) -> GardenSchedule:
        garden = require_role(self.repo, user_id, garden_id)
        return GardenSchedule(garden, self.repo.list(GardenTask, garden_id), self._labeler(garden_id))

    def complete_task(self, user_id: str, garden_id: str, task_id: str, completed_on: date | None = None,
                      completed_at: datetime | None = None):
        require_role(self.repo, user_id, garden_id, "editor")
        schedule = self.schedule(user_id, garden_id)
        done, following = schedule.complete(task_id, completed_on, completed_at)
        with self.repo.transaction():
            self.repo.save(done)
            if following is not None:
                self.repo.save(following)
        return done, following

    def update_task(self, user_id: str, garden_id: str, task_id: str, **changes) -> GardenTask:
        require_role(self.repo, user_id, garden_id, "editor")
        if not set(changes) <= EDITABLE_TASK_FIELDS:
            raise ValueError("Only task details can be edited.")
        updated = self.schedule(user_id, garden_id).update(task_id, **changes)
        self.repo.save(updated)
        return updated

    def delete_task(self, user_id: str, garden_id: str, task_id: str) -> None:
        require_role(self.repo, user_id, garden_id, "editor")
        task = self._owned(GardenTask, garden_id, task_id)
        if task.completed:
            raise ValueError("Completed tasks are kept as history.")
        self.repo.delete(GardenTask, task_id)

    # -- observations -----------------------------------------------------
    def add_observation(self, user_id: str, garden_id: str, planting_id: str, **details) -> Observation:
        require_role(self.repo, user_id, garden_id, "editor")
        self._owned(Planting, garden_id, planting_id)
        obs = Observation(garden_id, planting_id, **details)
        self.repo.save(obs)
        return obs

    def observations(self, user_id: str, garden_id: str, planting_id: str | None = None) -> list[Observation]:
        require_role(self.repo, user_id, garden_id)
        filters = {"planting_id": planting_id} if planting_id else {}
        return sorted(self.repo.list(Observation, garden_id, **filters), key=lambda o: o.observed_at)

    # -- recommendations --------------------------------------------------
    def store_recommendations(self, user_id: str, garden_id: str, recs: list[Recommendation]) -> list[Recommendation]:
        """Replace unanswered advice with a fresh evaluation.

        Advice the user already accepted or dismissed is kept and is not
        re-raised for the same rule_key.
        """
        require_role(self.repo, user_id, garden_id, "editor")
        answered = {r.rule_key for r in self.repo.list(Recommendation, garden_id, status=["accepted", "dismissed"])}
        fresh = [r for r in recs if r.rule_key not in answered]
        with self.repo.transaction():
            self.repo.delete_where(Recommendation, garden_id, status="new")
            for rec in fresh:
                if rec.garden_id != garden_id:
                    raise ValueError("Recommendation belongs to another garden.")
                self.repo.save(rec)
        return fresh

    def recommendations(self, user_id: str, garden_id: str, status: str | None = "new",
                        now: datetime | None = None) -> list[Recommendation]:
        require_role(self.repo, user_id, garden_id)
        filters = {} if status is None else {"status": status}
        recs = self.repo.list(Recommendation, garden_id, **filters)
        now = now or utcnow()
        order = {"action": 0, "watch": 1, "info": 2}
        return sorted([r for r in recs if status != "new" or not r.is_expired(now)],
                      key=lambda r: (order[r.severity], r.title))

    def accept_recommendation(self, user_id: str, garden_id: str, rec_id: str, due_date: date | None = None,
                              start_time: str | None = None) -> GardenTask | None:
        """Explicit user approval. Creates at most one task per recommendation."""
        require_role(self.repo, user_id, garden_id, "editor")
        rec = self._owned(Recommendation, garden_id, rec_id)
        task = None
        if rec.suggested_task:
            key = f"rec:{rec.id}"
            existing = self.repo.list(GardenTask, garden_id, idempotency_key=key)
            if existing:
                task = existing[0]
            else:
                spec = dict(rec.suggested_task)
                task = GardenTask(
                    garden_id, spec["description"], due_date or date.fromisoformat(spec["due_date"]),
                    start_time=start_time or spec.get("start_time", "08:00"),
                    duration_minutes=spec.get("duration_minutes", 15), priority=spec.get("priority", "medium"),
                    planting_id=rec.planting_id, growing_space_id=rec.growing_space_id,
                    recommendation_id=rec.id, source="suggested", idempotency_key=key)
        with self.repo.transaction():
            if task is not None:
                self.repo.save(task)
            self.repo.save(replace(rec, status="accepted"))
        log.info("recommendation accepted id=%s task=%s", rec.id, task.id if task else None)
        return task

    def dismiss_recommendation(self, user_id: str, garden_id: str, rec_id: str) -> Recommendation:
        require_role(self.repo, user_id, garden_id, "editor")
        rec = replace(self._owned(Recommendation, garden_id, rec_id), status="dismissed")
        self.repo.save(rec)
        log.info("recommendation dismissed id=%s", rec.id)
        return rec

    # -- helpers ----------------------------------------------------------
    def _owned(self, cls, garden_id: str, record_id: str):
        record = self.repo.get(cls, record_id) if record_id else None
        if record is None or record.garden_id != garden_id:
            raise ValueError(f"{cls.__name__} not found in this garden.")
        return record

    def _check_targets(self, garden_id, planting_id, space_id):
        if planting_id:
            self._owned(Planting, garden_id, planting_id)
        if space_id:
            self._owned(GrowingSpace, garden_id, space_id)

    def _labeler(self, garden_id: str):
        spaces = {s.id: s.name for s in self.repo.list(GrowingSpace, garden_id)}
        plantings = {}
        for p in self.repo.list(Planting, garden_id):
            variety = self.repo.get(SeedVariety, p.seed_variety_id)
            plantings[p.id] = p.nickname or (variety.label if variety else "Planting")
        return lambda key: plantings.get(key) or spaces.get(key)
