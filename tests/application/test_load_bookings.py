"""Tests for source selection (ADR-0001 development fallback, UC-001 1a)."""

from pathlib import Path

import pytest

from hotel_booking_analysis.application.configuration import Environment
from hotel_booking_analysis.application.load_bookings import BookingLoader
from hotel_booking_analysis.domain.booking import BookingRecord
from hotel_booking_analysis.domain.errors import InputError
from tests.support import FakeBookingReader, make_submission

SAMPLE = Path("data/example/nf_hotel_bookings.csv")


def _loader() -> tuple[BookingLoader, FakeBookingReader, FakeBookingReader]:
    supplied = FakeBookingReader(make_submission(BookingRecord(lead_time=1)))
    development = FakeBookingReader(make_submission(BookingRecord(lead_time=2)))
    return BookingLoader(supplied, development, SAMPLE), supplied, development


@pytest.mark.parametrize("environment", list(Environment))
def test_load_reads_supplied_file_in_every_environment(environment: Environment) -> None:
    loader, supplied, development = _loader()

    loader.load(Path("in.json"), environment)

    assert supplied.locations == [Path("in.json")]
    assert development.locations == []


def test_load_uses_development_sample_when_no_input_in_development() -> None:
    loader, supplied, development = _loader()

    submission = loader.load(None, Environment.DEVELOPMENT)

    assert development.locations == [SAMPLE]
    assert supplied.locations == []
    assert submission.records[0].lead_time == 2


def test_load_fails_when_no_input_outside_development() -> None:
    loader, supplied, development = _loader()

    with pytest.raises(InputError) as error:
        loader.load(None, Environment.PRODUCTION)

    assert error.value.code == "NO_INPUT"
    assert supplied.locations == []
    assert development.locations == []
