"""Booking record and booking submission (DM-001, ADR-0001, US-001.01)."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum

TEXT_FIELDS: tuple[str, ...] = (
    "hotel",
    "meal",
    "country",
    "market_segment",
    "assigned_room_type",
    "deposit_type",
    "agent",
    "customer_type",
)
INTEGER_FIELDS: tuple[str, ...] = (
    "lead_time",
    "stays_in_weekend_nights",
    "stays_in_week_nights",
    "adults",
    "children",
    "babies",
    "previous_cancellations",
    "booking_changes",
    "required_car_parking_spaces",
    "total_of_special_requests",
)
BOOLEAN_FIELDS: tuple[str, ...] = ("is_canceled", "is_repeated_guest")
DATE_FIELDS: tuple[str, ...] = ("booking_date", "arrival_date")

FIELD_NAMES: tuple[str, ...] = (
    "booking_id",
    *TEXT_FIELDS,
    *INTEGER_FIELDS,
    *BOOLEAN_FIELDS,
    *DATE_FIELDS,
    "price_per_night",
)
"""Every field of the input contract (ADR-0001); any other name is an unknown field."""


class InputSource(StrEnum):
    """Where a submission came from (ADR-0001 `supplied` or `development_sample`)."""

    SUPPLIED = "supplied"
    DEVELOPMENT_SAMPLE = "development_sample"


@dataclass(frozen=True, slots=True)
class BookingRecord:
    """One hotel booking (DM-001 Booking Record).

    A value is None when it is missing or invalid; `missing_fields` and `invalid_fields` say
    which of the two applies, so a record is left out of exactly the analyses that need a
    field it cannot supply (ADR-0001 value rules).
    """

    booking_id: str | None = None
    hotel: str | None = None
    is_canceled: bool | None = None
    lead_time: int | None = None
    booking_date: date | None = None
    arrival_date: date | None = None
    stays_in_weekend_nights: int | None = None
    stays_in_week_nights: int | None = None
    adults: int | None = None
    children: int | None = None
    babies: int | None = None
    meal: str | None = None
    country: str | None = None
    market_segment: str | None = None
    is_repeated_guest: bool | None = None
    previous_cancellations: int | None = None
    assigned_room_type: str | None = None
    booking_changes: int | None = None
    deposit_type: str | None = None
    agent: str | None = None
    customer_type: str | None = None
    required_car_parking_spaces: int | None = None
    total_of_special_requests: int | None = None
    price_per_night: Decimal | None = None
    missing_fields: frozenset[str] = field(default_factory=frozenset)
    invalid_fields: frozenset[str] = field(default_factory=frozenset)

    def value(self, field_name: str) -> object | None:
        """Return the valid value of a contract field, or None if missing or invalid."""
        if field_name not in FIELD_NAMES:
            raise KeyError(field_name)
        value: object | None = getattr(self, field_name)
        return value

    def has_valid(self, *field_names: str) -> bool:
        """Tell whether every named field holds a valid value."""
        return all(self.value(name) is not None for name in field_names)


@dataclass(frozen=True, slots=True)
class BookingSubmission:
    """One set of booking records for analysis (DM-001 Booking Submission, ADR-0002 `input`).

    `reference` is the file name only, without a directory.
    """

    source: InputSource
    reference: str
    content_sha256: str
    records: tuple[BookingRecord, ...]
    unknown_fields: tuple[str, ...] = ()
