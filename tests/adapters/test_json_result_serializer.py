"""Tests for result serialization and the version 1.0 schema (ADR-0002, US-001.08)."""

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from hotel_booking_analysis.adapters.json_result_serializer import (
    JsonResultSerializer,
    load_result_schema,
)
from hotel_booking_analysis.application.build_result import build_failed_result, build_result
from hotel_booking_analysis.application.validate_bookings import validate_bookings
from hotel_booking_analysis.domain.analysis import Analysis, AnalysisName, Availability
from hotel_booking_analysis.domain.booking import BookingRecord
from hotel_booking_analysis.domain.errors import InputError, Notice
from hotel_booking_analysis.domain.result import AnalysisResult
from tests.support import full_record, make_submission

MOMENT = datetime(2026, 9, 29, 12, 0, 1, 250000, tzinfo=UTC)
ID = "00000000-0000-0000-0000-000000000001"
VALIDATOR = Draft202012Validator(load_result_schema())


def _result(*records: BookingRecord, notices: tuple[Notice, ...] = ()) -> AnalysisResult:
    validated = validate_bookings(make_submission(*records))
    return build_result(validated, notices, ID, MOMENT)


def _document(result: AnalysisResult) -> dict[str, Any]:  # JSON document, shape checked by schema
    parsed: dict[str, Any] = json.loads(JsonResultSerializer().serialize(result))
    return parsed


def test_schema_is_a_valid_json_schema() -> None:
    Draft202012Validator.check_schema(load_result_schema())


def test_serialize_completed_result_validates_against_schema() -> None:
    VALIDATOR.validate(_document(_result(full_record())))


def test_serialize_result_with_unavailable_analyses_validates_against_schema() -> None:
    record = BookingRecord(lead_time=5, missing_fields=frozenset({"is_canceled"}))

    VALIDATOR.validate(_document(_result(record)))


def test_serialize_failed_result_validates_against_schema() -> None:
    failed = build_failed_result(InputError("INPUT_INVALID_JSON", "bad"), (), ID, MOMENT)

    document = _document(failed)

    VALIDATOR.validate(document)
    assert document["status"] == "failed"
    assert document["error"] == {"code": "INPUT_INVALID_JSON", "message": "bad"}
    assert "input" not in document


def test_serialize_is_one_compact_line_of_ascii_safe_json() -> None:
    notice = Notice("X", "line one\nline two " + chr(0x2028) + " caf" + chr(0xE9))

    text = JsonResultSerializer().serialize(_result(full_record(), notices=(notice,)))

    assert "\n" not in text
    assert "\r" not in text
    assert len(text.splitlines()) == 1
    assert text == json.dumps(json.loads(text), separators=(",", ":"), ensure_ascii=True)
    assert json.loads(text)["notices"][0]["message"] == notice.message


def test_serialize_writes_generated_at_as_rfc3339_utc() -> None:
    local = MOMENT.astimezone(timezone(timedelta(hours=7)))
    validated = validate_bookings(make_submission(full_record()))
    result = build_result(validated, (), ID, local)

    assert _document(result)["generated_at"] == "2026-09-29T12:00:01.250Z"


def test_serialize_reports_file_name_only_and_hash() -> None:
    document = _document(_result(full_record()))

    assert document["input"]["reference"] == "bookings.json"
    assert document["input"]["content_sha256"] == "0" * 64
    assert document["schema_version"] == "1.0"
    assert document["result_id"] == ID


def test_serialize_contains_no_raw_booking_records() -> None:
    record = BookingRecord(booking_id="SECRET-77", lead_time=123456, adults=2, country="Zzyzx")

    text = JsonResultSerializer().serialize(_result(record))

    assert "SECRET-77" not in text
    assert "Zzyzx" not in text
    assert "123456" not in text


def test_serialize_writes_money_as_decimal_string() -> None:
    result = _result(full_record())
    money = Analysis(
        AnalysisName.ROOM_VALUE,
        Availability.AVAILABLE,
        findings={"estimate": Decimal("1234.50")},  # type: ignore[dict-item]
    )
    with_money = AnalysisResult(
        result_id=result.result_id,
        generated_at=result.generated_at,
        status=result.status,
        input=result.input,
        data_quality=result.data_quality,
        analyses=(money,),
    )

    text = JsonResultSerializer().serialize(with_money)

    assert json.loads(text)["analyses"]["room_value"]["findings"]["estimate"] == "1234.50"


def test_serialize_same_result_twice_gives_identical_text() -> None:
    result = _result(full_record())

    assert JsonResultSerializer().serialize(result) == JsonResultSerializer().serialize(result)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.pop("result_id"),
        lambda d: d.update(status="unknown"),
        lambda d: d.update(schema_version="2.0"),
        lambda d: d.update(records=[{"booking_id": "1"}]),
        lambda d: d["input"].update(reference="dir/bookings.json"),
        lambda d: d.update(generated_at="2026-09-29 12:00:00"),
        lambda d: d["analyses"].pop("lead_time"),
        lambda d: d["analyses"]["lead_time"].update(status="unavailable"),
        lambda d: d.update(error={"code": "X", "message": "y"}),
    ],
)
def test_schema_rejects_documents_that_break_the_contract(
    mutate: Callable[[dict[str, Any]], object],
) -> None:
    document = _document(_result(full_record()))
    mutate(document)

    assert not VALIDATOR.is_valid(document)
