"""Builders of stored results for the interface tests: real ones and hand-built ones."""

import io
import json
from pathlib import Path
from typing import Any

from hotel_booking_analysis.infrastructure.cli import main

HISTORY_RELATIVE = Path("output") / "analysis_history.jsonl"

Result = dict[str, Any]  # a parsed history line; tests index into it


def booking(number: int, without: tuple[str, ...] = ()) -> dict[str, Any]:
    record: dict[str, Any] = {  # JSON fixture, values follow ADR-0001
        "booking_id": str(number),
        "is_canceled": number % 3 == 0,
        "lead_time": 10 + number,
        "booking_date": f"2023-03-{number:02d}",
        "arrival_date": f"2023-04-{number:02d}",
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
    for name in without:
        del record[name]
    return record


def run_analysis(working_directory: Path, without: tuple[str, ...] = ()) -> Result:
    """Run the real use case on a small fixture without the given fields; return the result."""
    records = [booking(number, without) for number in range(1, 8)]
    bookings = working_directory / "bookings.json"
    bookings.write_text(json.dumps(records), encoding="utf-8")
    code = main(
        ["analyze", "--input", str(bookings)],
        io.BytesIO(),
        io.StringIO(),
        working_directory,
        {},
        lock_wait_seconds=0.2,
    )
    assert code == 0
    lines = (working_directory / HISTORY_RELATIVE).read_text(encoding="utf-8").splitlines()
    stored: Result = json.loads(lines[-1])
    return stored


def write_history(working_directory: Path, *results: Result, extra: str = "") -> Path:
    """Write results (and raw extra text) as the history file of the default location."""
    path = working_directory / HISTORY_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(result, separators=(",", ":")) + "\n" for result in results)
    path.write_text(body + extra, encoding="utf-8")
    return path


def with_identity(result: Result, result_id: str, generated_at: str) -> Result:
    return {**result, "result_id": result_id, "generated_at": generated_at}
