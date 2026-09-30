"""The holiday calendar listing of UC-003 (DM-001 Holiday Calendar Listing and Year, ADR-0011).

A listing is an answer to the Calling system; it is never stored and never part of a result.
"""

from dataclasses import dataclass
from datetime import datetime

from hotel_booking_analysis.domain.analysis import Availability, Holiday
from hotel_booking_analysis.domain.errors import Notice

HOLIDAY_COUNTRY = "KH"
NO_CALENDAR_DATA = "NO_CALENDAR_DATA"


@dataclass(frozen=True, slots=True)
class HolidayCalendarYear:
    """One requested year: its holidays, or unavailable with a reason (ADR-0011 `years[]`).

    An unavailable year lists no holiday; nothing is invented for it.
    """

    year: int
    availability: Availability
    holidays: tuple[Holiday, ...] = ()
    reason: str | None = None

    @classmethod
    def from_holidays(cls, year: int, holidays: tuple[Holiday, ...]) -> "HolidayCalendarYear":
        """Available when the calendar supplied at least one holiday, else `NO_CALENDAR_DATA`."""
        if holidays:
            return cls(year, Availability.AVAILABLE, holidays)
        return cls(year, Availability.UNAVAILABLE, (), NO_CALENDAR_DATA)


@dataclass(frozen=True, slots=True)
class HolidayCalendarListing:
    """The Cambodian holidays of the requested years, ascending (ADR-0011)."""

    generated_at: datetime
    years: tuple[HolidayCalendarYear, ...]
    notices: tuple[Notice, ...] = ()
    country: str = HOLIDAY_COUNTRY
