"""CL-2.10 — lock the ToolAnnotations contract on every registered tool.

Every ``@mcp.tool`` must ship a human-readable ``title`` and a
``ToolAnnotations`` hint set. Apple Reminders is a closed local domain, so
``openWorldHint`` is always ``False``. Read tools set ``readOnlyHint=True`` and
leave the destructive/idempotent hints unset (they are "meaningful only when
``readOnlyHint == false``"); write tools set ``readOnlyHint=False`` and carry an
explicit destructive + idempotent stance. This guards against a new tool
landing without annotations — a silent 2.10 regression.
"""

from __future__ import annotations

import asyncio

from mcp_apple_reminders.server import mcp


def _tools():
    return asyncio.run(mcp.list_tools())


def test_every_tool_has_title_and_annotations() -> None:
    tools = _tools()
    assert tools, "no tools registered"
    missing_title = [t.name for t in tools if not (t.title and t.title.strip())]
    missing_ann = [t.name for t in tools if t.annotations is None]
    assert not missing_title, f"tools missing title: {missing_title}"
    assert not missing_ann, f"tools missing annotations: {missing_ann}"


def test_closed_world_everywhere() -> None:
    # Apple Reminders is a closed local domain — no tool is open-world.
    tools = _tools()
    open_world = [t.name for t in tools if t.annotations.openWorldHint is not False]
    assert not open_world, f"tools with openWorldHint != False: {open_world}"


def test_hint_coherence() -> None:
    # Read tools are read-only and leave destructive/idempotent unset; write
    # tools are not read-only and carry an explicit destructive + idempotent
    # stance.
    tools = _tools()
    for t in tools:
        a = t.annotations
        if a.readOnlyHint:
            assert a.destructiveHint is None, f"{t.name}: read-only tool sets destructiveHint"
            assert a.idempotentHint is None, f"{t.name}: read-only tool sets idempotentHint"
        else:
            assert a.destructiveHint is not None, f"{t.name}: write tool missing destructiveHint"
            assert a.idempotentHint is not None, f"{t.name}: write tool missing idempotentHint"
