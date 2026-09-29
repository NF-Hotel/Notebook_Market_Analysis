"""View model of the holiday analysis (US-001.03): windows against a same-weekday baseline.

Booking-date and arrival-date behaviour are separate sections. Pure functions from a parsed
result to rows and lines; no marimo.
"""

from dataclasses import dataclass

from hotel_booking_analysis.domain.analysis import AnalysisName, JsonValue
from hotel_booking_analysis.interface.figures import (
    Figure,
    Row,
    analysis_findings,
    count_text,
    read_figure,
    small_sample_text,
    unavailable_reason,
)
from hotel_booking_analysis.interface.json_access import (
    Result,
    as_int,
    as_list,
    as_mapping,
    as_text,
)

SECTION_LABELS: dict[str, str] = {
    "booking_date": "Booking-date behaviour (bookings per day)",
    "arrival_date": "Arrival-date behaviour (arrivals per day)",
}
HOLIDAY = "holiday"


@dataclass(frozen=True, slots=True)
class Side:
    """A group of days (holidays, or a window) or its baseline."""

    figure: Figure | None
    mean_per_day: str
    cancellation: Figure | None

    def days(self) -> str:
        return self.figure.denominator_text() if self.figure else "n/a"

    def records(self) -> str:
        return self.figure.count_text() if self.figure else "n/a"

    def small(self) -> str:
        return small_sample_text(self.figure.small_sample) if self.figure else ""


@dataclass(frozen=True, slots=True)
class Comparison:
    day_kind: str
    window_days: int | None
    group: Side
    baseline: Side
    by_weekday: tuple[tuple[str, Side, Side], ...]
    statement: str | None

    def label(self) -> str:
        if self.window_days is None:
            return "On holidays"
        return f"{self.window_days}-day window {self.day_kind} holidays"


@dataclass(frozen=True, slots=True)
class HolidaySection:
    title: str
    unavailable: str | None
    measure: str
    span: str
    years_used: tuple[int, ...]
    years_unavailable: tuple[int, ...]
    records_used: int | None
    records_left_out: int | None
    days_left_out: int | None
    holiday: Comparison | None
    windows: tuple[Comparison, ...]

    def comparisons(self, window: int | None) -> list[Comparison]:
        """Holidays plus the before and after windows of the chosen size."""
        chosen = [c for c in self.windows if window is not None and c.window_days == window]
        return ([self.holiday] if self.holiday else []) + chosen

    def comparison_table(self, window: int | None) -> list[Row]:
        return [_comparison_row(c) for c in self.comparisons(window)]

    def weekday_table(self, window: int | None) -> list[Row]:
        return [
            _weekday_row(c, weekday, group, baseline)
            for c in self.comparisons(window)
            for weekday, group, baseline in c.by_weekday
        ]

    def statements(self, window: int | None) -> list[str]:
        lines = [c.statement or "" for c in self.comparisons(window)]
        if self.unavailable:
            lines.append(f"Not available: {self.unavailable}")
        return [line for line in lines if line]

    def coverage_lines(self) -> list[str]:
        """Years used and unavailable, and what was left out for them."""
        return [
            f"Observed dates: {self.span}",
            "Years with holidays used: " + (_years(self.years_used) or "none"),
            "Years without holiday data: " + (_years(self.years_unavailable) or "none"),
            f"Records used: {count_text(self.records_used)}; records left out for years without "
            f"holiday data: {count_text(self.records_left_out)} "
            f"({count_text(self.days_left_out)} days).",
        ]


@dataclass(frozen=True, slots=True)
class HolidayView:
    message: str | None
    note: str | None
    calendar: str | None
    windows_days: tuple[int, ...]
    sections: dict[str, HolidaySection]

    def window_options(self) -> dict[str, int]:
        """Selector options, label to window size in days."""
        return {f"{days} day" + ("" if days == 1 else "s"): days for days in self.windows_days}


