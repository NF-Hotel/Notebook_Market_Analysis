"""Application configuration values and defaults (ADR-0004, US-001.09)."""

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from hotel_booking_analysis.domain.errors import Notice
from hotel_booking_analysis.domain.history import RetentionPolicy

DEFAULT_HISTORY_PATH = Path("output/analysis_history.jsonl")
DEFAULT_HOLIDAY_WINDOWS_DAYS: tuple[int, ...] = (1, 3, 7)
DEFAULT_MIN_GROUP_SIZE = 30


class Environment(StrEnum):
    """Deployment environment; only `development` enables the CSV fallback (ADR-0001)."""

    PRODUCTION = "production"
    DEVELOPMENT = "development"


@dataclass(frozen=True, slots=True)
class AppConfiguration:
    """Validated settings; every field has the ADR-0004 default."""

    environment: Environment = Environment.PRODUCTION
    history_path: Path = DEFAULT_HISTORY_PATH
    retention: RetentionPolicy = field(default_factory=RetentionPolicy)
    holiday_windows_days: tuple[int, ...] = DEFAULT_HOLIDAY_WINDOWS_DAYS
    min_group_size: int = DEFAULT_MIN_GROUP_SIZE


@dataclass(frozen=True, slots=True)
class LoadedConfiguration:
    """Settings plus the notices produced while reading them (ADR-0004)."""

    configuration: AppConfiguration
    notices: tuple[Notice, ...] = ()
