"""Tests for history retention (ADR-0003, ADR-0004, US-001.09, UC-001 step 7)."""

from pathlib import Path

import pytest

from hotel_booking_analysis.domain.errors import HistoryRetentionError
from hotel_booking_analysis.domain.history import RetentionPolicy
from hotel_booking_analysis.infrastructure.jsonl_history import (
    JsonlHistoryReader,
    JsonlHistoryWriter,
)
from hotel_booking_analysis.infrastructure.jsonl_retention import enforce_retention
from tests.support import make_line


def _write(path: Path, *lines: str) -> None:
    path.write_bytes(b"".join(line.encode() + b"\n" for line in lines))


def _ids(path: Path) -> list[str]:
    return [str(r["result_id"]) for r in JsonlHistoryReader().read(path).results]


def test_retention_removes_only_the_oldest_valid_results_beyond_the_limit(
    tmp_path: Path,
) -> None:
    path = tmp_path / "h.jsonl"
    _write(path, *(make_line(name) for name in "abcde"))

    removed = enforce_retention(path, 3)

    assert removed == 2
    assert _ids(path) == ["c", "d", "e"]


def test_retention_changes_nothing_when_within_the_limit(tmp_path: Path) -> None:
    path = tmp_path / "h.jsonl"
    _write(path, make_line("a"), make_line("b"))
    before = path.read_bytes()

    assert enforce_retention(path, 2) == 0

    assert path.read_bytes() == before


def test_retention_keeps_malformed_lines_in_place(tmp_path: Path) -> None:
    path = tmp_path / "h.jsonl"
    _write(path, "garbage-1", make_line("a"), "garbage-2", make_line("b"), make_line("c"), "{")

    enforce_retention(path, 2)

    assert path.read_text().splitlines() == [
        "garbage-1",
        "garbage-2",
        make_line("b"),
        make_line("c"),
        "{",
    ]


def test_retention_does_not_count_malformed_lines_toward_the_limit(tmp_path: Path) -> None:
    path = tmp_path / "h.jsonl"
    _write(path, "bad", "bad", "bad", make_line("a"), make_line("b"))

    assert enforce_retention(path, 2) == 0

    assert _ids(path) == ["a", "b"]


def test_retention_treats_later_in_file_as_latest_not_later_generated_at(
    tmp_path: Path,
) -> None:
    path = tmp_path / "h.jsonl"
    newer_first = make_line("first").replace("2026-09-29T12:00:00.000Z", "2030-01-01T00:00:00.000Z")
    _write(path, newer_first, make_line("second"))

    enforce_retention(path, 1)

    assert _ids(path) == ["second"]


def test_retention_leaves_no_temporary_file_behind(tmp_path: Path) -> None:
    path = tmp_path / "h.jsonl"
    _write(path, make_line("a"), make_line("b"))

    enforce_retention(path, 1)

    assert [p.name for p in tmp_path.iterdir()] == ["h.jsonl"]


def test_retention_failure_leaves_history_untouched_and_cleans_up(tmp_path: Path) -> None:
    path = tmp_path / "h.jsonl"
    _write(path, make_line("a"), make_line("b"))
    before = path.read_bytes()

    def failing_replace(source: Path, target: Path) -> None:
        raise PermissionError("locked by another process")

    with pytest.raises(HistoryRetentionError, match=r"h\.jsonl"):
        enforce_retention(path, 1, failing_replace)

    assert path.read_bytes() == before
    assert [p.name for p in tmp_path.iterdir()] == ["h.jsonl"]


def test_writer_keeps_appended_result_when_retention_fails(tmp_path: Path) -> None:
    path = tmp_path / "h.jsonl"
    _write(path, make_line("a"), make_line("b"))

    def failing_replace(source: Path, target: Path) -> None:
        raise PermissionError("locked")

    writer = JsonlHistoryWriter(lock_wait_seconds=0.2, replace=failing_replace)

    with pytest.raises(HistoryRetentionError):
        writer.append(path, make_line("c"), RetentionPolicy(2))

    assert _ids(path) == ["a", "b", "c"]
    assert not path.with_name("h.jsonl.lock").exists()
