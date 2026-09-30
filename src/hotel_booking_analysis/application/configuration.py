"""Application configuration values and defaults (ADR-0004, US-001.09)."""

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from hotel_booking_analysis.domain.errors import Notice
from hotel_booking_analysis.domain.history import RetentionPolicy
from hotel_booking_analysis.domain.llm import ProviderName

DEFAULT_HISTORY_PATH = Path("output/analysis_history.jsonl")
DEFAULT_HOLIDAY_WINDOWS_DAYS: tuple[int, ...] = (1, 3, 7)
DEFAULT_MIN_GROUP_SIZE = 30
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_LMSTUDIO_URL = "http://localhost:1234"
DEFAULT_DISCOVERY_TIMEOUT_SECONDS = 2.0
DEFAULT_GENERATION_TIMEOUT_SECONDS = 120.0
DEFAULT_TEMPERATURE = 0.0


class Environment(StrEnum):
    """Deployment environment; only `development` enables the CSV fallback (ADR-0001)."""

    PRODUCTION = "production"
    DEVELOPMENT = "development"


@dataclass(frozen=True, slots=True)
class LlmConfiguration:
    """The `[llm]` table (ADR-0012); safe defaults: local providers only, no fixed model.

    `provider` and `model` are None for automatic selection (the empty string in the file).
    """

    ollama_url: str = DEFAULT_OLLAMA_URL
    lmstudio_url: str = DEFAULT_LMSTUDIO_URL
    discovery_timeout_seconds: float = DEFAULT_DISCOVERY_TIMEOUT_SECONDS
    generation_timeout_seconds: float = DEFAULT_GENERATION_TIMEOUT_SECONDS
    provider: ProviderName | None = None
    model: str | None = None
    allow_remote: bool = False
    temperature: float = DEFAULT_TEMPERATURE


@dataclass(frozen=True, slots=True)
class AppConfiguration:
    """Validated settings; every field has the ADR-0004 default.

    `llm` holds the ADR-0012 defaults unless the configuration was loaded with `with_llm=True`.
    """

    environment: Environment = Environment.PRODUCTION
    history_path: Path = DEFAULT_HISTORY_PATH
    retention: RetentionPolicy = field(default_factory=RetentionPolicy)
    holiday_windows_days: tuple[int, ...] = DEFAULT_HOLIDAY_WINDOWS_DAYS
    min_group_size: int = DEFAULT_MIN_GROUP_SIZE
    llm: LlmConfiguration = field(default_factory=LlmConfiguration)


@dataclass(frozen=True, slots=True)
class LoadedConfiguration:
    """Settings plus the notices produced while reading them (ADR-0004)."""

    configuration: AppConfiguration
    notices: tuple[Notice, ...] = ()
