"""Tests for the seasonality and booking-pace analysis (US-001.04, ADR-0007, MIL-005 task 4)."""

from datetime import date
from decimal import Decimal
from typing import Any

from hotel_booking_analysis.adapters.seasonality_analyzer import SeasonalityAnalyzer
from hotel_booking_analysis.application.configuration import AppConfiguration
from hotel_booking_analysis.application.validate_bookings import validate_bookings
from hotel_booking_analysis.domain.analysis import Analysis, AnalysisName, Availability
from hotel_booking_analysis.domain.booking import BookingRecord
from hotel_booking_analysis.domain.wording import forbidden_words_in_findings
from tests.support import make_submission

Findings = dict[str, Any]  # findings are JSON-shaped; tests index into them


def _record(
    booking: date | None = None,
    arrival: date | None = None,
    canceled: bool | None = None,
    price: str | None = None,
) -> BookingRecord:
    return BookingRecord(
        booking_date=booking,
        arrival_date=arrival,
        is_canceled=canceled,
        price_per_night=None if price is None else Decimal(price),
    )


def _analyze(*records: BookingRecord, minimum: int = 2) -> Analysis:
    validated = validate_bookings(make_submission(*records))
    return SeasonalityAnalyzer().analyze(validated, AppConfiguration(min_group_size=minimum))


def _findings(*records: BookingRecord, minimum: int = 2) -> Findings:
    findings: Findings = dict(_analyze(*records, minimum=minimum).findings)
    return findings


def _periods(series: Findings) -> dict[str, Findings]:
    return {p["figure"]["group"]: p for p in series["periods"]}


def _booking_records() -> list[BookingRecord]:
    return [
        _record(booking=date(2021, 3, 8), canceled=True, price="20"),
        _record(booking=date(2021, 4, 1), canceled=False, price="30.5"),
        _record(booking=date(2021, 4, 30), canceled=False, price="19.0"),
        _record(booking=date(2021, 6, 15), canceled=False, price="27.31"),
    ]


def test_analyze_is_the_seasonality_analysis_and_available() -> None:
    analysis = _analyze(*_booking_records())

    assert SeasonalityAnalyzer().name is AnalysisName.SEASONALITY
    assert analysis.availability is Availability.AVAILABLE


def test_analyze_counts_bookings_per_month_with_partial_edge_months() -> None:
    monthly = _findings(*_booking_records())["bookings"]["monthly"]

    periods = _periods(monthly)
    assert list(periods) == ["2021-03", "2021-04", "2021-06"]
    assert [p["figure"]["numerator"] for p in periods.values()] == [1, 2, 1]
    assert [p["partial_period"] for p in periods.values()] == [True, False, True]
    assert periods["2021-04"]["figure"] == {
        "group": "2021-04",
        "numerator": 2,
        "denominator": 4,
        "small_sample": False,
    }


def test_analyze_lists_years_with_fewer_than_twelve_months_as_incomplete() -> None:
    bookings = _findings(*_booking_records())["bookings"]

    assert bookings["incomplete_years"] == [{"year": 2021, "months_present": 3}]


def test_analyze_year_with_all_twelve_months_is_not_incomplete() -> None:
    records = [_record(booking=date(2021, month, 15)) for month in range(1, 13)]
    records += [_record(booking=date(2022, 1, 15))]

    bookings = _findings(*records)["bookings"]

    assert bookings["incomplete_years"] == [{"year": 2022, "months_present": 1}]


def test_analyze_summarizes_cancellation_share_and_mean_price_per_month() -> None:
    periods = _periods(_findings(*_booking_records())["bookings"]["monthly"])

    april = periods["2021-04"]
    assert april["cancellation"] == {
        "group": "cancellation_share",
        "numerator": 0,
        "denominator": 2,
        "small_sample": False,
    }
    assert april["mean_price_per_night"] == {"value": "24.75", "count": 2, "small_sample": False}
    assert periods["2021-03"]["cancellation"]["numerator"] == 1
    assert periods["2021-03"]["mean_price_per_night"]["small_sample"] is True


