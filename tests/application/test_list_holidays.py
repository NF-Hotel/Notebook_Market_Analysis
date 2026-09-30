"""Tests for the list-holidays use case with fakes of its ports (UC-003, ADR-0011, ADR-0008)."""

from datetime import UTC, date, datetime
from pathlib import Path

from hotel_booking_analysis.application.analyze_bookings import RunStatus
from hotel_booking_analysis.application.configuration import AppConfiguration, LoadedConfiguration
from hotel_booking_analysis.application.list_holidays import ListHolidays
from hotel_booking_analysis.domain.analysis import Availability, Holiday
from hotel_booking_analysis.domain.errors import ConfigurationError, Notice
from hotel_booking_analysis.domain.listing import NO_CALENDAR_DATA, HolidayCalendarListing
from hotel_booking_analysis.domain.result import ResultError
from tests.support import FakeConfigurationLoader, FixedClock, RecordingSink

SOURCE = "fake calendar 1.2.3"
MOMENT = datetime(2026, 9, 30, 8, 0, tzinfo=UTC)


class FakeCalendar:
    """Holidays by year; a year that is not listed has no data. Records the years asked for."""

    def __init__(self, holidays: dict[int, tuple[Holiday, ...]]) -> None:
        self.holidays = holidays
        self.requested: list[int] = []

    def holidays_in_year(self, year: int) -> tuple[Holiday, ...]:
        self.requested.append(year)
        return self.holidays.get(year, ())

    def source(self) -> str:
        return SOURCE


class FakeListingSerializer:
    """Keeps what it was given and returns a marker line."""

    def __init__(self) -> None:
        self.listings: list[HolidayCalendarListing] = []
        self.failures: list[tuple[ResultError, tuple[Notice, ...], datetime]] = []

    def serialize(self, listing: HolidayCalendarListing) -> str:
        self.listings.append(listing)
        return "listing"

    def serialize_failure(
        self, error: ResultError, notices: tuple[Notice, ...], generated_at: datetime
    ) -> str:
        self.failures.append((error, notices, generated_at))
        return "failure"


class RecordingLoader(FakeConfigurationLoader):
    """Records how the configuration was loaded."""

    def __init__(self, loaded: LoadedConfiguration | ConfigurationError) -> None:
        super().__init__(loaded)
        self.calls: list[tuple[Path | None, bool]] = []

    def load(self, explicit_path: Path | None, with_llm: bool = False) -> LoadedConfiguration:
        self.calls.append((explicit_path, with_llm))
        return super().load(explicit_path, with_llm)


class Rig:
    """A use case wired to fakes."""

    def __init__(
        self,
        loaded: LoadedConfiguration | ConfigurationError | None = None,
        fail_delivery: bool = False,
    ) -> None:
        self.events: list[str] = []
        self.calendar = FakeCalendar(
            {2025: (Holiday(date(2025, 1, 1), "New Year"), Holiday(date(2025, 4, 14), "Khmer"))}
        )
        self.loader = RecordingLoader(loaded or LoadedConfiguration(AppConfiguration()))
        self.serializer = FakeListingSerializer()
        self.sink = RecordingSink(self.events, fail=fail_delivery)
        self.use_case = ListHolidays(
            self.loader, self.calendar, self.serializer, self.sink, FixedClock(MOMENT)
        )


def test_run_lists_available_year_with_holidays_in_calendar_order() -> None:
    rig = Rig()

    outcome = rig.use_case.run("2025", None)

    assert outcome.status is RunStatus.SUCCEEDED
    assert outcome.serialized == "listing"
    assert rig.sink.lines == ["listing"]
    (listing,) = rig.serializer.listings
    (entry,) = listing.years
    assert entry.year == 2025
    assert entry.availability is Availability.AVAILABLE
    assert [h.name for h in entry.holidays] == ["New Year", "Khmer"]
    assert listing.country == "KH"
    assert listing.generated_at == MOMENT


def test_run_marks_year_without_calendar_data_unavailable_and_invents_nothing() -> None:
    rig = Rig()

    outcome = rig.use_case.run("2025,1900", None)

    assert outcome.status is RunStatus.SUCCEEDED
    unavailable, available = rig.serializer.listings[0].years
    assert unavailable.year == 1900
    assert unavailable.availability is Availability.UNAVAILABLE
    assert unavailable.holidays == ()
    assert unavailable.reason == NO_CALENDAR_DATA
    assert available.year == 2025
    assert available.availability is Availability.AVAILABLE


def test_run_lists_years_ascending_without_duplicates() -> None:
    rig = Rig()

    rig.use_case.run("2026,2024,2025,2025", None)

    assert [entry.year for entry in rig.serializer.listings[0].years] == [2024, 2025, 2026]
    assert rig.calendar.requested == [2024, 2025, 2026]


def test_run_carries_only_calendar_source_notice_when_years_are_given() -> None:
    rig = Rig()

    rig.use_case.run("2025", None)

    (notice,) = rig.serializer.listings[0].notices
    assert notice.code == "CALENDAR_SOURCE"
    assert SOURCE in notice.message


def test_run_uses_current_year_from_clock_with_default_year_notice() -> None:
    rig = Rig()

    outcome = rig.use_case.run(None, None)

    assert outcome.status is RunStatus.SUCCEEDED
    listing = rig.serializer.listings[0]
    assert [entry.year for entry in listing.years] == [2026]
    assert [n.code for n in listing.notices] == ["CALENDAR_SOURCE", "DEFAULT_YEAR_USED"]
    assert "2026" in listing.notices[1].message


def test_run_reports_invalid_years_as_failed_document_without_calendar_access() -> None:
    rig = Rig()

    outcome = rig.use_case.run("2030-2020", None)

    assert outcome.status is RunStatus.INPUT_FAILED
    assert outcome.serialized == "failure"
    assert outcome.message
    error, notices, generated_at = rig.serializer.failures[0]
    assert error.code == "INVALID_YEARS"
    assert notices == ()
    assert generated_at == MOMENT
    assert rig.sink.lines == ["failure"]
    assert rig.calendar.requested == []
    assert rig.serializer.listings == []


def test_run_reports_unparsable_configuration_as_failed_document() -> None:
    rig = Rig(loaded=ConfigurationError("The configuration file x.toml cannot be read."))

    outcome = rig.use_case.run("2025", None)

    assert outcome.status is RunStatus.INPUT_FAILED
    error, notices, _ = rig.serializer.failures[0]
    assert error.code == "CONFIGURATION_ERROR"
    assert notices == ()
    assert rig.calendar.requested == []


def test_run_loads_configuration_without_validating_llm_values() -> None:
    rig = Rig()
    path = Path("some.toml")

    rig.use_case.run("2025", path)

    assert rig.loader.calls == [(path, False)]


def test_run_reports_delivery_failure_of_listing() -> None:
    rig = Rig(fail_delivery=True)

    outcome = rig.use_case.run("2025", None)

    assert outcome.status is RunStatus.DELIVERY_FAILED
    assert outcome.serialized is None
    assert outcome.message
    assert "nothing was stored" in outcome.message


def test_run_reports_delivery_failure_of_failed_document() -> None:
    rig = Rig(fail_delivery=True)

    outcome = rig.use_case.run("abc", None)

    assert outcome.status is RunStatus.DELIVERY_FAILED
    assert outcome.message
    assert "INVALID_YEARS" in outcome.message
