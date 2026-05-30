"""Attachments: URL + private metadata; the file-attachment kill-switch (CL-2.6).

`add_file_attachment` is gated behind env MCP_APPLE_REMINDERS_ENABLE_FILE_ATTACHMENTS;
with the switch off (the default) it must refuse cleanly rather than touch the
filesystem. If the env is set in this run, the gate assertion is skipped.
"""

from __future__ import annotations

import os

from .fixtures import TestStore
from .harness import Reporter, WireClient


async def run(c: WireClient, store: TestStore, r: Reporter) -> None:
    lid = store.list_id
    rid = store.track_reminder(
        await c.call_ok("create_reminder", {"title": "IT attach", "calendar_id": lid}, label="create attach target")
    )
    if not rid:
        r.check("attachments: target created", False)
        return

    url = await c.call_ok(
        "add_url_attachment",
        {"reminder_id": rid, "urls": ["https://example.com/a", "https://example.com/b"]},
        label="add_url_attachment",
    )
    r.check("add_url_attachment -> urls_added >= 1", bool(url) and (url.get("urls_added") or 0) >= 1)

    meta = await c.call_ok(
        "add_metadata", {"reminder_id": rid, "urls": ["https://example.com/c"], "tags": ["m1"]}, label="add_metadata"
    )
    r.check("add_metadata -> status", bool(meta) and bool(meta.get("status")))

    if os.environ.get("MCP_APPLE_REMINDERS_ENABLE_FILE_ATTACHMENTS"):
        r.check("add_file_attachment gate (env ON; skipped negative test)", True)
    else:
        err = await c.call_expect_error(
            "add_file_attachment",
            {"reminder_id": rid, "paths": ["/etc/hosts"]},
            label="add_file_attachment(gated off) -> isError",
        )
        r.check(
            "add_file_attachment refuses with a gate message",
            "enable" in err.lower() or "disabled" in err.lower() or "MCP_APPLE_REMINDERS" in err,
            err[:140],
        )
