"""pyremindkit — vendored EventKit wrapper for the mcp-apple-reminders server.

Public surface re-exported here is INTENTIONALLY stable; consumers should rely
on `from pyremindkit import RemindKit, Reminder, Priority` without reaching
into submodules.

Internal layout (not part of the public API):
- `models` — value types (`Priority`, `Reminder`)
- `_internal` — EventKit/Foundation glue (`_grant_permission`, conversion helpers)
- `calendars` — `Calendar` dataclass + `CalendarManager`
- `core` — `RemindKit` orchestrator
"""

__version__ = "0.1.0"

from .calendars import Calendar, CalendarManager
from .core import RemindKit
from .models import Priority, Reminder

__all__ = ["RemindKit", "Reminder", "Priority", "Calendar", "CalendarManager"]