def _years(years: tuple[int, ...]) -> str:
    return ", ".join(str(year) for year in years)


def _side(value: JsonValue | None) -> Side:
    item = as_mapping(value)
    mean = item.get("mean_per_day")
    return Side(
        figure=read_figure(item.get("figure")),
        mean_per_day="n/a" if mean is None else f"{mean}",
        cancellation=read_figure(item.get("cancellation_share")),
    )


def _comparison_row(c: Comparison) -> Row:
    row: Row = {
        "comparison": c.label(),
        "days": c.group.days(),
        "records": c.group.records(),
        "mean per day": c.group.mean_per_day,
        "small sample": c.group.small(),
        "baseline days (same weekdays)": c.baseline.days(),
        "baseline records": c.baseline.records(),
        "baseline mean per day": c.baseline.mean_per_day,
        "baseline small sample": c.baseline.small(),
    }
    if c.group.cancellation is not None:
        row["cancelled share"] = c.group.cancellation.ratio_text()
    if c.baseline.cancellation is not None:
        row["baseline cancelled share"] = c.baseline.cancellation.ratio_text()
    return row


def _weekday_row(c: Comparison, weekday: str, group: Side, baseline: Side) -> Row:
    return {
        "comparison": c.label(),
        "weekday": weekday,
        "days": group.days(),
        "records": group.records(),
        "mean per day": group.mean_per_day,
        "small sample": group.small(),
        "baseline days": baseline.days(),
        "baseline mean per day": baseline.mean_per_day,
        "baseline small sample": baseline.small(),
    }


def _comparison(value: JsonValue | None) -> Comparison | None:
    item = as_mapping(value)
    if not item:
        return None
    weekdays: list[tuple[str, Side, Side]] = []
    for entry in as_list(item.get("by_weekday")):
        day = as_mapping(entry)
        name = as_text(day.get("weekday")) or "?"
        weekdays.append((name, _side(day.get("group")), _side(day.get("baseline"))))
    return Comparison(
        day_kind=as_text(item.get("day_kind")) or HOLIDAY,
        window_days=as_int(item.get("window_days")),
        group=_side(item.get("group")),
        baseline=_side(item.get("baseline_same_weekdays")),
        by_weekday=tuple(weekdays),
        statement=as_text(item.get("statement")),
    )


def _years_list(value: JsonValue | None) -> tuple[int, ...]:
    return tuple(year for year in map(as_int, as_list(value)) if year is not None)


def _section(key: str, entry: JsonValue) -> HolidaySection:
    item = as_mapping(entry)
    span = as_mapping(item.get("span"))
    windows = (_comparison(w) for w in as_list(item.get("windows")))
    return HolidaySection(
        title=SECTION_LABELS[key],
        unavailable=unavailable_reason(item),
        measure=as_text(item.get("measure")) or "records",
        span=f"{as_text(span.get('first')) or 'n/a'} to {as_text(span.get('last')) or 'n/a'}",
        years_used=_years_list(item.get("years_used")),
        years_unavailable=_years_list(item.get("years_unavailable")),
        records_used=as_int(item.get("records_used")),
        records_left_out=as_int(item.get("records_left_out_unavailable_years")),
        days_left_out=as_int(item.get("days_left_out_unavailable_years")),
        holiday=_comparison(item.get("holiday_days")),
        windows=tuple(w for w in windows if w is not None and w.window_days is not None),
    )


def build_holiday_view(result: Result) -> HolidayView:
    """Turn the stored holiday findings into a view; tolerant of missing parts."""
    found = analysis_findings(result, AnalysisName.HOLIDAYS)
    findings = found.findings
    return HolidayView(
        message=found.message,
        note=as_text(findings.get("note")),
        calendar=as_text(findings.get("calendar")),
        windows_days=_years_list(findings.get("windows_days")),
        sections={key: _section(key, findings[key]) for key in SECTION_LABELS if key in findings},
    )
