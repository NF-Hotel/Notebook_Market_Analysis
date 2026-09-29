"""Shared fixtures of the interface tests: one real result of the development sample."""

import io
import json
from pathlib import Path

import pytest

from hotel_booking_analysis.infrastructure.cli import main
from tests.interface.builders import Result

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_CSV = REPO_ROOT / "data" / "example" / "nf_hotel_bookings.csv"


@pytest.fixture(scope="session")
def development_result(tmp_path_factory: pytest.TempPathFactory) -> Result:
    """The real result of the development CSV: rich enough to exercise every view."""
    if not SAMPLE_CSV.is_file():
        pytest.skip("development CSV is not present")
    folder = tmp_path_factory.mktemp("development")
    config = folder / "hotel_analysis.toml"
    history = folder / "history.jsonl"
    config.write_text(
        f"environment = 'development'\n[history]\npath = '{history.as_posix()}'\n",
        encoding="utf-8",
    )
    stdout = io.BytesIO()
    code = main(["analyze", "--config", str(config)], stdout, io.StringIO(), REPO_ROOT, {})
    assert code == 0
    result: Result = json.loads(stdout.getvalue())
    return result
