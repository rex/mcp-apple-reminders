"""SDK migration contracts with an isolated bridge and no real Reminders writes."""

import asyncio
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock

import mcp_types as types
import pytest
from mcp import MCPError
from mcp.client import Client

from mcp_apple_reminders import lifespan
from mcp_apple_reminders.models import Reminder
from mcp_apple_reminders.server import mcp
from mcp_apple_reminders.tools import bulk, sampling


@pytest.fixture
def bridge(monkeypatch):
    bridge = MagicMock()
    monkeypatch.setattr(lifespan, "RemindKit", lambda: bridge)
    monkeypatch.setattr(lifespan, "find_db_path", lambda: None)
    return bridge


@pytest.mark.parametrize("mode", ["auto", "legacy"])
def test_catalog_and_errors(mode, bridge):
    async def run():
        async with Client(mcp, mode=mode) as client:
            catalog = await client.list_tools()
            assert len(catalog.tools) == 58
            assert all(t.annotations and t.title for t in catalog.tools)
            assert len((await client.list_prompts()).prompts) == 5
            assert len((await client.list_resources()).resources) == 6
            if mode == "auto":
                assert catalog.result_type == "complete"
                assert catalog.ttl_ms >= 0
            with pytest.raises(MCPError) as unknown:
                await client.call_tool("reminders_missing", {})
            assert unknown.value.code == -32602
            result = await client.call_tool("bulk_complete", {"reminder_ids": []})
            assert not result.is_error
            assert result.structured_content["processed"] == 0

    asyncio.run(run())


@pytest.mark.parametrize("mode", ["auto", "legacy"])
def test_sampling_fallback_preserves_items(mode, bridge, monkeypatch):
    reminder = Reminder(id="fixture", title="Review fixture", list_id="fixture-list", deeplink="fixture://1")
    reader = MagicMock()
    reader.get_calendar_by_name.return_value = SimpleNamespace(id="fixture-list")
    reader.iter_reminders.return_value = [reminder]
    monkeypatch.setattr(lifespan.AppContext, "open_sqlite", lambda self: nullcontext(None))
    monkeypatch.setattr(sampling, "Reader", lambda conn: reader)

    async def run():
        async with Client(mcp, mode=mode) as client:
            result = await client.call_tool("triage_brain_dump", {})
            assert not result.is_error
            assert result.structured_content["items"][0]["id"] == "fixture"
            assert result.structured_content["routing"] == {}
            assert "Classify these items directly" in result.structured_content["model_response"]

    asyncio.run(run())


@pytest.mark.parametrize("mode", ["auto", "legacy"])
@pytest.mark.parametrize("action", ["accept", "decline", "cancel", None])
def test_bulk_confirmation_cannot_be_bypassed(mode, action, bridge, monkeypatch):
    reader = MagicMock()
    reader.iter_reminders.return_value = [SimpleNamespace(id="fixture")]
    monkeypatch.setattr(lifespan.AppContext, "open_sqlite", lambda self: nullcontext(None))
    monkeypatch.setattr(bulk, "Reader", lambda conn: reader)

    async def elicit(ctx, params):
        return types.ElicitResult(action=action, content={} if action == "accept" else None)

    async def run():
        async with Client(mcp, mode=mode, elicitation_callback=elicit if action else None) as client:
            if action is None:
                with pytest.raises(MCPError) as unavailable:
                    await client.call_tool(
                        "bulk_delete_completed", {"start": "2026-11-17T00:00:00", "end": "2026-11-17T01:00:00"}
                    )
                assert unavailable.value.code == -32021
                return
            result = await client.call_tool(
                "bulk_delete_completed", {"start": "2026-11-17T00:00:00", "end": "2026-11-17T01:00:00"}
            )
            assert result.is_error == (action != "accept")

    asyncio.run(run())
    if action == "accept":
        bridge.delete_reminder.assert_called_once_with("fixture")
    else:
        bridge.delete_reminder.assert_not_called()
