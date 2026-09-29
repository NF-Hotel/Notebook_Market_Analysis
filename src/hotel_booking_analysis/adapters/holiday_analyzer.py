"""Cambodian holiday analysis with polars (US-001.03, ADR-0007 Cambodian holidays).

Booking-date behavior and arrival-date behavior are analyzed separately; a side runs only when
its date field is usable. Days are classified by the domain rule `classify_days`; this module
counts bookings or arrivals per day and compares each window group with the baseline on the
same weekdays.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any

import polars as pl

from hotel_booking_analysis.application.configuration import AppConfiguration
from hotel_booking_analysis.application.ports import HolidayCalendar
from hotel_booking_analysis.application.validate_bookings import ValidatedBookings
from hotel_booking_analysis.domain.analysis import (
    Analysis,
    AnalysisName,
    Availability,
    JsonValue,
)
from hotel_booking_analysis.domain.analysis_rules import (
    figure_to_json,
    is_small_sample,
    missing_field_reason,
    rate_statistic,
    unavailable_marker,
)
from hotel_booking_analysis.domain.holiday_days import DayKind, classify_days
from hotel_booking_analysis.domain.wording import (
    HOLIDAY_ASSOCIATION_NOTE,
    HOLIDAY_HIGHER,
    HOLIDAY_LOWER,
    HOLIDAY_SAME,
    HOLIDAY_SMALL_SAMPLE,
    HOLIDAY_SUBJECT_HOLIDAY,
    HOLIDAY_SUBJECT_WINDOW,
)

type Row = dict[str, Any]  # Any is justified: polars rows are dynamically typed values.

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
"""Names for polars weekday numbers 1 (Monday) to 7 (Sunday)."""


@dataclass(frozen=True, slots=True)
class _Tally:
    """Days, events and cancellation counts of one group of days."""

    days: int = 0
    events: int = 0
    known: int = 0
    canceled: int = 0

    def __add__(self, other: "_Tally") -> "_Tally":
        return _Tally(
            self.days + other.days,
            self.events + other.events,
            self.known + other.known,
            self.canceled + other.canceled,
        )


@dataclass(frozen=True, slots=True)
class _Side:
    """One analyzed date field: what the events are and whether cancellation is reported."""

    field: str
    measure: str
    with_cancellation: bool


BOOKING_SIDE = _Side("booking_date", "bookings", with_cancellation=False)
ARRIVAL_SIDE = _Side("arrival_date", "arrivals", with_cancellation=True)


class HolidayAnalyzer:
    """Analyzer for `AnalysisName.HOLIDAYS`; holidays come from a `HolidayCalendar`."""

    def __init__(self, calendar: HolidayCalendar) -> None:
        self._calendar = calendar

    @property
    def name(self) -> AnalysisName:
        return AnalysisName.HOLIDAYS

    def analyze(self, validated: ValidatedBookings, configuration: AppConfiguration) -> Analysis:
        windows = tuple(sorted(set(configuration.holiday_windows_days)))
        sides = {
            side.field: self._side(validated, side, windows, configuration.min_group_size)
            for side in (BOOKING_SIDE, ARRIVAL_SIDE)
        }
        findings: dict[str, JsonValue] = {
            "calendar": "holidays package, country KH",
            "windows_days": list(windows),
            "note": HOLIDAY_ASSOCIATION_NOTE,
            **sides,
        }
        if all(side["status"] == "unavailable" for side in sides.values()):
            return Analysis(
                self.name,
                Availability.UNAVAILABLE,
                "No date field could be analyzed against the holiday calendar.",
                findings,
            )
        return Analysis(self.name, Availability.AVAILABLE, findings=findings)

    def _side(
        self, validated: ValidatedBookings, side: _Side, windows: tuple[int, ...], minimum: int
    ) -> dict[str, JsonValue]:
        records = validated.records_for(side.field)
        if not records:
            return unavailable_marker(missing_field_reason(side.field))
        dates = [d for r in records if (d := getattr(r, side.field)) is not None]
        years = sorted({d.year for d in dates})
        calendar = {year: self._calendar.holidays_in_year(year) for year in years}
        missing_years = [year for year in years if not calendar[year]]
        if len(missing_years) == len(years):
            return unavailable_marker(
                f"The holiday calendar has no data for any year in '{side.field}': "
                + ", ".join(str(year) for year in years)
            )
        holiday_dates = [h.date for year in years for h in calendar[year]]
        with_status = validated.records_for(side.field, "is_canceled")
        status = (
            [(getattr(r, side.field), bool(r.is_canceled)) for r in with_status]
            if side.with_cancellation
            else []
        )
        daily = _daily_table(dates, status, holiday_dates, windows, missing_years)
        left_out = sum(1 for d in dates if d.year in missing_years)
        return {
            "status": "available",
            "measure": side.measure,
            "date_field": side.field,
            "span": {"first": min(dates).isoformat(), "last": max(dates).isoformat()},
            "years_used": [year for year in years if year not in missing_years],
            "years_unavailable": [
                {
                    "year": year,
                    **unavailable_marker(f"The holiday calendar has no data for {year}."),
                }
                for year in missing_years
            ],
            "records_used": len(dates) - left_out,
            "records_left_out_unavailable_years": left_out,
            "days_left_out_unavailable_years": _left_out_days(
                min(dates), max(dates), missing_years
            ),
            "holiday_days": _comparison(daily, side, minimum, DayKind.HOLIDAY, None),
            "windows": [
                _comparison(daily, side, minimum, kind, window)
                for window in windows
                for kind in (DayKind.BEFORE, DayKind.AFTER)
            ],
            "baseline": _block(
                _tally(daily, _selector(DayKind.BASELINE, None)), "baseline", side, minimum
            ),
        }


def _left_out_days(first: date, last: date, missing_years: list[int]) -> int:
    span = pl.date_range(first, last, eager=True)
    return int(span.dt.year().is_in(missing_years).sum())


def _daily_table(
    dates: list[date],
    status: list[tuple[date, bool]],
    holiday_dates: list[date],
    windows: tuple[int, ...],
    missing_years: list[int],
) -> pl.DataFrame:
    """One row per calendar day of the span (days of unavailable years left out)."""
    classes = classify_days(min(dates), max(dates), holiday_dates, windows)
    days = pl.DataFrame(
        {
            "day": [c.day for c in classes],
            "kind": [c.kind.value for c in classes],
            "distance": [c.distance for c in classes],
        },
        schema={"day": pl.Date, "kind": pl.String, "distance": pl.Int64},
    )
    events = (
        pl.DataFrame({"day": dates}, schema={"day": pl.Date})
        .group_by("day")
        .agg(pl.len().alias("events"))
    )
    known = pl.DataFrame(
        {"day": [d for d, _ in status], "canceled": [c for _, c in status]},
        schema={"day": pl.Date, "canceled": pl.Boolean},
    )
    known_counts = known.group_by("day").agg(
        pl.len().alias("known"), pl.col("canceled").sum().alias("canceled")
    )
    return (
        days.filter(~pl.col("day").dt.year().is_in(missing_years))
        .join(events, on="day", how="left")
        .join(known_counts, on="day", how="left")
        .with_columns(
            pl.col("events", "known", "canceled").fill_null(0),
            pl.col("day").dt.weekday().alias("weekday"),
        )
    )


def _selector(kind: DayKind, window: int | None) -> pl.Expr:
    if window is None:
        return pl.col("kind") == kind.value
    return (pl.col("kind") == kind.value) & (pl.col("distance") <= window)


def _tallies_by_weekday(daily: pl.DataFrame, selector: pl.Expr) -> dict[int, _Tally]:
    table = (
        daily.lazy()
        .filter(selector)
        .group_by("weekday")
        .agg(
            pl.len().alias("days"),
            pl.col("events").sum(),
            pl.col("known").sum(),
            pl.col("canceled").sum(),
        )
        .collect()
    )
    rows: list[Row] = table.to_dicts()
    return {
        int(r["weekday"]): _Tally(
            int(r["days"]), int(r["events"]), int(r["known"]), int(r["canceled"])
        )
        for r in rows
    }


def _tally(daily: pl.DataFrame, selector: pl.Expr) -> _Tally:
    return sum(_tallies_by_weekday(daily, selector).values(), _Tally())


def _block(tally: _Tally, group: str, side: _Side, minimum: int) -> dict[str, JsonValue]:
    """Figures of one group of days: events over days, plus cancellation share if reported."""
    block: dict[str, JsonValue] = {
        "figure": figure_to_json(rate_statistic(group, tally.events, tally.days, minimum)),
        "mean_per_day": _mean(tally),
    }
    if side.with_cancellation:
        block["cancellation_share"] = figure_to_json(
            rate_statistic("cancellation_share", tally.canceled, tally.known, minimum)
        )
    return block


def _mean(tally: _Tally) -> float | None:
    return round(tally.events / tally.days, 4) if tally.days else None


def _comparison(
    daily: pl.DataFrame, side: _Side, minimum: int, kind: DayKind, window: int | None
) -> dict[str, JsonValue]:
    """Compare one group of days with the baseline on the same weekdays."""
    group_name = kind.value if window is None else f"{kind.value}_{window}_days"
    group = _tallies_by_weekday(daily, _selector(kind, window))
    baseline = _tallies_by_weekday(daily, _selector(DayKind.BASELINE, None))
    matched = sum((baseline.get(weekday, _Tally()) for weekday in group), _Tally())
    total = sum(group.values(), _Tally())
    by_weekday: list[JsonValue] = [
        {
            "weekday": WEEKDAYS[weekday - 1],
            "group": _block(group[weekday], group_name, side, minimum),
            "baseline": _block(baseline.get(weekday, _Tally()), "baseline", side, minimum),
        }
        for weekday in sorted(group)
    ]
    entry: dict[str, JsonValue] = {
        "day_kind": kind.value,
        "window_days": window,
        "group": _block(total, group_name, side, minimum),
        "baseline_same_weekdays": _block(matched, "baseline_same_weekdays", side, minimum),
        "by_weekday": by_weekday,
        "statement": _statement(total, matched, side, minimum, kind, window),
    }
    return entry


def _statement(
    group: _Tally, baseline: _Tally, side: _Side, minimum: int, kind: DayKind, window: int | None
) -> str:
    subject = (
        HOLIDAY_SUBJECT_HOLIDAY
        if window is None
        else HOLIDAY_SUBJECT_WINDOW.format(window=window, side=kind.value)
    )
    if is_small_sample(group.days, minimum) or is_small_sample(baseline.days, minimum):
        return HOLIDAY_SMALL_SAMPLE.format(subject=subject)
    group_mean, baseline_mean = group.events / group.days, baseline.events / baseline.days
    template = (
        HOLIDAY_HIGHER
        if group_mean > baseline_mean
        else HOLIDAY_LOWER
        if group_mean < baseline_mean
        else HOLIDAY_SAME
    )
    return template.format(
        measure=side.measure,
        subject=subject,
        window_mean=f"{group_mean:.2f}",
        baseline_mean=f"{baseline_mean:.2f}",
    )
