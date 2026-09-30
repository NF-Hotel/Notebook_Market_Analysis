"""Tests of the `holidays` command in process and as a subprocess (UC-003, ADR-0008, ADR-0011)."""

import io
import json
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Any

import holidays
import pytest
from jsonschema import Draft202012Validator

from hotel_booking_analysis.adapters.json_holiday_listing_serializer import (
    load_holiday_listing_schema,
)
from hotel_booking_analysis.infrastructure.cli import main

VALIDATOR = Draft202012Validator(load_holiday_listing_schema())
REPO_ROOT = Path(__file__).resolve().parents[2]


class Run:
    def __init__(self, code: int, stdout: bytes, stderr: str) -> None:
        self.code = code
        self.stdout = stdout
        self.stderr = stderr

    @property
    def document(self) -> dict[str, Any]:
        parsed: dict[str, Any] = json.loads(self.stdout)
        VALIDATOR.validate(parsed)
        return parsed


class BrokenStdout(io.BytesIO):
    def write(self, buffer: Any) -> int:  # noqa: ANN401 - matches io.BytesIO.write signature
        raise OSError("broken pipe")


def _holidays(
    tmp_path: Path, *args: str, stdout: io.BytesIO | None = None, config: str | None = None
) -> Run:
    out = stdout if stdout is not None else io.BytesIO()
    err = io.StringIO()
    extra: list[str] = []
    if config is not None:
        path = tmp_path / "custom.toml"
        path.write_text(config, encoding="utf-8")
        extra = ["--config", str(path)]
    code = main(["holidays", *args, *extra], out, err, tmp_path, {})
    return Run(code, out.getvalue(), err.getvalue())


def test_holidays_with_years_lists_khmer_holidays_from_the_holidays_package(
    tmp_path: Path,
) -> None:
    run = _holidays(tmp_path, "--years", "2025")

    assert run.code == 0
    document = run.document
    expected = sorted(holidays.country_holidays("KH", years=2025).items())
    (entry,) = document["years"]
    assert entry["status"] == "available"
    assert [(h["date"], h["name"]) for h in entry["holidays"]] == [
        (day.isoformat(), name) for day, name in expected
    ]
    assert [n["code"] for n in document["notices"]] == ["CALENDAR_SOURCE"]
    assert version("holidays") in document["notices"][0]["message"]
    assert run.stdout.endswith(b"\n")
    assert run.stdout.count(b"\n") == 1


def test_holidays_range_and_list_are_ascending(tmp_path: Path) -> None:
    range_run = _holidays(tmp_path, "--years", "2023-2025")
    list_run = _holidays(tmp_path, "--years", "2025,2023")

    assert [y["year"] for y in range_run.document["years"]] == [2023, 2024, 2025]
    assert [y["year"] for y in list_run.document["years"]] == [2023, 2025]


def test_holidays_without_years_uses_current_year_and_default_year_notice(
    tmp_path: Path,
) -> None:
    run = _holidays(tmp_path)

    assert run.code == 0
    document = run.document
    assert len(document["years"]) == 1
    assert [n["code"] for n in document["notices"]] == ["CALENDAR_SOURCE", "DEFAULT_YEAR_USED"]
    assert str(document["years"][0]["year"]) in document["notices"][1]["message"]


def test_holidays_lists_year_without_calendar_data_as_unavailable(tmp_path: Path) -> None:
    run = _holidays(tmp_path, "--years", "1900")

    assert run.code == 0
    entry = run.document["years"][0]
    assert not holidays.country_holidays("KH", years=1900)
    assert entry == {"year": 1900, "status": "unavailable", "reason": "NO_CALENDAR_DATA"}


@pytest.mark.parametrize("years", ["", "abc", "2026-2024", "1899", "2024-2026,2028", "2000-2030"])
def test_holidays_invalid_years_gives_failed_document_and_exit_2(
    tmp_path: Path, years: str
) -> None:
    run = _holidays(tmp_path, "--years", years)

    assert run.code == 2
    document = run.document
    assert document["status"] == "failed"
    assert document["error"]["code"] == "INVALID_YEARS"
    assert document["notices"] == []
    assert "years" not in document
    assert "Holiday listing delivered" not in run.stderr


def test_holidays_unparsable_config_gives_configuration_error_and_exit_2(tmp_path: Path) -> None:
    run = _holidays(tmp_path, "--years", "2025", config="this is not toml [")

    assert run.code == 2
    document = run.document
    assert document["error"]["code"] == "CONFIGURATION_ERROR"
    assert "years" not in document


def test_holidays_ignores_invalid_llm_values(tmp_path: Path) -> None:
    run = _holidays(tmp_path, "--years", "2025", config="[llm]\ntemperature = 9\nprovider = 1\n")

    assert run.code == 0
    assert run.document["status"] == "completed"


def test_holidays_llm_that_is_not_a_table_gives_configuration_error(tmp_path: Path) -> None:
    run = _holidays(tmp_path, "--years", "2025", config='llm = "on"\n')

    assert run.code == 2
    assert run.document["error"]["code"] == "CONFIGURATION_ERROR"


def test_holidays_does_not_touch_the_history_or_write_files(tmp_path: Path) -> None:
    before = sorted(tmp_path.rglob("*"))

    run = _holidays(tmp_path, "--years", "2024-2025")

    assert run.code == 0
    assert sorted(tmp_path.rglob("*")) == before
    assert not (tmp_path / "output").exists()


def test_holidays_delivery_failure_exits_4_with_message_on_stderr(tmp_path: Path) -> None:
    run = _holidays(tmp_path, "--years", "2025", stdout=BrokenStdout())

    assert run.code == 4
    assert run.stdout == b""
    assert "could not be written" in run.stderr
    assert "nothing was stored" in run.stderr


def test_holidays_delivery_failure_of_failed_document_exits_4(tmp_path: Path) -> None:
    run = _holidays(tmp_path, "--years", "abc", stdout=BrokenStdout())

    assert run.code == 4
    assert "INVALID_YEARS" in run.stderr


def test_holidays_rejects_unknown_option_with_usage_error(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["holidays", "--country", "TH"], io.BytesIO(), io.StringIO(), tmp_path, {})

    assert exit_info.value.code == 2


def _subprocess(cwd: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-m", "hotel_booking_analysis", "holidays", *args],
        cwd=cwd,
        capture_output=True,
        check=False,
        timeout=60,
    )


def test_module_run_holidays_writes_valid_khmer_listing_to_stdout(tmp_path: Path) -> None:
    completed = _subprocess(tmp_path, "--years", "2025")

    assert completed.returncode == 0, completed.stderr.decode()
    document = json.loads(completed.stdout)
    VALIDATOR.validate(document)
    expected = {day.isoformat() for day in holidays.country_holidays("KH", years=2025)}
    assert {h["date"] for h in document["years"][0]["holidays"]} == expected
    assert b"\r" not in completed.stdout
    assert not (tmp_path / "output").exists()


def test_module_run_holidays_with_invalid_years_exits_2_with_failed_document(
    tmp_path: Path,
) -> None:
    completed = _subprocess(tmp_path, "--years", "2101")

    assert completed.returncode == 2
    document = json.loads(completed.stdout)
    VALIDATOR.validate(document)
    assert document["error"]["code"] == "INVALID_YEARS"


def test_module_run_holidays_with_unknown_option_exits_2_without_json(tmp_path: Path) -> None:
    completed = _subprocess(tmp_path, "--bogus")

    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr
