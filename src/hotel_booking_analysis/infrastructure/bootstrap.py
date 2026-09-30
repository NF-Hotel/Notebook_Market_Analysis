"""Composition root: wires concrete adapters into the use case (ADR-0006)."""

from collections.abc import Mapping
from pathlib import Path
from typing import BinaryIO

from hotel_booking_analysis.adapters.cancellation_analyzer import CancellationAnalyzer
from hotel_booking_analysis.adapters.csv_reader import DevelopmentCsvReader
from hotel_booking_analysis.adapters.guest_mix_analyzer import GuestMixAnalyzer
from hotel_booking_analysis.adapters.holiday_analyzer import HolidayAnalyzer
from hotel_booking_analysis.adapters.json_holiday_listing_serializer import (
    JsonHolidayListingSerializer,
)
from hotel_booking_analysis.adapters.json_provider_listing_serializer import (
    JsonProviderListingSerializer,
)
from hotel_booking_analysis.adapters.json_reader import JsonBookingReader
from hotel_booking_analysis.adapters.json_result_serializer import JsonResultSerializer
from hotel_booking_analysis.adapters.khmer_holiday_calendar import KhmerHolidayCalendar
from hotel_booking_analysis.adapters.lead_time_analyzer import LeadTimeAnalyzer
from hotel_booking_analysis.adapters.llm_registry import ConfiguredLlmProviders
from hotel_booking_analysis.adapters.room_value_analyzer import RoomValueAnalyzer
from hotel_booking_analysis.adapters.seasonality_analyzer import SeasonalityAnalyzer
from hotel_booking_analysis.adapters.toml_configuration import TomlConfigurationLoader
from hotel_booking_analysis.application.analyze_bookings import AnalyzeBookings
from hotel_booking_analysis.application.list_holidays import ListHolidays
from hotel_booking_analysis.application.list_llm_providers import ListLlmProviders
from hotel_booking_analysis.application.load_bookings import BookingLoader
from hotel_booking_analysis.application.ports import Analyzer, LlmProviderRegistry
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


def build_list_holidays(
    stdout: BinaryIO, working_directory: Path, environ: Mapping[str, str]
) -> ListHolidays:
    """Create the list-holidays use case with the production adapters."""
    return ListHolidays(
        configuration_loader=TomlConfigurationLoader(working_directory, environ),
        calendar=KhmerHolidayCalendar(),
        serializer=JsonHolidayListingSerializer(),
        sink=StreamResultSink(stdout),
        clock=SystemClock(),
    )


def build_list_llm_providers(
    stdout: BinaryIO, working_directory: Path, environ: Mapping[str, str]
) -> ListLlmProviders:
    """Create the list-LLM-providers use case with the production adapters."""
    return ListLlmProviders(
        configuration_loader=TomlConfigurationLoader(working_directory, environ),
        registry=build_llm_registry(),
        serializer=JsonProviderListingSerializer(),
        sink=StreamResultSink(stdout),
        clock=SystemClock(),
    )


def build_llm_registry() -> LlmProviderRegistry:
    """Create the registry of the Ollama and LM Studio adapters."""
    return ConfiguredLlmProviders()


def build_analyzers() -> tuple[Analyzer, ...]:
    """Create the analyzers of all six analyses."""
    return (
        LeadTimeAnalyzer(),
        HolidayAnalyzer(KhmerHolidayCalendar()),
        SeasonalityAnalyzer(),
        CancellationAnalyzer(),
        RoomValueAnalyzer(),
        GuestMixAnalyzer(),
    )
