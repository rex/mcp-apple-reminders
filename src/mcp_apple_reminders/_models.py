"""Pydantic input/output models for the MCP server.

Output models double as the structured payload returned to clients:
FastMCP serializes them to JSON inside the tool result, while the
``__str__`` we provide gives a human-friendly representation for clients
that only render text.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — pydantic resolves at runtime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ._helpers import priority_label


class Calendar(BaseModel):
    """A Reminders list (Apple calls these "calendars" internally)."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    color: str | None = None
    is_default: bool = False
    owner: str | None = None

    def __str__(self) -> str:
        flag = " [default]" if self.is_default else ""
        return f"{self.name}{flag}  ({self.id})"


class Reminder(BaseModel):
    """A single Apple Reminder item."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    completed: bool = False
    due_date: datetime | None = None
    notes: str | None = None
    url: str | None = None
    priority: int = 0
    flagged: bool = False
    list_id: str | None = None
    created_date: datetime | None = None
    modified_date: datetime | None = None

    def __str__(self) -> str:
        bits: list[str] = [self.title]
        if self.completed:
            bits.append("✓")
        if self.flagged:
            bits.append("⚑")
        if self.due_date is not None:
            bits.append(f"due {self.due_date.isoformat()}")
        bits.append(f"[{priority_label(self.priority)}]")
        bits.append(f"({self.id})")
        return " ".join(bits)


class CalendarList(BaseModel):
    calendars: list[Calendar]
    count: int = Field(..., description="Number of calendars returned.")


class ReminderList(BaseModel):
    reminders: list[Reminder]
    count: int = Field(..., description="Number of reminders returned.")


class OperationResult(BaseModel):
    """Generic ack for write operations that don't return a Reminder."""

    success: bool
    message: str
    data: dict[str, Any] | None = None


def reminder_from_obj(obj: Any) -> Reminder:
    """Coerce a pyremindkit Reminder-like object into our Pydantic model.

    pyremindkit returns its own Reminder dataclass; we accept anything with
    the expected attribute names, so unit tests can pass plain SimpleNamespaces.
    """
    return Reminder(
        id=str(obj.id),
        title=obj.title,
        completed=bool(getattr(obj, "completed", False)),
        due_date=getattr(obj, "due_date", None),
        notes=getattr(obj, "notes", None),
        url=getattr(obj, "url", None),
        priority=int(getattr(obj, "priority", 0) or 0),
        flagged=bool(getattr(obj, "flagged", False)),
        list_id=getattr(obj, "list_id", None),
        created_date=getattr(obj, "created_date", None),
        modified_date=getattr(obj, "modified_date", None),
    )


def calendar_from_obj(obj: Any) -> Calendar:
    """Coerce a pyremindkit Calendar-like object into our Pydantic model."""
    return Calendar(
        id=str(obj.id),
        name=obj.name,
        color=getattr(obj, "color", None),
        is_default=bool(getattr(obj, "is_default", False)),
        owner=getattr(obj, "owner", None),
    )
