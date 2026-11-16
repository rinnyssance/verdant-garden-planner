"""Shared UI helpers: page context, styling and small display components."""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import date, datetime

import streamlit as st

from verdant.domain.common import utcnow

STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap');
:root { --ivory:#F7F4EB; --forest:#234D3B; --sage:#A8BDA4; --terracotta:#BD7355; --gold:#C5A56A; --ink:#1F2B24; }
/* Text only: never override spans, so Streamlit's Material icon font keeps working. */
html, body, .stApp, p, label, input, textarea, li, td, th { font-family: 'Inter', system-ui, sans-serif; }
h1, h2, h3, .vd-title { font-family: 'Fraunces', Georgia, serif !important; color: var(--forest); letter-spacing: -0.01em; }
.stApp { background: var(--ivory); color: var(--ink); }
.block-container { padding-top: 1.5rem; max-width: 1100px; }
.vd-brand { display:flex; align-items:baseline; gap:.6rem; flex-wrap:wrap; margin-bottom:.25rem; }
.vd-brand .vd-title { font-size:2rem; font-weight:600; margin:0; }
.vd-brand .vd-tag { color:#4c5f52; font-size:.95rem; }
.vd-badge { display:inline-block; padding:.1rem .55rem; border-radius:999px; font-size:.78rem; font-weight:600;
            border:1px solid transparent; margin-right:.3rem; }
.vd-action { background:#F6E3DA; color:#7A3B22; border-color:#BD7355; }
.vd-watch { background:#F4EBD6; color:#6B5420; border-color:#C5A56A; }
.vd-info { background:#E4ECE2; color:#234D3B; border-color:#A8BDA4; }
.vd-review { background:#F4EBD6; color:#6B5420; }
.vd-ok { background:#E4ECE2; color:#234D3B; }
.vd-muted { color:#5b6a60; font-size:.9rem; }
div.stButton > button[kind="primary"], div.stFormSubmitButton > button[kind="primary"] {
    background: var(--forest); border-color: var(--forest); color: #fff; }
div.stButton > button:focus-visible, div.stFormSubmitButton > button:focus-visible { outline: 3px solid var(--gold); }
@media (max-width: 640px) {
  .block-container { padding-left: 1rem; padding-right: 1rem; }
  .vd-brand .vd-title { font-size: 1.6rem; }
}
</style>
"""

STAGE_LABELS = {"planned": "Planned", "sown": "Sown", "germinating": "Germinating", "seedling": "Seedling",
                "vegetative": "Vegetative", "flowering": "Flowering", "fruiting": "Fruiting",
                "harvesting": "Harvesting", "finished": "Finished"}
VERIFY_LABELS = {"verified": "Verified", "transcribed": "From packet photo", "needs_review": "Needs review",
                 "user_entered": "Entered by you"}


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


def garden_today(garden) -> date:
    """Today's date in the garden's own time zone (falls back to the computer's date)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo(garden.timezone)).date()
    except Exception:
        return date.today()


def badge(text: str, kind: str = "info") -> str:
    return f'<span class="vd-badge vd-{kind}">{html.escape(text)}</span>'


def esc(value) -> str:
    return html.escape(str(value))


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
