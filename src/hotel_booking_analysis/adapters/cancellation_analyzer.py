"""Cancellation analysis with polars (US-001.05, ADR-0007 Cancellations).

The cancellation rate (cancelled bookings over the group size) is given overall and by lead-time
band, deposit type, market segment, customer type, arrival month, special requests and booking
changes. Each split needs its own field; a missing field makes only that split unavailable. The
figures describe associations; nothing is modeled or predicted.
"""

from dataclasses import dataclass

import polars as pl

from hotel_booking_analysis.adapters.analysis_frames import (
    KEY,
    SIZE,
    STATUS,
    Row,
    band_expression,
    build_frame,
    capped_expression,
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
    BOOKING_CHANGE_CAP,
    LEAD_TIME_BANDS,
    SPECIAL_REQUEST_CAP,
    capped_labels,
    figure_to_json,
    is_partial_month,
    missing_field_reason,
    rate_statistic,
    unavailable_marker,
)
from hotel_booking_analysis.domain.wording import CANCELLATION_NOTE, CANCELLATION_SPLIT_SUMMARY


@dataclass(frozen=True, slots=True)
class _Split:
    """A grouping of bookings: the field it needs, its group key and the order of its groups."""

    name: str
    field: str
    key: pl.Expr
    order: tuple[str, ...] | None = None


def _splits() -> tuple[_Split, ...]:
    return (
        _Split(
            "by_lead_time_band",
            "lead_time",
            band_expression("lead_time", LEAD_TIME_BANDS),
            tuple(band.label for band in LEAD_TIME_BANDS),
        ),
        _Split("by_deposit_type", "deposit_type", pl.col("deposit_type")),
        _Split("by_market_segment", "market_segment", pl.col("market_segment")),
        _Split("by_customer_type", "customer_type", pl.col("customer_type")),
        _Split("by_arrival_month", "arrival_date", pl.col("arrival_date").dt.strftime("%Y-%m")),
        _Split(
            "by_special_requests",
            "total_of_special_requests",
            capped_expression("total_of_special_requests", SPECIAL_REQUEST_CAP),
            capped_labels(SPECIAL_REQUEST_CAP),
        ),
        _Split(
            "by_booking_changes",
            "booking_changes",
            capped_expression("booking_changes", BOOKING_CHANGE_CAP),
            capped_labels(BOOKING_CHANGE_CAP),
        ),
    )


class CancellationAnalyzer:
    """Analyzer for `AnalysisName.CANCELLATIONS`."""

    @property
    def name(self) -> AnalysisName:
        return AnalysisName.CANCELLATIONS

    def analyze(self, validated: ValidatedBookings, configuration: AppConfiguration) -> Analysis:
        minimum = configuration.min_group_size
        records = validated.records_for(STATUS)
        findings: dict[str, JsonValue] = {
            "note": CANCELLATION_NOTE,
            "records_used": len(records),
            "overall": _overall(build_frame(records, [], status=True), minimum),
            "splits": {
                split.name: _split(validated, split, minimum, len(records)) for split in _splits()
            },
        }
        return Analysis(self.name, Availability.AVAILABLE, findings=findings)


def _overall(frame: pl.DataFrame, minimum: int) -> dict[str, JsonValue]:
    canceled = int(frame.select(pl.col(STATUS).sum()).item())
    return figure_to_json(rate_statistic("all", canceled, frame.height, minimum))


def _split(
    validated: ValidatedBookings, split: _Split, minimum: int, total: int
) -> dict[str, JsonValue]:
    records = validated.records_for(STATUS, split.field)
    if not records:
        return unavailable_marker(missing_field_reason(STATUS, split.field))
    frame = build_frame(records, [split.field], status=True)
    table = (
        frame.lazy().group_by(split.key.alias(KEY)).agg(*measure_aggregates(status=True)).collect()
    )
    rows = _ordered(table.to_dicts(), split.order)
    canceled = sum(int(r["canceled"]) for r in rows)
    groups: list[JsonValue] = [_group(row, minimum) for row in rows]
    if split.field == "arrival_date":
        groups = _mark_partial_months(groups, frame)
    return {
        "status": "available",
        "records_used": frame.height,
        "records_left_out": total - frame.height,
        "groups": groups,
        "summary": CANCELLATION_SPLIT_SUMMARY.format(
            split=split.name.removeprefix("by_").replace("_", " "),
            canceled=canceled,
            total=frame.height,
        ),
    }


def _ordered(rows: list[Row], order: tuple[str, ...] | None) -> list[Row]:
    if order is None:
        return sorted(rows, key=lambda row: str(row[KEY]))
    rank = {label: position for position, label in enumerate(order)}
    return sorted(rows, key=lambda row: rank[str(row[KEY])])


def _group(row: Row, minimum: int) -> JsonValue:
    figure = rate_statistic(str(row[KEY]), int(row["canceled"]), int(row[SIZE]), minimum)
    return {"figure": figure_to_json(figure)}


def _mark_partial_months(groups: list[JsonValue], frame: pl.DataFrame) -> list[JsonValue]:
    first = frame.select(pl.col("arrival_date").min()).item()
    last = frame.select(pl.col("arrival_date").max()).item()
    marked: list[JsonValue] = []
    for entry in groups:
        assert isinstance(entry, dict)
        figure = entry["figure"]
        assert isinstance(figure, dict)
        partial = is_partial_month(str(figure["group"]), first, last)
        marked.append({**entry, "partial_period": partial})
    return marked
