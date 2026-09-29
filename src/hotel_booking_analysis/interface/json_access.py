"""Tolerant access to parsed history results (ADR-0002, ADR-0003).

Stored results may come from another schema version or be incomplete, so every accessor
returns a neutral value instead of raising when a part is absent or has another shape.
"""

from collections.abc import Mapping

from hotel_booking_analysis.domain.analysis import JsonValue

type Result = Mapping[str, JsonValue]


def as_mapping(value: JsonValue | None) -> Mapping[str, JsonValue]:
    return value if isinstance(value, dict) else {}


def as_list(value: JsonValue | None) -> list[JsonValue]:
    return value if isinstance(value, list) else []


def as_int(value: JsonValue | None) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def as_text(value: JsonValue | None) -> str | None:
    return value if isinstance(value, str) else None
