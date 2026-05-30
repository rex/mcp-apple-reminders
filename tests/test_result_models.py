"""CL-2.11 — lock the typed-result contract.

The write / bulk / triage tools used to return bare ``dict`` (no output schema,
unstructured content only). This slice gave each a frozen result model so it
declares an ``outputSchema`` and emits ``structuredContent``. These tests guard
that contract: every converted tool keeps a typed schema, and the models behave
(``.of(**extras)`` preserves helper-echo keys, ``BulkResult`` coerces failures).
"""

from __future__ import annotations

import asyncio

import pytest
from pydantic import ValidationError

from mcp_apple_reminders.results import BulkResult, DeleteResult, WriteResult

# Tools converted from `-> dict` to a typed result model in CL-2.11, mapped to
# their expected output-schema title. A revert to a bare dict drops the schema
# and trips test_converted_tools_have_typed_output_schema.
_CONVERTED = {
    "delete_reminder": "DeleteResult",
    "delete_calendar": "DeleteResult",
    "delete_group": "DeleteResult",
    "delete_template": "DeleteResult",
    "delete_smart_list": "DeleteResult",
    "bulk_complete": "BulkResult",
    "bulk_move": "BulkResult",
    "bulk_delete_completed": "BulkResult",
    "set_urgent": "WriteResult",
    "set_early_reminder": "WriteResult",
    "add_section_and_assign": "WriteResult",
    "set_list_appearance": "WriteResult",
    "set_list_pinned": "WriteResult",
    "set_smart_list_pinned": "WriteResult",
    "create_template": "WriteResult",
    "apply_template": "WriteResult",
    "create_smart_list": "WriteResult",
    "update_smart_list": "WriteResult",
    "categorize_grocery_items": "WriteResult",
    "move_list_to_group": "WriteResult",
    "add_url_attachment": "WriteResult",
    "add_metadata": "WriteResult",
    "add_file_attachment": "WriteResult",
    "set_alarm": "WriteResult",
    "set_location_alarm": "WriteResult",
    "set_recurrence": "WriteResult",
    "triage_brain_dump": "TriageResult",
}


def test_converted_tools_have_typed_output_schema() -> None:
    from mcp_apple_reminders.server import mcp

    tools = {t.name: t for t in asyncio.run(mcp.list_tools())}
    missing = [n for n in _CONVERTED if tools[n].outputSchema is None]
    assert not missing, f"converted tools with no outputSchema: {missing}"
    wrong = {
        n: tools[n].outputSchema.get("title")
        for n, title in _CONVERTED.items()
        if (tools[n].outputSchema or {}).get("title") != title
    }
    assert not wrong, f"unexpected output-schema titles: {wrong}"


def test_write_result_preserves_echo_keys() -> None:
    # extra="allow" → helper-specific echo keys ride along and stay accessible.
    w = WriteResult.of(status="updated", id="rem-1", urgent=True)
    dumped = w.model_dump(mode="json")
    assert dumped == {"status": "updated", "id": "rem-1", "urgent": True}
    assert w.id == "rem-1"  # extras are attribute-accessible


def test_delete_result_defaults() -> None:
    d = DeleteResult.of(id="cal-1", name="Work", deleted_reminders=3)
    dumped = d.model_dump(mode="json")
    assert dumped["deleted"] is True
    assert dumped["deleted_reminders"] == 3


def test_bulk_result_coerces_failures() -> None:
    b = BulkResult.of(processed=1, failed=[{"id": "x", "error": "boom"}])
    assert b.failed[0].id == "x"
    assert b.failed[0].error == "boom"


def test_result_models_are_frozen() -> None:
    w = WriteResult.of(status="ok")
    with pytest.raises(ValidationError):
        w.status = "mutated"
