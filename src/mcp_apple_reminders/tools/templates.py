"""List-template MCP tools — CL-2.3.

Templates capture a list's structure for reuse (a flagship macOS Sequoia
Reminders feature). `create_template` snapshots an existing list; `apply_template`
spins up a fresh list from a template; `delete_template` removes one. Backed by
the Obj-C ReminderKit helper (private API).
"""

from __future__ import annotations

from mcp.server.fastmcp import Context

from .._native.reminderkit import ReminderKitHelperError, ReminderKitHelperUnavailable
from .._native.reminderkit_content import (
    apply_template as helper_apply_template,
)
from .._native.reminderkit_content import (
    create_template as helper_create_template,
)
from .._native.reminderkit_content import (
    delete_template as helper_delete_template,
)
from ..results import DeleteResult, WriteResult
from ..server import mcp
from ._annotations import CREATE, DESTROY


def _run(fn, *args, **kwargs) -> dict:
    """Run a helper wrapper, translating helper errors into ValueErrors."""
    try:
        return fn(*args, **kwargs)
    except ReminderKitHelperUnavailable as e:
        raise ValueError(f"ReminderKit helper not built. Run `make build-native`. ({e})") from e
    except ReminderKitHelperError as e:
        raise ValueError(e.message) from e


@mcp.tool(
    name="create_template",
    title="Create Template",
    annotations=CREATE,
    description=(
        "Save an existing list as a reusable template. Pass `name` for the "
        "template and `source_list_id` (the list UUID to snapshot). Set "
        "`include_completed=true` to also capture completed reminders "
        "(default: structure + incomplete items only). Private ReminderKit API."
    ),
)
async def create_template(
    name: str,
    source_list_id: str,
    ctx: Context,
    include_completed: bool = False,
) -> WriteResult:
    """Save `source_list_id` as a template named `name`."""
    if not name or not name.strip():
        raise ValueError("name is required and must be non-empty")
    if not source_list_id or not source_list_id.strip():
        raise ValueError("source_list_id is required and must be non-empty")
    resp = _run(helper_create_template, name, source_list_id, include_completed=include_completed)
    tid = str(resp.get("id") or "")
    await ctx.info(f"Created template {tid} ({name!r}) from list {source_list_id}")
    return WriteResult.of(status=resp.get("status", "created"), id=tid, name=name, source_list_id=source_list_id)


@mcp.tool(
    name="apply_template",
    title="Apply Template",
    annotations=CREATE,
    description=(
        "Create a new list from a template by its UUID. Returns the new list's " "id. Private ReminderKit API."
    ),
)
async def apply_template(template_id: str, ctx: Context) -> WriteResult:
    """Instantiate a new list from `template_id`."""
    if not template_id or not template_id.strip():
        raise ValueError("template_id is required and must be non-empty")
    resp = _run(helper_apply_template, template_id)
    new_id = str(resp.get("id") or "")
    await ctx.info(f"Applied template {template_id} -> new list {new_id}")
    return WriteResult.of(status=resp.get("status", "created"), template_id=template_id, id=new_id)


@mcp.tool(
    name="delete_template",
    title="Delete Template",
    annotations=DESTROY,
    description=(
        "Permanently delete a list template by its UUID. Does not affect lists "
        "already created from it. DESTRUCTIVE. Private ReminderKit API."
    ),
)
async def delete_template(template_id: str, ctx: Context) -> DeleteResult:
    """Delete a template by UUID."""
    if not template_id or not template_id.strip():
        raise ValueError("template_id is required and must be non-empty")
    await ctx.warning(f"Deleting template {template_id} (destructive)")
    resp = _run(helper_delete_template, template_id)
    await ctx.info(f"Deleted template {template_id}")
    return DeleteResult.of(deleted=True, id=template_id, status=resp.get("status", "deleted"))
