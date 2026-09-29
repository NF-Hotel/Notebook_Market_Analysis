"""Tests for the shared analysis rules (ADR-0007 common rules and lead time, ADR-0002)."""

from datetime import date

import pytest

from hotel_booking_analysis.domain.analysis import GroupStatistic
from hotel_booking_analysis.domain.analysis_rules import (
    LEAD_TIME_BANDS,
    count_statistic,
    figure_to_json,
    is_partial_period,
    is_small_sample,
    lead_time_band,
    missing_field_reason,
    month_bounds,
    rate_statistic,
    unavailable_marker,
)


@pytest.mark.parametrize(
    ("days", "band"),
    [
        (0, "0-7"),
        (7, "0-7"),
        (8, "8-30"),
        (30, "8-30"),
        (31, "31-90"),
        (90, "31-90"),
        (91, "91-180"),
        (180, "91-180"),
        (181, "181+"),
        (5000, "181+"),
    ],
)
def test_lead_time_band_uses_adr_0007_edges(days: int, band: str) -> None:
    assert lead_time_band(days) == band


def test_lead_time_band_rejects_negative_days() -> None:
    with pytest.raises(ValueError, match="negative"):
        lead_time_band(-1)


def test_lead_time_bands_are_contiguous_and_end_open() -> None:
    uppers = [band.upper for band in LEAD_TIME_BANDS]
    lowers = [band.lower for band in LEAD_TIME_BANDS]

    assert uppers[-1] is None
    assert lowers[1:] == [upper + 1 for upper in uppers[:-1] if upper is not None]


def test_is_small_sample_flags_only_groups_below_the_minimum() -> None:
    assert is_small_sample(29, 30)
    assert not is_small_sample(30, 30)


def test_rate_statistic_keeps_numerator_and_flags_by_denominator() -> None:
    assert rate_statistic("g", 2, 29, 30) == GroupStatistic("g", 2, 29, True)
    assert rate_statistic("g", 2, 30, 30) == GroupStatistic("g", 2, 30, False)


def test_count_statistic_flags_by_the_count_of_the_group() -> None:
    assert count_statistic("g", 3, 100, 5).small_sample
    assert not count_statistic("g", 5, 100, 5).small_sample


def test_figure_to_json_has_exactly_the_adr_0002_group_figure_keys() -> None:
    figure = figure_to_json(GroupStatistic("g", 1, 4, True))

    assert figure == {"group": "g", "numerator": 1, "denominator": 4, "small_sample": True}


def test_month_bounds_handles_leap_february() -> None:
    assert month_bounds(2024, 2) == (date(2024, 2, 1), date(2024, 2, 29))


@pytest.mark.parametrize(
    ("first", "last", "partial"),
    [
        (date(2021, 3, 1), date(2021, 3, 31), False),
        (date(2021, 2, 20), date(2021, 4, 5), False),
        (date(2021, 3, 8), date(2021, 3, 31), True),
        (date(2021, 3, 1), date(2021, 3, 30), True),
    ],
)
def test_is_partial_period_when_observed_dates_do_not_cover_the_month(
    first: date, last: date, partial: bool
) -> None:
    start, end = month_bounds(2021, 3)

    assert is_partial_period(start, end, first, last) is partial


def test_unavailable_marker_carries_status_and_reason() -> None:
    assert unavailable_marker("why") == {"status": "unavailable", "reason": "why"}


def test_missing_field_reason_names_every_field() -> None:
    reason = missing_field_reason("lead_time", "is_canceled")

    assert "'lead_time'" in reason
    assert "'is_canceled'" in reason
