"""Serialize the holiday listing to compact JSON (ADR-0011, UC-003).

The schema for version 1.0 is `schemas/holiday_calendar_1_0.schema.json`.
"""

from datetime import datetime
from typing import Any

from hotel_booking_analysis.adapters.listing_json import (
    envelope,
    failure_document,
    load_schema,
    to_line,
)
from hotel_booking_analysis.domain.analysis import Availability, JsonValue
from hotel_booking_analysis.domain.errors import Notice
from hotel_booking_analysis.domain.listing import HolidayCalendarListing, HolidayCalendarYear
from hotel_booking_analysis.domain.result import ResultError

SCHEMA_RESOURCE = "holiday_calendar_1_0.schema.json"
KIND = "holiday_calendar"


# Any is justified: a JSON Schema document is free-form JSON consumed by jsonschema.
def load_holiday_listing_schema() -> dict[str, Any]:
    """Return the JSON Schema of the holiday listing version 1.0 (ADR-0011)."""
    return load_schema(SCHEMA_RESOURCE)


def _year(entry: HolidayCalendarYear) -> dict[str, JsonValue]:
    document: dict[str, JsonValue] = {"year": entry.year, "status": entry.availability.value}
    if entry.availability is Availability.AVAILABLE:
        document["holidays"] = [
            {"date": holiday.date.isoformat(), "name": holiday.name} for holiday in entry.holidays
        ]
    else:
        document["reason"] = entry.reason
    return document


class JsonHolidayListingSerializer:
    """Serializes to one line of compact JSON without a trailing newline (the sink adds it)."""

    def serialize(self, listing: HolidayCalendarListing) -> str:
        document = envelope(KIND, "completed", listing.generated_at, listing.notices)
        document["country"] = listing.country
        document["years"] = [_year(entry) for entry in listing.years]
        return to_line(document)

    def serialize_failure(
        self, error: ResultError, notices: tuple[Notice, ...], generated_at: datetime
    ) -> str:
        """A failed document: `error`, and no `years`."""
        return to_line(failure_document(KIND, error, notices, generated_at))
