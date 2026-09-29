"""View model of the room-value analysis (US-001.06): a labelled estimate, never revenue.

Cancelled and not-cancelled bookings are separate rows; they are never combined. Pure functions
from a parsed result to rows and lines; no marimo.
"""

from dataclasses import dataclass

from hotel_booking_analysis.domain.analysis import AnalysisName, JsonValue
from hotel_booking_analysis.interface.figures import (
    Row,
    analysis_findings,
    count_text,
    figure_rows,
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
from hotel_booking_analysis.interface.limitations import ESTIMATE_LABEL

ESTIMATE_HEADING = "Estimate, not realized revenue"


@dataclass(frozen=True, slots=True)
class RoomValueView:
    message: str | None
    estimate_label: str
    estimate_code: str | None
    unit: str
    value_rows: tuple[Row, ...]
    value_unavailable: str | None
    value_note: str | None
    value_summaries: tuple[str, ...]
    stay_length_rows: tuple[Row, ...]
    total_nights: int | None
    zero_night_records: int | None
    zero_price_records: int | None
    records_without_price: int | None

    def value_table(self) -> list[Row]:
        """Estimated value, one row per cancellation status."""
        return list(self.value_rows)

    def stay_length_table(self) -> list[Row]:
        return list(self.stay_length_rows)

    def count_lines(self) -> list[str]:
        return [
            f"Bookings with zero nights (left out of stay length and value): "
            f"{count_text(self.zero_night_records)}",
            f"Bookings with a price per night of zero (included in the estimate): "
            f"{count_text(self.zero_price_records)}",
            f"Bookings without a price (left out of the estimate): "
            f"{count_text(self.records_without_price)}",
            f"Total nights: {count_text(self.total_nights)}",
        ]

    def statements(self) -> list[str]:
        lines = [self.estimate_label, *self.value_summaries]
        if self.value_note:
            lines.append(self.value_note)
        if self.value_unavailable:
            lines.append(f"Estimated value not available: {self.value_unavailable}")
        return lines


def _value_row(entry_value: JsonValue, unit: str) -> Row | None:
    entry = as_mapping(entry_value)
    figure = read_figure(entry.get("figure"))
    if figure is None:
        return None
    return {
        "cancellation status": as_text(entry.get("cancellation_status")) or figure.group,
        f"estimated value, total ({unit})": as_text(entry.get("total")) or "n/a",
        f"estimated value, mean per booking ({unit})": as_text(entry.get("mean")) or "n/a",
        "bookings": count_text(as_int(entry.get("count"))),
        "of all priced bookings": figure.denominator_text(),
        "zero-price bookings": count_text(as_int(entry.get("zero_price_records"))),
        "small sample": small_sample_text(figure.small_sample),
    }


def build_room_value_view(result: Result) -> RoomValueView:
    """Turn the stored room-value findings into a view; tolerant of missing parts."""
    found = analysis_findings(result, AnalysisName.ROOM_VALUE)
    findings = found.findings
    estimate = as_mapping(findings.get("estimate"))
    unit = as_text(estimate.get("unit")) or "price units of the input"
    value = as_mapping(findings.get("estimated_value"))
    groups = as_list(value.get("groups"))
    rows = (_value_row(group, unit) for group in groups)
    stay = as_mapping(findings.get("length_of_stay"))
    return RoomValueView(
        message=found.message,
        estimate_label=as_text(estimate.get("label")) or ESTIMATE_LABEL,
        estimate_code=as_text(estimate.get("notice_code")),
        unit=unit,
        value_rows=tuple(row for row in rows if row is not None),
        value_unavailable=unavailable_reason(value),
        value_note=as_text(value.get("note")),
        value_summaries=tuple(
            text for g in groups if (text := as_text(as_mapping(g).get("summary")))
        ),
        stay_length_rows=tuple(figure_rows("nights", as_list(stay.get("buckets")), "of stays")),
        total_nights=as_int(stay.get("total_nights")),
        zero_night_records=as_int(findings.get("zero_night_records")),
        zero_price_records=as_int(value.get("zero_price_records")),
        records_without_price=as_int(value.get("records_without_price")),
    )
