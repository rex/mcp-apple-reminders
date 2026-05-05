"""Hermetic tests for helpers — no pyremindkit involvement."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mcp_apple_reminders._helpers import (
    parse_datetime,
    parse_priority,
    priority_label,
    today_window,
)


class TestParseDatetime:
    def test_naive_iso(self) -> None:
        result = parse_datetime("2024-01-15T14:30:00")
        assert result == datetime(2024, 1, 15, 14, 30, 0)

    def test_z_suffix_is_utc(self) -> None:
        # The top user-facing bug we shipped: Python <3.11 fromisoformat()
        # rejects this. Must work everywhere now.
        result = parse_datetime("2024-01-15T14:30:00Z")
        assert result == datetime(2024, 1, 15, 14, 30, 0, tzinfo=timezone.utc)

    def test_offset_form(self) -> None:
        result = parse_datetime("2024-01-15T14:30:00+05:00")
        assert result.utcoffset() is not None
        assert result.year == 2024 and result.hour == 14

    def test_passthrough_datetime(self) -> None:
        d = datetime(2024, 1, 1)
        assert parse_datetime(d) is d

    @pytest.mark.parametrize("bad", ["not a date", "", "2024-13-99T99:99:99"])
    def test_invalid_raises_value_error(self, bad: str) -> None:
        with pytest.raises(ValueError):
            parse_datetime(bad)


class TestParsePriority:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("none", 0),
            ("LOW", 1),
            ("Medium", 5),
            ("high", 9),
            ("0", 0),
            ("9", 9),
            (0, 0),
            (5, 5),
            (9, 9),
            (3, 3),  # mid-range int passes through
        ],
    )
    def test_accepts(self, value: str | int, expected: int) -> None:
        assert parse_priority(value) == expected

    @pytest.mark.parametrize("bad", ["urgent", "10", -1, 100, ""])
    def test_invalid_raises_value_error(self, bad: str | int) -> None:
        with pytest.raises(ValueError):
            parse_priority(bad)


class TestPriorityLabel:
    @pytest.mark.parametrize(
        ("priority", "label"),
        [(0, "None"), (1, "Low"), (3, "Low"), (5, "Medium"), (7, "High"), (9, "High")],
    )
    def test_known(self, priority: int, label: str) -> None:
        assert priority_label(priority) == label


class TestTodayWindow:
    def test_returns_midnight_to_next_midnight(self) -> None:
        now = datetime(2024, 6, 15, 14, 30, 22, 123456)
        start, end = today_window(now)
        assert start == datetime(2024, 6, 15, 0, 0, 0, 0)
        assert end == datetime(2024, 6, 16, 0, 0, 0, 0)

    def test_end_is_exclusive_next_day_midnight(self) -> None:
        now = datetime(2024, 6, 15, 23, 59, 59)
        _, end = today_window(now)
        # Crucially, NOT 23:59:59.999999 — clean exclusive boundary
        assert end.microsecond == 0
        assert end.day == 16
