"""Reminder CRUD MCP tools — FastMCP edition.

Six operations: create, update, complete (sugar over update), uncomplete
(sugar), get-by-id, delete. The complete/uncomplete handlers are thin
wrappers that call `update_reminder(is_completed=…)` so they stay in sync
with the canonical update path automatically.
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import Context

from .._native.eventkit_readback import summarize_alarms, summarize_recurrence
from .._native.reminderkit import (
    ReminderKitHelperError,
    ReminderKitHelperUnavailable,
)
from .._native.reminderkit_actions import (
    add_tags as helper_add_tags,
)
from .._native.reminderkit_actions import (
    clear_tags as helper_clear_tags,
)
from .._native.reminderkit_actions import (
    create_subtask as helper_create_subtask,
)
from .._native.reminderkit_actions import (
    set_flagged as helper_set_flagged,
)
from .._native.sqlite import Reader, RemindersDBUnavailable
from ..formatting import parse_datetime, parse_priority
from ..lifespan import app_context as _app_context
from ..lifespan import bridge_from_ctx as _bridge_from_ctx
from ..models import Reminder, native_reminder_to_pydantic, reminder_deeplink
from ..results import DeleteResult
from ..server import mcp
from ._annotations import CREATE, DESTROY, MUTATE, READ


@mcp.tool(
    name="create_reminder",
    title="Create Reminder",
    annotations=CREATE,
    description=(
        "Create a new reminder in Apple Reminders. You can specify the title, "
        "due date, notes, priority, URL, and which calendar (list) to add it "
        "to. If no calendar is specified, it will be added to the default list."
    ),
)
async def create_reminder(
    title: str,
    ctx: Context,
    due_date: Optional[str] = None,
    notes: Optional[str] = None,
    priority: Optional[str] = None,
    url: Optional[str] = None,
    calendar_id: Optional[str] = None,
    parent_reminder_id: Optional[str] = None,
    flagged: Optional[bool] = None,
) -> Reminder:
    """Create a new reminder. If `parent_reminder_id` is set, creates a subtask.

    Subtasks inherit the parent's list automatically. Passing both
    `parent_reminder_id` and `calendar_id` that don't match the parent's
    list raises ValueError.

    Args:
        title: The title/name of the reminder.
        due_date: ISO format datetime string. Optional.
        notes: Additional notes. Optional.
        priority: 'none', 'low', 'medium', 'high', or integer 0-9. Optional.
        url: URL to associate. Optional.
        calendar_id: Calendar ID. If not specified, uses the default. Optional.
        parent_reminder_id: When set, route through the ReminderKit helper
            and create a subtask under this parent. Subtask inherits the
            parent's calendar. Optional.
    """
    app = _app_context(ctx)

    if parent_reminder_id:
        # Subtask path — ReminderKit private API.
        # Resolve parent + its list via SQLite for the calendar mismatch check.
        parent_list_id: Optional[str] = None
        try:
            with app.open_sqlite() as conn:
                parent = Reader(conn).get_reminder_by_id(parent_reminder_id)
                if parent is None:
                    raise ValueError(f"Parent reminder {parent_reminder_id!r} not found.")
                parent_list_id = parent.list_id
        except RemindersDBUnavailable:
            # If SQLite is unavailable, skip the upfront sanity check — the
            # ReminderKit helper itself will fail with a clear error if the
            # parent doesn't exist.
            await ctx.warning("SQLite read path unavailable; cannot pre-check parent existence/calendar.")

        if calendar_id and parent_list_id and calendar_id != parent_list_id:
            raise ValueError(
                f"calendar_id {calendar_id!r} doesn't match the parent reminder's "
                f"calendar {parent_list_id!r}. Subtasks always live in the parent's list."
            )

        try:
            response = helper_create_subtask(parent_reminder_id, title)
        except ReminderKitHelperUnavailable as e:
            await ctx.error(f"ReminderKit helper unavailable: {e}")
            raise ValueError(f"ReminderKit helper not built. Run `make build-native`. ({e})") from e
        except ReminderKitHelperError as e:
            await ctx.error(f"create subtask failed: {e.message}")
            raise ValueError(e.message) from e

        # Extract the new subtask's UUID + url.
        subtask_meta = (response.get("subtasks") or [{}])[0]
        new_id = str(subtask_meta.get("id") or "")
        if not new_id:
            raise ValueError(f"ReminderKit helper succeeded but did not return a subtask id: {response!r}")

        # Build the Pydantic — the helper doesn't echo every field, so we
        # fall back to a freshly-constructed Reminder. Downstream callers
        # who want the canonical view can `get_reminder(new_id)`.
        created = Reminder(
            id=new_id,
            title=title,
            list_id=parent_list_id or "",
            parent_reminder_id=parent_reminder_id,
            deeplink=reminder_deeplink(new_id),
        )
        await ctx.info(f"Created subtask {new_id} under {parent_reminder_id} ({title!r})")
        return created

    # Top-level reminder — EventKit path (existing behavior).
    kwargs: dict = {"title": title}
    if due_date:
        kwargs["due_date"] = parse_datetime(due_date)
    if notes:
        kwargs["notes"] = notes
    if priority:
        kwargs["priority"] = parse_priority(priority)
    if url:
        kwargs["url"] = url
    if calendar_id:
        kwargs["calendar_id"] = calendar_id

    created = native_reminder_to_pydantic(app.bridge.create_reminder(**kwargs))

    # Post-create flagged: ReminderKit private API. Skip if not requested.
    if flagged is not None:
        try:
            helper_set_flagged(created.id, flagged)
        except ReminderKitHelperUnavailable as e:
            await ctx.error(f"set_flagged via ReminderKit unavailable: {e}")
            raise ValueError(f"ReminderKit helper not built. Run `make build-native`. ({e})") from e
        except ReminderKitHelperError as e:
            await ctx.error(f"set_flagged failed: {e.message}")
            raise ValueError(e.message) from e
        # Re-stamp the Pydantic with the flag we just set (the bridge return
        # predates the helper write).
        created = created.model_copy(update={"flagged": bool(flagged)})

    await ctx.info(f"Created reminder {created.id} in list {created.list_id}: {created.title!r}")
    return created


@mcp.tool(
    name="update_reminder",
    title="Update Reminder",
    annotations=MUTATE,
    description=(
        "Update an existing reminder. You can modify any combination of: title, "
        "due date, notes, priority, URL, completion status, flag, and tags (add "
        "and/or clear). Only the fields you specify are updated; others remain "
        "unchanged. For tag replacement, pass clear_tags=true together with "
        "add_tags=[...] (the clear is applied first)."
    ),
)
async def update_reminder(
    reminder_id: str,
    ctx: Context,
    title: Optional[str] = None,
    due_date: Optional[str] = None,
    notes: Optional[str] = None,
    priority: Optional[str] = None,
    url: Optional[str] = None,
    is_completed: Optional[bool] = None,
    flagged: Optional[bool] = None,
    add_tags: Optional[list[str]] = None,
    clear_tags: bool = False,
) -> Reminder:
    """Update an existing reminder.

    Args:
        reminder_id: The unique identifier of the reminder to update.
        title: New title for the reminder. Optional.
        due_date: New due date in ISO format (e.g., '2024-01-15T14:30:00'). Optional.
        notes: New notes/description. Optional.
        priority: New priority: 'none', 'low', 'medium', 'high', or integer 0-9. Optional.
        url: New URL to associate with the reminder. Optional.
        is_completed: Mark the reminder as completed (true) or incomplete (false). Optional.
        flagged: Set or clear the reminder's flag (via the ReminderKit helper). Optional.
        add_tags: Tags to add (merged with existing; via the ReminderKit helper). Optional.
        clear_tags: Remove all existing tags first (via the ReminderKit helper). Combine
            with add_tags for replacement semantics. Default False.
    """
    kwargs: dict = {}
    if title:
        kwargs["title"] = title
    if due_date:
        kwargs["due_date"] = parse_datetime(due_date)
    if notes is not None:
        # Empty string is an explicit clear, not a no-op.
        kwargs["notes"] = notes
    if priority:
        kwargs["priority"] = parse_priority(priority)
    if url is not None:
        kwargs["url"] = url
    if is_completed is not None:
        kwargs["is_completed"] = is_completed

    bridge = _bridge_from_ctx(ctx)
    # Only invoke EventKit update if there are EventKit-side changes.
    if kwargs:
        updated = native_reminder_to_pydantic(bridge.update_reminder(reminder_id, **kwargs))
    else:
        updated = native_reminder_to_pydantic(bridge.get_reminder_by_id(reminder_id))

    if flagged is not None:
        try:
            helper_set_flagged(reminder_id, flagged)
        except ReminderKitHelperUnavailable as e:
            await ctx.error(f"set_flagged via ReminderKit unavailable: {e}")
            raise ValueError(f"ReminderKit helper not built. Run `make build-native`. ({e})") from e
        except ReminderKitHelperError as e:
            await ctx.error(f"set_flagged failed: {e.message}")
            raise ValueError(e.message) from e
        updated = updated.model_copy(update={"flagged": bool(flagged)})

    # Clear before add so (clear_tags + add_tags) yields replacement semantics.
    if clear_tags:
        try:
            helper_clear_tags(reminder_id)
        except ReminderKitHelperUnavailable as e:
            await ctx.error(f"clear_tags via ReminderKit unavailable: {e}")
            raise ValueError(f"ReminderKit helper not built. Run `make build-native`. ({e})") from e
        except ReminderKitHelperError as e:
            await ctx.error(f"clear_tags failed: {e.message}")
            raise ValueError(e.message) from e
        updated = updated.model_copy(update={"tags": []})

    if add_tags:
        try:
            helper_add_tags(reminder_id, add_tags)
        except ReminderKitHelperUnavailable as e:
            await ctx.error(f"add_tags via ReminderKit unavailable: {e}")
            raise ValueError(f"ReminderKit helper not built. Run `make build-native`. ({e})") from e
        except ReminderKitHelperError as e:
            await ctx.error(f"add_tags failed: {e.message}")
            raise ValueError(e.message) from e
        merged_tags = sorted(set(updated.tags) | set(add_tags))
        updated = updated.model_copy(update={"tags": merged_tags})

    fields = sorted(kwargs.keys())
    if flagged is not None:
        fields.append("flagged")
    if clear_tags:
        fields.append("tags-cleared")
    if add_tags:
        fields.append("tags+=")
    await ctx.info(f"Updated reminder {reminder_id}: fields={fields}")
    return updated


@mcp.tool(
    name="complete_reminder",
    title="Complete Reminder",
    annotations=MUTATE,
    description=(
        "Mark a reminder as completed. This is a convenience tool that's "
        "equivalent to calling update_reminder with is_completed=true."
    ),
)
async def complete_reminder(reminder_id: str, ctx: Context) -> Reminder:
    """Mark a reminder as completed.

    Args:
        reminder_id: The unique identifier of the reminder to mark as complete.
    """
    bridge = _bridge_from_ctx(ctx)
    result = native_reminder_to_pydantic(bridge.update_reminder(reminder_id, is_completed=True))
    await ctx.info(f"Completed reminder {reminder_id}")
    return result


@mcp.tool(
    name="uncomplete_reminder",
    title="Uncomplete Reminder",
    annotations=MUTATE,
    description=(
        "Mark a reminder as incomplete/not done. This is useful for reopening "
        "a reminder that was previously completed."
    ),
)
async def uncomplete_reminder(reminder_id: str, ctx: Context) -> Reminder:
    """Mark a reminder as incomplete.

    Args:
        reminder_id: The unique identifier of the reminder to mark as incomplete.
    """
    bridge = _bridge_from_ctx(ctx)
    result = native_reminder_to_pydantic(bridge.update_reminder(reminder_id, is_completed=False))
    await ctx.info(f"Uncompleted reminder {reminder_id}")
    return result


@mcp.tool(
    name="get_reminder",
    title="Get Reminder",
    annotations=READ,
    description=(
        "Get a specific reminder by its unique ID. Returns all details about "
        "the reminder including title, due date, notes, priority, completion "
        "status, tags, early reminders, and — enriched from EventKit on this "
        "single-item read — its recurrence summary and alarm summaries."
    ),
)
async def get_reminder(reminder_id: str, ctx: Context) -> Reminder:
    """Get a reminder by its unique ID. SQLite-first; EventKit fallback.

    `recurrence` + `alarms` are summarized from EventKit on this single-item read
    (ADR 0002); bulk list queries omit them to stay on the fast SQLite path.

    Args:
        reminder_id: The unique identifier of the reminder.
    """
    app = _app_context(ctx)
    base: Optional[Reminder] = None
    try:
        with app.open_sqlite() as conn:
            base = Reader(conn).get_reminder_by_id(reminder_id)
    except RemindersDBUnavailable as e:
        await ctx.warning(f"SQLite read path unavailable ({e}); falling back to EventKit.")
    if base is None:
        base = native_reminder_to_pydantic(app.bridge.get_reminder_by_id(reminder_id))

    # EventKit enrichment: recurrence + alarm summaries (single-read; ADR 0002).
    try:
        ek_item = app.bridge._event_store.calendarItemWithIdentifier_(reminder_id)  # noqa: SLF001
    except Exception as e:  # best-effort — any EventKit hiccup returns the un-enriched reminder
        await ctx.debug(f"EventKit enrichment skipped ({type(e).__name__}).")
        return base
    if ek_item is None:
        return base
    recurrence = summarize_recurrence(ek_item)
    alarms = summarize_alarms(ek_item)
    if recurrence is None and not alarms:
        return base
    return base.model_copy(update={"recurrence": recurrence, "alarms": alarms})


@mcp.tool(
    name="delete_reminder",
    title="Delete Reminder",
    annotations=DESTROY,
    description=(
        "Permanently delete a reminder. This action cannot be undone. The "
        "reminder will be removed from Apple Reminders entirely."
    ),
)
async def delete_reminder(reminder_id: str, ctx: Context) -> DeleteResult:
    """Permanently delete a reminder.

    Args:
        reminder_id: The unique identifier of the reminder to delete.
    """
    bridge = _bridge_from_ctx(ctx)
    await ctx.warning(f"Deleting reminder {reminder_id} (destructive, no undo)")
    success = bridge.delete_reminder(reminder_id)
    if success:
        await ctx.info(f"Deleted reminder {reminder_id}")
    else:
        await ctx.error(f"Failed to delete reminder {reminder_id}")
    return DeleteResult.of(
        deleted=bool(success),
        message=(
            f"Reminder {reminder_id} deleted successfully." if success else f"Failed to delete reminder {reminder_id}."
        ),
        reminder_id=reminder_id,
    )
