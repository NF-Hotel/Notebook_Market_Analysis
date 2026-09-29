"""Tests for the ADR-0001 value rules."""

from datetime import date
from decimal import Decimal

import pytest

from hotel_booking_analysis.adapters.record_parsing import parse_record, unknown_field_names


def test_parse_record_reads_valid_values_of_every_type() -> None:
    record = parse_record(
        {
            "booking_id": 7,
            "is_canceled": 1,
            "is_repeated_guest": False,
            "lead_time": 348,
            "booking_date": "2021-03-08",
            "arrival_date": "2022-02-19",
            "meal": "BB",
            "agent": 0,
            "price_per_night": Decimal("27.31"),
        }
    )

    assert record.booking_id == "7"
    assert record.is_canceled is True
    assert record.is_repeated_guest is False
    assert record.lead_time == 348
    assert record.booking_date == date(2021, 3, 8)
    assert record.arrival_date == date(2022, 2, 19)
    assert record.meal == "BB"
    assert record.agent == "0"
    assert record.price_per_night == Decimal("27.31")
    assert "lead_time" not in record.missing_fields | record.invalid_fields


@pytest.mark.parametrize(
    ("value", "expected"),
    [(True, True), (False, False), (1, True), (0, False)],
)
def test_boolean_accepts_true_false_one_zero(value: object, expected: bool) -> None:
    assert parse_record({"is_canceled": value}).is_canceled is expected


@pytest.mark.parametrize("value", [2, -1, "true", "1", Decimal("1.0"), []])
def test_boolean_rejects_other_spellings_as_invalid(value: object) -> None:
    record = parse_record({"is_canceled": value})

    assert record.is_canceled is None
    assert "is_canceled" in record.invalid_fields


@pytest.mark.parametrize("value", [None, "", "   "])
def test_null_blank_and_absent_values_are_missing(value: object) -> None:
    present = parse_record({"meal": value})
    absent = parse_record({})

    assert present.meal is None
    assert "meal" in present.missing_fields
    assert "meal" in absent.missing_fields
    assert "meal" not in present.invalid_fields


@pytest.mark.parametrize(
    "value", ["2022-13-01", "01-02-2022", "2022-01-01T10:00:00", "20220101", 5]
)
def test_unparseable_dates_are_invalid(value: object) -> None:
    record = parse_record({"arrival_date": value})

    assert record.arrival_date is None
    assert "arrival_date" in record.invalid_fields


@pytest.mark.parametrize("value", ["12", 3.5, True, -1, Decimal("2.0")])
def test_wrongly_typed_or_negative_integers_are_invalid(value: object) -> None:
    record = parse_record({"lead_time": value})

    assert record.lead_time is None
    assert "lead_time" in record.invalid_fields


@pytest.mark.parametrize("value", ["19.0", True, Decimal("-1")])
def test_invalid_price_is_reported_invalid(value: object) -> None:
    record = parse_record({"price_per_night": value})

    assert record.price_per_night is None
    assert "price_per_night" in record.invalid_fields


def test_zero_price_is_valid() -> None:
    record = parse_record({"price_per_night": 0})

    assert record.price_per_night == Decimal(0)
    assert "price_per_night" not in record.invalid_fields


def test_text_field_with_number_is_invalid() -> None:
    record = parse_record({"country": 12})

    assert record.country is None
    assert "country" in record.invalid_fields


def test_unknown_field_names_are_sorted_and_deduplicated() -> None:
    raws = [{"booking_id": 1, "b": 1}, {"a": 2, "b": 3}]

    assert unknown_field_names(raws) == ("a", "b")
