"""Ports of the core pipeline, one per consumer need (ADR-0006)."""

from datetime import datetime
from pathlib import Path
from typing import Protocol

from hotel_booking_analysis.application.configuration import LoadedConfiguration
from hotel_booking_analysis.domain.booking import BookingSubmission
from hotel_booking_analysis.domain.history import HistoryReadout, RetentionPolicy
from hotel_booking_analysis.domain.result import AnalysisResult


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


class ResultSerializer(Protocol):
    """Turns a result into the one compact JSON line used for history and caller (ADR-0002)."""

    def serialize(self, result: AnalysisResult) -> str: ...


class HistoryWriter(Protocol):
    """Appends a serialized result to the history and applies retention (ADR-0003, ADR-0005).

    Raises `HistoryWriteError` if the line was not appended, and `HistoryRetentionError` if it
    was appended but retention failed.
    """

    def append(self, location: Path, line: str, retention: RetentionPolicy) -> None: ...


class HistoryReader(Protocol):
    """Reads the history tolerantly and never changes it (ADR-0003, UC-002).

    Raises `HistoryReadError` if an existing file cannot be read; a missing file is empty.
    """

    def read(self, location: Path) -> HistoryReadout: ...


class ResultSink(Protocol):
    """Hands the serialized result to the caller (ADR-0005).

    Raises `ResultDeliveryError` if it cannot be written.
    """

    def write(self, line: str) -> None: ...


class Clock(Protocol):
    """Source of timezone-aware current time."""

    def now(self) -> datetime: ...


class ResultIdGenerator(Protocol):
    """Source of unique result identifiers (ADR-0002 `result_id`)."""

    def new_id(self) -> str: ...
