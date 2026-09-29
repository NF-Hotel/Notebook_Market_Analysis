"""View model of the cancellation analysis (US-001.05): shares by split with their counts.

Pure functions from a parsed result to rows and lines; no marimo.
"""

from dataclasses import dataclass

from hotel_booking_analysis.domain.analysis import AnalysisName, JsonValue
from hotel_booking_analysis.interface.figures import (
    Row,
    analysis_findings,
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

SPLIT_LABELS: dict[str, str] = {
    "by_lead_time_band": "Lead time band",
    "by_deposit_type": "Deposit type",
    "by_market_segment": "Market segment",
    "by_customer_type": "Customer type",
    "by_arrival_month": "Arrival month",
    "by_special_requests": "Special requests",
    "by_booking_changes": "Booking changes",
}


@dataclass(frozen=True, slots=True)
class CancellationSplit:
    summary: str | None
    records_used: int | None
    records_left_out: int | None
    rows: tuple[Row, ...]


@dataclass(frozen=True, slots=True)
class CancellationView:
    message: str | None
    note: str | None
    overall: Row | None
    splits: dict[str, CancellationSplit]
    unavailable_splits: dict[str, str]

    def split_options(self) -> dict[str, str]:
        return {label: key for key, label in SPLIT_LABELS.items() if key in self.splits}

    def table(self, split: str) -> list[Row]:
        """Overall row first, then one row per group with numerator and denominator."""
        found = self.splits.get(split)
        rows = list(found.rows) if found else []
        return ([self.overall] if self.overall else []) + rows

    def statements(self, split: str) -> list[str]:
        found = self.splits.get(split)
        lines: list[str] = []
        if found is not None:
            lines.append(found.summary or "")
            if found.records_left_out:
                lines.append(
                    f"{found.records_left_out} records were left out of this split because the "
                    "attribute is missing or invalid."
                )
        lines.extend(
            f"{SPLIT_LABELS.get(k, k)}: not available - {r}"
            for k, r in self.unavailable_splits.items()
        )
        return [line for line in lines if line]


def _row(entry: JsonValue) -> Row | None:
    item = as_mapping(entry)
    figure = read_figure(item.get("figure"))
    if figure is None:
        return None
    return {
        "group": figure.group,
        "cancelled": figure.count_text(),
        "bookings in group": figure.denominator_text(),
        "cancellation share": figure.share(),
        "small sample": small_sample_text(figure.small_sample),
        "partial period": "partial" if item.get("partial_period") is True else "",
    }


def _split(entry: JsonValue) -> CancellationSplit:
    item = as_mapping(entry)
    rows = (_row(group) for group in as_list(item.get("groups")))
    return CancellationSplit(
        summary=as_text(item.get("summary")),
        records_used=as_int(item.get("records_used")),
        records_left_out=as_int(item.get("records_left_out")),
        rows=tuple(row for row in rows if row is not None),
    )


def _overall(value: JsonValue | None) -> Row | None:
    figure = read_figure(value)
    if figure is None:
        return None
    return {
        "group": "All bookings",
        "cancelled": figure.count_text(),
        "bookings in group": figure.denominator_text(),
        "cancellation share": figure.share(),
        "small sample": small_sample_text(figure.small_sample),
        "partial period": "",
    }


def build_cancellation_view(result: Result) -> CancellationView:
    """Turn the stored cancellation findings into a view; tolerant of missing parts."""
    found = analysis_findings(result, AnalysisName.CANCELLATIONS)
    splits: dict[str, CancellationSplit] = {}
    unavailable: dict[str, str] = {}
    for key, entry in as_mapping(found.findings.get("splits")).items():
        reason = unavailable_reason(as_mapping(entry))
        if reason is not None:
            unavailable[key] = reason
        else:
            splits[key] = _split(entry)
    return CancellationView(
        message=found.message,
        note=as_text(found.findings.get("note")),
        overall=_overall(found.findings.get("overall")),
        splits=splits,
        unavailable_splits=unavailable,
    )
