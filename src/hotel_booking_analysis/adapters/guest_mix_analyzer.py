"""Guest and booking mix analysis with polars (US-001.07, ADR-0007 Guest and booking mix).

Total guests is adults plus children plus babies. Distributions (count and share with their
denominators) are given for total guests, country, meal, assigned room type, repeat-guest status,
parking spaces and special requests. A group that is not a small sample is compared with length of
stay, cancellation share and mean price; for a small sample the comparison is omitted and said so.
A missing field makes only its own summary unavailable.
"""

from collections.abc import Callable
from dataclasses import dataclass

import polars as pl

from hotel_booking_analysis.adapters.analysis_frames import (
    KEY,
    SIZE,
    Row,
    build_frame,
    cancellation_block,
    mean_nights_block,
    mean_price_block,
    measure_aggregates,
)
from hotel_booking_analysis.application.configuration import AppConfiguration
from hotel_booking_analysis.application.validate_bookings import ValidatedBookings
from hotel_booking_analysis.domain.analysis import (
    Analysis,
    AnalysisName,
    Availability,
    JsonValue,
)
from hotel_booking_analysis.domain.analysis_rules import (
    count_statistic,
    figure_to_json,
    is_small_sample,
    missing_field_reason,
    unavailable_marker,
)
from hotel_booking_analysis.domain.booking import BookingRecord
from hotel_booking_analysis.domain.wording import GUEST_MIX_COMPARISON_OMITTED, GUEST_MIX_NOTE

TOTAL_GUESTS = "total_guests"


def _total_guests(record: BookingRecord) -> int | None:
    parts = (record.adults, record.children, record.babies)
    return None if None in parts else sum(part for part in parts if part is not None)


@dataclass(frozen=True, slots=True)
class _Summary:
    """A distribution: the fields it needs and the column that is counted."""

    name: str
    required: tuple[str, ...]
    column: str
    derived: Callable[[BookingRecord], object] | None = None


SUMMARIES: tuple[_Summary, ...] = (
    _Summary(TOTAL_GUESTS, ("adults", "children", "babies"), TOTAL_GUESTS, _total_guests),
    _Summary("country", ("country",), "country"),
    _Summary("meal", ("meal",), "meal"),
    _Summary("assigned_room_type", ("assigned_room_type",), "assigned_room_type"),
    _Summary("is_repeated_guest", ("is_repeated_guest",), "is_repeated_guest"),
    _Summary(
        "required_car_parking_spaces",
        ("required_car_parking_spaces",),
        "required_car_parking_spaces",
    ),
    _Summary(
        "total_of_special_requests", ("total_of_special_requests",), "total_of_special_requests"
    ),
)


class GuestMixAnalyzer:
    """Analyzer for `AnalysisName.GUEST_MIX`."""

    @property
    def name(self) -> AnalysisName:
        return AnalysisName.GUEST_MIX

    def analyze(self, validated: ValidatedBookings, configuration: AppConfiguration) -> Analysis:
        minimum = configuration.min_group_size
        findings: dict[str, JsonValue] = {
            "note": GUEST_MIX_NOTE,
            "distributions": {s.name: _summary(validated, s, minimum) for s in SUMMARIES},
        }
        return Analysis(self.name, Availability.AVAILABLE, findings=findings)


def _summary(validated: ValidatedBookings, summary: _Summary, minimum: int) -> dict[str, JsonValue]:
    records = validated.records_for(*summary.required)
    if not records:
        return unavailable_marker(missing_field_reason(*summary.required))
    derived = {summary.column: summary.derived} if summary.derived is not None else None
    fields = [] if derived else [summary.column]
    frame = build_frame(records, fields, status=True, price=True, nights=True, derived=derived)
    table = (
        frame.lazy()
        .group_by(pl.col(summary.column).alias(KEY))
        .agg(*measure_aggregates(status=True, price=True, nights=True))
        .sort(KEY)
        .collect()
    )
    return {
        "status": "available",
        "records_used": frame.height,
        "groups": [_group(row, frame.height, minimum) for row in table.to_dicts()],
    }


def _label(value: object) -> str:
    if isinstance(value, bool):
        return "repeated" if value else "not_repeated"
    return str(value)


def _group(row: Row, total: int, minimum: int) -> JsonValue:
    label, count = _label(row[KEY]), int(row[SIZE])
    return {
        "figure": figure_to_json(count_statistic(label, count, total, minimum)),
        "comparison": _comparison(row, label, count, minimum),
    }


def _comparison(row: Row, label: str, count: int, minimum: int) -> dict[str, JsonValue]:
    if is_small_sample(count, minimum):
        return {
            "status": "omitted_small_sample",
            "statement": GUEST_MIX_COMPARISON_OMITTED.format(group=label, count=count),
        }
    return {
        "status": "available",
        "mean_length_of_stay": mean_nights_block(row, minimum),
        "cancellation_share": cancellation_block(row, minimum),
        "mean_price_per_night": mean_price_block(row, minimum),
    }
