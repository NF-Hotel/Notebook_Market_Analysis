"""Tests for the lead-time analysis (US-001.02, ADR-0007, MIL-005 criteria 1, 2, 5, 7)."""

from datetime import date
from typing import Any

from hotel_booking_analysis.adapters.lead_time_analyzer import LeadTimeAnalyzer
from hotel_booking_analysis.application.configuration import AppConfiguration
from hotel_booking_analysis.application.validate_bookings import validate_bookings
from hotel_booking_analysis.domain.analysis import Analysis, AnalysisName, Availability
from hotel_booking_analysis.domain.booking import BookingRecord
from hotel_booking_analysis.domain.wording import forbidden_words_in_findings
from tests.support import make_submission

Findings = dict[str, Any]  # findings are JSON-shaped; tests index into them


def _record(
    lead_time: int,
    canceled: bool | None = None,
    arrival: date | None = None,
    booking: date | None = None,
    segment: str | None = None,
    customer: str | None = None,
) -> BookingRecord:
    return BookingRecord(
        lead_time=lead_time,
        is_canceled=canceled,
        arrival_date=arrival,
        booking_date=booking,
        market_segment=segment,
        customer_type=customer,
    )


def _analyze(*records: BookingRecord, minimum: int = 2) -> Analysis:
    validated = validate_bookings(make_submission(*records))
    return LeadTimeAnalyzer().analyze(validated, AppConfiguration(min_group_size=minimum))


def _findings(*records: BookingRecord, minimum: int = 2) -> Findings:
    findings: Findings = dict(_analyze(*records, minimum=minimum).findings)
    return findings


def _edge_records() -> list[BookingRecord]:
    """Eight records on the band edges 7/8, 30/31, 90/91, 180/181, alternating cancellation."""
    leads = [7, 8, 30, 31, 90, 91, 180, 181]
    return [
        _record(
            lead,
            canceled=index % 2 == 1,
            arrival=date(2021, 3 if index < 4 else 4, 10 + index),
            segment="Online" if index < 6 else "Offline",
            customer="Transient",
        )
        for index, lead in enumerate(leads)
    ]


def _bands(entry: Findings) -> dict[str, int]:
    return {band["group"]: band["numerator"] for band in entry["bands"]}


def test_analyze_is_the_lead_time_analysis_and_available() -> None:
    analysis = _analyze(*_edge_records())

    assert LeadTimeAnalyzer().name is AnalysisName.LEAD_TIME
    assert analysis.name is AnalysisName.LEAD_TIME
    assert analysis.availability is Availability.AVAILABLE


def test_analyze_counts_records_in_each_band_at_the_edges() -> None:
    overall = _findings(*_edge_records())["overall"]

    assert _bands(overall) == {"0-7": 1, "8-30": 2, "31-90": 2, "91-180": 2, "181+": 1}


def test_analyze_overall_median_of_eight_values_is_the_mean_of_the_middle_pair() -> None:
    overall = _findings(*_edge_records())["overall"]

    assert overall["median_days"] == 60.5  # sorted 7 8 30 31 90 91 180 181 -> (31 + 90) / 2
    assert overall["figure"] == {
        "group": "all",
        "numerator": 8,
        "denominator": 8,
        "small_sample": False,
    }


def test_analyze_median_is_an_integer_when_whole() -> None:
    overall = _findings(_record(10), _record(20), _record(30))["overall"]

    assert overall["median_days"] == 20
    assert isinstance(overall["median_days"], int)


def test_analyze_splits_by_cancellation_status_with_counts_and_medians() -> None:
    split = _findings(*_edge_records())["splits"]["by_cancellation_status"]

    groups = {g["figure"]["group"]: g for g in split["groups"]}
    assert groups["canceled"]["figure"]["numerator"] == 4
    assert groups["canceled"]["figure"]["denominator"] == 8
    assert groups["canceled"]["median_days"] == 61  # 8 31 91 181 -> (31 + 91) / 2
    assert groups["not_canceled"]["median_days"] == 60  # 7 30 90 180 -> (30 + 90) / 2


