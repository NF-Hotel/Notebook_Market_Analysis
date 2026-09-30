"""Analysis entities and value objects (DM-001, ADR-0002, ADR-0007)."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

type JsonValue = str | int | float | bool | list[JsonValue] | dict[str, JsonValue] | None
"""Plain JSON-shaped data; money is carried as a decimal string (ADR-0002)."""


class AnalysisName(StrEnum):
    """The six analyses of UC-001 step 4 (ADR-0002 `analyses` keys)."""

    LEAD_TIME = "lead_time"
    HOLIDAYS = "holidays"
    SEASONALITY = "seasonality"
    CANCELLATIONS = "cancellations"
    ROOM_VALUE = "room_value"
    GUEST_MIX = "guest_mix"


class Availability(StrEnum):
    """Whether an analysis could run (ADR-0002 analysis `status`)."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class AnalysisAvailability:
    """Availability of one analysis from its required fields (ADR-0001, US-001.01).

    `missing_fields` names the fields that no record could supply, whether the analysis is
    unavailable or only partly available (for example the holiday booking side).
    """

    analysis: AnalysisName
    availability: Availability
    reason: str | None = None
    missing_fields: tuple[str, ...] = ()

    @property
    def is_available(self) -> bool:
        return self.availability is Availability.AVAILABLE


@dataclass(frozen=True, slots=True)
class GroupStatistic:
    """A count-based figure for one group (DM-001, ADR-0002, ADR-0007 common rules)."""

    group: str
    numerator: int
    denominator: int
    small_sample: bool


@dataclass(frozen=True, slots=True)
class Analysis:
    """One analysis in a result (DM-001 Analysis, ADR-0002 `analyses` entry)."""

    name: AnalysisName
    availability: Availability
    reason: str | None = None
    findings: Mapping[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Holiday:
    """A Cambodian public holiday (DM-001 Holiday, ADR-0007)."""

    date: date
    name: str
