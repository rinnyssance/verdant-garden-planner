"""Shared UI helpers: page context, notices and small utilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

import streamlit as st

from verdant.domain.common import utcnow

from .theme import CSS, chip, esc  # noqa: F401  (re-exported for screens)

STYLE = CSS

STAGE_LABELS = {"planned": "Planned", "sown": "Sown", "germinating": "Germinating", "seedling": "Seedling",
                "vegetative": "Vegetative", "flowering": "Flowering", "fruiting": "Fruiting",
                "harvesting": "Harvesting", "finished": "Finished"}
VERIFY_LABELS = {"verified": "Verified", "transcribed": "From packet photo", "needs_review": "Needs review",
                 "user_entered": "Entered by you"}
VERIFY_TONE = {"verified": "", "transcribed": "ink", "needs_review": "gold", "user_entered": "out"}


@dataclass
class Page:
    service: object
    weather: object
    user_id: str
    garden: object
    today: date

    @property
    def gid(self) -> str:
        return self.garden.id

    def key(self, name: str) -> str:
        """Widget keys are per garden so switching gardens never carries form state across."""
        return f"{self.gid}:{name}"

    def card(self, name: str):
        """A styled card container (CSS targets the st-key-vc- prefix)."""
        safe = "".join(ch if ch.isalnum() else "-" for ch in f"{self.gid[:8]}-{name}")
        return st.container(key=f"vc-{safe}")


def garden_now(garden) -> datetime:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo(garden.timezone))
    except Exception:
        return datetime.now()


def garden_today(garden) -> date:
    """Today's date in the garden's own time zone (falls back to the computer's date)."""
    return garden_now(garden).date()


def html(markup: str):
    st.markdown(markup, unsafe_allow_html=True)


def badge(text: str, kind: str = "info") -> str:
    return f'<span class="vd-chip vd-sev-{kind}">{esc(text)}</span>'


def notify(message: str, kind: str = "success"):
    st.session_state["vd_notice"] = (kind, message)
    st.rerun()


def show_notice():
    if "vd_notice" in st.session_state:
        kind, message = st.session_state.pop("vd_notice")
        getattr(st, kind)(message)
        st.toast(message)  # visible even when the page is scrolled down


def run_safely(action, success: str | None = None):
    """Show validation errors in place instead of crashing the page."""
    try:
        result = action()
    except (ValueError, PermissionError) as error:
        st.error(str(error))
        return None
    if success:
        notify(success)
    return result


def optional(value):
    """Streamlit returns '' for empty text inputs; store unknowns as None."""
    if isinstance(value, str):
        return value.strip() or None
    return value


def ago(moment: datetime | None) -> str:
    if moment is None:
        return "never"
    minutes = int((utcnow() - moment).total_seconds() // 60)
    if minutes < 1:
        return "just now"
    if minutes < 90:
        return f"{minutes} min ago"
    return f"{minutes // 60} h ago" if minutes < 48 * 60 else f"{moment:%Y-%m-%d %H:%M} UTC"


def days_ago(day: date, today: date) -> str:
    delta = (today - day).days
    return "today" if delta == 0 else "yesterday" if delta == 1 else f"{delta} days ago" if delta > 0 else f"in {-delta} days"


def plant_photo(page: Page, planting_id: str) -> str | None:
    """Most recent journal photo for a planting, if the user has taken one."""
    from verdant.services.photos import photo_belongs_to
    for obs in reversed(page.service.observations(page.user_id, page.gid, planting_id)):
        if photo_belongs_to(obs.photo_path, page.gid):
            return obs.photo_path
    return None
