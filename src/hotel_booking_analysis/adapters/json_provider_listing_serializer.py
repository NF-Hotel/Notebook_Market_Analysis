"""Serialize the provider listing to compact JSON (ADR-0011, UC-004).

The schema for version 1.0 is `schemas/llm_providers_1_0.schema.json`.
"""

from datetime import datetime
from typing import Any

from hotel_booking_analysis.adapters.listing_json import (
    envelope,
    failure_document,
    load_schema,
    to_line,
)
from hotel_booking_analysis.domain.analysis import JsonValue
from hotel_booking_analysis.domain.errors import Notice
from hotel_booking_analysis.domain.llm import ProviderListing, ProviderStatus
from hotel_booking_analysis.domain.result import ResultError

SCHEMA_RESOURCE = "llm_providers_1_0.schema.json"
KIND = "llm_providers"


# Any is justified: a JSON Schema document is free-form JSON consumed by jsonschema.
def load_provider_listing_schema() -> dict[str, Any]:
    """Return the JSON Schema of the provider listing version 1.0 (ADR-0011)."""
    return load_schema(SCHEMA_RESOURCE)


def _provider(status: ProviderStatus) -> dict[str, JsonValue]:
    return {
        "provider": status.provider.name.value,
        "base_url": status.provider.base_url,
        "status": "reachable" if status.reachable else "unreachable",
        "reason": status.reason.value if status.reason is not None else None,
        "models": [{"name": model.name} for model in status.models],
    }


class JsonProviderListingSerializer:
    """Serializes to one line of compact JSON without a trailing newline (the sink adds it)."""

    def serialize(self, listing: ProviderListing) -> str:
        document = envelope(KIND, "completed", listing.generated_at, listing.notices)
        document["providers"] = [_provider(status) for status in listing.providers]
        return to_line(document)

    def serialize_failure(
        self, error: ResultError, notices: tuple[Notice, ...], generated_at: datetime
    ) -> str:
        """A failed document: `error`, and no `providers`."""
        return to_line(failure_document(KIND, error, notices, generated_at))
