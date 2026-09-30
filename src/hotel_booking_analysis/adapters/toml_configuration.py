"""TOML configuration loader (ADR-0004, ADR-0012, US-001.09, UC-001 extensions 7a and 7b).

The `[llm]` table (ADR-0012) is validated lazily, as DCD-001 designs it: `load` builds and
validates `LlmConfiguration` only when called with `with_llm=True`, which the commands that use
it (`llm-providers`, `analyze --insights`) do. Without it the file is only parsed, `llm` (when
present) is checked to be a table, its unknown keys are still listed, and
`AppConfiguration.llm` holds the defaults.
"""

import math
import tomllib
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlparse

from hotel_booking_analysis.application.configuration import (
    DEFAULT_HISTORY_PATH,
    DEFAULT_HOLIDAY_WINDOWS_DAYS,
    DEFAULT_MIN_GROUP_SIZE,
    AppConfiguration,
    Environment,
    LlmConfiguration,
    LoadedConfiguration,
)
from hotel_booking_analysis.domain.errors import ConfigurationError, Notice
from hotel_booking_analysis.domain.history import DEFAULT_RETENTION, RetentionPolicy
from hotel_booking_analysis.domain.llm import ProviderName

CONFIG_FILE_NAME = "hotel_analysis.toml"
CONFIG_ENV_VAR = "HOTEL_ANALYSIS_CONFIG"

_KNOWN_KEYS: dict[str, frozenset[str]] = {
    "": frozenset({"environment", "history", "analysis", "llm"}),
    "history": frozenset({"retention", "path"}),
    "analysis": frozenset({"holiday_windows_days", "min_group_size"}),
    "llm": frozenset(
        {
            "ollama_url",
            "lmstudio_url",
            "discovery_timeout_seconds",
            "generation_timeout_seconds",
            "provider",
            "model",
            "allow_remote",
            "temperature",
        }
    ),
}
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


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


def _llm_key(name: str) -> str:
    return f"llm.{name}"


def _number(value: object, name: str, upper: float | None = None) -> float:
    """A finite number (never a boolean) greater than 0, or from 0 to `upper` when given."""
    key = _llm_key(name)
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise ConfigurationError(f"'{key}' must be a number.", key)
    if upper is None and value <= 0:
        raise ConfigurationError(f"'{key}' must be a number greater than 0.", key)
    if upper is not None and not 0 <= value <= upper:
        raise ConfigurationError(f"'{key}' must be a number from 0 to {upper:g}.", key)
    return float(value)


def _allow_remote(value: object) -> bool:
    if not isinstance(value, bool):
        key = _llm_key("allow_remote")
        raise ConfigurationError(f"'{key}' must be true or false.", key)
    return value


def _url(value: object, name: str, allow_remote: bool) -> str:
    key = _llm_key(name)
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"'{key}' must be a non-empty string.", key)
    try:
        parsed = urlparse(value)
        host = parsed.hostname
    except ValueError as error:
        raise ConfigurationError(f"'{key}' is not a valid URL: {error}", key) from error
    if parsed.scheme not in ("http", "https"):
        raise ConfigurationError(f"'{key}' must start with http:// or https://.", key)
    if not host:
        raise ConfigurationError(f"'{key}' must name a host.", key)
    if host not in _LOOPBACK_HOSTS and not allow_remote:
        raise ConfigurationError(
            f"'{key}' names a remote host; only localhost, 127.0.0.1 and ::1 are allowed "
            "unless 'llm.allow_remote' is true.",
            key,
        )
    return value


def _provider(value: object) -> ProviderName | None:
    allowed = ["", *(name.value for name in ProviderName)]
    if not isinstance(value, str) or value not in allowed:
        key = _llm_key("provider")
        raise ConfigurationError(f"'{key}' must be one of {allowed}.", key)
    return ProviderName(value) if value else None


def _model(value: object) -> str | None:
    if not isinstance(value, str) or value != value.strip():
        key = _llm_key("model")
        raise ConfigurationError(
            f"'{key}' must be a string without leading or trailing blanks.", key
        )
    return value or None


def build_llm_configuration(data: Mapping[str, object]) -> LlmConfiguration:
    """Validate the `[llm]` table and apply defaults; raises `ConfigurationError` (ADR-0012)."""
    llm = _table(data, "llm")
    defaults = LlmConfiguration()
    allow_remote = _allow_remote(llm["allow_remote"]) if "allow_remote" in llm else False
    return LlmConfiguration(
        ollama_url=_url(llm["ollama_url"], "ollama_url", allow_remote)
        if "ollama_url" in llm
        else defaults.ollama_url,
        lmstudio_url=_url(llm["lmstudio_url"], "lmstudio_url", allow_remote)
        if "lmstudio_url" in llm
        else defaults.lmstudio_url,
        discovery_timeout_seconds=_number(
            llm["discovery_timeout_seconds"], "discovery_timeout_seconds"
        )
        if "discovery_timeout_seconds" in llm
        else defaults.discovery_timeout_seconds,
        generation_timeout_seconds=_number(
            llm["generation_timeout_seconds"], "generation_timeout_seconds"
        )
        if "generation_timeout_seconds" in llm
        else defaults.generation_timeout_seconds,
        provider=_provider(llm["provider"]) if "provider" in llm else None,
        model=_model(llm["model"]) if "model" in llm else None,
        allow_remote=allow_remote,
        temperature=_number(llm["temperature"], "temperature", upper=1.0)
        if "temperature" in llm
        else defaults.temperature,
    )


def _unknown_keys(data: Mapping[str, object]) -> list[str]:
    unknown = [key for key in data if key not in _KNOWN_KEYS[""]]
    for section in ("history", "analysis", "llm"):
        table = data.get(section)
        if isinstance(table, dict):
            unknown += [f"{section}.{key}" for key in table if key not in _KNOWN_KEYS[section]]
    return sorted(unknown)


def build_configuration(data: Mapping[str, object], with_llm: bool = False) -> AppConfiguration:
    """Validate parsed TOML data and apply defaults; raises `ConfigurationError` (ADR-0004).

    The `[llm]` values are validated only when `with_llm` is true (ADR-0012); otherwise `llm`
    is only checked to be a table and the configuration holds the `[llm]` defaults.
    """
    history = _table(data, "history")
    analysis = _table(data, "analysis")
    _table(data, "llm")
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
        llm=build_llm_configuration(data) if with_llm else LlmConfiguration(),
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

    def load(self, explicit_path: Path | None, with_llm: bool = False) -> LoadedConfiguration:
        path = self.resolve_path(explicit_path)
        if not path.is_file():
            notice = Notice(
                "CONFIG_FILE_NOT_FOUND",
                f"No configuration file was found at {path.name}; defaults were applied.",
            )
            return LoadedConfiguration(AppConfiguration(), (notice,))
        data = self._parse(path)
        configuration = build_configuration(data, with_llm)
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
