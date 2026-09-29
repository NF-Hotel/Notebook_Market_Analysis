"""Tests for the Cambodian holiday calendar adapter (ADR-0007, MIL-005 criterion 3)."""

from datetime import date

import pytest

from hotel_booking_analysis.adapters.khmer_holiday_calendar import KhmerHolidayCalendar


@pytest.mark.parametrize("year", [2021, 2022, 2023, 2024, 2025])
def test_holidays_in_year_has_cambodian_holidays_for_the_sample_years(year: int) -> None:
    result = KhmerHolidayCalendar().holidays_in_year(year)

    assert result
    assert all(h.date.year == year for h in result)
    assert [h.date for h in result] == sorted(h.date for h in result)


def test_holidays_in_year_includes_khmer_new_year_and_new_years_day() -> None:
    dates = {h.date for h in KhmerHolidayCalendar().holidays_in_year(2023)}

    assert date(2023, 1, 1) in dates
    assert date(2023, 4, 14) in dates
