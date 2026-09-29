"""Exclusive lock file for the history writer (ADR-0003 concurrency rule)."""

import os
import time
from collections.abc import Callable
from pathlib import Path
from types import TracebackType
from typing import Self

from hotel_booking_analysis.domain.errors import HistoryWriteError

LOCK_WAIT_SECONDS = 10.0
STALE_AFTER_SECONDS = 60.0
POLL_SECONDS = 0.05


class FileLock:
    """Holds `<history file>.lock`, created exclusively, for the length of a `with` block.

    Waits up to `wait_seconds`; a lock file older than `stale_after_seconds` is treated as
    abandoned and replaced. Failing to get the lock raises `HistoryWriteError`.
    """

    def __init__(
        self,
        path: Path,
        wait_seconds: float = LOCK_WAIT_SECONDS,
        stale_after_seconds: float = STALE_AFTER_SECONDS,
        poll_seconds: float = POLL_SECONDS,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._path = path
        self._wait_seconds = wait_seconds
        self._stale_after_seconds = stale_after_seconds
        self._poll_seconds = poll_seconds
        self._clock = clock
        self._held = False

    def __enter__(self) -> Self:
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.release()

    def acquire(self) -> None:
        deadline = time.monotonic() + self._wait_seconds
        while True:
            if self._try_create():
                self._held = True
                return
            if self._remove_if_stale():
                continue
            if time.monotonic() >= deadline:
                raise HistoryWriteError(
                    f"The history lock {self._path.name} is held by another run; "
                    f"gave up after {self._wait_seconds:g} seconds."
                )
            time.sleep(self._poll_seconds)

    def release(self) -> None:
        if not self._held:
            return
        self._held = False
        try:
            self._path.unlink()
        except FileNotFoundError:
            pass
        except OSError as error:
            raise HistoryWriteError(
                f"The history lock {self._path.name} could not be released: {error}"
            ) from error

    def _try_create(self) -> bool:
        try:
            descriptor = os.open(self._path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        except OSError as error:
            raise HistoryWriteError(
                f"The history lock {self._path.name} could not be created: {error}"
            ) from error
        os.close(descriptor)
        return True

    def _remove_if_stale(self) -> bool:
        try:
            age = self._clock() - self._path.stat().st_mtime
        except FileNotFoundError:
            return True
        except OSError:
            return False
        if age <= self._stale_after_seconds:
            return False
        try:
            self._path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            return False
        return True
