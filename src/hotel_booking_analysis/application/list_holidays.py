"""List-holidays use case (UC-003, ADR-0011, ADR-0008).

Order of a run: configuration (only checked to parse), years, calendar, listing, hand-over.
It never touches the history and never runs an analysis.
"""

from dataclasses import dataclass
from pathlib import Path

from hotel_booking_analysis.application.listing_delivery import deliver_listing
from hotel_booking_analysis.application.listing_outcome import ListingOutcome
from hotel_booking_analysis.application.ports import (
    Clock,
    ConfigurationLoader,
    HolidayCalendar,
    HolidayListingSerializer,
    ResultSink,
)
from hotel_booking_analysis.domain.errors import InputError, Notice
from hotel_booking_analysis.domain.listing import HolidayCalendarListing, HolidayCalendarYear
from hotel_booking_analysis.domain.result import ResultError
from hotel_booking_analysis.domain.year_selection import parse_years


@dataclass(frozen=True, slots=True)
class ListHolidays:
    """Returns the Cambodian holidays of the requested years (UC-003)."""

    configuration_loader: ConfigurationLoader
    calendar: HolidayCalendar
    serializer: HolidayListingSerializer
    sink: ResultSink
    clock: Clock

    def run(self, years: str | None, config_path: Path | None) -> ListingOutcome:
        try:
            self.configuration_loader.load(config_path)
            selected = parse_years(years, self.clock.now().year)
        except InputError as error:
            return self._deliver(self._failure_line(error, ()), error)
        notices: tuple[Notice, ...] = (
            Notice("CALENDAR_SOURCE", f"Holidays from {self.calendar.source()}."),
        )
        if years is None:
            notices += (
                Notice("DEFAULT_YEAR_USED", f"No year was requested; {selected[0]} was used."),
            )
        listing = HolidayCalendarListing(
            self.clock.now(),
            tuple(
                HolidayCalendarYear.from_holidays(year, self.calendar.holidays_in_year(year))
                for year in selected
            ),
            notices,
        )
        return self._deliver(self.serializer.serialize(listing), None)

    def _failure_line(self, error: InputError, notices: tuple[Notice, ...]) -> str:
        return self.serializer.serialize_failure(
            ResultError(error.code, error.message), notices, self.clock.now()
        )

    def _deliver(self, line: str, failure: InputError | None) -> ListingOutcome:
        return deliver_listing(self.sink, line, failure)
