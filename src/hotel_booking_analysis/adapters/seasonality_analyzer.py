"""Seasonality and booking-pace analysis with polars (US-001.04, ADR-0007 Seasonality).

Bookings are counted by booking date and arrivals by arrival date, as separate monthly and
ISO-week series. A series runs only when its date field is usable. Each period carries its count,
the cancellation share and the mean price per night where those fields exist, and is marked
partial when the observed dates of its series do not cover it.
"""

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

import polars as pl

from hotel_booking_analysis.adapters.analysis_frames import (
    KEY,
    SIZE,
    Row,
    build_frame,
    cancellation_block,
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
    is_partial_iso_week,
    is_partial_month,
    missing_field_reason,
    unavailable_marker,
)
from hotel_booking_analysis.domain.wording import SEASONALITY_NOTE, SEASONALITY_SERIES_SUMMARY

MONTHS_IN_YEAR = 12


@dataclass(frozen=True, slots=True)
class _Side:
    """One series: the date field it counts by and what the counted events are."""

    field: str
    measure: str


@dataclass(frozen=True, slots=True)
class _Grain:
    """A period length: how a date is labelled and how a label is checked for coverage."""

    name: str
    key: Callable[[str], pl.Expr]
    is_partial: Callable[[str, date, date], bool]


BOOKING_SIDE = _Side("booking_date", "bookings")
ARRIVAL_SIDE = _Side("arrival_date", "arrivals")
MONTHLY = _Grain("monthly", lambda f: pl.col(f).dt.strftime("%Y-%m"), is_partial_month)
WEEKLY = _Grain("iso_week", lambda f: pl.col(f).dt.strftime("%G-W%V"), is_partial_iso_week)


class SeasonalityAnalyzer:
    """Analyzer for `AnalysisName.SEASONALITY`."""

    @property
    def name(self) -> AnalysisName:
        return AnalysisName.SEASONALITY

    def analyze(self, validated: ValidatedBookings, configuration: AppConfiguration) -> Analysis:
        minimum = configuration.min_group_size
        findings: dict[str, JsonValue] = {
            "note": SEASONALITY_NOTE,
            "bookings": _side(validated, BOOKING_SIDE, minimum),
            "arrivals": _side(validated, ARRIVAL_SIDE, minimum),
        }
        return Analysis(self.name, Availability.AVAILABLE, findings=findings)


def _side(validated: ValidatedBookings, side: _Side, minimum: int) -> dict[str, JsonValue]:
    records = validated.records_for(side.field)
    if not records:
        return unavailable_marker(missing_field_reason(side.field))
    has_status = any(r.is_canceled is not None for r in records)
    has_price = any(r.price_per_night is not None for r in records)
    frame = build_frame(records, [side.field], status=has_status, price=has_price)
    first, last = _span(frame, side.field)
    grains = {
        grain.name: _series(frame, side.field, grain, (first, last), minimum, has_status, has_price)
        for grain in (MONTHLY, WEEKLY)
    }
    unavailable: dict[str, JsonValue] = {}
    if not has_status:
        unavailable["cancellation_share"] = unavailable_marker(
            missing_field_reason(side.field, "is_canceled")
        )
    if not has_price:
        unavailable["mean_price_per_night"] = unavailable_marker(
            missing_field_reason(side.field, "price_per_night")
        )
    return {
        "status": "available",
        "measure": side.measure,
        "date_field": side.field,
        "span": {"first": first.isoformat(), "last": last.isoformat()},
        "records_used": frame.height,
        "summary": _summary(side, frame.height, first, last, grains),
        "unavailable_parts": unavailable,
        **grains,
        "incomplete_years": _incomplete_years(grains["monthly"]),
    }


def _span(frame: pl.DataFrame, field: str) -> tuple[date, date]:
    first: date = frame.select(pl.col(field).min()).item()
    last: date = frame.select(pl.col(field).max()).item()
    return first, last


def _series(
    frame: pl.DataFrame,
    field: str,
    grain: _Grain,
    observed: tuple[date, date],
    minimum: int,
    has_status: bool,
    has_price: bool,
) -> dict[str, JsonValue]:
    table = (
        frame.lazy()
        .group_by(grain.key(field).alias(KEY))
        .agg(*measure_aggregates(status=has_status, price=has_price))
        .sort(KEY)
        .collect()
    )
    rows: list[Row] = table.to_dicts()
    periods: list[JsonValue] = []
    for row in rows:
        label = str(row[KEY])
        period: dict[str, JsonValue] = {
            "figure": figure_to_json(count_statistic(label, int(row[SIZE]), frame.height, minimum)),
            "partial_period": grain.is_partial(label, *observed),
        }
        if has_status:
            period["cancellation"] = cancellation_block(row, minimum)
        if has_price:
            period["mean_price_per_night"] = mean_price_block(row, minimum)
        periods.append(period)
    return {"periods": periods}


def _labels(series: JsonValue) -> list[tuple[str, bool]]:
    assert isinstance(series, dict)
    periods = series["periods"]
    assert isinstance(periods, list)
    labels: list[tuple[str, bool]] = []
    for period in periods:
        assert isinstance(period, dict)
        figure, partial = period["figure"], period["partial_period"]
        assert isinstance(figure, dict)
        assert isinstance(partial, bool)
        labels.append((str(figure["group"]), partial))
    return labels


def _incomplete_years(monthly: JsonValue) -> list[JsonValue]:
    """Years with fewer than 12 months present, with the number of months present."""
    months_per_year = Counter(label[:4] for label, _ in _labels(monthly))
    return [
        {"year": int(year), "months_present": months}
        for year, months in sorted(months_per_year.items())
        if months < MONTHS_IN_YEAR
    ]


def _summary(
    side: _Side, count: int, first: date, last: date, grains: dict[str, dict[str, JsonValue]]
) -> str:
    months, weeks = _labels(grains["monthly"]), _labels(grains["iso_week"])
    return SEASONALITY_SERIES_SUMMARY.format(
        count=count,
        measure=side.measure,
        first=first.isoformat(),
        last=last.isoformat(),
        months=len(months),
        weeks=len(weeks),
        partial=sum(1 for _, partial in (*months, *weeks) if partial),
    )