def test_analyze_mean_price_uses_exact_decimals_and_skips_records_without_price() -> None:
    records = [_record(booking=date(2021, 3, 1), price="0.1"), _record(booking=date(2021, 3, 2))]
    records += [_record(booking=date(2021, 3, 3), price="0.2")]

    period = _periods(_findings(*records)["bookings"]["monthly"])["2021-03"]

    assert period["mean_price_per_night"]["value"] == "0.15"
    assert period["mean_price_per_night"]["count"] == 2
    assert period["figure"]["numerator"] == 3


def test_analyze_iso_weeks_put_the_year_end_days_in_week_53() -> None:
    records = [
        _record(booking=date(2020, 12, 31)),
        _record(booking=date(2021, 1, 3)),
        _record(booking=date(2021, 1, 4)),
    ]

    weekly = _findings(*records)["bookings"]["iso_week"]

    periods = _periods(weekly)
    assert list(periods) == ["2020-W53", "2021-W01"]
    assert periods["2020-W53"]["figure"]["numerator"] == 2
    assert periods["2021-W01"]["figure"]["numerator"] == 1
    assert [p["partial_period"] for p in periods.values()] == [True, True]


def test_analyze_iso_weeks_fully_covered_are_not_partial() -> None:
    days = (4, 10, 11, 17)  # Monday of W01 to Sunday of W02, 2021
    records = [_record(booking=date(2021, 1, day)) for day in days]

    periods = _periods(_findings(*records)["bookings"]["iso_week"])

    assert list(periods) == ["2021-W01", "2021-W02"]
    assert [p["partial_period"] for p in periods.values()] == [False, False]


def test_analyze_keeps_booking_and_arrival_series_separate() -> None:
    records = [
        _record(booking=date(2021, 3, 8), arrival=date(2021, 5, 1)),
        _record(booking=date(2021, 3, 9), arrival=date(2021, 5, 2)),
        _record(booking=date(2021, 4, 1), arrival=date(2021, 6, 1)),
    ]

    findings = _findings(*records)

    assert list(_periods(findings["bookings"]["monthly"])) == ["2021-03", "2021-04"]
    assert list(_periods(findings["arrivals"]["monthly"])) == ["2021-05", "2021-06"]
    assert findings["bookings"]["measure"] == "bookings"
    assert findings["arrivals"]["measure"] == "arrivals"
    assert findings["arrivals"]["span"] == {"first": "2021-05-01", "last": "2021-06-01"}


def test_analyze_series_without_its_date_field_is_unavailable() -> None:
    findings = _findings(*_booking_records())

    assert findings["arrivals"]["status"] == "unavailable"
    assert "arrival_date" in findings["arrivals"]["reason"]
    assert findings["bookings"]["status"] == "available"


def test_analyze_missing_cancellation_and_price_fields_drop_only_those_parts() -> None:
    records = [_record(booking=date(2021, 3, 1)), _record(booking=date(2021, 3, 2))]

    bookings = _findings(*records)["bookings"]

    assert set(bookings["unavailable_parts"]) == {"cancellation_share", "mean_price_per_night"}
    assert bookings["unavailable_parts"]["cancellation_share"]["status"] == "unavailable"
    period = _periods(bookings["monthly"])["2021-03"]
    assert "cancellation" not in period
    assert "mean_price_per_night" not in period
    assert period["figure"]["numerator"] == 2


def test_analyze_flags_small_periods_by_the_configured_minimum() -> None:
    periods = _periods(_findings(*_booking_records(), minimum=2)["bookings"]["monthly"])

    assert periods["2021-03"]["figure"]["small_sample"] is True
    assert periods["2021-04"]["figure"]["small_sample"] is False


def test_analyze_findings_contain_no_forbidden_words() -> None:
    analysis = _analyze(*_booking_records())

    assert forbidden_words_in_findings(analysis.findings) == ()
