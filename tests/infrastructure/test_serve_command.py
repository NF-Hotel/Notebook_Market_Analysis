"""Tests of the `serve` subcommand: arguments, start-up and one real process (ADR-0013)."""

import io
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest
import uvicorn

from hotel_booking_analysis.infrastructure import http_api
from hotel_booking_analysis.infrastructure.cli import build_parser, main
from hotel_booking_analysis.infrastructure.http_api import ServiceSettings
from tests.infrastructure.service_process import (
    START_SECONDS,
    STOP_SECONDS,
    free_port,
    health,
    stop,
)


def test_serve_defaults_to_loopback_port_8000() -> None:
    arguments = build_parser().parse_args(["serve"])

    assert (arguments.host, arguments.port, arguments.config) == ("127.0.0.1", 8000, None)


def test_serve_reads_host_port_and_config() -> None:
    arguments = build_parser().parse_args(
        ["serve", "--host", "0.0.0.0", "--port", "8080", "--config", "c.toml"]
    )

    assert (arguments.host, arguments.port, arguments.config) == ("0.0.0.0", 8080, Path("c.toml"))


@pytest.mark.parametrize("port", ["0", "65536", "-1", "abc", "8.5", ""])
def test_serve_rejects_a_port_outside_1_to_65535(port: str) -> None:
    with pytest.raises(SystemExit) as stop:
        build_parser().parse_args(["serve", "--port", port])

    assert stop.value.code == 2


def test_main_starts_the_service_with_the_settings_of_the_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    started: list[tuple[str, int, ServiceSettings]] = []

    def fake_serve(host: str, port: int, settings: ServiceSettings) -> int:
        started.append((host, port, settings))
        return 0

    monkeypatch.setattr(http_api, "serve", fake_serve)
    stdout = io.BytesIO()

    code = main(
        ["serve", "--port", "8123", "--config", "c.toml"], stdout, io.StringIO(), tmp_path, {}, 3.0
    )

    assert code == 0
    assert stdout.getvalue() == b""
    assert started == [("127.0.0.1", 8123, ServiceSettings(tmp_path, {}, Path("c.toml"), 3.0))]


@pytest.mark.parametrize(
    ("host", "warned"), [("127.0.0.1", False), ("localhost", False), ("0.0.0.0", True)]
)
def test_serve_warns_when_bound_beyond_loopback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    host: str,
    warned: bool,
) -> None:
    runs: list[dict[str, Any]] = []
    monkeypatch.setattr(uvicorn, "run", lambda app, **kwargs: runs.append(kwargs))

    with caplog.at_level(logging.WARNING, logger="hotel_booking_analysis.http_api"):
        code = http_api.serve(host, 9000, ServiceSettings(tmp_path, {}))

    assert code == 0
    assert runs == [{"host": host, "port": 9000}]
    assert ("no authentication" in caplog.text) is warned


def test_serve_process_answers_health_and_stops_when_asked(tmp_path: Path) -> None:
    port = free_port()
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    process = subprocess.Popen(
        [sys.executable, "-m", "hotel_booking_analysis", "serve", "--port", str(port)],
        cwd=tmp_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=flags,
    )
    try:
        deadline = time.monotonic() + START_SECONDS
        body = None
        while body is None and process.poll() is None and time.monotonic() < deadline:
            body = health(port)
            time.sleep(0.2)
        assert body == b'{"status":"ok"}'
        stop(process)
        _, log = process.communicate(timeout=STOP_SECONDS)
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=STOP_SECONDS)
    # The exit status after a signal is platform specific; the shutdown log shows a clean stop.
    assert b"Application shutdown complete" in log
