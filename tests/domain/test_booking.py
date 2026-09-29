"""Tests for DM-001 booking record (ADR-0001)."""

from datetime import date
from decimal import Decimal

import pytest

from hotel_booking_analysis.domain.booking import FIELD_NAMES, BookingRecord


def test_value_returns_field_value_when_valid() -> None:
    record = BookingRecord(lead_time=5, price_per_night=Decimal("19.0"))

    assert record.value("lead_time") == 5
    assert record.value("price_per_night") == Decimal("19.0")


def test_value_raises_key_error_for_non_contract_field() -> None:
    with pytest.raises(KeyError):
        BookingRecord().value("missing_fields")


def test_has_valid_is_false_when_any_field_is_empty() -> None:
    record = BookingRecord(lead_time=5, arrival_date=date(2022, 1, 1))

    assert record.has_valid("lead_time", "arrival_date")
    assert not record.has_valid("lead_time", "booking_date")


def test_every_contract_field_is_a_record_attribute() -> None:
    record = BookingRecord()

    assert all(record.value(name) is None for name in FIELD_NAMES)
