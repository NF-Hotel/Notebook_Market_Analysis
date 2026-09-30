"""Tests for the holiday listing serializer and its schema (ADR-0011, UC-003)."""

import json
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta, timezone
from typing import Any

import pytest
from jsonschema import Draft202012Validator, ValidationError

from hotel_booking_analysis.adapters.json_holiday_listing_serializer import (
    JsonHolidayListingSerializer,
    load_holiday_listing_schema,
)
from hotel_booking_analysis.domain.analysis import Holiday
from hotel_booking_analysis.domain.errors import Notice
from hotel_booking_analysis.domain.listing import HolidayCalendarListing, HolidayCalendarYear
from hotel_booking_analysis.domain.result import ResultError

MOMENT = datetime(2026, 9, 30, 8, 0, 1, 250000, tzinfo=UTC)
VALIDATOR = Draft202012Validator(load_holiday_listing_schema())
SOURCE = Notice("CALENDAR_SOURCE", "Holidays from the Python 'holidays' package 0.1 for KH.")


def _listing(*years: HolidayCalendarYear, notices: tuple[Notice, ...] = (SOURCE,)) -> str:
    return JsonHolidayListingSerializer().serialize(HolidayCalendarListing(MOMENT, years, notices))


def _document(line: str) -> dict[str, Any]:  # JSON document, shape checked by the schema
    parsed: dict[str, Any] = json.loads(line)
    return parsed


def _available(year: int = 2025) -> HolidayCalendarYear:
    return HolidayCalendarYear.from_holidays(
        year, (Holiday(date(year, 1, 1), "New Year"), Holiday(date(year, 4, 14), "Khmer é"))
    )


def test_schema_is_a_valid_json_schema() -> None:
    Draft202012Validator.check_schema(load_holiday_listing_schema())


def test_serialize_listing_with_available_and_unavailable_years_validates() -> None:
    line = _listing(HolidayCalendarYear.from_holidays(1900, ()), _available())

    document = _document(line)

    VALIDATOR.validate(document)
    assert document["kind"] == "holiday_calendar"
    assert document["schema_version"] == "1.0"
    assert document["status"] == "completed"
    assert document["country"] == "KH"
    assert document["generated_at"] == "2026-09-30T08:00:01.250Z"
    assert document["years"][0] == {
        "year": 1900,
        "status": "unavailable",
        "reason": "NO_CALENDAR_DATA",
    }
    assert document["years"][1]["holidays"][0] == {"date": "2025-01-01", "name": "New Year"}
    assert "error" not in document


def test_serialize_writes_one_compact_ascii_line() -> None:
    line = _listing(_available())

    assert "\n" not in line
    assert ": " not in line
    assert ", " not in line
    assert line.isascii()
    assert json.loads(line)["years"][0]["holidays"][1]["name"] == "Khmer é"


def test_serialize_converts_generated_at_to_utc() -> None:
    zone = timezone(timedelta(hours=7))
    listing = HolidayCalendarListing(
        datetime(2026, 9, 30, 15, 0, tzinfo=zone), (_available(),), (SOURCE,)
    )

    document = _document(JsonHolidayListingSerializer().serialize(listing))

    assert document["generated_at"] == "2026-09-30T08:00:00.000Z"


def test_serialize_failure_has_error_empty_notices_and_no_years() -> None:
    line = JsonHolidayListingSerializer().serialize_failure(
        ResultError("INVALID_YEARS", "The year 2101 is outside 1900 to 2100."), (), MOMENT
    )

    document = _document(line)

    VALIDATOR.validate(document)
    assert document["status"] == "failed"
    assert document["error"] == {
        "code": "INVALID_YEARS",
        "message": "The year 2101 is outside 1900 to 2100.",
    }
    assert document["notices"] == []
    assert "years" not in document
    assert "country" not in document


def test_serialize_failure_accepts_configuration_error_code() -> None:
    line = JsonHolidayListingSerializer().serialize_failure(
        ResultError("CONFIGURATION_ERROR", "The configuration file cannot be read."), (), MOMENT
    )

    VALIDATOR.validate(_document(line))


def test_serialize_is_deterministic_for_the_same_listing() -> None:
    assert _listing(_available()) == _listing(_available())


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d.update(kind="llm_providers"),
        lambda d: d.update(schema_version="1.1"),
        lambda d: d.update(country="TH"),
        lambda d: d.update(extra=1),
        lambda d: d.update(notices=[]),
        lambda d: d.update(years=[]),
        lambda d: d.update(error={"code": "INVALID_YEARS", "message": "x"}),
        lambda d: d["years"][0].update(reason="NO_CALENDAR_DATA"),
        lambda d: d["years"][0].pop("holidays"),
        lambda d: d["years"][0]["holidays"].clear(),
        lambda d: d["years"][0].update(year=1899),
        lambda d: d["years"][0]["holidays"][0].update(date="2025-1-1"),
        lambda d: d.update(generated_at="2026-09-30T08:00:00+07:00"),
    ],
)
def test_schema_rejects_documents_that_break_the_contract(
    change: Callable[[dict[str, Any]], object],
) -> None:
    document = _document(_listing(_available()))
    change(document)

    with pytest.raises(ValidationError):
        VALIDATOR.validate(document)


def test_schema_rejects_failed_document_with_years_or_notices() -> None:
    failed = _document(
        JsonHolidayListingSerializer().serialize_failure(
            ResultError("INVALID_YEARS", "bad"), (), MOMENT
        )
    )

    changes: tuple[dict[str, Any], ...] = (
        {"years": []},
        {"notices": [{"code": "CALENDAR_SOURCE", "message": "x"}]},
        {"error": {"code": "OTHER", "message": "x"}},
    )
    for change in changes:
        with pytest.raises(ValidationError):
            VALIDATOR.validate({**failed, **change})


def test_schema_rejects_completed_document_without_calendar_source_notice() -> None:
    with pytest.raises(ValidationError):
        VALIDATOR.validate(_document(_listing(_available(), notices=())))
