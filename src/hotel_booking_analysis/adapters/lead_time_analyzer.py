"""Lead-time analysis with polars (US-001.02, ADR-0007 Lead time).

The distribution (count and median) is given overall and split by cancellation status, arrival
month, market segment and customer type. Each split needs its own field; a missing field makes
only that split unavailable. The supplied lead time is also compared with the date difference.
"""

from collections.abc import Sequence
from typing import Any

import polars as pl

from hotel_booking_analysis.application.configuration import AppConfiguration
from hotel_booking_analysis.application.validate_bookings import ValidatedBookings
from hotel_booking_analysis.domain.analysis import (
    Analysis,
    AnalysisName,
    Availability,
    JsonValue,
)
from hotel_booking_analysis.domain.analysis_rules import (
    LEAD_TIME_BANDS,
    count_statistic,
    figure_to_json,
    is_partial_period,
    missing_field_reason,
    month_bounds,
    rate_statistic,
    unavailable_marker,
)
from hotel_booking_analysis.domain.booking import BookingRecord
from hotel_booking_analysis.domain.wording import LEAD_TIME_DATE_DIFFERENCE, LEAD_TIME_MEDIAN

type Row = dict[str, Any]  # Any is justified: polars rows are dynamically typed values.

_KEY = "group_key"
_COUNT = "record_count"
_MEDIAN = "median_days"


def _band_column() -> pl.Expr:
    """Assign each lead time to its ADR-0007 band, built from the domain band table."""
    lead = pl.col("lead_time")
    expression = pl.lit("")
    for band in reversed(LEAD_TIME_BANDS):
        condition = lead >= band.lower if band.upper is None else lead <= band.upper
        expression = pl.when(condition).then(pl.lit(band.label)).otherwise(expression)
    return expression.alias("band")


def _number(value: float | None) -> int | float | None:
    """Return a median as an integer when it is whole."""
    if value is None:
        return None
    return int(value) if float(value).is_integer() else value


class LeadTimeAnalyzer:
    """Analyzer for `AnalysisName.LEAD_TIME`."""

    @property
    def name(self) -> AnalysisName:
        return AnalysisName.LEAD_TIME

    def analyze(self, validated: ValidatedBookings, configuration: AppConfiguration) -> Analysis:
        minimum = configuration.min_group_size
        records = validated.records_for("lead_time")
        findings: dict[str, JsonValue] = {
            "unit": "days",
            "bands": [band.label for band in LEAD_TIME_BANDS],
            "records_used": len(records),
            "overall": _entries(_frame(records, None), minimum, None)[0],
            "splits": {
                "by_cancellation_status": _split(validated, "is_canceled", minimum),
                "by_arrival_month": _split(validated, "arrival_date", minimum),
                "by_market_segment": _split(validated, "market_segment", minimum),
                "by_customer_type": _split(validated, "customer_type", minimum),
            },
            "date_comparison": _date_comparison(validated, minimum),
        }
        return Analysis(self.name, Availability.AVAILABLE, findings=findings)


def _split(validated: ValidatedBookings, field: str, minimum: int) -> dict[str, JsonValue]:
    records = validated.records_for("lead_time", field)
    if not records:
        return unavailable_marker(missing_field_reason("lead_time", field))
    groups = _entries(_frame(records, field), minimum, _key_expression(field))
    if field == "arrival_date":
        return {"status": "available", "groups": _mark_partial_months(groups, records)}
    return {"status": "available", "groups": list(groups)}


def _key_expression(field: str) -> pl.Expr:
    if field == "is_canceled":
        return pl.when(pl.col(field)).then(pl.lit("canceled")).otherwise(pl.lit("not_canceled"))
    if field == "arrival_date":
        return pl.col(field).dt.strftime("%Y-%m")
    return pl.col(field)


def _frame(records: Sequence[BookingRecord], field: str | None) -> pl.DataFrame:
    columns: dict[str, list[object]] = {"lead_time": [r.lead_time for r in records]}
    if field is not None:
        columns[field] = [r.value(field) for r in records]
    return pl.DataFrame(columns)


def _entries(frame: pl.DataFrame, minimum: int, key: pl.Expr | None) -> list[dict[str, JsonValue]]:
    """Return one distribution entry per group, or one entry named `all` without a key."""
    total = frame.height
    if key is None:
        grouped = frame.with_columns(pl.lit("all").alias(_KEY))
    else:
        grouped = frame.with_columns(key.alias(_KEY))
    table = (
        grouped.lazy()
        .with_columns(_band_column())
        .group_by(_KEY)
        .agg(
            pl.len().alias(_COUNT),
            pl.col("lead_time").median().alias(_MEDIAN),
            *[(pl.col("band") == band.label).sum().alias(band.label) for band in LEAD_TIME_BANDS],
        )
        .sort(_KEY)
        .collect()
    )
    return [_group_entry(row, total, minimum) for row in table.to_dicts()]


def _group_entry(row: Row, total: int, minimum: int) -> dict[str, JsonValue]:
    label = str(row[_KEY])
    count = int(row[_COUNT])
    median = _number(row[_MEDIAN])
    bands: list[JsonValue] = [
        figure_to_json(count_statistic(band.label, int(row[band.label]), count, minimum))
        for band in LEAD_TIME_BANDS
    ]
    return {
        "figure": figure_to_json(count_statistic(label, count, total, minimum)),
        "median_days": median,
        "bands": bands,
        "summary": LEAD_TIME_MEDIAN.format(median=median, count=count),
    }


def _mark_partial_months(
    groups: list[dict[str, JsonValue]], records: Sequence[BookingRecord]
) -> list[JsonValue]:
    arrivals = [r.arrival_date for r in records if r.arrival_date is not None]
    first, last = min(arrivals), max(arrivals)
    marked: list[JsonValue] = []
    for entry in groups:
        figure = entry["figure"]
        assert isinstance(figure, dict)
        year, month = str(figure["group"]).split("-")
        start, end = month_bounds(int(year), int(month))
        marked.append({**entry, "partial_period": is_partial_period(start, end, first, last)})
    return marked


def _date_comparison(validated: ValidatedBookings, minimum: int) -> dict[str, JsonValue]:
    fields = ("lead_time", "booking_date", "arrival_date")
    records = validated.records_for(*fields)
    if not records:
        return unavailable_marker(missing_field_reason(*fields))
    frame = pl.DataFrame(
        {
            "lead_time": [r.lead_time for r in records],
            "booking_date": [r.booking_date for r in records],
            "arrival_date": [r.arrival_date for r in records],
        },
        schema={"lead_time": pl.Int64, "booking_date": pl.Date, "arrival_date": pl.Date},
    )
    differing = int(
        frame.select(
            (
                (pl.col("arrival_date") - pl.col("booking_date")).dt.total_days()
                != pl.col("lead_time")
            ).sum()
        ).item()
    )
    total = frame.height
    return {
        "status": "available",
        "difference_definition": "arrival date minus booking date, in days",
        "figure": figure_to_json(
            rate_statistic("differs_from_supplied", differing, total, minimum)
        ),
        "summary": LEAD_TIME_DATE_DIFFERENCE.format(differing=differing, total=total),
    }
