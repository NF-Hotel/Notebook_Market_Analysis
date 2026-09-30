"""Helpers shared by the HTTP API tests (ADR-0013): bodies, configuration, client and command."""

import io
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from hotel_booking_analysis.infrastructure.cli import main
from hotel_booking_analysis.infrastructure.http_api import ServiceSettings, create_app
from tests.adapters import fake_servers as servers

HISTORY_NAME = "history.jsonl"


def bookings_body(count: int = 2) -> bytes:
    """A JSON array of `count` valid booking records (ADR-0001), as a request body."""
    records: list[dict[str, Any]] = []
    for index in range(count):
        booked = date(2021, 3, 8) + timedelta(days=index)
        records.append(
            {
                "booking_id": str(index + 1),
                "is_canceled": index % 2 == 1,
                "lead_time": 10,
                "booking_date": booked.isoformat(),
                "arrival_date": (booked + timedelta(days=10)).isoformat(),
                "stays_in_weekend_nights": 1,
                "stays_in_week_nights": 2,
                "adults": 2,
                "price_per_night": 27.31,
            }
        )
    return json.dumps(records).encode("utf-8")


def unreachable_llm_table() -> str:
    """An `[llm]` table whose two providers refuse the connection at once."""
    return (
        f'[llm]\nollama_url = "{servers.closed_port_url()}"\n'
        f'lmstudio_url = "{servers.closed_port_url()}"\n'
    )


def write_config(tmp_path: Path, llm_table: str = "", history: str = HISTORY_NAME) -> Path:
    """A configuration file whose history is `history` under `tmp_path`."""
    path = tmp_path / "config.toml"
    location = (tmp_path / history).as_posix()
    path.write_text(f"[history]\npath = '{location}'\n{llm_table}", encoding="utf-8")
    return path


def make_client(tmp_path: Path, config: Path | None = None, **settings: Any) -> TestClient:  # noqa: ANN401 - forwarded to ServiceSettings
    """A test client of the service; its history and configuration live under `tmp_path`."""
    chosen = config if config is not None else write_config(tmp_path, unreachable_llm_table())
    return TestClient(create_app(ServiceSettings(tmp_path, {}, chosen, **settings)))


def run_command(tmp_path: Path, config: Path, *args: str) -> tuple[int, bytes]:
    """Run the command line in process; returns the exit code and what it wrote to stdout."""
    out = io.BytesIO()
    code = main([args[0], "--config", str(config), *args[1:]], out, io.StringIO(), tmp_path, {})
    return code, out.getvalue()


def history_lines(tmp_path: Path) -> list[bytes]:
    path = tmp_path / HISTORY_NAME
    return path.read_bytes().splitlines(keepends=True) if path.exists() else []
