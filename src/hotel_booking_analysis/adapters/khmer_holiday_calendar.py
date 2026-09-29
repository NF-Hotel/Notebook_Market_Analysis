"""Cambodian public holidays from the `holidays` package (ADR-0007, US-001.03)."""

import holidays

from hotel_booking_analysis.domain.analysis import Holiday

COUNTRY_CODE = "KH"


class KhmerHolidayCalendar:
    """Holiday calendar for Cambodia (`holidays.country_holidays("KH", years=...)`)."""

    def holidays_in_year(self, year: int) -> tuple[Holiday, ...]:
        """Return the holidays of `year` in date order; empty when the package has none."""
        calendar = holidays.country_holidays(COUNTRY_CODE, years=year)
        return tuple(
            Holiday(day, name) for day, name in sorted(calendar.items()) if day.year == year
        )
