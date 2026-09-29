"""Tests for the cancellation analysis (US-001.05, ADR-0007, MIL-005 task 5)."""

from datetime import date
from typing import Any

from hotel_booking_analysis.adapters.cancellation_analyzer import CancellationAnalyzer
from hotel_booking_analysis.application.configuration import AppConfiguration
from hotel_booking_analysis.application.validate_bookings import validate_bookings
from hotel_booking_analysis.domain.analysis import Analysis, AnalysisName, Availability
from hotel_booking_analysis.domain.booking import BookingRecord
from hotel_booking_analysis.domain.wording import forbidden_words_in_findings
from tests.support import make_submission

Findings = dict[str, Any]  # findings are JSON-shaped; tests index into them

# lead_time, canceled, deposit, segment, customer, arrival, special requests, booking changes
_ROWS: list[tuple[int, bool, str, str, str, date, int, int]] = [
    (7, False, "No Deposit", "Online", "Transient", date(2021, 3, 10), 0, 0),
    (8, True, "No Deposit", "Online", "Transient", date(2021, 3, 20), 1, 1),
    (30, True, "Non Refund", "Online", "Group", date(2021, 4, 1), 2, 2),
    (31, False, "No Deposit", "Online", "Group", date(2021, 4, 15), 3, 3),
    (90, True, "Non Refund", "Online", "Transient", date(2021, 4, 30), 4, 0),
    (91, False, "No Deposit", "Online", "Transient", date(2021, 5, 5), 0, 1),
    (180, True, "Non Refund", "Offline", "Group", date(2021, 5, 10), 1, 2),
    (181, True, "Non Refund", "Offline", "Group", date(2021, 5, 20), 5, 7),
]


def _records() -> list[BookingRecord]:
    return [
        BookingRecord(
            lead_time=lead,
            is_canceled=canceled,
            deposit_type=deposit,
            market_segment=segment,
            customer_type=customer,
            arrival_date=arrival,
            total_of_special_requests=requests,
            booking_changes=changes,
        )
        for lead, canceled, deposit, segment, customer, arrival, requests, changes in _ROWS
    ]


def _analyze(*records: BookingRecord, minimum: int = 2) -> Analysis:
    validated = validate_bookings(make_submission(*records))
    return CancellationAnalyzer().analyze(validated, AppConfiguration(min_group_size=minimum))


def _splits(*records: BookingRecord, minimum: int = 2) -> Findings:
    findings: Findings = dict(_analyze(*records, minimum=minimum).findings)
    splits: Findings = findings["splits"]
    return splits


def _rates(split: Findings) -> dict[str, tuple[int, int]]:
    return {
        g["figure"]["group"]: (g["figure"]["numerator"], g["figure"]["denominator"])
        for g in split["groups"]
    }


def test_analyze_is_the_cancellation_analysis_and_available() -> None:
    analysis = _analyze(*_records())

    assert CancellationAnalyzer().name is AnalysisName.CANCELLATIONS
    assert analysis.availability is Availability.AVAILABLE


def test_analyze_overall_rate_has_numerator_and_denominator() -> None:
    findings: Findings = dict(_analyze(*_records()).findings)

    assert findings["overall"] == {
        "group": "all",
        "numerator": 5,
        "denominator": 8,
        "small_sample": False,
    }


def test_analyze_rates_by_lead_time_band_at_the_edges() -> None:
    split = _splits(*_records())["by_lead_time_band"]

    assert _rates(split) == {
        "0-7": (0, 1),
        "8-30": (2, 2),
        "31-90": (1, 2),
        "91-180": (1, 2),
        "181+": (1, 1),
    }
    assert [g["figure"]["group"] for g in split["groups"]] == [
        "0-7",
        "8-30",
        "31-90",
        "91-180",
        "181+",
    ]


def test_analyze_rates_by_deposit_type_market_segment_and_customer_type() -> None:
    splits = _splits(*_records())

    assert _rates(splits["by_deposit_type"]) == {"No Deposit": (1, 4), "Non Refund": (4, 4)}
    assert _rates(splits["by_market_segment"]) == {"Offline": (2, 2), "Online": (3, 6)}
    assert _rates(splits["by_customer_type"]) == {"Group": (3, 4), "Transient": (2, 4)}


def test_analyze_rates_by_arrival_month_mark_partial_months() -> None:
    split = _splits(*_records())["by_arrival_month"]

    assert _rates(split) == {"2021-03": (1, 2), "2021-04": (2, 3), "2021-05": (2, 3)}
    assert [g["partial_period"] for g in split["groups"]] == [True, False, True]


def test_analyze_special_requests_group_three_and_more() -> None:
    split = _splits(*_records())["by_special_requests"]

    assert _rates(split) == {"0": (0, 2), "1": (2, 2), "2": (1, 1), "3+": (2, 3)}
    assert [g["figure"]["group"] for g in split["groups"]] == ["0", "1", "2", "3+"]


def test_analyze_booking_changes_group_two_and_more() -> None:
    split = _splits(*_records())["by_booking_changes"]

    assert _rates(split) == {"0": (1, 2), "1": (1, 2), "2+": (3, 4)}


def test_analyze_flags_small_sample_groups() -> None:
    findings: Findings = dict(_analyze(*_records(), minimum=3).findings)

    split = findings["splits"]["by_lead_time_band"]
    flags = {g["figure"]["group"]: g["figure"]["small_sample"] for g in split["groups"]}
    assert set(flags.values()) == {True}
    assert findings["overall"]["small_sample"] is False


def test_analyze_missing_split_field_drops_only_that_split() -> None:
    records = [
        BookingRecord(is_canceled=True, lead_time=5, market_segment="Online"),
        BookingRecord(is_canceled=False, lead_time=50, market_segment="Online"),
    ]

    splits = _splits(*records)

    assert splits["by_deposit_type"]["status"] == "unavailable"
    assert "deposit_type" in splits["by_deposit_type"]["reason"]
    assert splits["by_arrival_month"]["status"] == "unavailable"
    assert splits["by_lead_time_band"]["status"] == "available"
    assert _rates(splits["by_market_segment"]) == {"Online": (1, 2)}


def test_analyze_split_leaves_out_and_counts_records_without_the_split_field() -> None:
    records = [
        BookingRecord(is_canceled=True, market_segment="Online"),
        BookingRecord(is_canceled=False),
    ]

    split = _splits(*records)["by_market_segment"]

    assert split["records_used"] == 1
    assert split["records_left_out"] == 1


def test_analyze_findings_contain_no_forbidden_words() -> None:
    analysis = _analyze(*_records())

    assert forbidden_words_in_findings(analysis.findings) == ()
