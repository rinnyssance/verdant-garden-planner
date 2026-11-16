"""Membership-based authorization. Mirrors the RLS policies planned for Supabase."""

from __future__ import annotations

from verdant.domain import Garden, GardenMembership

ROLE_RANK = {"viewer": 0, "editor": 1, "owner": 2}


class AccessDenied(PermissionError):
    """Raised when a user has no (or too weak a) membership for a garden."""


def membership(repo, user_id: str, garden_id: str) -> GardenMembership | None:
    found = repo.list(GardenMembership, garden_id=garden_id, user_id=user_id)
    return found[0] if found else None


def require_role(repo, user_id: str, garden_id: str, minimum: str = "viewer") -> Garden:
    """Return the garden if the user may act on it; otherwise raise AccessDenied.

    The same message is used for 'no such garden' and 'not a member' so the
    check never reveals which gardens exist.
    """
    found = membership(repo, user_id, garden_id)
    garden = repo.get(Garden, garden_id) if found else None
    if garden is None:
        raise AccessDenied("You do not have access to that garden.")
    if ROLE_RANK[found.role] < ROLE_RANK[minimum]:
        raise AccessDenied(f"This action needs {minimum} access to {garden.display_name}.")
    return garden


def gardens_for(repo, user_id: str) -> list[Garden]:
    ids = [m.garden_id for m in repo.list(GardenMembership, user_id=user_id)]
    return [g for g in (repo.get(Garden, gid) for gid in ids) if g is not None]
