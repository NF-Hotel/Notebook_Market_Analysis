"""Outcome of a listing command (DCD-001 ListingOutcome, ADR-0008)."""

from dataclasses import dataclass

from hotel_booking_analysis.application.analyze_bookings import RunStatus


@dataclass(frozen=True, slots=True)
class ListingOutcome:
    """What a listing command produced.

    `status` is SUCCEEDED, INPUT_FAILED (exit code 2, a failed document was delivered) or
    DELIVERY_FAILED (exit code 4). `serialized` is the delivered line; `message` describes a
    failure and is never set on success.
    """

    status: RunStatus
    serialized: str | None = None
    message: str | None = None
