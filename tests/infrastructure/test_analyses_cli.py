"""Full-result tests with all six real analyses (MIL-005 criteria 4, 5, 6 and task 8)."""

import csv
import io
import json
import statistics
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from hotel_booking_analysis.adapters.json_result_serializer import load_result_schema
from hotel_booking_analysis.application.placeholder_analyses import ANALYSIS_NOT_IMPLEMENTED
from hotel_booking_analysis.domain.analysis import AnalysisName
from hotel_booking_analysis.domain.wording import forbidden_words_in_findings
from hotel_booking_analysis.infrastructure.bootstrap import build_analyzers
from hotel_booking_analysis.infrastructure.cli import main

VALIDATOR = Draft202012Validator(load_result_schema())
SAMPLE_CSV = Path(__file__).resolve().parents[2] / "data" / "example" / "nf_hotel_bookings.csv"


def _booking(number: int, arrival: str, booked: str, lead: int, canceled: bool) -> dict[str, Any]:
    return {  # JSON fixture, values follow ADR-0001
        "booking_id": str(number),
        "is_canceled": canceled,
        "lead_time": lead,
        "booking_date": booked,
        "arrival_date": arrival,
        "market_segment": "Online",
        "customer_type": "Transient",
        "stays_in_weekend_nights": 1,
        "stays_in_week_nights": 2,
        "adults": 2,
        "children": 0,
        "babies": 0,
        "country": "PT",
        "meal": "BB",
        "assigned_room_type": "A",
        "is_repeated_guest": False,
        "required_car_parking_spaces": 0,
        "total_of_special_requests": number % 2,
        "deposit_type": "No Deposit",
        "booking_changes": 0,
        "price_per_night": 27.31,
    }


def _run(tmp_path: Path, records: list[dict[str, Any]]) -> tuple[dict[str, Any], str, str]:
    bookings = tmp_path / "bookings.json"
    bookings.write_text(json.dumps(records), encoding="utf-8")
    history = tmp_path / "out" / "h.jsonl"
    config = tmp_path / "hotel_analysis.toml"
    config.write_text(f"[history]\npath = '{history.as_posix()}'\n", encoding="utf-8")
    out = io.BytesIO()
    code = main(
        ["analyze", "--input", str(bookings), "--config", str(config)],
        out,
        io.StringIO(),
        tmp_path,
        {},
        lock_wait_seconds=0.2,
    )
    assert code == 0
    line = out.getvalue().decode().removesuffix("\n")
    stored = history.read_text(encoding="utf-8").splitlines()
    assert len(stored) == 1
    document: dict[str, Any] = json.loads(line)
    return document, line, stored[0]


def _records() -> list[dict[str, Any]]:
    return [
        _booking(1, "2023-04-14", "2023-03-01", 44, False),
        _booking(2, "2023-04-20", "2023-04-10", 10, True),
        _booking(3, "2023-05-02", "2023-04-30", 3, False),
    ]


def test_full_result_with_real_analyses_validates_and_equals_the_history_line(
    tmp_path: Path,
) -> None:
    document, line, stored = _run(tmp_path, _records())

    VALIDATOR.validate(document)
    assert line == stored
    assert document["analyses"]["lead_time"]["status"] == "available"
    assert document["analyses"]["holidays"]["status"] == "available"


def test_build_analyzers_covers_all_six_analyses() -> None:
    assert {analyzer.name for analyzer in build_analyzers()} == set(AnalysisName)


def test_full_result_has_no_placeholder_findings_and_no_not_implemented_notice(
    tmp_path: Path,
) -> None:
    document, line, _ = _run(tmp_path, _records())

    for name, analysis in document["analyses"].items():
        assert analysis["status"] == "available", name
        assert "implemented" not in analysis["findings"], name
    assert ANALYSIS_NOT_IMPLEMENTED not in line
    assert [n["code"] for n in document["notices"]] == ["ESTIMATE_NOT_REVENUE"]


def test_full_result_findings_use_no_causal_wording(tmp_path: Path) -> None:
    document, _, _ = _run(tmp_path, _records())

    for name in AnalysisName:
        assert forbidden_words_in_findings(document["analyses"][name.value]["findings"]) == ()


