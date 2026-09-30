"""Helpers shared by the listing-command CLI tests."""

import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


class Run:
    """The outcome of one in-process CLI run; `document` is schema-validated."""

    def __init__(
        self, code: int, stdout: bytes, stderr: str, validator: Draft202012Validator
    ) -> None:
        self.code = code
        self.stdout = stdout
        self.stderr = stderr
        self._validator = validator

    @property
    def document(self) -> dict[str, Any]:
        parsed: dict[str, Any] = json.loads(self.stdout)
        self._validator.validate(parsed)
        return parsed


class BrokenStdout(io.BytesIO):
    def write(self, buffer: Any) -> int:  # noqa: ANN401 - matches io.BytesIO.write signature
        raise OSError("broken pipe")


def run_module(command: str, cwd: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    """Run `python -m hotel_booking_analysis <command> ...` in `cwd`."""
    return subprocess.run(
        [sys.executable, "-m", "hotel_booking_analysis", command, *args],
        cwd=cwd,
        capture_output=True,
        check=False,
        timeout=60,
    )
