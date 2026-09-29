"""JSONL result history with locking (ADR-0003, ADR-0005, US-001.09, UC-001 steps 6 and 7).

The writer and the reader are separate classes because the analysis run writes and the
notebook (UC-002) only reads.
"""

import os
from collections.abc import Callable
from pathlib import Path

from hotel_booking_analysis.domain.analysis import JsonValue
from hotel_booking_analysis.domain.errors import HistoryReadError, HistoryWriteError
from hotel_booking_analysis.domain.history import (
    STORED_STATUSES,
    HistoryReadout,
    RetentionPolicy,
)
from hotel_booking_analysis.infrastructure.file_lock import (
    LOCK_WAIT_SECONDS,
    STALE_AFTER_SECONDS,
    FileLock,
)
from hotel_booking_analysis.infrastructure.jsonl_format import (
    NEWLINE,
    is_blank,
    parse_valid_result,
    split_lines,
)
from hotel_booking_analysis.infrastructure.jsonl_retention import enforce_retention


def lock_path_for(history: Path) -> Path:
    return history.with_name(history.name + ".lock")


class JsonlHistoryReader:
    """Tolerant reader: skips and counts malformed lines and never modifies the file.

    A relative location is resolved against `base_directory` (ADR-0003: relative to the
    working directory).
    """

    def __init__(self, base_directory: Path = Path()) -> None:
        self._base_directory = base_directory

    def read(self, location: Path) -> HistoryReadout:
        location = self._base_directory / location
        try:
            content = location.read_bytes()
        except FileNotFoundError:
            return HistoryReadout((), 0)
        except OSError as error:
            raise HistoryReadError(
                f"The history {location.name} cannot be read: {error}"
            ) from error
        results: list[dict[str, JsonValue]] = []
        malformed = 0
        for line in split_lines(content):
            if is_blank(line):
                continue
            parsed = parse_valid_result(line)
            if parsed is None:
                malformed += 1
            else:
                results.append(parsed)
        return HistoryReadout(tuple(results), malformed)


class JsonlHistoryWriter:
    """Appends one line under the lock, then applies retention (ADR-0003)."""

    def __init__(
        self,
        lock_wait_seconds: float = LOCK_WAIT_SECONDS,
        lock_stale_after_seconds: float = STALE_AFTER_SECONDS,
        replace: Callable[[Path, Path], None] = os.replace,
        base_directory: Path = Path(),
    ) -> None:
        self._lock_wait_seconds = lock_wait_seconds
        self._lock_stale_after_seconds = lock_stale_after_seconds
        self._replace = replace
        self._base_directory = base_directory

    def append(self, location: Path, line: str, retention: RetentionPolicy) -> None:
        location = self._base_directory / location
        payload = self._payload(line)
        try:
            location.parent.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise HistoryWriteError(f"The history directory cannot be created: {error}") from error
        lock = FileLock(
            lock_path_for(location),
            self._lock_wait_seconds,
            self._lock_stale_after_seconds,
        )
        with lock:
            self._append(location, payload)
            enforce_retention(location, retention.limit, self._replace)

    @staticmethod
    def _payload(line: str) -> bytes:
        encoded = line.encode("utf-8")
        parsed = parse_valid_result(encoded)
        if NEWLINE in encoded or parsed is None or parsed["status"] not in STORED_STATUSES:
            raise HistoryWriteError("Only a completed result on a single line is stored.")
        return encoded + NEWLINE

    @staticmethod
    def _append(location: Path, payload: bytes) -> None:
        try:
            if _lacks_final_newline(location):
                payload = NEWLINE + payload
            with location.open("ab") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as error:
            raise HistoryWriteError(
                f"The history {location.name} could not be written: {error}"
            ) from error


def _lacks_final_newline(location: Path) -> bool:
    try:
        with location.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                return False
            handle.seek(-1, os.SEEK_END)
            return handle.read(1) != NEWLINE
    except FileNotFoundError:
        return False
