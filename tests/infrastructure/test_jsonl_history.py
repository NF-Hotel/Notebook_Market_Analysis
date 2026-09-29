"""Tests for the JSONL history writer and reader (ADR-0003, US-001.09, UC-001 step 6)."""

import json
import os
import time
from pathlib import Path

import pytest

from hotel_booking_analysis.domain.errors import HistoryWriteError
from hotel_booking_analysis.domain.history import RetentionPolicy
from hotel_booking_analysis.infrastructure.jsonl_history import (
    JsonlHistoryReader,
    JsonlHistoryWriter,
    lock_path_for,
)
from tests.support import make_line

RETENTION = RetentionPolicy(10)


def _writer() -> JsonlHistoryWriter:
    return JsonlHistoryWriter(lock_wait_seconds=0.2)


def _ids(path: Path) -> list[str]:
    readout = JsonlHistoryReader().read(path)
    return [str(result["result_id"]) for result in readout.results]


def test_append_creates_directory_and_file_on_first_append(tmp_path: Path) -> None:
    path = tmp_path / "output" / "analysis_history.jsonl"

    _writer().append(path, make_line("a"), RETENTION)

    assert path.read_bytes() == make_line("a").encode() + b"\n"


def test_append_adds_one_line_per_result_in_order(tmp_path: Path) -> None:
    path = tmp_path / "h.jsonl"

    for name in ("a", "b", "c"):
        _writer().append(path, make_line(name), RETENTION)

    assert path.read_bytes().count(b"\n") == 3
    assert _ids(path) == ["a", "b", "c"]


def test_append_leaves_no_lock_file_behind(tmp_path: Path) -> None:
    path = tmp_path / "h.jsonl"

    _writer().append(path, make_line("a"), RETENTION)

    assert not lock_path_for(path).exists()


def test_append_isolates_an_interrupted_line_with_a_newline_first(tmp_path: Path) -> None:
    path = tmp_path / "h.jsonl"
    path.write_bytes(make_line("a").encode() + b'\n{"schema_version":"1.0","res')

    _writer().append(path, make_line("b"), RETENTION)

    lines = path.read_bytes().split(b"\n")
    assert lines[1] == b'{"schema_version":"1.0","res'
    assert lines[2] == make_line("b").encode()
    assert lines[3] == b""
    readout = JsonlHistoryReader().read(path)
    assert [r["result_id"] for r in readout.results] == ["a", "b"]
    assert readout.malformed_line_count == 1


def test_append_does_not_add_extra_newline_when_file_ends_with_one(tmp_path: Path) -> None:
    path = tmp_path / "h.jsonl"
    path.write_bytes(make_line("a").encode() + b"\n")

    _writer().append(path, make_line("b"), RETENTION)

    assert b"\n\n" not in path.read_bytes()


@pytest.mark.parametrize("status", ["failed", "unknown"])
def test_append_refuses_results_that_are_not_completed(tmp_path: Path, status: str) -> None:
    path = tmp_path / "h.jsonl"

    with pytest.raises(HistoryWriteError):
        _writer().append(path, make_line("a", status), RETENTION)

    assert not path.exists()


def test_append_refuses_a_line_with_an_embedded_newline(tmp_path: Path) -> None:
    path = tmp_path / "h.jsonl"

    with pytest.raises(HistoryWriteError):
        _writer().append(path, make_line("a") + "\nextra", RETENTION)


def test_append_accepts_completed_with_warnings(tmp_path: Path) -> None:
    path = tmp_path / "h.jsonl"

    _writer().append(path, make_line("a", "completed_with_warnings"), RETENTION)

    assert _ids(path) == ["a"]


def test_append_fails_with_history_write_error_when_lock_is_held(tmp_path: Path) -> None:
    path = tmp_path / "h.jsonl"
    lock_path_for(path).write_bytes(b"")

    with pytest.raises(HistoryWriteError, match="held by another run"):
        _writer().append(path, make_line("a"), RETENTION)

    assert not path.exists()
    assert lock_path_for(path).exists()


def test_append_replaces_a_stale_lock(tmp_path: Path) -> None:
    path = tmp_path / "h.jsonl"
    lock = lock_path_for(path)
    lock.write_bytes(b"")
    old = time.time() - 120
    os.utime(lock, (old, old))

    _writer().append(path, make_line("a"), RETENTION)

    assert _ids(path) == ["a"]
    assert not lock.exists()


def test_append_fails_with_history_write_error_when_path_is_a_directory(tmp_path: Path) -> None:
    path = tmp_path / "h.jsonl"
    path.mkdir()

    with pytest.raises(HistoryWriteError):
        _writer().append(path, make_line("a"), RETENTION)

    assert not lock_path_for(path).exists()


def test_append_fails_with_history_write_error_when_parent_is_a_file(tmp_path: Path) -> None:
    blocker = tmp_path / "output"
    blocker.write_text("not a directory")

    with pytest.raises(HistoryWriteError):
        _writer().append(blocker / "h.jsonl", make_line("a"), RETENTION)


def test_read_returns_empty_readout_when_file_is_missing(tmp_path: Path) -> None:
    readout = JsonlHistoryReader().read(tmp_path / "missing.jsonl")

    assert readout.results == ()
    assert readout.malformed_line_count == 0


def test_read_skips_and_counts_malformed_lines_without_modifying_the_file(
    tmp_path: Path,
) -> None:
    path = tmp_path / "h.jsonl"
    incomplete = json.dumps({"schema_version": "1.0", "result_id": "x"})
    content = b"\n".join(
        [
            make_line("a").encode(),
            b"not json",
            incomplete.encode(),
            b"[1,2]",
            b"\xff\xfe",
            b"",
            make_line("b").encode(),
            b'{"schema_version":"1.0"',
        ]
    )
    path.write_bytes(content)
    before = path.read_bytes()
    mtime = path.stat().st_mtime_ns

    readout = JsonlHistoryReader().read(path)

    assert [r["result_id"] for r in readout.results] == ["a", "b"]
    assert readout.malformed_line_count == 5
    assert path.read_bytes() == before
    assert path.stat().st_mtime_ns == mtime