def test_full_result_room_value_states_the_estimate_and_the_notice_code(tmp_path: Path) -> None:
    document, _, _ = _run(tmp_path, _records())

    findings = document["analyses"]["room_value"]["findings"]
    assert findings["estimate"]["notice_code"] == "ESTIMATE_NOT_REVENUE"
    assert "not realized revenue" in findings["estimate"]["label"]
    groups = {g["figure"]["group"]: g for g in findings["estimated_value"]["groups"]}
    assert groups["not_canceled"]["total"] == "163.86"  # 27.31 x 3 nights x 2 bookings
    assert groups["canceled"]["total"] == "81.93"


def test_full_result_group_figures_have_the_adr_0002_shape(tmp_path: Path) -> None:
    document, _, _ = _run(tmp_path, _records())

    figure = document["analyses"]["lead_time"]["findings"]["overall"]["figure"]
    assert figure == {"group": "all", "numerator": 3, "denominator": 3, "small_sample": True}


@pytest.mark.skipif(not SAMPLE_CSV.is_file(), reason="development CSV is not present")
def test_development_sample_result_validates_and_equals_the_history_line(tmp_path: Path) -> None:
    history = tmp_path / "out" / "h.jsonl"
    config = tmp_path / "hotel_analysis.toml"
    config.write_text(
        f"environment = 'development'\n[history]\npath = '{history.as_posix()}'\n",
        encoding="utf-8",
    )
    out = io.BytesIO()

    code = main(
        ["analyze", "--config", str(config)],
        out,
        io.StringIO(),
        SAMPLE_CSV.parents[2],
        {},
        lock_wait_seconds=0.2,
    )

    assert code == 0
    document = json.loads(out.getvalue())
    VALIDATOR.validate(document)
    stored = history.read_text(encoding="utf-8").splitlines()[0]
    assert out.getvalue().decode().removesuffix("\n") == stored
    for name in AnalysisName:
        analysis = document["analyses"][name.value]
        assert analysis["status"] == "available"
        assert forbidden_words_in_findings(analysis["findings"]) == ()
    assert ANALYSIS_NOT_IMPLEMENTED not in out.getvalue().decode()
    holidays = document["analyses"]["holidays"]["findings"]
    assert holidays["booking_date"]["years_used"] == [2021, 2022, 2023, 2024, 2025]
    assert holidays["arrival_date"]["years_used"] == [2022, 2023, 2024, 2025]


def _csv_rows() -> list[dict[str, str]]:
    with SAMPLE_CSV.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


@pytest.mark.skipif(not SAMPLE_CSV.is_file(), reason="development CSV is not present")
def test_development_sample_key_figures_match_an_independent_computation(tmp_path: Path) -> None:
    history = tmp_path / "out" / "h.jsonl"
    config = tmp_path / "hotel_analysis.toml"
    config.write_text(
        f"environment = 'development'\n[history]\npath = '{history.as_posix()}'\n",
        encoding="utf-8",
    )
    out = io.BytesIO()
    main(["analyze", "--config", str(config)], out, io.StringIO(), SAMPLE_CSV.parents[2], {})
    analyses = json.loads(out.getvalue())["analyses"]
    rows = _csv_rows()

    canceled = sum(1 for r in rows if r["is_canceled"] == "1")
    overall = analyses["cancellations"]["findings"]["overall"]
    assert (overall["numerator"], overall["denominator"]) == (canceled, len(rows))

    median = statistics.median(int(r["lead_time"]) for r in rows)
    assert analyses["lead_time"]["findings"]["overall"]["median_days"] == median

    totals = {"canceled": Decimal(0), "not_canceled": Decimal(0)}
    counts = {"canceled": 0, "not_canceled": 0}
    for r in rows:
        nights = int(r["stays_in_weekend_nights"]) + int(r["stays_in_week_nights"])
        if nights == 0:
            continue
        key = "canceled" if r["is_canceled"] == "1" else "not_canceled"
        totals[key] += Decimal(r["price_per_night"]) * nights
        counts[key] += 1
    groups = {
        g["figure"]["group"]: g
        for g in analyses["room_value"]["findings"]["estimated_value"]["groups"]
    }
    for key in totals:
        assert Decimal(groups[key]["total"]) == totals[key]
        assert groups[key]["count"] == counts[key]

    arrivals = analyses["seasonality"]["findings"]["arrivals"]["monthly"]["periods"]
    assert sum(p["figure"]["numerator"] for p in arrivals) == len(rows)
    arrival_days = (r["arrival_date"] for r in rows)  # dd-mm-yyyy
    first = min(date(int(d[6:]), int(d[3:5]), int(d[:2])) for d in arrival_days)
    assert arrivals[0]["figure"]["group"] == first.strftime("%Y-%m")
