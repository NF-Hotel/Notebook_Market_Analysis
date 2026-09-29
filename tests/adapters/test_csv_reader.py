"""Tests for the development CSV reader (ADR-0001 fact list of the sample)."""

from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from hotel_booking_analysis.adapters.csv_reader import DevelopmentCsvReader
from hotel_booking_analysis.application.validate_bookings import validate_bookings
from hotel_booking_analysis.domain.booking import InputSource
from hotel_booking_analysis.domain.errors import InputError

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "example" / "nf_hotel_bookings.csv"

HEADER = "booking_id;is_canceled;lead_time;booking_date;arrival_date;meal;price_per_night;extra"


def _write(tmp_path: Path, *rows: str) -> Path:
    path = tmp_path / "sample.csv"
    path.write_text("\n".join([HEADER, *rows]) + "\n", encoding="utf-8")
    return path


def test_read_converts_semicolon_csv_with_day_first_dates(tmp_path: Path) -> None:
    path = _write(tmp_path, "1;0;348;08-03-2021;19-02-2022;BB;19.0;x")

    submission = DevelopmentCsvReader().read(path)

    record = submission.records[0]
    assert submission.source is InputSource.DEVELOPMENT_SAMPLE
    assert submission.reference == "sample.csv"
    assert record.booking_id == "1"
    assert record.is_canceled is False
    assert record.lead_time == 348
    assert record.booking_date == date(2021, 3, 8)
    assert record.arrival_date == date(2022, 2, 19)
    assert record.price_per_night == Decimal("19.0")
    assert submission.unknown_fields == ("extra",)


def test_read_treats_blank_cells_as_missing_and_bad_cells_as_invalid(tmp_path: Path) -> None:
    path = _write(tmp_path, "1;0;abc;31-02-2021;2022/01/01;;5;x")

    record = DevelopmentCsvReader().read(path).records[0]

    assert "meal" in record.missing_fields
    assert {"lead_time", "booking_date", "arrival_date"} <= record.invalid_fields


def test_read_rejects_csv_without_rows(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    path.write_text(HEADER + "\n", encoding="utf-8")

    with pytest.raises(InputError) as error:
        DevelopmentCsvReader().read(path)

    assert error.value.code == "INPUT_EMPTY"


def test_read_reports_missing_file_as_input_error(tmp_path: Path) -> None:
    with pytest.raises(InputError) as error:
        DevelopmentCsvReader().read(tmp_path / "absent.csv")

    assert error.value.code == "INPUT_NOT_FOUND"


@pytest.mark.skipif(not SAMPLE.is_file(), reason="sample CSV not present")
def test_sample_csv_matches_documented_facts() -> None:
    submission = DevelopmentCsvReader().read(SAMPLE)

    summary = validate_bookings(submission).summary
    records = submission.records
    assert summary.record_count == 8538
    assert summary.duplicate_booking_id_count == 0
    assert summary.missing_counts["meal"] == 87
    assert summary.zero_price_count == 91
    assert summary.earliest_arrival_date == date(2022, 1, 1)
    assert summary.latest_arrival_date == date(2025, 12, 31)
    assert summary.earliest_booking_date == date(2021, 3, 8)
    assert summary.latest_booking_date == date(2025, 12, 29)
    assert not summary.has_invalid_values
    assert Counter(r.hotel for r in records) == {"NF Hotel": 8538}
    assert all(
        r.lead_time == (r.arrival_date - r.booking_date).days
        for r in records
        if r.lead_time is not None and r.arrival_date and r.booking_date
    )
