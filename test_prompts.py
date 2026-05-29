"""Slice 2.2 — MCP Prompts smoke tests."""

from __future__ import annotations

import asyncio

from mcp_apple_reminders.server import mcp


def _list_prompts():
    return asyncio.run(mcp.list_prompts())


def _get_prompt(name: str, **arguments):
    return asyncio.run(mcp.get_prompt(name, arguments or None))


def test_four_prompts_registered():
    names = {p.name for p in _list_prompts()}
    assert names >= {"daily_review", "weekly_retro", "brain_dump_triage", "agent_visibility_sync"}


def test_daily_review_returns_messages():
    result = _get_prompt("daily_review")
    assert result.messages, "Expected at least one message"
    titles = [m.role for m in result.messages]
    assert "user" in titles
    assert "assistant" in titles


def test_weekly_retro_accepts_window_days():
    result = _get_prompt("weekly_retro", window_days="3")
    text_content = "".join(m.content.text if hasattr(m.content, "text") else "" for m in result.messages)
    assert "Weekly Retro" in text_content
    assert "last 3 day(s)" in text_content


def test_brain_dump_triage_handles_missing_list():
    """If the named list doesn't exist, the prompt returns a friendly explanation."""
    result = _get_prompt("brain_dump_triage", list_name="DefinitelyDoesNotExist-S22")
    text_content = "".join(m.content.text if hasattr(m.content, "text") else "" for m in result.messages)
    assert "not found" in text_content


def test_agent_visibility_sync_handles_missing_project_list():
    """Targets Agents-<project>; if missing, bootstraps instructions."""
    result = _get_prompt("agent_visibility_sync", project_name="NoSuchProject-S22")
    text_content = "".join(m.content.text if hasattr(m.content, "text") else "" for m in result.messages)
    assert "Agents-NoSuchProject-S22" in text_content
    assert "create_calendar" in text_content
