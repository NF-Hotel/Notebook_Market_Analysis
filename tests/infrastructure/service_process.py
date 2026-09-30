"""Run the real service in a subprocess for the tests (ADR-0013): start, wait, stop."""

import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

START_SECONDS = 30.0
STOP_SECONDS = 15.0


@dataclass(frozen=True, slots=True)
class RunningService:
    base_url: str
    config: Path
    history: Path
    log: Path


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def health(port: int) -> bytes | None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as answer:
            return bytes(answer.read())
    except (urllib.error.URLError, OSError):
        return None


def stop(process: subprocess.Popen[bytes]) -> None:
    """Ask the process to stop the way an operator does (Ctrl+Break on Windows, SIGINT else)."""
    if sys.platform == "win32":
        process.send_signal(signal.CTRL_BREAK_EVENT)
    else:
        process.send_signal(signal.SIGINT)


def _wait_until_healthy(process: subprocess.Popen[bytes], port: int) -> None:
    deadline = time.monotonic() + START_SECONDS
    while process.poll() is None and time.monotonic() < deadline:
        if health(port) == b'{"status":"ok"}':
            return
        time.sleep(0.2)
    raise AssertionError("the service did not answer /health in time")


@contextmanager
def running_service(directory: Path, llm_table: str) -> Iterator[RunningService]:
    """`python -m hotel_booking_analysis serve` on a free port with its history under `directory`.

    The service is stopped, or killed after `STOP_SECONDS`, when the block ends.
    """
    port = free_port()
    config = directory / "service.toml"
    history = directory / "history.jsonl"
    config.write_text(f"[history]\npath = '{history.as_posix()}'\n{llm_table}", encoding="utf-8")
    log = directory / "service.log"
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    with log.open("wb") as sink:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "hotel_booking_analysis",
                "serve",
                "--port",
                str(port),
                "--config",
                str(config),
            ],
            cwd=directory,
            stdout=sink,
            stderr=sink,
            creationflags=flags,
        )
        try:
            _wait_until_healthy(process, port)
            yield RunningService(f"http://127.0.0.1:{port}", config, history, log)
        finally:
            if process.poll() is None:
                stop(process)
                try:
                    process.wait(timeout=STOP_SECONDS)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=STOP_SECONDS)
