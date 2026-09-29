"""View model of the lead-time analysis (US-001.02): distribution splits and date comparison.

Pure functions from a parsed result to rows and lines; no marimo.
"""

from dataclasses import dataclass

from hotel_booking_analysis.domain.analysis import AnalysisName, JsonValue
from hotel_booking_analysis.interface.figures import (
    Row,
    analysis_findings,
    count_text,
    read_figure,
    share_row,
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

OVERALL = "overall"
SPLIT_LABELS: dict[str, str] = {
    OVERALL: "Overall",
    "by_cancellation_status": "Cancellation status",
    "by_arrival_month": "Arrival month",
    "by_market_segment": "Market segment",
    "by_customer_type": "Customer type",
}


@dataclass(frozen=True, slots=True)
class LeadTimeGroup:
    group: str
    records: int | None
    median_days: int | None
    small_sample: bool
    partial_period: bool
    bands: tuple[Row, ...]


@dataclass(frozen=True, slots=True)
class LeadTimeView:
    message: str | None
    splits: dict[str, tuple[LeadTimeGroup, ...]]
    unavailable_splits: dict[str, str]
    date_comparison: str | None
    summary: str | None

    def split_options(self) -> dict[str, str]:
        """Selector options, label to split key, for the splits that have data."""
        return {label: key for key, label in SPLIT_LABELS.items() if key in self.splits}

    def summary_table(self, split: str) -> list[Row]:
        """One row per group of the split with its record count and median."""
        return [
            {
                "group": g.group,
                "records": count_text(g.records),
                "median lead time (days)": count_text(g.median_days),
                "small sample": small_sample_text(g.small_sample),
                "partial period": "partial" if g.partial_period else "",
            }
            for g in self.splits.get(split, ())
        ]

    def band_table(self, split: str) -> list[Row]:
        """Lead-time bands of each group, with the group size as the denominator."""
        return [{"group": g.group, **band} for g in self.splits.get(split, ()) for band in g.bands]

    def statements(self) -> list[str]:
        lines = [text for text in (self.summary, self.date_comparison) if text]
        lines.extend(
            f"{SPLIT_LABELS.get(k, k)}: not available - {r}"
            for k, r in self.unavailable_splits.items()
        )
        return lines


def _group(entry: JsonValue) -> LeadTimeGroup | None:
    item = as_mapping(entry)
    figure = read_figure(item.get("figure"))
    if figure is None:
        return None
    bands: list[Row] = []
    for band in as_list(item.get("bands")):
        band_figure = read_figure(band)
        if band_figure is not None:
            bands.append(share_row("band", band_figure.group, band_figure, "of group"))
    return LeadTimeGroup(
        group=figure.group,
        records=figure.numerator,
        median_days=as_int(item.get("median_days")),
        small_sample=figure.small_sample,
        partial_period=item.get("partial_period") is True,
        bands=tuple(bands),
    )


def _groups(entries: list[JsonValue]) -> tuple[LeadTimeGroup, ...]:
    found = (_group(entry) for entry in entries)
    return tuple(group for group in found if group is not None)


def build_lead_time_view(result: Result) -> LeadTimeView:
    """Turn the stored lead-time findings into a view; tolerant of missing parts."""
    found = analysis_findings(result, AnalysisName.LEAD_TIME)
    findings = found.findings
    splits: dict[str, tuple[LeadTimeGroup, ...]] = {}
    unavailable: dict[str, str] = {}
    overall = _group(findings.get(OVERALL))
    if overall is not None:
        splits[OVERALL] = (overall,)
    for key, entry in as_mapping(findings.get("splits")).items():
        item = as_mapping(entry)
        reason = unavailable_reason(item)
        if reason is not None:
            unavailable[key] = reason
        elif groups := _groups(as_list(item.get("groups"))):
            splits[key] = groups
    comparison = as_mapping(findings.get("date_comparison"))
    reason = unavailable_reason(comparison)
    comparison_text = (
        f"Date comparison not available: {reason}" if reason else as_text(comparison.get("summary"))
    )
    return LeadTimeView(
        message=found.message,
        splits=splits,
        unavailable_splits=unavailable,
        date_comparison=comparison_text,
        summary=as_text(as_mapping(findings.get(OVERALL)).get("summary")),
    )
