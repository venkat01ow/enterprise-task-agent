"""Lightweight natural-language date resolution for tool parameters.

Turns words like 'today', 'tomorrow', 'thursday', 'next week', or an explicit
``dd-mm-yyyy`` / ``dd/mm/yyyy`` into a concrete :class:`datetime.date`, and
produces ISO datetime windows for calendar events.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

_WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def resolve_date(text: str, base: date | None = None) -> date:
    """Best-effort resolution of a date expression to a concrete date."""
    base = base or date.today()
    lowered = (text or "").lower()

    explicit = re.search(r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})\b", lowered)
    if explicit:
        day, month, year = (int(g) for g in explicit.groups())
        if year < 100:
            year += 2000
        try:
            return date(year, month, day)
        except ValueError:
            return base

    if "today" in lowered:
        return base
    if "tomorrow" in lowered:
        return base + timedelta(days=1)
    if "next week" in lowered:
        return base + timedelta(days=7)

    for name, index in _WEEKDAYS.items():
        if name in lowered:
            days_ahead = (index - base.weekday()) % 7
            # "Thursday" said on a Thursday means the next one.
            return base + timedelta(days=days_ahead or 7)

    return base


def work_window(day: date, start_hour: int = 9, end_hour: int = 18) -> tuple[str, str]:
    """Return (start_iso, end_iso) naive local datetimes for a working day."""
    start = f"{day.isoformat()}T{start_hour:02d}:00:00"
    end = f"{day.isoformat()}T{end_hour:02d}:00:00"
    return start, end


def all_day_window(day: date) -> tuple[str, str]:
    """Return (start_iso, end_iso) for an all-day event (midnight to midnight)."""
    start = f"{day.isoformat()}T00:00:00"
    end = f"{(day + timedelta(days=1)).isoformat()}T00:00:00"
    return start, end
