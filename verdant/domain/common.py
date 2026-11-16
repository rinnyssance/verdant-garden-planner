"""Small validation helpers shared by every Verdant domain model."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4


def new_id() -> str:
    """Return an opaque identifier; never shown to people in the UI."""
    return uuid4().hex


def utcnow() -> datetime:
    """Timezone-aware 'now' so stored timestamps are unambiguous."""
    return datetime.now(timezone.utc).replace(microsecond=0)


def text(value, label: str) -> str:
    """Trim required text and reject blanks."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} cannot be blank.")
    return value.strip()


def optional_text(value) -> str | None:
    """Trim optional text; blank strings become None (unknown)."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Expected text.")
    return value.strip() or None


def choice(value, options, label: str) -> str:
    """Reject values outside a fixed vocabulary."""
    if value not in options:
        raise ValueError(f"{label} must be one of: {', '.join(options)}.")
    return value


def optional_number(value, label: str, *, minimum: float = 0, maximum: float | None = None,
                    integer: bool = False):
    """Validate an optional measurement. None means 'not known', never zero."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number.")
    if integer and int(value) != value:
        raise ValueError(f"{label} must be a whole number.")
    if value < minimum or (maximum is not None and value > maximum):
        upper = f" and {maximum}" if maximum is not None else ""
        raise ValueError(f"{label} must be between {minimum}{upper}." if upper
                         else f"{label} must be at least {minimum}.")
    return int(value) if integer else float(value)
