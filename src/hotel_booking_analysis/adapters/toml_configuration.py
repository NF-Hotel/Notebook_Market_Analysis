"""TOML configuration loader (ADR-0004, US-001.09, UC-001 extensions 7a and 7b)."""

import tomllib
from collections.abc import Mapping
from pathlib import Path

from hotel_booking_analysis.application.configuration import (
    DEFAULT_HISTORY_PATH,
    DEFAULT_HOLIDAY_WINDOWS_DAYS,
    DEFAULT_MIN_GROUP_SIZE,
    AppConfiguration,
    Environment,
    LoadedConfiguration,
)
from hotel_booking_analysis.domain.errors import ConfigurationError, Notice
from hotel_booking_analysis.domain.history import DEFAULT_RETENTION, RetentionPolicy

CONFIG_FILE_NAME = "hotel_analysis.toml"
CONFIG_ENV_VAR = "HOTEL_ANALYSIS_CONFIG"

_KNOWN_KEYS: dict[str, frozenset[str]] = {
    "": frozenset({"environment", "history", "analysis"}),
    "history": frozenset({"retention", "path"}),
    "analysis": frozenset({"holiday_windows_days", "min_group_size"}),
}


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _positive_int(value: object, key: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ConfigurationError(f"'{key}' must be an integer of at least 1.", key)
    return value


def _table(data: Mapping[str, object], name: str) -> Mapping[str, object]:
    section = data.get(name, {})
    if not isinstance(section, dict):
        raise ConfigurationError(f"'{name}' must be a table.", name)
    return section


def _environment(value: object) -> Environment:
    allowed = [e.value for e in Environment]
    if isinstance(value, str) and value in allowed:
        return Environment(value)
    raise ConfigurationError(f"'environment' must be one of {allowed}.", "environment")


def _windows(value: object) -> tuple[int, ...]:
    key = "analysis.holiday_windows_days"
    message = f"'{key}' must be a non-empty list of distinct integers of at least 1."
    if not isinstance(value, list) or not value:
        raise ConfigurationError(message, key)
    if not all(_is_int(item) and item >= 1 for item in value) or len(set(value)) != len(value):
        raise ConfigurationError(message, key)
    return tuple(value)


def _history_path(value: object) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError("'history.path' must be a non-empty string.", "history.path")
    return Path(value)


def _retention(value: object) -> RetentionPolicy:
    return RetentionPolicy(_positive_int(value, "history.retention"))


def _unknown_keys(data: Mapping[str, object]) -> list[str]:
    unknown = [key for key in data if key not in _KNOWN_KEYS[""]]
    for section in ("history", "analysis"):
        table = data.get(section)
        if isinstance(table, dict):
            unknown += [f"{section}.{key}" for key in table if key not in _KNOWN_KEYS[section]]
    return sorted(unknown)


def build_configuration(data: Mapping[str, object]) -> AppConfiguration:
    """Validate parsed TOML data and apply defaults; raises `ConfigurationError` (ADR-0004)."""
    history = _table(data, "history")
    analysis = _table(data, "analysis")
    return AppConfiguration(
        environment=_environment(data["environment"])
        if "environment" in data
        else Environment.PRODUCTION,
        history_path=_history_path(history["path"]) if "path" in history else DEFAULT_HISTORY_PATH,
        retention=_retention(history["retention"])
        if "retention" in history
        else RetentionPolicy(DEFAULT_RETENTION),
        holiday_windows_days=_windows(analysis["holiday_windows_days"])
        if "holiday_windows_days" in analysis
        else DEFAULT_HOLIDAY_WINDOWS_DAYS,
        min_group_size=_positive_int(analysis["min_group_size"], "analysis.min_group_size")
        if "min_group_size" in analysis
        else DEFAULT_MIN_GROUP_SIZE,
    )


class TomlConfigurationLoader:
    """Reads `hotel_analysis.toml` with the standard library (ADR-0004).

    The file is the explicit path if given (the `--config` option), else the path in
    `HOTEL_ANALYSIS_CONFIG`, else `hotel_analysis.toml` in the working directory.
    """

    def __init__(self, working_directory: Path, environ: Mapping[str, str]) -> None:
        self._working_directory = working_directory
        self._environ = environ

    def resolve_path(self, explicit_path: Path | None) -> Path:
        if explicit_path is not None:
            return explicit_path
        from_environment = self._environ.get(CONFIG_ENV_VAR)
        if from_environment:
            return Path(from_environment)
        return self._working_directory / CONFIG_FILE_NAME

    def load(self, explicit_path: Path | None) -> LoadedConfiguration:
        path = self.resolve_path(explicit_path)
        if not path.is_file():
            notice = Notice(
                "CONFIG_FILE_NOT_FOUND",
                f"No configuration file was found at {path.name}; defaults were applied.",
            )
            return LoadedConfiguration(AppConfiguration(), (notice,))
        data = self._parse(path)
        configuration = build_configuration(data)
        unknown = _unknown_keys(data)
        notices = (
            (
                Notice(
                    "CONFIG_UNKNOWN_KEYS",
                    f"Unknown configuration keys ignored: {', '.join(unknown)}",
                ),
            )
            if unknown
            else ()
        )
        return LoadedConfiguration(configuration, notices)

    @staticmethod
    def _parse(path: Path) -> dict[str, object]:
        try:
            with path.open("rb") as handle:
                return tomllib.load(handle)
        except (tomllib.TOMLDecodeError, UnicodeDecodeError, OSError) as error:
            raise ConfigurationError(
                f"The configuration file {path.name} cannot be read: {error}"
            ) from error
