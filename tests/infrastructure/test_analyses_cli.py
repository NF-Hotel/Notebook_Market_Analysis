"""Full-result tests with the real lead-time and holiday analyses (MIL-005 criteria 5 and 6)."""

import io
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from hotel_booking_analysis.adapters.json_result_serializer import load_result_schema
from hotel_booking_analysis.application.placeholder_analyses import ANALYSIS_NOT_IMPLEMENTED
from hotel_booking_analysis.domain.wording import forbidden_words_in_findings
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


def test_full_result_marks_only_unimplemented_analyses_as_placeholders(tmp_path: Path) -> None:
    document, _, _ = _run(tmp_path, _records())

    analyses = document["analyses"]
    assert "implemented" not in analyses["lead_time"]["findings"]
    assert "implemented" not in analyses["holidays"]["findings"]
    for name in ("seasonality", "cancellations", "room_value", "guest_mix"):
        assert analyses[name]["findings"] == {"implemented": False}
    notices = [n for n in document["notices"] if n["code"] == ANALYSIS_NOT_IMPLEMENTED]
    assert len(notices) == 4
    assert not any("lead_time" in n["message"] or "holidays" in n["message"] for n in notices)


def test_full_result_findings_use_no_causal_wording(tmp_path: Path) -> None:
    document, _, _ = _run(tmp_path, _records())

    for name in ("lead_time", "holidays"):
        assert forbidden_words_in_findings(document["analyses"][name]["findings"]) == ()


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
    for name in ("lead_time", "holidays"):
        assert forbidden_words_in_findings(document["analyses"][name]["findings"]) == ()
    holidays = document["analyses"]["holidays"]["findings"]
    assert holidays["booking_date"]["years_used"] == [2021, 2022, 2023, 2024, 2025]
    assert holidays["arrival_date"]["years_used"] == [2022, 2023, 2024, 2025]
