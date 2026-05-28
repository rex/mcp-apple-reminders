# Archived: 001-visibility-foundation

**Archived**: 2026-05-28
**Reason**: Scope materially expanded after research pass on gold-standard MCP server practices, current EventKit / ReminderKit reality, and competitor (`FradSer/mcp-server-apple-events`) feature parity.

**Superseded by**: `specs/002-modernize-and-foundation/`

The original spec assumed:
1. EventKit has a public subtask API. **It does not** — subtasks live in the private `ReminderKit.framework`.
2. The MCP server should stay on the low-level `Server` class. **No** — we're modernizing to FastMCP with Resources, Prompts, Sampling, Elicitation, lifespan, structured outputs.
3. Scope was P0 only (4 slices). **No** — Pierce approved all four phases (modernize → P0 → MCP primitives → feature parity + visibility-plane pilot), ~16-22 slices.

Slice 1.1 (`is_default` fix) DID land — preserved in git history (`117cc8a`). The fix is in `libs/pyremindkit/src/pyremindkit/calendars.py::CalendarManager.list()`. The new spec acknowledges that work in its Phase 1 prerequisites.

This directory is preserved verbatim for planning archaeology — what we thought before the research pass.
