"""Slice 2.5 — `triage_brain_dump` sampling smoke tests.

Pure unit-level — exercises the prompt-building + response-parsing helpers
without actually invoking the LLM. Integration with a real client's
sampling endpoint is exercised manually.
"""

from __future__ import annotations

from mcp_apple_reminders.tools.sampling import _VALID_ROUTES, _build_triage_prompt, _parse_routing


class _FakeReminder:
    def __init__(self, rid: str, title: str):
        self.id = rid
        self.title = title


def test_valid_routes_includes_all_workflow_buckets():
    """The router knows every Claude-* destination plus delete."""
    assert "Claude-Active" in _VALID_ROUTES
    assert "Claude-On-Deck" in _VALID_ROUTES
    assert "Claude-Waiting" in _VALID_ROUTES
    assert "Claude-Done" in _VALID_ROUTES
    assert "delete" in _VALID_ROUTES


def test_build_prompt_lists_each_item_and_options():
    """The rendered prompt names every option + every item id."""
    items = [_FakeReminder("UUID-A", "Write docs"), _FakeReminder("UUID-B", "Buy milk")]
    prompt = _build_triage_prompt(items)
    for route in _VALID_ROUTES:
        assert route in prompt
    assert "UUID-A" in prompt
    assert "UUID-B" in prompt
    assert "Write docs" in prompt


def test_parse_routing_keeps_only_valid_pairs():
    """Unknown ids and invalid destinations are dropped."""
    response = '{"GOOD-1": "Claude-Active", "BAD-id": "Claude-Active", "GOOD-2": "made-up-route"}'
    out = _parse_routing(response, valid_ids={"GOOD-1", "GOOD-2"})
    assert out == {"GOOD-1": "Claude-Active"}


def test_parse_routing_strips_code_fences():
    """LLMs sometimes wrap JSON in ``` fences; we strip them before parsing."""
    response = '```json\n{"X": "Claude-Done"}\n```'
    out = _parse_routing(response, valid_ids={"X"})
    assert out == {"X": "Claude-Done"}


def test_parse_routing_returns_empty_on_garbage():
    """Garbage in → empty dict out, no exception."""
    assert _parse_routing("not json", valid_ids={"X"}) == {}
    assert _parse_routing("[1, 2, 3]", valid_ids={"X"}) == {}
