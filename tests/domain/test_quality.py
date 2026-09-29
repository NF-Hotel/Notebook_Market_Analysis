"""Tests for data-quality summary and availability rules (ADR-0001, US-001.01)."""

from datetime import date
from decimal import Decimal

from hotel_booking_analysis.domain.analysis import AnalysisAvailability, AnalysisName, Availability
from hotel_booking_analysis.domain.booking import FIELD_NAMES, BookingRecord
from hotel_booking_analysis.domain.quality import (
    assess_availability,
    records_with_valid,
    summarize,
    usable_fields,
)


def _availability(records: tuple[BookingRecord, ...], name: AnalysisName) -> AnalysisAvailability:
    return next(a for a in assess_availability(records) if a.analysis is name)


def test_summary_counts_records_and_date_coverage() -> None:
    records = (
        BookingRecord(booking_date=date(2021, 3, 8), arrival_date=date(2022, 1, 5)),
        BookingRecord(booking_date=date(2021, 1, 1), arrival_date=date(2022, 2, 9)),
        BookingRecord(),
    )

    summary = summarize(records)

    assert summary.record_count == 3
    assert summary.earliest_booking_date == date(2021, 1, 1)
    assert summary.latest_booking_date == date(2021, 3, 8)
    assert summary.earliest_arrival_date == date(2022, 1, 5)
    assert summary.latest_arrival_date == date(2022, 2, 9)


def test_summary_has_no_dates_when_no_record_has_one() -> None:
    summary = summarize((BookingRecord(lead_time=1),))

    assert summary.earliest_booking_date is None
    assert summary.latest_arrival_date is None


def test_summary_counts_surplus_copies_of_booking_ids_and_keeps_all() -> None:
    records = tuple(BookingRecord(booking_id=i) for i in ("1", "1", "1", "2", None, None))

    summary = summarize(records)

    assert summary.duplicate_booking_id_count == 2
    assert summary.record_count == 6


def test_summary_counts_missing_and_invalid_per_field_for_every_field() -> None:
    records = (
        BookingRecord(missing_fields=frozenset({"meal"}), invalid_fields=frozenset({"lead_time"})),
        BookingRecord(missing_fields=frozenset({"meal", "country"})),
    )

    summary = summarize(records)

    assert set(summary.missing_counts) == set(FIELD_NAMES)
    assert summary.missing_counts["meal"] == 2
    assert summary.missing_counts["country"] == 1
    assert summary.invalid_counts["lead_time"] == 1
    assert summary.invalid_counts["meal"] == 0
    assert summary.has_invalid_values


def test_summary_counts_zero_price_separately_and_treats_it_as_valid() -> None:
    records = (
        BookingRecord(price_per_night=Decimal("0")),
        BookingRecord(price_per_night=Decimal("0.00")),
        BookingRecord(price_per_night=Decimal("10")),
    )

    summary = summarize(records)

    assert summary.zero_price_count == 2
    assert summary.invalid_counts["price_per_night"] == 0


def test_summary_lists_unknown_fields_sorted() -> None:
    summary = summarize((BookingRecord(),), unknown_fields=("zeta", "alpha"))

    assert summary.unknown_fields == ("alpha", "zeta")


def test_records_with_valid_leaves_out_records_lacking_a_field() -> None:
    complete = BookingRecord(lead_time=3, is_canceled=False)
    lacking = BookingRecord(lead_time=3)

    assert records_with_valid((complete, lacking), "lead_time", "is_canceled") == (complete,)
    assert records_with_valid((complete, lacking), "lead_time") == (complete, lacking)


def test_usable_fields_lists_fields_with_at_least_one_valid_value() -> None:
    records = (BookingRecord(lead_time=1), BookingRecord(is_canceled=True))

    assert usable_fields(records) == frozenset({"lead_time", "is_canceled"})


def test_lead_time_unavailable_names_missing_field() -> None:
    records = (BookingRecord(missing_fields=frozenset(FIELD_NAMES)),)

    result = _availability(records, AnalysisName.LEAD_TIME)

    assert result.availability is Availability.UNAVAILABLE
    assert result.missing_fields == ("lead_time",)
    assert result.reason is not None
    assert "'lead_time'" in result.reason
    assert "missing" in result.reason


def test_unavailable_reason_says_invalid_when_field_present_but_never_valid() -> None:
    records = (BookingRecord(invalid_fields=frozenset({"lead_time"})),)

    result = _availability(records, AnalysisName.LEAD_TIME)

    assert result.reason is not None
    assert "invalid" in result.reason


def test_room_value_needs_both_stay_night_fields() -> None:
    records = (BookingRecord(stays_in_weekend_nights=1, price_per_night=Decimal("5")),)

    result = _availability(records, AnalysisName.ROOM_VALUE)

    assert result.availability is Availability.UNAVAILABLE
    assert result.missing_fields == ("stays_in_week_nights",)


def test_holidays_available_with_one_date_side_and_names_the_other_as_missing() -> None:
    records = (BookingRecord(arrival_date=date(2022, 1, 1)),)

    result = _availability(records, AnalysisName.HOLIDAYS)

    assert result.is_available
    assert result.reason is None
    assert result.missing_fields == ("booking_date",)


def test_holidays_and_seasonality_unavailable_without_any_date() -> None:
    records = (BookingRecord(lead_time=1),)

    for name in (AnalysisName.HOLIDAYS, AnalysisName.SEASONALITY):
        result = _availability(records, name)
        assert not result.is_available
        assert set(result.missing_fields) == {"booking_date", "arrival_date"}


def test_guest_mix_available_with_any_one_listed_field() -> None:
    assert _availability((BookingRecord(meal="BB"),), AnalysisName.GUEST_MIX).is_available
    assert not _availability((BookingRecord(lead_time=1),), AnalysisName.GUEST_MIX).is_available


def test_cancellations_available_when_is_canceled_valid_in_some_record() -> None:
    records = (BookingRecord(), BookingRecord(is_canceled=False))

    assert _availability(records, AnalysisName.CANCELLATIONS).is_available


def test_assess_availability_covers_all_six_analyses_once() -> None:
    result = assess_availability((BookingRecord(lead_time=1),))

    assert [a.analysis for a in result] == list(AnalysisName)
