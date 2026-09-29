"""Retention of the JSONL history (ADR-0003, ADR-0004, US-001.09, UC-001 step 7)."""

import os
import tempfile
from collections.abc import Callable
from pathlib import Path

from hotel_booking_analysis.domain.errors import HistoryRetentionError
from hotel_booking_analysis.infrastructure.jsonl_format import (
    NEWLINE,
    is_blank,
    parse_valid_result,
    split_lines,
)


def enforce_retention(
    path: Path,
    limit: int,
    replace: Callable[[Path, Path], None] = os.replace,
) -> int:
    """Keep the latest `limit` valid results and remove nothing else; return how many went.

    The oldest valid results beyond `limit` are removed. Malformed and blank lines stay in
    place. The file is rewritten to a temporary file in the same directory and then replaced
    atomically. Raises `HistoryRetentionError` on any failure and leaves the file untouched.
    """
    try:
        lines = split_lines(path.read_bytes())
        doomed = _lines_to_remove(lines, limit)
        if not doomed:
            return 0
        kept = [line for index, line in enumerate(lines) if index not in doomed]
        _rewrite(path, kept, replace)
    except OSError as error:
        raise HistoryRetentionError(f"Retention could not rewrite {path.name}: {error}") from error
    return len(doomed)


def _lines_to_remove(lines: list[bytes], limit: int) -> set[int]:
    valid = [
        index
        for index, line in enumerate(lines)
        if not is_blank(line) and parse_valid_result(line) is not None
    ]
    return set(valid[: max(0, len(valid) - limit)])


def _rewrite(path: Path, lines: list[bytes], replace: Callable[[Path, Path], None]) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(b"".join(line + NEWLINE for line in lines))
            handle.flush()
            os.fsync(handle.fileno())
        replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
