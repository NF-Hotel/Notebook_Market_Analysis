"""Tests for the history lock file (ADR-0003 concurrency rule)."""

import os
import time
from pathlib import Path

import pytest

from hotel_booking_analysis.domain.errors import HistoryWriteError
from hotel_booking_analysis.infrastructure.file_lock import FileLock


def test_lock_creates_lock_file_and_removes_it_on_exit(tmp_path: Path) -> None:
    path = tmp_path / "h.jsonl.lock"

    with FileLock(path):
        assert path.exists()

    assert not path.exists()


def test_lock_removes_file_when_block_raises(tmp_path: Path) -> None:
    path = tmp_path / "h.jsonl.lock"

    with pytest.raises(RuntimeError), FileLock(path):
        raise RuntimeError("boom")

    assert not path.exists()


def test_lock_fails_with_history_write_error_when_held_past_the_wait(tmp_path: Path) -> None:
    path = tmp_path / "h.jsonl.lock"
    path.write_bytes(b"")

    started = time.monotonic()
    with pytest.raises(HistoryWriteError, match="held by another run"):
        FileLock(path, wait_seconds=0.2, poll_seconds=0.02).acquire()

    assert time.monotonic() - started >= 0.2
    assert path.exists()


def test_lock_does_not_remove_a_lock_it_never_acquired(tmp_path: Path) -> None:
    path = tmp_path / "h.jsonl.lock"
    path.write_bytes(b"")
    lock = FileLock(path, wait_seconds=0.05, poll_seconds=0.01)

    with pytest.raises(HistoryWriteError):
        lock.acquire()
    lock.release()

    assert path.exists()


def test_lock_replaces_a_stale_lock_file(tmp_path: Path) -> None:
    path = tmp_path / "h.jsonl.lock"
    path.write_bytes(b"")
    old = time.time() - 61
    os.utime(path, (old, old))

    with FileLock(path, wait_seconds=0.2):
        assert path.exists()
        assert path.stat().st_mtime > old + 30


def test_lock_keeps_a_fresh_lock_file_younger_than_sixty_seconds(tmp_path: Path) -> None:
    path = tmp_path / "h.jsonl.lock"
    path.write_bytes(b"")
    recent = time.time() - 30
    os.utime(path, (recent, recent))

    with pytest.raises(HistoryWriteError):
        FileLock(path, wait_seconds=0.1, poll_seconds=0.02).acquire()


def test_lock_fails_with_history_write_error_when_directory_is_missing(tmp_path: Path) -> None:
    with pytest.raises(HistoryWriteError, match="could not be created"):
        FileLock(tmp_path / "missing" / "h.lock").acquire()