def test_analyze_splits_by_arrival_month_and_marks_partial_edge_months() -> None:
    records = [
        _record(10, arrival=date(2021, 3, 10)),
        _record(20, arrival=date(2021, 4, 1)),
        _record(30, arrival=date(2021, 4, 30)),
        _record(40, arrival=date(2021, 4, 15)),
        _record(50, arrival=date(2021, 5, 20)),
    ]

    split = _findings(*records)["splits"]["by_arrival_month"]

    groups = {g["figure"]["group"]: g for g in split["groups"]}
    assert list(groups) == ["2021-03", "2021-04", "2021-05"]
    assert groups["2021-04"]["figure"]["numerator"] == 3
    assert groups["2021-04"]["median_days"] == 30
    assert [groups[m]["partial_period"] for m in groups] == [True, False, True]


def test_analyze_splits_by_market_segment_and_customer_type() -> None:
    splits = _findings(*_edge_records())["splits"]

    segments = {
        g["figure"]["group"]: g["figure"]["numerator"]
        for g in splits["by_market_segment"]["groups"]
    }
    customers = {
        g["figure"]["group"]: g["figure"]["numerator"] for g in splits["by_customer_type"]["groups"]
    }
    assert segments == {"Offline": 2, "Online": 6}
    assert customers == {"Transient": 8}


def test_analyze_flags_small_sample_groups_by_the_configured_minimum() -> None:
    findings = _findings(*_edge_records(), minimum=5)

    groups = {
        g["figure"]["group"]: g["figure"]["small_sample"]
        for g in findings["splits"]["by_market_segment"]["groups"]
    }
    assert groups == {"Offline": True, "Online": False}
    assert findings["overall"]["figure"]["small_sample"] is False
    band_flags = {b["group"]: b["small_sample"] for b in findings["overall"]["bands"]}
    assert band_flags["0-7"] is True
    assert band_flags["8-30"] is True


def test_analyze_uses_default_minimum_of_thirty_from_configuration() -> None:
    validated = validate_bookings(make_submission(*_edge_records()))

    analysis = LeadTimeAnalyzer().analyze(validated, AppConfiguration())

    findings: Findings = dict(analysis.findings)
    assert findings["overall"]["figure"]["small_sample"] is True


def test_analyze_missing_split_field_drops_only_that_split() -> None:
    records = [_record(10, canceled=False, arrival=date(2021, 3, 1)), _record(20, canceled=True)]

    splits = _findings(*records)["splits"]

    assert splits["by_market_segment"]["status"] == "unavailable"
    assert "market_segment" in splits["by_market_segment"]["reason"]
    assert splits["by_customer_type"]["status"] == "unavailable"
    assert splits["by_cancellation_status"]["status"] == "available"
    assert splits["by_arrival_month"]["status"] == "available"
    assert splits["by_arrival_month"]["groups"][0]["figure"]["numerator"] == 1


def test_analyze_split_uses_only_records_with_the_split_field() -> None:
    records = [_record(10, canceled=False), _record(20, canceled=True), _record(30)]

    split = _findings(*records)["splits"]["by_cancellation_status"]

    assert {g["figure"]["denominator"] for g in split["groups"]} == {2}


def test_analyze_compares_supplied_lead_time_with_the_date_difference() -> None:
    records = [
        _record(10, booking=date(2021, 3, 8), arrival=date(2021, 3, 18)),  # 10 days: same
        _record(10, booking=date(2021, 3, 8), arrival=date(2021, 3, 19)),  # 11 days: differs
        _record(5, booking=date(2021, 3, 8), arrival=date(2021, 3, 8)),  # 0 days: differs
        _record(7, booking=date(2021, 3, 8)),  # no arrival date: not compared
    ]

    comparison = _findings(*records)["date_comparison"]

    assert comparison["status"] == "available"
    assert comparison["figure"] == {
        "group": "differs_from_supplied",
        "numerator": 2,
        "denominator": 3,
        "small_sample": False,
    }


def test_analyze_date_comparison_is_negative_when_arrival_precedes_booking() -> None:
    records = [_record(0, booking=date(2021, 3, 8), arrival=date(2021, 3, 7))] * 2

    comparison = _findings(*records)["date_comparison"]

    assert comparison["figure"]["numerator"] == 2


def test_analyze_date_comparison_is_unavailable_without_both_dates() -> None:
    comparison = _findings(_record(10, booking=date(2021, 3, 8)))["date_comparison"]

    assert comparison["status"] == "unavailable"
    assert "arrival_date" in comparison["reason"]


def test_analyze_findings_contain_no_forbidden_words() -> None:
    analysis = _analyze(*_edge_records())

    assert forbidden_words_in_findings(analysis.findings) == ()
