"""Tests for the guest and booking mix analysis (US-001.07, ADR-0007, MIL-005 task 7)."""

from decimal import Decimal
from typing import Any

from hotel_booking_analysis.adapters.guest_mix_analyzer import GuestMixAnalyzer
from hotel_booking_analysis.application.configuration import AppConfiguration
from hotel_booking_analysis.application.validate_bookings import validate_bookings
from hotel_booking_analysis.domain.analysis import Analysis, AnalysisName, Availability
from hotel_booking_analysis.domain.booking import BookingRecord
from hotel_booking_analysis.domain.wording import forbidden_words_in_findings
from tests.support import make_submission

Findings = dict[str, Any]  # findings are JSON-shaped; tests index into them


def _records() -> list[BookingRecord]:
    """Three bookings: two from PT (2 and 3 guests) and one from FR (1 guest)."""
    return [
        BookingRecord(
            adults=2,
            children=0,
            babies=0,
            country="PT",
            meal="BB",
            assigned_room_type="A",
            is_repeated_guest=False,
            required_car_parking_spaces=0,
            total_of_special_requests=0,
            is_canceled=False,
            price_per_night=Decimal("20"),
            stays_in_weekend_nights=1,
            stays_in_week_nights=1,
        ),
        BookingRecord(
            adults=2,
            children=1,
            babies=0,
            country="PT",
            meal="BB",
            assigned_room_type="A",
            is_repeated_guest=False,
            required_car_parking_spaces=1,
            total_of_special_requests=1,
            is_canceled=True,
            price_per_night=Decimal("30"),
            stays_in_weekend_nights=0,
            stays_in_week_nights=3,
        ),
        BookingRecord(
            adults=1,
            children=0,
            babies=0,
            country="FR",
            meal="HB",
            assigned_room_type="B",
            is_repeated_guest=True,
            required_car_parking_spaces=0,
            total_of_special_requests=0,
            is_canceled=False,
            price_per_night=Decimal("10"),
            stays_in_weekend_nights=1,
            stays_in_week_nights=0,
        ),
    ]


def _analyze(*records: BookingRecord, minimum: int = 2) -> Analysis:
    validated = validate_bookings(make_submission(*records))
    return GuestMixAnalyzer().analyze(validated, AppConfiguration(min_group_size=minimum))


def _distributions(*records: BookingRecord, minimum: int = 2) -> Findings:
    findings: Findings = dict(_analyze(*records, minimum=minimum).findings)
    distributions: Findings = findings["distributions"]
    return distributions


def _groups(distribution: Findings) -> dict[str, Findings]:
    return {g["figure"]["group"]: g for g in distribution["groups"]}


def test_analyze_is_the_guest_mix_analysis_and_available() -> None:
    analysis = _analyze(*_records())

    assert GuestMixAnalyzer().name is AnalysisName.GUEST_MIX
    assert analysis.availability is Availability.AVAILABLE


def test_analyze_total_guests_is_adults_plus_children_plus_babies() -> None:
    groups = _groups(_distributions(*_records())["total_guests"])

    assert {k: g["figure"]["numerator"] for k, g in groups.items()} == {"1": 1, "2": 1, "3": 1}
    assert {g["figure"]["denominator"] for g in groups.values()} == {3}


def test_analyze_country_distribution_has_counts_and_denominators() -> None:
    groups = _groups(_distributions(*_records())["country"])

    assert groups["PT"]["figure"] == {
        "group": "PT",
        "numerator": 2,
        "denominator": 3,
        "small_sample": False,
    }
    assert groups["FR"]["figure"]["small_sample"] is True


def test_analyze_distributions_cover_meal_room_repeat_parking_and_requests() -> None:
    distributions = _distributions(*_records())

    assert set(distributions) == {
        "total_guests",
        "country",
        "meal",
        "assigned_room_type",
        "is_repeated_guest",
        "required_car_parking_spaces",
        "total_of_special_requests",
    }
    assert {k: g["figure"]["numerator"] for k, g in _groups(distributions["meal"]).items()} == {
        "BB": 2,
        "HB": 1,
    }
    repeat = _groups(distributions["is_repeated_guest"])
    assert {k: g["figure"]["numerator"] for k, g in repeat.items()} == {
        "not_repeated": 2,
        "repeated": 1,
    }
    parking = distributions["required_car_parking_spaces"]
    assert [g["figure"]["group"] for g in parking["groups"]] == ["0", "1"]
    requests = _groups(distributions["total_of_special_requests"])
    assert {k: g["figure"]["numerator"] for k, g in requests.items()} == {"0": 2, "1": 1}


def test_analyze_compares_a_group_that_is_not_a_small_sample() -> None:
    comparison = _groups(_distributions(*_records())["country"])["PT"]["comparison"]

    assert comparison["status"] == "available"
    assert comparison["mean_length_of_stay"] == {"value": "2.5", "count": 2, "small_sample": False}
    assert comparison["cancellation_share"] == {
        "group": "cancellation_share",
        "numerator": 1,
        "denominator": 2,
        "small_sample": False,
    }
    assert comparison["mean_price_per_night"] == {
        "value": "25",
        "count": 2,
        "small_sample": False,
    }


def test_analyze_omits_the_comparison_of_a_small_sample_and_says_so() -> None:
    comparison = _groups(_distributions(*_records())["country"])["FR"]["comparison"]

    assert comparison["status"] == "omitted_small_sample"
    assert "FR" in comparison["statement"]
    assert "small sample" in comparison["statement"]
    assert "mean_length_of_stay" not in comparison
    assert "cancellation_share" not in comparison


def test_analyze_missing_field_makes_only_that_summary_unavailable() -> None:
    records = [
        BookingRecord(adults=2, country="PT", is_canceled=False),
        BookingRecord(adults=1, country="PT", is_canceled=True),
    ]

    distributions = _distributions(*records)

    assert distributions["meal"]["status"] == "unavailable"
    assert "meal" in distributions["meal"]["reason"]
    assert distributions["total_guests"]["status"] == "unavailable"
    assert "children" in distributions["total_guests"]["reason"]
    assert distributions["country"]["status"] == "available"


def test_analyze_comparison_metric_without_its_field_is_unavailable() -> None:
    records = [BookingRecord(country="PT"), BookingRecord(country="PT")]

    comparison = _groups(_distributions(*records)["country"])["PT"]["comparison"]

    assert comparison["status"] == "available"
    assert comparison["cancellation_share"]["status"] == "unavailable"
    assert comparison["mean_price_per_night"]["status"] == "unavailable"
    assert comparison["mean_length_of_stay"]["status"] == "unavailable"


def test_analyze_findings_contain_no_forbidden_words() -> None:
    analysis = _analyze(*_records())

    assert forbidden_words_in_findings(analysis.findings) == ()
