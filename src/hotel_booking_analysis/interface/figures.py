"""Shared reading of stored group figures {group, numerator, denominator, small_sample}.

Every analysis view shows a figure with the number of records it rests on (ADR-0007); these
helpers read one tolerantly and format it as table cells. Pure functions, no marimo.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from hotel_booking_analysis.domain.analysis import JsonValue
from hotel_booking_analysis.interface.json_access import as_int, as_mapping, as_text

type Row = dict[str, str | int]

UNKNOWN = "unknown"
SMALL_SAMPLE_MARK = "small sample"


@dataclass(frozen=True, slots=True)
class Figure:
    group: str
    numerator: int | None
    denominator: int | None
    small_sample: bool

    def share(self) -> str:
        if self.numerator is None or not self.denominator:
            return "n/a"
        return f"{self.numerator / self.denominator:.1%}"

    def count_text(self) -> str:
        return count_text(self.numerator)

    def denominator_text(self) -> str:
        return count_text(self.denominator)

    def ratio_text(self) -> str:
        """`numerator of denominator (share)` as one cell."""
        return f"{self.count_text()} of {self.denominator_text()} ({self.share()})"


def count_text(value: int | None) -> str:
    return UNKNOWN if value is None else str(value)


def read_figure(value: JsonValue | None) -> Figure | None:
    """The figure stored in `value`, or None when it does not have the figure shape."""
    if not isinstance(value, dict) or "numerator" not in value:
        return None
    return Figure(
        group=as_text(value.get("group")) or "",
        numerator=as_int(value.get("numerator")),
        denominator=as_int(value.get("denominator")),
        small_sample=value.get("small_sample") is True,
    )


def small_sample_text(is_small: bool) -> str:
    return SMALL_SAMPLE_MARK if is_small else ""


def share_row(label_key: str, label: str, figure: Figure, of_name: str = "of") -> Row:
    """A table row: group label, count, its denominator, share and the small-sample mark."""
    return {
        label_key: label,
        "records": figure.count_text(),
        of_name: figure.denominator_text(),
        "share": figure.share(),
        "small sample": small_sample_text(figure.small_sample),
    }


def figure_rows(label_key: str, groups: list[JsonValue], of_name: str = "of") -> list[Row]:
    """Rows of group entries, bare figures or `{figure: ...}`; other entries are skipped."""
    rows: list[Row] = []
    for entry in groups:
        item = as_mapping(entry)
        figure = read_figure(item.get("figure")) or read_figure(dict(item))
        if figure is not None:
            rows.append(share_row(label_key, figure.group, figure, of_name))
    return rows


def unavailable_reason(entry: Mapping[str, JsonValue]) -> str | None:
    """The stored reason when `entry` is marked unavailable, else None."""
    if entry.get("status") == "unavailable":
        return as_text(entry.get("reason")) or "No reason was recorded."
    return None


@dataclass(frozen=True, slots=True)
class AnalysisFindings:
    """The stored findings of one analysis, or the reason there are none."""

    findings: Mapping[str, JsonValue]
    message: str | None


def analysis_findings(result: Mapping[str, JsonValue], name: str) -> AnalysisFindings:
    """Findings of analysis `name`; `message` says why they are empty when they are."""
    entry = as_mapping(as_mapping(result.get("analyses")).get(name))
    if not entry:
        return AnalysisFindings({}, "This analysis is not part of the selected result.")
    reason = unavailable_reason(entry)
    if reason is not None:
        return AnalysisFindings({}, f"Not available: {reason}")
    findings = as_mapping(entry.get("findings"))
    if not findings:
        return AnalysisFindings({}, "This analysis has no findings in the selected result.")
    return AnalysisFindings(findings, None)
