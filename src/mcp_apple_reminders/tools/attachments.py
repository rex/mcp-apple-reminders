"""Attachment MCP tools — CL-2.6.

`add_url_attachment` and `add_metadata` are *unprivileged*: web URLs / hashtags
only, no filesystem. `add_file_attachment` reads local files off disk and embeds
them into Reminders, so it is *privileged* — it is gated behind the opt-in
``MCP_APPLE_REMINDERS_ENABLE_FILE_ATTACHMENTS`` env var (default OFF) and
validates every path (absolute, exists, regular file, readable, size cap) before
the helper touches it. Generic files use ReminderKit's
``addFileAttachmentWithURL:``; image files route to the image attachment path so
they render with a thumbnail. Backed by the Obj-C ReminderKit helper (private
API).
"""

from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import Context

from .._native.reminderkit import ReminderKitHelperError, ReminderKitHelperUnavailable
from .._native.reminderkit_content import add_file_attachments as helper_add_file_attachments
from .._native.reminderkit_content import add_private_metadata as helper_add_private_metadata
from .._native.reminderkit_content import add_url_attachments as helper_add_url_attachments
from ..server import mcp
from ._annotations import CREATE

# Opt-in env var that unlocks the privileged local-file attachment tool.
_ENABLE_ENV = "MCP_APPLE_REMINDERS_ENABLE_FILE_ATTACHMENTS"
_TRUTHY = {"1", "true", "yes", "on"}
# Per-file size guard — attachments are copied into the Reminders store.
_MAX_BYTES = 100 * 1024 * 1024


def _run(fn, *args, **kwargs) -> dict:
    """Run a helper wrapper, translating helper errors into ValueErrors."""
    try:
        return fn(*args, **kwargs)
    except ReminderKitHelperUnavailable as e:
        raise ValueError(f"ReminderKit helper not built. Run `make build-native`. ({e})") from e
    except ReminderKitHelperError as e:
        raise ValueError(e.message) from e


def _file_attachments_enabled() -> bool:
    """True only when the operator has explicitly opted in via the env var."""
    return os.environ.get(_ENABLE_ENV, "").strip().lower() in _TRUTHY


def _classify_and_validate(paths: list[str]) -> tuple[list[str], list[str]]:
    """Validate each local path; split into (generic files, image files).

    Raises ValueError on a blank, relative, missing, non-regular, unreadable, or
    oversized path — before any path reaches the helper.
    """
    files: list[str] = []
    images: list[str] = []
    for raw in paths:
        if not raw or not raw.strip():
            raise ValueError("attachment paths must be non-empty")
        p = Path(raw).expanduser()
        if not p.is_absolute():
            raise ValueError(f"attachment path must be absolute: {raw!r}")
        if not p.is_file():
            raise ValueError(f"attachment path does not exist or is not a regular file: {raw!r}")
        if not os.access(p, os.R_OK):
            raise ValueError(f"attachment path is not readable: {raw!r}")
        if p.stat().st_size > _MAX_BYTES:
            raise ValueError(f"attachment exceeds the {_MAX_BYTES // (1024 * 1024)} MB limit: {raw!r}")
        mime, _ = mimetypes.guess_type(str(p))
        (images if (mime or "").startswith("image/") else files).append(str(p))
    return files, images


@mcp.tool(
    name="add_url_attachment",
    title="Add URL Attachment",
    annotations=CREATE,
    description=(
        "Attach one or more web URLs (links) to a reminder by its UUID. Additive "
        "— existing attachments are preserved. URLs must be web URLs (http/https). "
        "Unprivileged: no filesystem access. Private ReminderKit API."
    ),
)
async def add_url_attachment(reminder_id: str, urls: list[str], ctx: Context) -> dict:
    """Attach web URLs to a reminder. See the tool description."""
    if not reminder_id or not reminder_id.strip():
        raise ValueError("reminder_id is required and must be non-empty")
    if not urls:
        raise ValueError("urls is required and must contain at least one URL")
    resp = _run(helper_add_url_attachments, reminder_id, urls)
    await ctx.info(f"Attached {resp.get('urlsAdded', len(urls))} URL(s) to {reminder_id}")
    return {
        "reminder_id": reminder_id,
        "urls_added": resp.get("urlsAdded", len(urls)),
        "status": resp.get("status", "updated"),
    }


@mcp.tool(
    name="add_metadata",
    title="Add Metadata",
    annotations=CREATE,
    description=(
        "Attach web URLs and/or hashtags (tags) to a reminder by its UUID in one "
        "call. Additive. At least one URL or tag is required. Unprivileged: no "
        "filesystem access. Private ReminderKit API."
    ),
)
async def add_metadata(
    reminder_id: str,
    ctx: Context,
    urls: Optional[list[str]] = None,
    tags: Optional[list[str]] = None,
) -> dict:
    """Attach web URLs and/or hashtags to a reminder. See the tool description."""
    if not reminder_id or not reminder_id.strip():
        raise ValueError("reminder_id is required and must be non-empty")
    if not urls and not tags:
        raise ValueError("at least one of urls or tags is required")
    resp = _run(helper_add_private_metadata, reminder_id, urls=urls, tags=tags)
    await ctx.info(
        f"Added metadata to {reminder_id} (urls={resp.get('urlsAdded', 0)}, tags={resp.get('tagsAdded', 0)})"
    )
    return {
        "reminder_id": reminder_id,
        "urls_added": resp.get("urlsAdded", 0),
        "tags_added": resp.get("tagsAdded", 0),
        "status": resp.get("status", "updated"),
    }


@mcp.tool(
    name="add_file_attachment",
    title="Add File Attachment",
    annotations=CREATE,
    description=(
        "Attach one or more LOCAL files to a reminder by its UUID, by absolute "
        "path. Image files render with a thumbnail; any other file type attaches "
        "generically (PDF, doc, etc.). PRIVILEGED — this reads files off disk and "
        f"embeds them, so it is disabled unless the operator sets {_ENABLE_ENV}=1 "
        "in the server environment. Each path must be absolute, exist, be a "
        "readable regular file, and be under 100 MB. Additive. Private ReminderKit API."
    ),
)
async def add_file_attachment(reminder_id: str, paths: list[str], ctx: Context) -> dict:
    """Attach local files/images to a reminder by path. Opt-in gated; see description."""
    if not reminder_id or not reminder_id.strip():
        raise ValueError("reminder_id is required and must be non-empty")
    if not _file_attachments_enabled():
        raise ValueError(
            "Local-file attachments are disabled. This tool reads files off disk and embeds "
            f"them into Reminders, so it is opt-in: set {_ENABLE_ENV}=1 in the server "
            "environment to enable it. (URL and tag attachments do not require this.)"
        )
    if not paths:
        raise ValueError("paths is required and must contain at least one file path")
    files, images = _classify_and_validate(paths)
    resp = _run(helper_add_file_attachments, reminder_id, files=files or None, images=images or None)
    await ctx.info(f"Attached {len(files) + len(images)} local file(s) to {reminder_id}")
    return {
        "reminder_id": reminder_id,
        "files_added": resp.get("filesAdded", len(files)),
        "images_added": resp.get("imagesAdded", len(images)),
        "status": resp.get("status", "updated"),
    }
