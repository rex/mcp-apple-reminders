# Tech Stack

- Python 3.10+ minimum (`requires-python` in pyproject.toml). Repo venv runs 3.13.5 (miniconda).
- `mcp>=0.1.0` — Model Context Protocol Python SDK
- `pyobjc-core>=10.0`, `pyobjc-framework-EventKit>=10.0` — Objective-C bridge for EventKit
- `pyremindkit` — vendored in `libs/pyremindkit/src/`, version `0.1.0`, not on PyPI
- Dev tools: `pytest>=7.0`, `black>=23.0`, `ruff>=0.1.0`

## Build / install

- `setuptools>=61.0` build backend; editable install via `pip install -e .` from repo root.
- `./install.sh` creates `./venv` and runs the editable install.
- No Docker. macOS-only.

## EventKit constraints

- `requestFullAccessToRemindersWithCompletion_` is the post-Sequoia API (used in `_grant_permission`). Older `requestAccessToEntityType:completion:` is also valid but not used.
- EventKit calls dispatch async; `pyremindkit` uses `threading.Event` to sync-wait on Cocoa completion handlers.
- Date semantics: `EKReminder` uses `dueDateComponents` (an `NSDateComponents`), not a single `NSDate`. Conversion goes through `NSCalendar.currentCalendar().components_fromDate_`.
- Priority semantics: integer 0-9 in EventKit (0=none, 1-4=low, 5=medium, 6-9=high). Server-side enum maps to {0, 1, 5, 9}.

## macOS APIs touched

- `EventKit` (EKEventStore, EKCalendar, EKReminder, EKEntityTypeReminder)
- `Foundation` (NSCalendar, NSDate, NSURL, NSCalendarUnit*)
- `objc` (raw bridge — used for the completion-handler glue)
- `osascript` via subprocess (in `shim_mcp.sh`, for the permission-prompt nudge)
