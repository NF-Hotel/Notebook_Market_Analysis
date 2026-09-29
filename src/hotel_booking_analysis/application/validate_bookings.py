"""Validate a submission and summarize its data quality (ADR-0001, US-001.01, UC-001 2b, 3)."""

from dataclasses import dataclass

from hotel_booking_analysis.domain.analysis import AnalysisAvailability, AnalysisName
from hotel_booking_analysis.domain.booking import (
    BookingRecord,
    BookingSubmission,
)
from hotel_booking_analysis.domain.errors import InputError
from hotel_booking_analysis.domain.quality import (
    DataQualitySummary,
    assess_availability,
    records_with_valid,
    summarize,
    usable_fields,
)


@dataclass(frozen=True, slots=True)
class ValidatedBookings:
    """A submission with its data-quality summary and analysis availability.

    Later steps take records for an analysis through `records_for`, which leaves out records
    with a missing or invalid value in a needed field (ADR-0001, ADR-0007).
    """

    submission: BookingSubmission
    summary: DataQualitySummary
    availability: tuple[AnalysisAvailability, ...]
    usable_fields: frozenset[str]

    def availability_of(self, analysis: AnalysisName) -> AnalysisAvailability:
        return next(a for a in self.availability if a.analysis is analysis)

    def records_for(self, *field_names: str) -> tuple[BookingRecord, ...]:
        """Return the records holding a valid value in every named field."""
        return records_with_valid(self.submission.records, *field_names)


def validate_bookings(submission: BookingSubmission) -> ValidatedBookings:
    """Summarize data quality and mark analyses unavailable when fields are missing.

    Raises `InputError` when no record holds any valid value (UC-001 2b).
    """
    records = submission.records
    usable = usable_fields(records)
    if not usable:
        raise InputError("NO_VALID_RECORDS", "No booking record holds a valid value.")
    return ValidatedBookings(
        submission=submission,
        summary=summarize(records, submission.unknown_fields),
        availability=assess_availability(records),
        usable_fields=usable,
    )
