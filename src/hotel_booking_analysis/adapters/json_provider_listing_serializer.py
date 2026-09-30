"""Serialize the provider listing to compact JSON (ADR-0011, UC-004).

The schema for version 1.0 is `schemas/llm_providers_1_0.schema.json`.
"""

import json
from datetime import UTC, datetime
from importlib import resources
from typing import Any

from hotel_booking_analysis.domain.analysis import JsonValue
from hotel_booking_analysis.domain.errors import Notice
from hotel_booking_analysis.domain.llm import ProviderListing, ProviderStatus
from hotel_booking_analysis.domain.result import ResultError

SCHEMA_RESOURCE = "llm_providers_1_0.schema.json"
SCHEMA_VERSION = "1.0"
KIND = "llm_providers"


# Any is justified: a JSON Schema document is free-form JSON consumed by jsonschema.
def load_provider_listing_schema() -> dict[str, Any]:
    """Return the JSON Schema of the provider listing version 1.0 (ADR-0011)."""
    text = (
        resources.files("hotel_booking_analysis.adapters")
        .joinpath("schemas", SCHEMA_RESOURCE)
        .read_text(encoding="utf-8")
    )
    document: dict[str, Any] = json.loads(text)
    return document


def _timestamp(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _notice(notice: Notice) -> dict[str, JsonValue]:
    return {"code": notice.code, "message": notice.message}


def _provider(status: ProviderStatus) -> dict[str, JsonValue]:
    return {
        "provider": status.provider.name.value,
        "base_url": status.provider.base_url,
        "status": "reachable" if status.reachable else "unreachable",
        "reason": status.reason.value if status.reason is not None else None,
        "models": [{"name": model.name} for model in status.models],
    }


def _envelope(
    status: str, generated_at: datetime, notices: tuple[Notice, ...]
) -> dict[str, JsonValue]:
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "status": status,
        "generated_at": _timestamp(generated_at),
        "notices": [_notice(notice) for notice in notices],
    }


def _line(document: dict[str, JsonValue]) -> str:
    return json.dumps(document, separators=(",", ":"), ensure_ascii=True)


class JsonProviderListingSerializer:
    """Serializes to one line of compact JSON without a trailing newline (the sink adds it)."""

    def serialize(self, listing: ProviderListing) -> str:
        document = _envelope("completed", listing.generated_at, listing.notices)
        document["providers"] = [_provider(status) for status in listing.providers]
        return _line(document)

    def serialize_failure(
        self, error: ResultError, notices: tuple[Notice, ...], generated_at: datetime
    ) -> str:
        """A failed document: `error`, and no `providers`."""
        document = _envelope("failed", generated_at, notices)
        document["error"] = {"code": error.code, "message": error.message}
        return _line(document)
