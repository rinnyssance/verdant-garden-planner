"""A user can only read or change gardens they are a member of."""

from datetime import date

import pytest

from verdant.domain import SeedVariety
from verdant.persistence import SQLiteRepository
from verdant.services.access import AccessDenied
from verdant.services.garden_service import GardenService

DAY = date(2026, 11, 16)


@pytest.fixture
def setup():
    service = GardenService(SQLiteRepository())
    for uid in ("operator", "mom", "stranger"):
        service.ensure_user(uid, uid.title())
    mine = service.create_garden("operator", "My Garden")
    moms = service.create_garden("operator", "Mom's Garden")
    return service, mine, moms


def test_non_member_cannot_read_or_write(setup):
    service, mine, _ = setup
    assert service.gardens("stranger") == []
    for call in (lambda: service.garden("stranger", mine.id),
                 lambda: service.tasks("stranger", mine.id),
                 lambda: service.inventory("stranger", mine.id),
                 lambda: service.add_task("stranger", mine.id, "Water", DAY),
                 lambda: service.add_space("stranger", mine.id, "Bed")):
        with pytest.raises(AccessDenied):
            call()


def test_unknown_garden_looks_the_same_as_forbidden(setup):
    service, _, _ = setup
    with pytest.raises(AccessDenied, match="do not have access"):
        service.garden("operator", "does-not-exist")


def test_invited_mom_sees_only_her_garden(setup):
    service, mine, moms = setup
    service.grant_access("operator", moms.id, "mom", "editor")
    assert [g.display_name for g in service.gardens("mom")] == ["Mom's Garden"]
    service.add_seed("mom", moms.id, SeedVariety("Zinnia", "flower"))
    with pytest.raises(AccessDenied):
        service.inventory("mom", mine.id)
    with pytest.raises(AccessDenied):  # editors cannot manage membership
        service.grant_access("mom", moms.id, "stranger", "viewer")


def test_viewer_can_read_but_not_write(setup):
    service, mine, _ = setup
    service.grant_access("operator", mine.id, "mom", "viewer")
    assert service.tasks("mom", mine.id) == []
    with pytest.raises(AccessDenied):
        service.add_task("mom", mine.id, "Water", DAY)
    with pytest.raises(AccessDenied):
        service.update_garden("mom", mine.id, city="Elsewhere")
