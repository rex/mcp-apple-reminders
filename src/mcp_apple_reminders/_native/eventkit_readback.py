"""EventKit read-back summarizers: EKRecurrenceRule / EKAlarm -> human strings.

Recurrence and alarms are not in the SQLite store (they live in the opaque
CloudKit blob), so these summaries are sourced from EventKit on single-reminder
reads (`get_reminder`). See ADR 0002. The `*_summary` functions are pure
(testable with primitives); `summarize_*` are the thin EventKit adapters.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

_FREQ_LABEL = {0: "Daily", 1: "Weekly", 2: "Monthly", 3: "Yearly"}
_FREQ_UNIT = {0: "day", 1: "week", 2: "month", 3: "year"}
_DOW = {1: "Sun", 2: "Mon", 3: "Tue", 4: "Wed", 5: "Thu", 6: "Fri", 7: "Sat"}
_PROXIMITY = {1: "Arriving", 2: "Leaving"}


def recurrence_summary(
    frequency: int,
    interval: int,
    *,
    end_date: Optional[str] = None,
    end_count: Optional[int] = None,
    days_of_week: Optional[list[int]] = None,
    days_of_month: Optional[list[int]] = None,
) -> str:
    """Pure: render already-extracted recurrence parts into a human summary."""
    if interval and interval > 1:
        base = f"Every {interval} {_FREQ_UNIT.get(frequency, 'period')}s"
    else:
        base = _FREQ_LABEL.get(frequency, "Repeats")
    if days_of_week:
        base += " on " + ", ".join(_DOW.get(d, "?") for d in days_of_week)
    elif days_of_month:
        base += " on day " + ", ".join(str(d) for d in days_of_month)
    if end_date:
        base += f" until {end_date}"
    elif end_count:
        base += f" for {end_count} occurrences"
    return base


def alarm_summary(
    *,
    absolute_date: Optional[str] = None,
    proximity: int = 0,
    place: Optional[str] = None,
    radius: Optional[float] = None,
) -> Optional[str]:
    """Pure: render already-extracted alarm parts into a human summary, or None."""
    if proximity in _PROXIMITY:
        label = _PROXIMITY[proximity]
        text = f"{label}: {place}" if place else f"{label} a location"
        if radius:
            text += f" (within {int(radius)} m)"
        return text
    if absolute_date:
        return f"At {absolute_date}"
    return None


def _fmt(nsdate, *, date_only: bool = False) -> Optional[str]:
    """Best-effort format an NSDate (or datetime) into a local string."""
    if nsdate is None:
        return None
    if isinstance(nsdate, datetime):
        return nsdate.strftime("%Y-%m-%d" if date_only else "%Y-%m-%d %H:%M")
    if hasattr(nsdate, "timeIntervalSince1970"):
        dt = datetime.fromtimestamp(nsdate.timeIntervalSince1970())
        return dt.strftime("%Y-%m-%d" if date_only else "%Y-%m-%d %H:%M")
    return str(nsdate)


def summarize_recurrence(ek_item) -> Optional[str]:
    """Adapter: summarize an EKReminder's first recurrence rule (or None)."""
    rules = ek_item.recurrenceRules() if ek_item is not None else None
    if not rules:
        return None
    rule = rules[0]
    end = rule.recurrenceEnd()
    end_date = end_count = None
    if end is not None:
        if end.endDate() is not None:
            end_date = _fmt(end.endDate(), date_only=True)
        elif end.occurrenceCount():
            end_count = int(end.occurrenceCount())
    dow = rule.daysOfTheWeek()
    days_of_week = [int(d.dayOfTheWeek()) for d in dow] if dow else None
    dom = rule.daysOfTheMonth()
    days_of_month = [int(x) for x in dom] if dom else None
    return recurrence_summary(
        int(rule.frequency()),
        int(rule.interval()),
        end_date=end_date,
        end_count=end_count,
        days_of_week=days_of_week,
        days_of_month=days_of_month,
    )


def summarize_alarms(ek_item) -> list[str]:
    """Adapter: summarize an EKReminder's alarms into human strings."""
    if ek_item is None:
        return []
    out: list[str] = []
    for alarm in ek_item.alarms() or []:
        loc = alarm.structuredLocation()
        place = loc.title() if loc is not None else None
        radius = loc.radius() if loc is not None else None
        summary = alarm_summary(
            absolute_date=_fmt(alarm.absoluteDate()),
            proximity=int(alarm.proximity()),
            place=str(place) if place else None,
            radius=float(radius) if radius else None,
        )
        if summary:
            out.append(summary)
    return out
