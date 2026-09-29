"""Tests for the room value and stay analysis (US-001.06, ADR-0007, MIL-005 criterion 4)."""

from decimal import Decimal
from typing import Any

from hotel_booking_analysis.adapters.room_value_analyzer import RoomValueAnalyzer
from hotel_booking_analysis.application.configuration import AppConfiguration
from hotel_booking_analysis.application.validate_bookings import validate_bookings
from hotel_booking_analysis.domain.analysis import Analysis, AnalysisName, Availability
from hotel_booking_analysis.domain.booking import BookingRecord
from hotel_booking_analysis.domain.wording import forbidden_words_in_findings
from tests.support import make_submission

Findings = dict[str, Any]  # findings are JSON-shaped; tests index into them


def _record(
    weekend: int,
    week: int,
    price: str | None = None,
    canceled: bool | None = None,
) -> BookingRecord:
    return BookingRecord(
        stays_in_weekend_nights=weekend,
        stays_in_week_nights=week,
        price_per_night=None if price is None else Decimal(price),
        is_canceled=canceled,
    )


def _analyze(*records: BookingRecord, minimum: int = 2) -> Analysis:
    validated = validate_bookings(make_submission(*records))
    return RoomValueAnalyzer().analyze(validated, AppConfiguration(min_group_size=minimum))


def _findings(*records: BookingRecord, minimum: int = 2) -> Findings:
    findings: Findings = dict(_analyze(*records, minimum=minimum).findings)
    return findings


def _groups(findings: Findings) -> dict[str, Findings]:
    return {g["figure"]["group"]: g for g in findings["estimated_value"]["groups"]}


def _fixture() -> list[BookingRecord]:
    """Six bookings: 2, 1, 5, 0 (excluded), 8 (price 0) and 3 nights."""
    return [
        _record(1, 1, "19.0", False),  # 2 nights: 38.0
        _record(0, 1, "27.31", True),  # 1 night: 27.31
        _record(2, 3, "10.5", False),  # 5 nights: 52.5
        _record(0, 0, "50", False),  # 0 nights: left out of value, counted
        _record(4, 4, "0", True),  # 8 nights at price 0: included, value 0
        _record(1, 2, "20", False),  # 3 nights: 60
    ]


def test_analyze_is_the_room_value_analysis_and_available() -> None:
    analysis = _analyze(*_fixture())

    assert RoomValueAnalyzer().name is AnalysisName.ROOM_VALUE
    assert analysis.availability is Availability.AVAILABLE


def test_analyze_length_of_stay_is_weekend_plus_week_nights_in_buckets() -> None:
    stay = _findings(*_fixture())["length_of_stay"]

    counts = {b["group"]: b["numerator"] for b in stay["buckets"]}
    assert counts == {"1": 1, "2": 1, "3": 1, "4-7": 1, "8+": 1}
    assert {b["denominator"] for b in stay["buckets"]} == {5}
    assert stay["total_nights"] == 2 + 1 + 5 + 8 + 3


def test_analyze_bucket_edges_three_four_seven_and_eight() -> None:
    records = [_record(0, nights) for nights in (3, 4, 7, 8)]

    stay = _findings(*records)["length_of_stay"]

    counts = {b["group"]: b["numerator"] for b in stay["buckets"]}
    assert counts == {"1": 0, "2": 0, "3": 1, "4-7": 2, "8+": 1}


def test_analyze_leaves_out_and_counts_zero_night_records() -> None:
    findings = _findings(*_fixture())

    assert findings["records_used"] == 6
    assert findings["zero_night_records"] == 1
    assert findings["length_of_stay"]["records_used"] == 5
    assert findings["estimated_value"]["records_used"] == 5


def test_analyze_value_is_price_times_nights_with_cancelled_and_not_cancelled_separate() -> None:
    groups = _groups(_findings(*_fixture()))

    assert list(groups) == ["canceled", "not_canceled"]
    assert groups["not_canceled"]["count"] == 3
    assert groups["not_canceled"]["total"] == "150.5"  # 38.0 + 52.5 + 60
    assert groups["not_canceled"]["mean"] == "50.1667"
    assert groups["canceled"]["count"] == 2
    assert groups["canceled"]["total"] == "27.31"  # 27.31 + 0
    assert groups["canceled"]["mean"] == "13.655"
    assert groups["canceled"]["cancellation_status"] == "cancelled"


