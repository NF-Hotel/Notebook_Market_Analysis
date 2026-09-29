"""Ports of the core pipeline, one per consumer need (ADR-0006)."""

from pathlib import Path
from typing import Protocol

from hotel_booking_analysis.application.configuration import LoadedConfiguration
from hotel_booking_analysis.domain.booking import BookingSubmission


class ConfigurationLoader(Protocol):
    """Reads the configuration once at the start of a run (ADR-0004).

    Raises `ConfigurationError` for an unparsable file or an invalid value.
    """

    def load(self, explicit_path: Path | None) -> LoadedConfiguration: ...


class BookingReader(Protocol):
    """Reads booking records from one file (ADR-0001).

    Raises `InputError` when the file cannot be used as input.
    """

    def read(self, location: Path) -> BookingSubmission: ...
