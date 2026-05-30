"""Tests for attachment tools — gating, path validation, classification, reg.

The privileged file path is exercised only up to validation (no native helper
call): the opt-in gate and path checks all run before the helper, so these tests
need neither a granted Reminders permission nor the compiled binary.
"""

from __future__ import annotations

import asyncio

import pytest

from mcp_apple_reminders.tools.attachments import (
    _classify_and_validate,
    _file_attachments_enabled,
    add_file_attachment,
)

_ENV = "MCP_APPLE_REMINDERS_ENABLE_FILE_ATTACHMENTS"


class _FakeCtx:
    async def info(self, *a, **k): ...

    async def debug(self, *a, **k): ...

    async def warning(self, *a, **k): ...

    async def error(self, *a, **k): ...


def test_enable_flag_off_by_default(monkeypatch):
    monkeypatch.delenv(_ENV, raising=False)
    assert _file_attachments_enabled() is False


def test_enable_flag_truthy(monkeypatch):
    monkeypatch.setenv(_ENV, "1")
    assert _file_attachments_enabled() is True
    monkeypatch.setenv(_ENV, "off")
    assert _file_attachments_enabled() is False


def test_classify_splits_images_and_files(tmp_path):
    img = tmp_path / "shot.png"
    img.write_bytes(b"x")
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"x")
    files, images = _classify_and_validate([str(img), str(pdf)])
    assert images == [str(img)]
    assert files == [str(pdf)]


def test_classify_rejects_relative_path():
    with pytest.raises(ValueError, match="absolute"):
        _classify_and_validate(["relative/shot.png"])


def test_classify_rejects_missing_path(tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        _classify_and_validate([str(tmp_path / "nope.txt")])


def test_file_attachment_tool_gated_off_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv(_ENV, raising=False)
    img = tmp_path / "shot.png"
    img.write_bytes(b"x")
    with pytest.raises(ValueError, match="disabled"):
        asyncio.run(add_file_attachment("rem-1", [str(img)], _FakeCtx()))


def test_attachment_tools_registered():
    from mcp_apple_reminders.server import mcp

    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert {"add_url_attachment", "add_metadata", "add_file_attachment"} <= names