def test_analyze_never_reports_a_combined_figure() -> None:
    findings = _findings(*_fixture())

    value = findings["estimated_value"]
    assert set(value) >= {"groups"}
    assert "total" not in value
    assert "mean" not in value
    assert len(value["groups"]) == 2


def test_analyze_counts_price_zero_records_separately_but_includes_them() -> None:
    findings = _findings(*_fixture())

    assert findings["estimated_value"]["zero_price_records"] == 1
    groups = _groups(findings)
    assert groups["canceled"]["zero_price_records"] == 1
    assert groups["canceled"]["count"] == 2
    assert groups["not_canceled"]["zero_price_records"] == 0


def test_analyze_value_of_nineteen_times_two_nights_is_exactly_thirty_eight() -> None:
    groups = _groups(_findings(_record(1, 1, "19.0", False)))

    assert groups["not_canceled"]["total"] == "38"
    assert groups["not_canceled"]["mean"] == "38"  # one booking: the mean is its value


def test_analyze_value_uses_exact_decimals_not_floats() -> None:
    groups = _groups(_findings(_record(0, 3, "0.1", False)))

    assert groups["not_canceled"]["total"] == "0.3"


def test_analyze_without_cancellation_status_reports_one_unknown_group() -> None:
    findings = _findings(_record(0, 2, "10"), _record(0, 1, "5"))

    groups = _groups(findings)
    assert list(groups) == ["cancellation_status_unknown"]
    assert groups["cancellation_status_unknown"]["cancellation_status"] == (
        "cancellation status unknown"
    )
    assert groups["cancellation_status_unknown"]["total"] == "25"
    assert "cancellation status unknown" in findings["estimated_value"]["note"]


def test_analyze_records_without_status_never_mix_into_the_known_groups() -> None:
    findings = _findings(_record(0, 2, "10", True), _record(0, 1, "5"), _record(0, 1, "1", False))

    groups = _groups(findings)
    assert groups["canceled"]["total"] == "20"
    assert groups["not_canceled"]["total"] == "1"
    assert groups["cancellation_status_unknown"]["total"] == "5"


def test_analyze_states_the_estimate_label_and_notice_code_in_the_findings() -> None:
    findings = _findings(*_fixture())

    estimate = findings["estimate"]
    assert estimate["notice_code"] == "ESTIMATE_NOT_REVENUE"
    assert "estimate" in estimate["label"].lower()
    assert "not realized revenue" in estimate["label"]
    assert "price units of the input" in estimate["label"]
    assert findings["estimated_value"]["unit"] == "price units of the input"
    assert "not realized revenue" in findings["estimated_value"]["groups"][0]["summary"]


def test_analyze_missing_price_makes_only_the_value_unavailable() -> None:
    findings = _findings(_record(0, 2), _record(1, 1))

    assert findings["estimated_value"]["status"] == "unavailable"
    assert "price_per_night" in findings["estimated_value"]["reason"]
    assert findings["length_of_stay"]["records_used"] == 2


def test_analyze_counts_stay_records_without_a_valid_price() -> None:
    findings = _findings(_record(0, 2, "10", False), _record(0, 1, None, False))

    assert findings["estimated_value"]["records_without_price"] == 1
    assert findings["estimated_value"]["records_used"] == 1


def test_analyze_flags_small_value_groups() -> None:
    groups = _groups(_findings(*_fixture(), minimum=3))

    assert groups["not_canceled"]["figure"]["small_sample"] is False
    assert groups["canceled"]["figure"]["small_sample"] is True


def test_analyze_findings_contain_no_forbidden_words() -> None:
    analysis = _analyze(*_fixture())

    assert forbidden_words_in_findings(analysis.findings) == ()
