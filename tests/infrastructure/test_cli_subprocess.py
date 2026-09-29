"""Subprocess smoke tests of `python -m hotel_booking_analysis analyze` (ADR-0006, UC-001)."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from hotel_booking_analysis.adapters.json_result_serializer import load_result_schema

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_CSV = REPO_ROOT / "data" / "example" / "nf_hotel_bookings.csv"


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-m", "hotel_booking_analysis", "analyze", *args],
        cwd=cwd,
        capture_output=True,
        check=False,
        timeout=60,
    )


def test_module_run_on_json_fixture_writes_result_to_stdout_and_history(tmp_path: Path) -> None:
    source = tmp_path / "bookings.json"
    source.write_text(
        json.dumps(
            [
                {
                    "booking_id": "1",
                    "is_canceled": False,
                    "lead_time": 10,
                    "booking_date": "2021-03-08",
                    "arrival_date": "2021-03-18",
                    "stays_in_weekend_nights": 1,
                    "stays_in_week_nights": 2,
                    "adults": 2,
                }
            ]
        ),
        encoding="utf-8",
    )

    completed = _run(tmp_path, "--input", str(source))

    assert completed.returncode == 0, completed.stderr.decode()
    Draft202012Validator(load_result_schema()).validate(json.loads(completed.stdout))
    history = tmp_path / "output" / "analysis_history.jsonl"
    assert history.read_bytes() == completed.stdout
    assert b"\r" not in completed.stdout
    assert completed.stderr


def test_module_run_with_invalid_input_exits_2_with_failed_result(tmp_path: Path) -> None:
    source = tmp_path / "bad.json"
    source.write_text("not json", encoding="utf-8")

    completed = _run(tmp_path, "--input", str(source))

    assert completed.returncode == 2
    assert json.loads(completed.stdout)["status"] == "failed"
    assert not (tmp_path / "output").exists()


@pytest.mark.skipif(not SAMPLE_CSV.is_file(), reason="development CSV is not present")
def test_module_run_falls_back_to_development_csv(tmp_path: Path) -> None:
    config = tmp_path / "hotel_analysis.toml"
    history = tmp_path / "history.jsonl"
    config.write_text(
        f"environment = 'development'\n[history]\npath = '{history.as_posix()}'\n",
        encoding="utf-8",
    )

    completed = _run(REPO_ROOT, "--config", str(config))

    assert completed.returncode == 0, completed.stderr.decode()
    document = json.loads(completed.stdout)
    Draft202012Validator(load_result_schema()).validate(document)
    assert document["input"]["source"] == "development_sample"
    assert history.read_bytes() == completed.stdout
