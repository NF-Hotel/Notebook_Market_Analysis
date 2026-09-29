"""View model of the data-quality summary of one result (US-001.01, UC-002).

Pure functions from a parsed result to rows and lines; no marimo.
"""

from dataclasses import dataclass

from hotel_booking_analysis.interface.json_access import (
    Result,
    as_int,
    as_list,
    as_mapping,
    as_text,
)

NOT_SUPPLIED = "not supplied"


@dataclass(frozen=True, slots=True)
class FieldQuality:
    field: str
    missing: int
    invalid: int


@dataclass(frozen=True, slots=True)
class UnavailableAnalysis:
    analysis: str
    reason: str


@dataclass(frozen=True, slots=True)
class DataQualityView:
    record_count: int | None
    booking_dates: tuple[str, str]
    arrival_dates: tuple[str, str]
    fields: tuple[FieldQuality, ...]
    duplicate_booking_id_count: int | None
    zero_price_count: int | None
    unknown_fields: tuple[str, ...]
    unavailable_analyses: tuple[UnavailableAnalysis, ...]
    notices: tuple[str, ...]

    def field_table(self) -> list[dict[str, str | int]]:
        return [{"field": f.field, "missing": f.missing, "invalid": f.invalid} for f in self.fields]

    def unavailable_table(self) -> list[dict[str, str]]:
        return [{"analysis": u.analysis, "reason": u.reason} for u in self.unavailable_analyses]

    def summary_lines(self) -> list[str]:
        """Plain statements of the headline figures, in display order."""
        return [
            f"Records: {_count(self.record_count)}",
            f"Booking dates: {_span(self.booking_dates)}",
            f"Arrival dates: {_span(self.arrival_dates)}",
            f"Duplicate booking IDs: {_count(self.duplicate_booking_id_count)}",
            f"Records with a price per night of zero: {_count(self.zero_price_count)}",
            "Unknown fields: " + (", ".join(self.unknown_fields) or "none"),
        ]


def _count(value: int | None) -> str:
    return "unknown" if value is None else str(value)


def _span(dates: tuple[str, str]) -> str:
    first, last = dates
    return f"{first} to {last}"


def _date_span(quality: Result, first: str, last: str) -> tuple[str, str]:
    return (
        as_text(quality.get(first)) or NOT_SUPPLIED,
        as_text(quality.get(last)) or NOT_SUPPLIED,
    )


def _fields(quality: Result) -> tuple[FieldQuality, ...]:
    missing = as_mapping(quality.get("missing_counts"))
    invalid = as_mapping(quality.get("invalid_counts"))
    names = list(missing) + [name for name in invalid if name not in missing]
    return tuple(
        FieldQuality(name, as_int(missing.get(name)) or 0, as_int(invalid.get(name)) or 0)
        for name in names
    )


def _unavailable(result: Result) -> tuple[UnavailableAnalysis, ...]:
    found: list[UnavailableAnalysis] = []
    for name, entry in as_mapping(result.get("analyses")).items():
        analysis = as_mapping(entry)
        if analysis.get("status") == "unavailable":
            reason = as_text(analysis.get("reason")) or "No reason was recorded."
            found.append(UnavailableAnalysis(name, reason))
    return tuple(found)


def _notices(result: Result) -> tuple[str, ...]:
    notices = (as_mapping(item) for item in as_list(result.get("notices")))
    return tuple(
        f"{as_text(n.get('code')) or 'NOTICE'}: {as_text(n.get('message')) or ''}" for n in notices
    )


def build_quality_view(result: Result) -> DataQualityView:
    """Turn the stored data-quality summary and availability into a view (US-001.01)."""
    quality = as_mapping(result.get("data_quality"))
    unknown = tuple(
        item for item in as_list(quality.get("unknown_fields")) if isinstance(item, str)
    )
    return DataQualityView(
        record_count=as_int(quality.get("record_count")),
        booking_dates=_date_span(quality, "earliest_booking_date", "latest_booking_date"),
        arrival_dates=_date_span(quality, "earliest_arrival_date", "latest_arrival_date"),
        fields=_fields(quality),
        duplicate_booking_id_count=as_int(quality.get("duplicate_booking_id_count")),
        zero_price_count=as_int(quality.get("zero_price_count")),
        unknown_fields=unknown,
        unavailable_analyses=_unavailable(result),
        notices=_notices(result),
    )
