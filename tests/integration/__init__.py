"""Wire-level integration suite — NOT collected by pytest.

These modules drive a FRESH stdio MCP server (current code) against the LIVE
macOS Reminders store, so they require Reminders permission on the interpreter
and are run by hand / by an agent, not in the unit-test gate:

    ./venv/bin/python -m tests.integration.run $(date +%H%M%S)

Unit tests bypass MCP's structured-output validation (the datetime + elicitation
bugs proved this); the integration suite is the only layer that exercises the
real JSON-RPC wire, the native EventKit/ReminderKit helpers, and the SQLite
reader end-to-end. All data is created under a self-cleaning `MCP-IntegTest`
group/list and removed on exit.
"""

from __future__ import annotations

# Guard: ensure pytest never tries to collect this package as unit tests.
__test__ = False
