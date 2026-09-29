"""Composition root: wires concrete adapters into the use case (ADR-0006)."""

from collections.abc import Mapping
from pathlib import Path
from typing import BinaryIO

from hotel_booking_analysis.adapters.csv_reader import DevelopmentCsvReader
from hotel_booking_analysis.adapters.holiday_analyzer import HolidayAnalyzer
from hotel_booking_analysis.adapters.json_reader import JsonBookingReader
from hotel_booking_analysis.adapters.json_result_serializer import JsonResultSerializer
from hotel_booking_analysis.adapters.khmer_holiday_calendar import KhmerHolidayCalendar
from hotel_booking_analysis.adapters.lead_time_analyzer import LeadTimeAnalyzer
from hotel_booking_analysis.adapters.toml_configuration import TomlConfigurationLoader
from hotel_booking_analysis.application.analyze_bookings import AnalyzeBookings
from hotel_booking_analysis.application.load_bookings import BookingLoader
from hotel_booking_analysis.application.ports import Analyzer
from hotel_booking_analysis.infrastructure.file_lock import LOCK_WAIT_SECONDS
from hotel_booking_analysis.infrastructure.jsonl_history import (
    JsonlHistoryReader,
    JsonlHistoryWriter,
)
from hotel_booking_analysis.infrastructure.system import (
    StreamResultSink,
    SystemClock,
    UuidGenerator,
)

DEVELOPMENT_SAMPLE = Path("data/example/nf_hotel_bookings.csv")


def build_analyze_bookings(
    stdout: BinaryIO,
    working_directory: Path,
    environ: Mapping[str, str],
    lock_wait_seconds: float = LOCK_WAIT_SECONDS,
) -> AnalyzeBookings:
    """Create the analyze-bookings use case with the production adapters."""
    return AnalyzeBookings(
        configuration_loader=TomlConfigurationLoader(working_directory, environ),
        booking_loader=BookingLoader(
            JsonBookingReader(), DevelopmentCsvReader(), working_directory / DEVELOPMENT_SAMPLE
        ),
        serializer=JsonResultSerializer(),
        history_writer=JsonlHistoryWriter(lock_wait_seconds, base_directory=working_directory),
        history_reader=JsonlHistoryReader(working_directory),
        sink=StreamResultSink(stdout),
        clock=SystemClock(),
        ids=UuidGenerator(),
        analyzers=build_analyzers(),
    )


def build_analyzers() -> tuple[Analyzer, ...]:
    """Create the implemented analyzers; analyses without one are reported as placeholders."""
    return (LeadTimeAnalyzer(), HolidayAnalyzer(KhmerHolidayCalendar()))
