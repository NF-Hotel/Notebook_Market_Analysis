"""View model of the seasonality analysis (US-001.04): counts per month or ISO week.

Bookings (by booking date) and arrivals (by arrival date) are separate series. Pure functions
from a parsed result to rows and lines; no marimo.
"""

from dataclasses import dataclass

from hotel_booking_analysis.domain.analysis import AnalysisName, JsonValue
from hotel_booking_analysis.interface.figures import (
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

SERIES_LABELS: dict[str, str] = {
    "bookings": "By booking date (bookings)",
    "arrivals": "By arrival date (arrivals)",
}
GRANULARITY_LABELS: dict[str, str] = {"monthly": "Monthly", "iso_week": "ISO week"}


@dataclass(frozen=True, slots=True)
class SeasonalitySeries:
    summary: str | None
    span: str
    unavailable: str | None
    periods: dict[str, tuple[Row, ...]]
    incomplete_years: tuple[str, ...]
    unavailable_parts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SeasonalityView:
    message: str | None
    note: str | None
    series: dict[str, SeasonalitySeries]

    def series_options(self) -> dict[str, str]:
        return {label: key for key, label in SERIES_LABELS.items() if key in self.series}

    def granularity_options(self) -> dict[str, str]:
        return {label: key for key, label in GRANULARITY_LABELS.items()}

    def table(self, series: str, granularity: str) -> list[Row]:
        """Rows of one series at one granularity; partial periods are marked."""
        found = self.series.get(series)
        return list(found.periods.get(granularity, ())) if found else []

    def statements(self, series: str) -> list[str]:
        """Summary, span, incomplete years and unavailable parts of the chosen series."""
        found = self.series.get(series)
        if found is None:
            return []
        lines = [found.summary or "", f"Observed dates: {found.span}", *found.incomplete_years]
        lines.extend(found.unavailable_parts)
        if found.unavailable:
            lines.append(f"Not available: {found.unavailable}")
        return [line for line in lines if line]


def _price_text(value: JsonValue | None) -> str:
    item = as_mapping(value)
    price = as_text(item.get("value"))
    if price is None:
        return "n/a"
    return f"{price} (n={count_text(as_int(item.get('count')))})"


def _period_row(entry: JsonValue) -> Row | None:
    item = as_mapping(entry)
    figure = read_figure(item.get("figure"))
    if figure is None:
        return None
    cancellation = read_figure(item.get("cancellation"))
    return {
        "period": figure.group,
        "records": figure.count_text(),
        "of all records": figure.denominator_text(),
        "partial period": "partial" if item.get("partial_period") is True else "",
        "small sample": small_sample_text(figure.small_sample),
        "cancelled": cancellation.ratio_text() if cancellation else "n/a",
        "mean price per night": _price_text(item.get("mean_price_per_night")),
    }


def _periods(series: dict[str, JsonValue], granularity: str) -> tuple[Row, ...]:
    entries = as_list(as_mapping(series.get(granularity)).get("periods"))
    rows = (_period_row(entry) for entry in entries)
    return tuple(row for row in rows if row is not None)


def _incomplete_years(series: dict[str, JsonValue]) -> tuple[str, ...]:
    lines: list[str] = []
    for entry in as_list(series.get("incomplete_years")):
        item = as_mapping(entry)
        lines.append(
            f"Year {count_text(as_int(item.get('year')))} is incomplete: "
            f"{count_text(as_int(item.get('months_present')))} months present."
        )
    return tuple(lines)


def _series(entry: JsonValue) -> SeasonalitySeries:
    item = as_mapping(entry)
    span = as_mapping(item.get("span"))
    parts = as_mapping(item.get("unavailable_parts"))
    return SeasonalitySeries(
        summary=as_text(item.get("summary")),
        span=f"{as_text(span.get('first')) or 'n/a'} to {as_text(span.get('last')) or 'n/a'}",
        unavailable=unavailable_reason(item),
        periods={g: _periods(dict(item), g) for g in GRANULARITY_LABELS},
        incomplete_years=_incomplete_years(dict(item)),
        unavailable_parts=tuple(
            f"{name}: not available - {as_text(reason) or 'no reason was recorded'}"
            for name, reason in parts.items()
        ),
    )


def build_seasonality_view(result: Result) -> SeasonalityView:
    """Turn the stored seasonality findings into a view; tolerant of missing parts."""
    found = analysis_findings(result, AnalysisName.SEASONALITY)
    series = {key: _series(found.findings[key]) for key in SERIES_LABELS if key in found.findings}
    return SeasonalityView(
        message=found.message, note=as_text(found.findings.get("note")), series=series
    )
