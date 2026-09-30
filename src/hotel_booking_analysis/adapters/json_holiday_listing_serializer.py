"""Serialize the holiday listing to compact JSON (ADR-0011, UC-003).

The schema for version 1.0 is `schemas/holiday_calendar_1_0.schema.json`.
"""

import json
from datetime import UTC, datetime
from importlib import resources
from typing import Any

from hotel_booking_analysis.domain.analysis import Availability, JsonValue
from hotel_booking_analysis.domain.errors import Notice
from hotel_booking_analysis.domain.listing import HolidayCalendarListing, HolidayCalendarYear
from hotel_booking_analysis.domain.result import ResultError

SCHEMA_RESOURCE = "holiday_calendar_1_0.schema.json"
SCHEMA_VERSION = "1.0"
KIND = "holiday_calendar"


# Any is justified: a JSON Schema document is free-form JSON consumed by jsonschema.
def load_holiday_listing_schema() -> dict[str, Any]:
    """Return the JSON Schema of the holiday listing version 1.0 (ADR-0011)."""
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


def _year(entry: HolidayCalendarYear) -> dict[str, JsonValue]:
    document: dict[str, JsonValue] = {"year": entry.year, "status": entry.availability.value}
    if entry.availability is Availability.AVAILABLE:
        document["holidays"] = [
            {"date": holiday.date.isoformat(), "name": holiday.name} for holiday in entry.holidays
        ]
    else:
        document["reason"] = entry.reason
    return document


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


class JsonHolidayListingSerializer:
    """Serializes to one line of compact JSON without a trailing newline (the sink adds it)."""

    def serialize(self, listing: HolidayCalendarListing) -> str:
        document = _envelope("completed", listing.generated_at, listing.notices)
        document["country"] = listing.country
        document["years"] = [_year(entry) for entry in listing.years]
        return _line(document)

    def serialize_failure(
        self, error: ResultError, notices: tuple[Notice, ...], generated_at: datetime
    ) -> str:
        """A failed document: `error`, and no `years`."""
        document = _envelope("failed", generated_at, notices)
        document["error"] = {"code": error.code, "message": error.message}
        return _line(document)
