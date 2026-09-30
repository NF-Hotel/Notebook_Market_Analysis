"""Tests for validation and availability (ADR-0001, US-001.01, UC-001 2b and 4a)."""

from datetime import date

import pytest

from hotel_booking_analysis.application.validate_bookings import (
    ValidatedBookings,
    validate_bookings,
)
from hotel_booking_analysis.domain.analysis import AnalysisAvailability, AnalysisName, Availability
from hotel_booking_analysis.domain.booking import FIELD_NAMES, BookingRecord
from hotel_booking_analysis.domain.errors import InputError
from tests.support import make_submission


def _availability(validated: ValidatedBookings, analysis: AnalysisName) -> AnalysisAvailability:
    return next(a for a in validated.availability if a.analysis is analysis)


def test_validate_returns_summary_and_availability_for_all_analyses() -> None:
    submission = make_submission(
        BookingRecord(booking_id="1", lead_time=4, arrival_date=date(2022, 1, 1)),
        unknown=("extra",),
    )

    validated = validate_bookings(submission)

    assert validated.summary.record_count == 1
    assert validated.summary.unknown_fields == ("extra",)
    assert len(validated.availability) == len(AnalysisName)
    assert _availability(validated, AnalysisName.LEAD_TIME).is_available
    assert validated.usable_fields == frozenset({"booking_id", "lead_time", "arrival_date"})


def test_unavailable_analysis_names_field_and_carries_no_value() -> None:
    validated = validate_bookings(
        make_submission(BookingRecord(lead_time=4, missing_fields=frozenset({"is_canceled"})))
    )

    cancellations = _availability(validated, AnalysisName.CANCELLATIONS)

    assert cancellations.availability is Availability.UNAVAILABLE
    assert cancellations.missing_fields == ("is_canceled",)


def test_records_for_leaves_out_records_with_missing_or_invalid_value() -> None:
    good = BookingRecord(lead_time=4, is_canceled=True)
    missing = BookingRecord(is_canceled=True, missing_fields=frozenset({"lead_time"}))
    invalid = BookingRecord(is_canceled=False, invalid_fields=frozenset({"lead_time"}))

    validated = validate_bookings(make_submission(good, missing, invalid))

    assert validated.records_for("lead_time") == (good,)
    assert validated.records_for("is_canceled") == (good, missing, invalid)
    assert validated.summary.invalid_counts["lead_time"] == 1
    assert validated.summary.missing_counts["lead_time"] == 1


def test_validate_fails_when_no_record_holds_any_valid_value() -> None:
    empty = BookingRecord(missing_fields=frozenset(FIELD_NAMES))

    with pytest.raises(InputError) as error:
        validate_bookings(make_submission(empty, empty))

    assert error.value.code == "NO_VALID_RECORDS"
