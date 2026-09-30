"""Tests for the holiday calendar year (ADR-0011, UC-003)."""

from datetime import date

from hotel_booking_analysis.domain.analysis import Availability, Holiday
from hotel_booking_analysis.domain.listing import NO_CALENDAR_DATA, HolidayCalendarYear


def test_from_holidays_is_available_when_the_calendar_supplied_holidays() -> None:
    holidays = (Holiday(date(2025, 1, 1), "New Year"),)

    entry = HolidayCalendarYear.from_holidays(2025, holidays)

    assert entry.availability is Availability.AVAILABLE
    assert entry.holidays == holidays
    assert entry.reason is None


def test_from_holidays_is_unavailable_without_holidays_and_invents_none() -> None:
    entry = HolidayCalendarYear.from_holidays(1900, ())

    assert entry.availability is Availability.UNAVAILABLE
    assert entry.holidays == ()
    assert entry.reason == NO_CALENDAR_DATA
