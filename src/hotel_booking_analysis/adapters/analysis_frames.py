"""Polars building blocks shared by the analyzers (ADR-0007).

Records become a small frame; aggregate expressions and JSON blocks give every analysis the same
cancellation share, mean price and mean stay figures.
"""

from collections.abc import Callable, Mapping, Sequence
from decimal import Decimal
from typing import Any

import polars as pl

from hotel_booking_analysis.domain.analysis import JsonValue
from hotel_booking_analysis.domain.analysis_rules import (
    Bucket,
    LeadTimeBand,
    figure_to_json,
    is_small_sample,
    mean_decimal_string,
    rate_statistic,
    unavailable_marker,
)
from hotel_booking_analysis.domain.booking import BookingRecord

type Row = dict[str, Any]  # Any is justified: polars rows are dynamically typed values.

KEY = "group_key"
SIZE = "record_count"
STATUS = "is_canceled"
PRICE = "price"
NIGHTS = "nights"
PRICE_DECIMAL = pl.Decimal(38, 6)


def nights_of(record: BookingRecord) -> int | None:
    """Length of stay: weekend nights plus week nights, or None if either is not valid."""
    weekend, week = record.stays_in_weekend_nights, record.stays_in_week_nights
    return None if weekend is None or week is None else weekend + week


def build_frame(
    records: Sequence[BookingRecord],
    fields: Sequence[str],
    *,
    status: bool = False,
    price: bool = False,
    nights: bool = False,
    derived: Mapping[str, Callable[[BookingRecord], object]] | None = None,
) -> pl.DataFrame:
    """Return one row per record: the named fields plus optional status, price and nights.

    `derived` adds columns computed from each record.
    """
    columns: dict[str, list[Any]] = {name: [r.value(name) for r in records] for name in fields}
    for name, compute in (derived or {}).items():
        columns[name] = [compute(r) for r in records]
    schema: dict[str, Any] = {}
    if status:
        columns[STATUS] = [r.is_canceled for r in records]
        schema[STATUS] = pl.Boolean
    if price:
        prices = [r.price_per_night for r in records]
        columns[PRICE] = prices
        if all(p is None for p in prices):
            schema[PRICE] = PRICE_DECIMAL
    if nights:
        columns[NIGHTS] = [nights_of(r) for r in records]
        schema[NIGHTS] = pl.Int64
    return pl.DataFrame(columns, schema_overrides=schema)


def band_expression(column: str, bands: Sequence[LeadTimeBand | Bucket]) -> pl.Expr:
    """Label each value of a column with its band or bucket; values outside all get ''."""
    value = pl.col(column)
    expression = pl.lit("")
    for band in reversed(bands):
        above = value >= band.lower
        condition = above if band.upper is None else above & (value <= band.upper)
        expression = pl.when(condition).then(pl.lit(band.label)).otherwise(expression)
    return expression


def capped_expression(column: str, cap: int) -> pl.Expr:
    """Label a count column `0`, `1`, ..., with `cap` and more as `cap+`."""
    value = pl.col(column)
    return (
        pl.when(value >= cap).then(pl.lit(f"{cap}+")).otherwise(value.cast(pl.String)).alias(column)
    )


def status_expression() -> pl.Expr:
    """Label a cancellation status column `canceled` or `not_canceled`."""
    return pl.when(pl.col(STATUS)).then(pl.lit("canceled")).otherwise(pl.lit("not_canceled"))


def measure_aggregates(
    *, status: bool = False, price: bool = False, nights: bool = False
) -> list[pl.Expr]:
    """Aggregates for a group: size, plus the sums behind cancellation share, price and stay."""
    aggregates = [pl.len().alias(SIZE)]
    if status:
        aggregates += [
            pl.col(STATUS).is_not_null().sum().alias("known"),
            pl.col(STATUS).sum().alias("canceled"),
        ]
    if price:
        aggregates += [
            pl.col(PRICE).is_not_null().sum().alias("priced"),
            pl.col(PRICE).sum().alias("price_total"),
        ]
    if nights:
        aggregates += [
            pl.col(NIGHTS).is_not_null().sum().alias("nights_known"),
            pl.col(NIGHTS).sum().alias("nights_total"),
        ]
    return aggregates


def cancellation_block(row: Row, minimum: int) -> dict[str, JsonValue]:
    """The cancellation share of a group, or the unavailable marker if no status is known."""
    known = int(row["known"])
    if known == 0:
        return unavailable_marker("No record in the group holds a valid 'is_canceled'.")
    return figure_to_json(
        rate_statistic("cancellation_share", int(row["canceled"]), known, minimum)
    )


def mean_price_block(row: Row, minimum: int) -> dict[str, JsonValue]:
    """The mean price per night of a group, as a decimal string, with its record count."""
    priced = int(row["priced"])
    if priced == 0:
        return unavailable_marker("No record in the group holds a valid 'price_per_night'.")
    return {
        "value": mean_decimal_string(Decimal(row["price_total"]), priced),
        "count": priced,
        "small_sample": is_small_sample(priced, minimum),
    }


def mean_nights_block(row: Row, minimum: int) -> dict[str, JsonValue]:
    """The mean length of stay of a group in nights, as a decimal string, with its count."""
    known = int(row["nights_known"])
    if known == 0:
        return unavailable_marker("No record in the group holds valid night counts.")
    return {
        "value": mean_decimal_string(Decimal(int(row["nights_total"])), known),
        "count": known,
        "small_sample": is_small_sample(known, minimum),
    }
