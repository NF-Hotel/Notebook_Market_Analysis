"""Shared analysis rules: bands, group figures, small samples, coverage, unavailable marker.

Pure rules from ADR-0007 common rules and ADR-0002 group figures; no library is needed here.
"""

import calendar
from dataclasses import dataclass
from datetime import date

from hotel_booking_analysis.domain.analysis import GroupStatistic, JsonValue

UNAVAILABLE_STATUS = "unavailable"


@dataclass(frozen=True, slots=True)
class LeadTimeBand:
    """A lead-time band in days; `upper` is None for the open-ended last band."""

    label: str
    lower: int
    upper: int | None


LEAD_TIME_BANDS: tuple[LeadTimeBand, ...] = (
    LeadTimeBand("0-7", 0, 7),
    LeadTimeBand("8-30", 8, 30),
    LeadTimeBand("31-90", 31, 90),
    LeadTimeBand("91-180", 91, 180),
    LeadTimeBand("181+", 181, None),
)
"""Bands in days (ADR-0007): 0 to 7, 8 to 30, 31 to 90, 91 to 180, 181 and more."""


def lead_time_band(days: int) -> str:
    """Return the label of the band holding a lead time in days.

    Raises `ValueError` for a negative lead time, which the input rules never let through.
    """
    if days < 0:
        raise ValueError("A lead time cannot be negative.")
    for band in LEAD_TIME_BANDS:
        if band.upper is None or days <= band.upper:
            return band.label
    raise AssertionError("The last band is open-ended.")  # pragma: no cover


def is_small_sample(group_size: int, min_group_size: int) -> bool:
    """Tell whether a group has fewer records than `min_group_size` (ADR-0007)."""
    return group_size < min_group_size


def rate_statistic(
    group: str, numerator: int, denominator: int, min_group_size: int
) -> GroupStatistic:
    """Build a rate or mean figure; the group size is its denominator."""
    return GroupStatistic(
        group, numerator, denominator, is_small_sample(denominator, min_group_size)
    )


def count_statistic(group: str, count: int, total: int, min_group_size: int) -> GroupStatistic:
    """Build a distribution figure: `count` records of `total`; the group size is the count."""
    return GroupStatistic(group, count, total, is_small_sample(count, min_group_size))


def figure_to_json(statistic: GroupStatistic) -> dict[str, JsonValue]:
    """Return the ADR-0002 group figure `{group, numerator, denominator, small_sample}`."""
    return {
        "group": statistic.group,
        "numerator": statistic.numerator,
        "denominator": statistic.denominator,
        "small_sample": statistic.small_sample,
    }


def month_bounds(year: int, month: int) -> tuple[date, date]:
    """Return the first and last day of a calendar month."""
    return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])


def is_partial_period(
    period_start: date, period_end: date, first_observed: date, last_observed: date
) -> bool:
    """Tell whether observed dates fail to cover the whole period (ADR-0007 coverage rule)."""
    return first_observed > period_start or last_observed < period_end


def unavailable_marker(reason: str) -> dict[str, JsonValue]:
    """Return the marker for a part of an analysis that could not be computed."""
    return {"status": UNAVAILABLE_STATUS, "reason": reason}


def missing_field_reason(*field_names: str) -> str:
    """Say which fields are missing or invalid in every record."""
    quoted = ", ".join(f"'{name}'" for name in field_names)
    return f"No record holds a valid value in every required field: {quoted}"
