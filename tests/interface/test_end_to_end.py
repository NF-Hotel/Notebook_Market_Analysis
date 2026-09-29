"""End-to-end acceptance (MIL-006 criteria 5 and 6; UC-001, UC-002, ADR-0005).

A sample JSON file goes through the real caller entry point (`python -m hotel_booking_analysis
analyze`), and the returned JSON, the history line and what the notebook loads are the same result.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from hotel_booking_analysis.interface.history_source import load_history
from hotel_booking_analysis.interface.limitations import ASSOCIATION_STATEMENT
from tests.interface.builders import HISTORY_RELATIVE, booking, export_notebook
from tests.interface.conftest import REPO_ROOT, SAMPLE_CSV

SECTION_TITLES = (
    "Data quality",
    "Lead time",
    "Seasonality",
    "Holidays",
    "Cancellations",
    "Room value",
    "Guest mix",
)


def _analyze(cwd: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-m", "hotel_booking_analysis", "analyze", *args],
        cwd=cwd,
        capture_output=True,
        check=False,
        timeout=120,
    )


def _assert_notebook_shows_everything(html: str, result_id: str, generated_at: str) -> None:
    assert result_id in html
    assert generated_at in html
    for title in SECTION_TITLES:
        assert title in html, title
    assert html.count(ASSOCIATION_STATEMENT) >= len(SECTION_TITLES) - 1
    assert "not realized revenue" in html
    assert "Estimate, not realized revenue" in html


def test_json_file_through_caller_entry_gives_same_result_in_output_history_and_notebook(
    tmp_path: Path,
) -> None:
    source = tmp_path / "bookings.json"
    source.write_text(json.dumps([booking(n) for n in range(1, 29)]), encoding="utf-8")
    config = tmp_path / "hotel_analysis.toml"
    config.write_text("[history]\nretention = 5\n", encoding="utf-8")

    completed = _analyze(tmp_path, "--input", str(source), "--config", str(config))

    assert completed.returncode == 0, completed.stderr.decode()
    returned = json.loads(completed.stdout)
    history_lines = (tmp_path / HISTORY_RELATIVE).read_text(encoding="utf-8").splitlines()
    assert len(history_lines) == 1
    assert json.loads(history_lines[0]) == returned
    assert (tmp_path / HISTORY_RELATIVE).read_bytes() == completed.stdout
    loaded = load_history(tmp_path, {"HOTEL_ANALYSIS_CONFIG": str(config)})
    assert loaded.readout.results == (returned,)
    html = export_notebook(tmp_path, {"HOTEL_ANALYSIS_CONFIG": str(config)})
    _assert_notebook_shows_everything(html, returned["result_id"], returned["generated_at"])
    assert returned["input"]["source"] == "supplied"


def test_history_notebook_lists_the_newest_of_two_runs_first(tmp_path: Path) -> None:
    source = tmp_path / "bookings.json"
    source.write_text(json.dumps([booking(n) for n in range(1, 10)]), encoding="utf-8")
    first = json.loads(_analyze(tmp_path, "--input", str(source)).stdout)
    second = json.loads(_analyze(tmp_path, "--input", str(source)).stdout)

    html = export_notebook(tmp_path)

    assert first["result_id"] != second["result_id"]
    assert html.index(second["result_id"]) < html.index(first["result_id"])


@pytest.mark.skipif(not SAMPLE_CSV.is_file(), reason="development CSV is not present")
def test_development_fallback_result_reaches_history_and_notebook(tmp_path: Path) -> None:
    history = tmp_path / "history.jsonl"
    config = tmp_path / "hotel_analysis.toml"
    config.write_text(
        f"environment = 'development'\n[history]\npath = '{history.as_posix()}'\n",
        encoding="utf-8",
    )

    completed = _analyze(REPO_ROOT, "--config", str(config))

    assert completed.returncode == 0, completed.stderr.decode()
    returned = json.loads(completed.stdout)
    assert returned["input"]["source"] == "development_sample"
    assert history.read_bytes() == completed.stdout
    html = export_notebook(tmp_path, {"HOTEL_ANALYSIS_CONFIG": str(config)})
    _assert_notebook_shows_everything(html, returned["result_id"], returned["generated_at"])


def test_development_fallback_is_refused_in_production_without_input(tmp_path: Path) -> None:
    config = tmp_path / "hotel_analysis.toml"
    config.write_text("environment = 'production'\n", encoding="utf-8")

    completed = _analyze(REPO_ROOT, "--config", str(config))

    assert completed.returncode == 2
    assert json.loads(completed.stdout)["status"] == "failed"
    assert "development" in completed.stdout.decode()
