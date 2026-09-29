"""Retention policy of the result history (DM-001, ADR-0003, ADR-0004, US-001.09)."""

from dataclasses import dataclass

DEFAULT_RETENTION = 10


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    """How many results the history keeps; at least 1 (ADR-0004)."""

    limit: int = DEFAULT_RETENTION

    def __post_init__(self) -> None:
        if type(self.limit) is not int or self.limit < 1:
            raise ValueError("retention limit must be an integer of at least 1")
