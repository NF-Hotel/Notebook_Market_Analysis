"""Retention policy of the result history (DM-001, ADR-0003, ADR-0004, US-001.09)."""

from collections.abc import Mapping
from dataclasses import dataclass

from hotel_booking_analysis.domain.analysis import JsonValue

DEFAULT_RETENTION = 10


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    """How many results the history keeps; at least 1 (ADR-0004)."""

    limit: int = DEFAULT_RETENTION

    def __post_init__(self) -> None:
        if type(self.limit) is not int or self.limit < 1:
            raise ValueError("retention limit must be an integer of at least 1")


REQUIRED_ENVELOPE_FIELDS: tuple[str, ...] = (
    "schema_version",
    "result_id",
    "generated_at",
    "status",
    "input",
    "data_quality",
    "analyses",
    "notices",
)
"""Fields a stored line must carry to count as a valid result (ADR-0003 read rule)."""

STORED_STATUSES: tuple[str, ...] = ("completed", "completed_with_warnings")
"""Only these result statuses are stored; a failed result never is (ADR-0003)."""


@dataclass(frozen=True, slots=True)
class HistoryReadout:
    """Valid results in file order plus the number of skipped malformed lines (ADR-0003).

    Each result is the parsed JSON object of one history line; the last one is the latest.
    """

    results: tuple[Mapping[str, JsonValue], ...]
    malformed_line_count: int
