"""Tests for the JSON booking reader (ADR-0001, UC-001 extension 2a)."""

import hashlib
from decimal import Decimal
from pathlib import Path

import pytest

from hotel_booking_analysis.adapters.json_reader import JsonBookingReader
from hotel_booking_analysis.domain.booking import InputSource
from hotel_booking_analysis.domain.errors import InputError
from tests.support import write_json


def test_read_returns_supplied_submission_with_file_name_only(tmp_path: Path) -> None:
    path = write_json(tmp_path / "bookings.json", [{"booking_id": 1, "lead_time": 3}])

    submission = JsonBookingReader().read(path)

    assert submission.source is InputSource.SUPPLIED
    assert submission.reference == "bookings.json"
    assert len(submission.records) == 1
    assert submission.records[0].lead_time == 3
    assert submission.content_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()


def test_read_parses_price_as_exact_decimal(tmp_path: Path) -> None:
    path = tmp_path / "b.json"
    path.write_text('[{"booking_id": 1, "price_per_night": 27.31}]', encoding="utf-8")

    price = JsonBookingReader().read(path).records[0].price_per_night

    assert price == Decimal("27.31")
    assert isinstance(price, Decimal)


def test_read_reports_unknown_fields_and_ignores_them(tmp_path: Path) -> None:
    path = write_json(tmp_path / "b.json", [{"booking_id": 1, "zzz": 1, "aaa": 2}])

    submission = JsonBookingReader().read(path)

    assert submission.unknown_fields == ("aaa", "zzz")


def test_read_keeps_records_with_bad_values_and_counts_them(tmp_path: Path) -> None:
    path = write_json(
        tmp_path / "b.json",
        [
            {"booking_id": 1, "arrival_date": "nope"},
            {"booking_id": 1, "arrival_date": "2022-01-01"},
        ],
    )

    submission = JsonBookingReader().read(path)

    assert len(submission.records) == 2
    assert "arrival_date" in submission.records[0].invalid_fields


def test_read_rejects_empty_array(tmp_path: Path) -> None:
    with pytest.raises(InputError) as error:
        JsonBookingReader().read(write_json(tmp_path / "b.json", []))

    assert error.value.code == "INPUT_EMPTY"


@pytest.mark.parametrize("document", [{"records": []}, "text", 5, None])
def test_read_rejects_top_level_that_is_not_an_array(tmp_path: Path, document: object) -> None:
    with pytest.raises(InputError) as error:
        JsonBookingReader().read(write_json(tmp_path / "b.json", document))

    assert error.value.code == "INPUT_NOT_ARRAY"


@pytest.mark.parametrize("content", [b"[{", b"not json", b"", b"[NaN]", b"\xff\xfe"])
def test_read_rejects_invalid_json(tmp_path: Path, content: bytes) -> None:
    path = tmp_path / "b.json"
    path.write_bytes(content)

    with pytest.raises(InputError) as error:
        JsonBookingReader().read(path)

    assert error.value.code == "INPUT_INVALID_JSON"


def test_read_rejects_array_item_that_is_not_an_object(tmp_path: Path) -> None:
    with pytest.raises(InputError) as error:
        JsonBookingReader().read(write_json(tmp_path / "b.json", [{"booking_id": 1}, 3]))

    assert error.value.code == "INPUT_RECORD_NOT_OBJECT"


def test_read_reports_missing_file_as_input_error(tmp_path: Path) -> None:
    with pytest.raises(InputError) as error:
        JsonBookingReader().read(tmp_path / "absent.json")

    assert error.value.code == "INPUT_NOT_FOUND"
