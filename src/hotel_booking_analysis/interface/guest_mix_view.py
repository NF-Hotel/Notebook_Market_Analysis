"""View model of the guest-mix analysis (US-001.07): distributions and their comparisons.

A comparison is stated only for groups that are not small samples; omitted ones are listed.
Pure functions from a parsed result to rows and lines; no marimo.
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

ATTRIBUTE_LABELS: dict[str, str] = {
    "total_guests": "Total guests",
    "country": "Country",
    "meal": "Meal",
    "assigned_room_type": "Assigned room type",
    "is_repeated_guest": "Repeated guest",
    "required_car_parking_spaces": "Car parking spaces",
    "total_of_special_requests": "Special requests",
}
OMITTED = "omitted: small sample"


@dataclass(frozen=True, slots=True)
class Distribution:
    records_used: int | None
    rows: tuple[Row, ...]
    omitted: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GuestMixView:
    message: str | None
    note: str | None
    distributions: dict[str, Distribution]
    unavailable_attributes: dict[str, str]

    def attribute_options(self) -> dict[str, str]:
        return {label: key for key, label in ATTRIBUTE_LABELS.items() if key in self.distributions}

    def table(self, attribute: str) -> list[Row]:
        found = self.distributions.get(attribute)
        return list(found.rows) if found else []

    def statements(self, attribute: str) -> list[str]:
        found = self.distributions.get(attribute)
        lines: list[str] = []
        if found is not None:
            lines.append(f"Records used for this distribution: {count_text(found.records_used)}")
            lines.extend(found.omitted)
        lines.extend(
            f"{ATTRIBUTE_LABELS.get(k, k)}: not available - {r}"
            for k, r in self.unavailable_attributes.items()
        )
        return lines


def _mean(value: JsonValue | None) -> str:
    item = as_mapping(value)
    text = as_text(item.get("value"))
    if text is None:
        return "n/a"
    return f"{text} (n={count_text(as_int(item.get('count')))})"


def _comparison_cells(comparison: JsonValue | None) -> tuple[Row, str | None]:
    item = as_mapping(comparison)
    if item.get("status") != "available":
        text = as_text(item.get("statement"))
        return {
            "mean length of stay (nights)": OMITTED,
            "cancelled": OMITTED,
            "mean price per night": OMITTED,
        }, text
    cancelled = read_figure(item.get("cancellation_share"))
    return {
        "mean length of stay (nights)": _mean(item.get("mean_length_of_stay")),
        "cancelled": cancelled.ratio_text() if cancelled else "n/a",
        "mean price per night": _mean(item.get("mean_price_per_night")),
    }, None


def _distribution(entry: JsonValue) -> Distribution:
    item = as_mapping(entry)
    rows: list[Row] = []
    omitted: list[str] = []
    for group in as_list(item.get("groups")):
        entry_group = as_mapping(group)
        figure = read_figure(entry_group.get("figure"))
        if figure is None:
            continue
        cells, statement = _comparison_cells(entry_group.get("comparison"))
        if statement:
            omitted.append(statement)
        rows.append(
            {
                "group": figure.group,
                "records": figure.count_text(),
                "of all records": figure.denominator_text(),
                "share": figure.share(),
                "small sample": small_sample_text(figure.small_sample),
                **cells,
            }
        )
    return Distribution(as_int(item.get("records_used")), tuple(rows), tuple(omitted))


def build_guest_mix_view(result: Result) -> GuestMixView:
    """Turn the stored guest-mix findings into a view; tolerant of missing parts."""
    found = analysis_findings(result, AnalysisName.GUEST_MIX)
    distributions: dict[str, Distribution] = {}
    unavailable: dict[str, str] = {}
    for key, entry in as_mapping(found.findings.get("distributions")).items():
        reason = unavailable_reason(as_mapping(entry))
        if reason is not None:
            unavailable[key] = reason
        else:
            distributions[key] = _distribution(entry)
    return GuestMixView(
        message=found.message,
        note=as_text(found.findings.get("note")),
        distributions=distributions,
        unavailable_attributes=unavailable,
    )
