"""Typed result models for the write / bulk / triage tools (CL-2.11).

Before this slice the mutation tools returned a bare ``dict``; FastMCP cannot
derive an ``outputSchema`` from ``-> dict``, so those tools emitted only
unstructured text. These frozen, tail-safe models give every such tool a
declared output schema and make it emit ``structuredContent``.

``WriteResult`` / ``DeleteResult`` keep ``extra="allow"`` so each tool's own echo
keys (ids, names, counts, flags returned by the native helpers) ride along
without enumerating helper-internal detail here — Pydantic's ``extra="allow"``
leaves ``additionalProperties`` open in the JSON schema, so those extras validate
cleanly over the wire. ``BulkResult`` and ``TriageResult`` have precise shapes and
are fully typed.

These are NOT the S0.3 contract models (``models.py``); they are free to evolve,
but are kept frozen + additive by habit.
"""

from __future__ import annotations

from typing import Any, Optional, Self

from pydantic import BaseModel, ConfigDict, Field

from .models import Reminder


class _Result(BaseModel):
    """Base for the typed tool-result models.

    ``of(**fields)`` builds an instance from declared *plus* helper-echo keys
    without mypy rejecting the extras (``extra="allow"`` is a runtime-only
    setting the PEP-681 dataclass-transform view can't see) and absorbs the
    ``list[dict] -> BulkFailure`` coercion; the runtime model still enforces the
    real shape. Prefer ``Model.of(...)`` over ``Model(...)`` at call sites that
    pass echo keys.
    """

    model_config = ConfigDict(frozen=True)

    @classmethod
    def of(cls, **fields: Any) -> Self:
        return cls(**fields)


class WriteResult(_Result):
    """Acknowledgement for a status-bearing write / mutation tool.

    The native helpers reply with a ``status`` string ("ok" / "created" /
    "updated" / …); tool-specific echo keys ride as permitted extras.
    """

    model_config = ConfigDict(frozen=True, extra="allow")

    status: str = "ok"


class DeleteResult(_Result):
    """Acknowledgement for a ``delete_*`` tool (the deleted entity's id/name and
    any cascade count ride as permitted extras)."""

    model_config = ConfigDict(frozen=True, extra="allow")

    deleted: bool = True
    message: str = ""


class BulkFailure(_Result):
    """One failed item in a bulk operation."""

    model_config = ConfigDict(frozen=True)

    id: str
    error: str


class BulkWindow(_Result):
    """The half-open ``[start, end)`` completion window of bulk_delete_completed."""

    model_config = ConfigDict(frozen=True)

    start: str
    end: str


class BulkResult(_Result):
    """Per-item outcome of a ``bulk_*`` tool."""

    model_config = ConfigDict(frozen=True)

    processed: int
    failed: list[BulkFailure] = Field(default_factory=list)
    target_calendar_id: Optional[str] = None
    window: Optional[BulkWindow] = None


class TriageResult(_Result):
    """Proposed routing produced by ``triage_brain_dump`` (read-only).

    ``protected_namespaces=()`` lets the ``model_response`` field keep its name
    (Pydantic otherwise reserves the ``model_`` prefix).
    """

    model_config = ConfigDict(frozen=True, protected_namespaces=())

    from_list: str
    items: list[Reminder] = Field(default_factory=list)
    routing: dict[str, str] = Field(default_factory=dict)
    valid_destinations: list[str] = Field(default_factory=list)
    model_response: str = ""
