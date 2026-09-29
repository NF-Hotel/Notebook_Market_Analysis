"""Read-only access to the configured history for the notebook (UC-002, ADR-0003, ADR-0004).

The history location comes from the configuration file, resolved against the working
directory. Nothing here writes.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from hotel_booking_analysis.adapters.toml_configuration import TomlConfigurationLoader
from hotel_booking_analysis.domain.errors import ConfigurationError, HistoryReadError
from hotel_booking_analysis.domain.history import HistoryReadout
from hotel_booking_analysis.infrastructure.jsonl_history import JsonlHistoryReader


@dataclass(frozen=True, slots=True)
class LoadedHistory:
    """The readout plus an `error` message if configuration or file could not be read."""

    readout: HistoryReadout
    location: Path | None
    error: str | None = None


def load_history(working_directory: Path, environ: Mapping[str, str]) -> LoadedHistory:
    """Read the history named by the configuration; failures become a message, not a raise."""
    try:
        configuration = TomlConfigurationLoader(working_directory, environ).load(None)
        location = configuration.configuration.history_path
    except ConfigurationError as error:
        return LoadedHistory(HistoryReadout((), 0), None, error.message)
    try:
        readout = JsonlHistoryReader(working_directory).read(location)
    except HistoryReadError as error:
        return LoadedHistory(HistoryReadout((), 0), location, str(error))
    return LoadedHistory(readout, location)
