"""Shared `ToolAnnotations` presets for the MCP tool surface (CL-2.10).

MCP `ToolAnnotations` are *hints* a client may use to render and gate tools —
read-only badges, destructive-action confirmations, retry safety. Apple
Reminders is a single, closed, local domain, so every tool sets
``openWorldHint=False``; the read/write split and the destructive/idempotent
shape are captured by four presets shared across the tool modules. Each tool
still supplies its own human-readable ``title=`` (the spec's display name) on
the decorator — the title is per-tool, the behavioral hints are shared.

Categories
----------
``READ``    Does not modify the store (get/list/search, and `triage_brain_dump`,
            which only reads + samples the LLM). ``readOnlyHint`` is the only
            meaningful flag; the others are left unset per the spec (they are
            "meaningful only when ``readOnlyHint == false``").
``CREATE``  Additive and *non*-idempotent: each call adds a new entity —
            `create_*`, `apply_template`, the `add_*` attachment/section tools,
            and the append-style `set_alarm` / `set_location_alarm`.
``MUTATE``  A converging setter: re-running with the same args leaves the store
            unchanged — `update_*` / `move_*` / `assign_*` / `complete_*` /
            `set_recurrence` / `set_urgent` / the pin & appearance tools.
``DESTROY`` May remove data — `delete_*` and `bulk_delete_completed`.
            Destructive and idempotent (deleting an already-gone item has no
            further effect).

The instances are shared (read-only) across tools; nothing mutates them after
registration.
"""

from __future__ import annotations

from mcp.types import ToolAnnotations

READ = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
CREATE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)
MUTATE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False)
DESTROY = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=False)
