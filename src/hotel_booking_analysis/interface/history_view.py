"""View models of the retained-results list (US-001.10, UC-002).

Pure functions from the history readout to rows and messages; no marimo and no file access.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from hotel_booking_analysis.domain.history import HistoryReadout
from hotel_booking_analysis.interface.json_access import (
    Result,
    as_int,
    as_mapping,
    as_text,
)

SUPPORTED_MAJOR_VERSION = 1
NO_RESULTS_MESSAGE = (
    "There are no saved results yet. Run an analysis first; the history is created by it."
)
UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class HistoryRow:
    """One retained result in the list, newest first."""

    result_id: str
    generated_at: str
    status: str
    source: str
    record_count: int | None
    schema_version: str
    fully_supported: bool

    def label(self, position: int) -> str:
        """Unique text for a picker; `position` is 1 for the newest result."""
        count = "?" if self.record_count is None else str(self.record_count)
        return (
            f"{position}. {self.generated_at} | {self.status} | {self.source} | "
            f"{count} records | {self.result_id}"
        )

    def as_table_row(self) -> dict[str, str | int]:
        return {
            "generated_at": self.generated_at,
            "status": self.status,
            "source": self.source,
            "record_count": UNKNOWN if self.record_count is None else self.record_count,
            "schema_version": self.schema_version,
            "result_id": self.result_id,
        }


@dataclass(frozen=True, slots=True)
class HistoryView:
    """What the list shows: rows, plus an empty message and a malformed-lines message.

    `results` holds the parsed results in the same order as `rows`.
    """

    rows: tuple[HistoryRow, ...]
    empty_message: str | None
    malformed_message: str | None
    results: tuple[Result, ...]

    def labels(self) -> list[str]:
        return [row.label(position) for position, row in enumerate(self.rows, start=1)]


def major_version(schema_version: str) -> int | None:
    """Major part of a `major.minor` version, or None if it cannot be read."""
    head = schema_version.split(".", 1)[0]
    return int(head) if head.isdecimal() else None


def is_fully_supported(result: Result) -> bool:
    version = as_text(result.get("schema_version"))
    return version is not None and major_version(version) == SUPPORTED_MAJOR_VERSION


def version_notice(result: Result) -> str | None:
    """Statement for a result that this viewer cannot fully display, else None."""
    if is_fully_supported(result):
        return None
    version = as_text(result.get("schema_version")) or UNKNOWN
    return (
        f"This result was produced under result schema version {version}, which cannot be "
        f"fully displayed here (this viewer supports major version {SUPPORTED_MAJOR_VERSION}). "
        "Only the parts that can be read are shown."
    )


def malformed_message(count: int) -> str | None:
    if count < 1:
        return None
    if count == 1:
        return "1 history line could not be read and was skipped."
    return f"{count} history lines could not be read and were skipped."


def _generated_key(result: Result, position: int) -> tuple[datetime, int]:
    """Sort key: time first, later file position wins ties, unreadable times sort oldest."""
    text = as_text(result.get("generated_at")) or ""
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return datetime.min.replace(tzinfo=UTC), position
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment, position


def _row(result: Result) -> HistoryRow:
    source = as_text(as_mapping(result.get("input")).get("source"))
    return HistoryRow(
        result_id=as_text(result.get("result_id")) or UNKNOWN,
        generated_at=as_text(result.get("generated_at")) or UNKNOWN,
        status=as_text(result.get("status")) or UNKNOWN,
        source=source or UNKNOWN,
        record_count=as_int(as_mapping(result.get("input")).get("record_count")),
        schema_version=as_text(result.get("schema_version")) or UNKNOWN,
        fully_supported=is_fully_supported(result),
    )


def build_history_view(readout: HistoryReadout) -> HistoryView:
    """List the retained results newest first (UC-002)."""
    order = sorted(
        range(len(readout.results)),
        key=lambda position: _generated_key(readout.results[position], position),
        reverse=True,
    )
    results = tuple(readout.results[position] for position in order)
    return HistoryView(
        rows=tuple(_row(result) for result in results),
        empty_message=None if results else NO_RESULTS_MESSAGE,
        malformed_message=malformed_message(readout.malformed_line_count),
        results=results,
    )
