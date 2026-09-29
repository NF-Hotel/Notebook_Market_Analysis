"""Room value and stay analysis with polars and exact decimals (US-001.06, ADR-0007 Room value).

Length of stay is weekend nights plus week nights. Estimated value is price per night times
length of stay, reported per cancellation status and never combined into one figure. Every value
is an estimate in the price units of the input and not realized revenue.
"""

from decimal import Decimal

import polars as pl

from hotel_booking_analysis.adapters.analysis_frames import (
    KEY,
    NIGHTS,
    PRICE,
    SIZE,
    STATUS,
    Row,
    band_expression,
    build_frame,
    measure_aggregates,
)
from hotel_booking_analysis.application.build_result import ESTIMATE_NOT_REVENUE
from hotel_booking_analysis.application.configuration import AppConfiguration
from hotel_booking_analysis.application.validate_bookings import ValidatedBookings
from hotel_booking_analysis.domain.analysis import (
    Analysis,
    AnalysisName,
    Availability,
    JsonValue,
)
from hotel_booking_analysis.domain.analysis_rules import (
    STAY_BUCKETS,
    count_statistic,
    decimal_string,
    figure_to_json,
    mean_decimal_string,
    missing_field_reason,
    unavailable_marker,
)
from hotel_booking_analysis.domain.wording import (
    CANCELLATION_STATUS_UNKNOWN,
    ROOM_VALUE_GROUP_SUMMARY,
    ROOM_VALUE_LABEL,
    ROOM_VALUE_STATUS_UNKNOWN_NOTE,
)

PRICE_UNIT = "price units of the input"
VALUE = "estimated_value"
ZERO_PRICE = "zero_price"
CANCELED = "canceled"
NOT_CANCELED = "not_canceled"
UNKNOWN = "cancellation_status_unknown"
STATUS_TEXT = {
    CANCELED: "cancelled",
    NOT_CANCELED: "not cancelled",
    UNKNOWN: CANCELLATION_STATUS_UNKNOWN,
}


class RoomValueAnalyzer:
    """Analyzer for `AnalysisName.ROOM_VALUE`."""

    @property
    def name(self) -> AnalysisName:
        return AnalysisName.ROOM_VALUE

    def analyze(self, validated: ValidatedBookings, configuration: AppConfiguration) -> Analysis:
        minimum = configuration.min_group_size
        records = validated.records_for("stays_in_weekend_nights", "stays_in_week_nights")
        frame = build_frame(records, [], status=True, price=True, nights=True)
        stays = frame.filter(pl.col(NIGHTS) >= 1)
        findings: dict[str, JsonValue] = {
            "estimate": {
                "notice_code": ESTIMATE_NOT_REVENUE,
                "label": ROOM_VALUE_LABEL,
                "unit": PRICE_UNIT,
            },
            "records_used": frame.height,
            "zero_night_records": frame.height - stays.height,
            "length_of_stay": _length_of_stay(stays, minimum),
            "estimated_value": _estimated_value(stays, validated, minimum),
        }
        return Analysis(self.name, Availability.AVAILABLE, findings=findings)


def _length_of_stay(stays: pl.DataFrame, minimum: int) -> dict[str, JsonValue]:
    counts = (
        stays.lazy()
        .group_by(band_expression(NIGHTS, STAY_BUCKETS).alias(KEY))
        .agg(pl.len().alias(SIZE))
        .collect()
    )
    by_label = {str(r[KEY]): int(r[SIZE]) for r in counts.to_dicts()}
    buckets: list[JsonValue] = [
        figure_to_json(
            count_statistic(bucket.label, by_label.get(bucket.label, 0), stays.height, minimum)
        )
        for bucket in STAY_BUCKETS
    ]
    return {
        "unit": "nights",
        "records_used": stays.height,
        "total_nights": int(stays.select(pl.col(NIGHTS).sum()).item() or 0),
        "buckets": buckets,
    }


def _status_key() -> pl.Expr:
    return (
        pl.when(pl.col(STATUS).is_null())
        .then(pl.lit(UNKNOWN))
        .when(pl.col(STATUS))
        .then(pl.lit(CANCELED))
        .otherwise(pl.lit(NOT_CANCELED))
    )


def _estimated_value(
    stays: pl.DataFrame, validated: ValidatedBookings, minimum: int
) -> dict[str, JsonValue]:
    if not validated.records_for("price_per_night"):
        return unavailable_marker(missing_field_reason("price_per_night"))
    priced = stays.filter(pl.col(PRICE).is_not_null()).with_columns(
        (pl.col(PRICE) * pl.col(NIGHTS)).alias(VALUE)
    )
    table = (
        priced.lazy()
        .group_by(_status_key().alias(KEY))
        .agg(
            *measure_aggregates(),
            pl.col(VALUE).sum().alias("total"),
            (pl.col(PRICE) == 0).sum().alias(ZERO_PRICE),
        )
        .collect()
    )
    rank = {CANCELED: 0, NOT_CANCELED: 1, UNKNOWN: 2}
    rows: list[Row] = sorted(table.to_dicts(), key=lambda r: rank[str(r[KEY])])
    result: dict[str, JsonValue] = {
        "status": "available",
        "unit": PRICE_UNIT,
        "label": ROOM_VALUE_LABEL,
        "records_used": priced.height,
        "records_without_price": stays.height - priced.height,
        "zero_price_records": sum(int(r[ZERO_PRICE]) for r in rows),
        "groups": [_group(row, priced.height, minimum) for row in rows],
    }
    if any(str(r[KEY]) == UNKNOWN for r in rows):
        result["note"] = ROOM_VALUE_STATUS_UNKNOWN_NOTE
    return result


def _group(row: Row, total: int, minimum: int) -> JsonValue:
    key, count = str(row[KEY]), int(row[SIZE])
    amount = Decimal(row["total"])
    mean = mean_decimal_string(amount, count)
    return {
        "figure": figure_to_json(count_statistic(key, count, total, minimum)),
        "cancellation_status": STATUS_TEXT[key],
        "count": count,
        "total": decimal_string(amount),
        "mean": mean,
        "zero_price_records": int(row[ZERO_PRICE]),
        "summary": ROOM_VALUE_GROUP_SUMMARY.format(
            count=count, status=STATUS_TEXT[key], total=decimal_string(amount), mean=mean
        ),
    }
