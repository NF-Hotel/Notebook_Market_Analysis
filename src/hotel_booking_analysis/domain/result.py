"""Analysis result entity (DM-001 Analysis Result, ADR-0002, US-001.08)."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from hotel_booking_analysis.domain.analysis import Analysis
from hotel_booking_analysis.domain.booking import InputSource
from hotel_booking_analysis.domain.errors import Notice
from hotel_booking_analysis.domain.quality import DataQualitySummary

SCHEMA_VERSION = "1.0"


class AnalysisStatus(StrEnum):
    """Outcome of a run (ADR-0002 `status`)."""

    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ResultInput:
    """Input metadata; no raw records and no directory (ADR-0002 `input`)."""

    source: InputSource
    reference: str
    record_count: int
    content_sha256: str


@dataclass(frozen=True, slots=True)
class ResultError:
    """Failure description, present only for a failed result (ADR-0002 `error`)."""

    code: str
    message: str


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """The complete outcome of one run (DM-001, ADR-0002).

    A failed result has no analyses and no data-quality summary if none could be built.
    """

    result_id: str
    generated_at: datetime
    status: AnalysisStatus
    input: ResultInput | None
    data_quality: DataQualitySummary | None
    analyses: tuple[Analysis, ...] = ()
    notices: tuple[Notice, ...] = ()
    error: ResultError | None = None
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at must be timezone-aware")
        if (self.status is AnalysisStatus.FAILED) != (self.error is not None):
            raise ValueError("error is present exactly when status is failed")
