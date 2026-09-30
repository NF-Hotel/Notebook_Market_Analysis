"""Shared JSON building blocks of the listing serializers (ADR-0011)."""

import json
from datetime import UTC, datetime
from importlib import resources
from typing import Any

from hotel_booking_analysis.domain.analysis import JsonValue
from hotel_booking_analysis.domain.errors import Notice
from hotel_booking_analysis.domain.result import ResultError

SCHEMA_VERSION = "1.0"


# Any is justified: a JSON Schema document is free-form JSON consumed by jsonschema.
def load_schema(resource: str) -> dict[str, Any]:
    """Return the JSON Schema document stored under `schemas/<resource>`."""
    text = (
        resources.files("hotel_booking_analysis.adapters")
        .joinpath("schemas", resource)
        .read_text(encoding="utf-8")
    )
    document: dict[str, Any] = json.loads(text)
    return document


def _timestamp(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _notice(notice: Notice) -> dict[str, JsonValue]:
    return {"code": notice.code, "message": notice.message}


def envelope(
    kind: str, status: str, generated_at: datetime, notices: tuple[Notice, ...]
) -> dict[str, JsonValue]:
    """The fields every listing document carries."""
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": kind,
        "status": status,
        "generated_at": _timestamp(generated_at),
        "notices": [_notice(notice) for notice in notices],
    }


def failure_document(
    kind: str, error: ResultError, notices: tuple[Notice, ...], generated_at: datetime
) -> dict[str, JsonValue]:
    """A failed listing document: `error` and no payload."""
    document = envelope(kind, "failed", generated_at, notices)
    document["error"] = {"code": error.code, "message": error.message}
    return document


def to_line(document: dict[str, JsonValue]) -> str:
    """Compact single-line JSON."""
    return json.dumps(document, separators=(",", ":"), ensure_ascii=True)
