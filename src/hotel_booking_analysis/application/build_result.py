"""Assemble the result envelope from a validated submission (ADR-0002, US-001.08, UC-001 step 5).

The result carries aggregate figures and metadata only, never raw booking records.
"""

from datetime import datetime

from hotel_booking_analysis.application.placeholder_analyses import run_analyses
from hotel_booking_analysis.application.validate_bookings import ValidatedBookings
from hotel_booking_analysis.domain.analysis import Analysis, Availability
from hotel_booking_analysis.domain.booking import InputSource
from hotel_booking_analysis.domain.errors import InputError, Notice
from hotel_booking_analysis.domain.result import (
    AnalysisResult,
    AnalysisStatus,
    ResultError,
    ResultInput,
)

ESTIMATE_NOT_REVENUE = "ESTIMATE_NOT_REVENUE"
DEVELOPMENT_SAMPLE_USED = "DEVELOPMENT_SAMPLE_USED"
CONFIG_UNKNOWN_KEYS = "CONFIG_UNKNOWN_KEYS"

WARNING_NOTICE_CODES: frozenset[str] = frozenset({CONFIG_UNKNOWN_KEYS})
"""Notices that make a result `completed_with_warnings`; all other notices are informational."""


def build_result(
    validated: ValidatedBookings,
    config_notices: tuple[Notice, ...],
    result_id: str,
    generated_at: datetime,
) -> AnalysisResult:
    """Build the result of a run whose input was accepted (ADR-0002)."""
    submission = validated.submission
    analyses, analysis_notices = run_analyses(validated)
    notices = (
        *config_notices,
        *_source_notices(submission.source),
        *analysis_notices,
        _estimate_notice(),
    )
    return AnalysisResult(
        result_id=result_id,
        generated_at=generated_at,
        status=_status(validated, analyses, notices),
        input=ResultInput(
            source=submission.source,
            reference=submission.reference,
            record_count=len(submission.records),
            content_sha256=submission.content_sha256,
        ),
        data_quality=validated.summary,
        analyses=analyses,
        notices=notices,
    )


def build_failed_result(
    error: InputError,
    notices: tuple[Notice, ...],
    result_id: str,
    generated_at: datetime,
) -> AnalysisResult:
    """Build the `failed` result for an input or configuration error (ADR-0005)."""
    return AnalysisResult(
        result_id=result_id,
        generated_at=generated_at,
        status=AnalysisStatus.FAILED,
        input=None,
        data_quality=None,
        notices=notices,
        error=ResultError(error.code, error.message),
    )


def _status(
    validated: ValidatedBookings, analyses: tuple[Analysis, ...], notices: tuple[Notice, ...]
) -> AnalysisStatus:
    has_warnings = (
        any(a.availability is Availability.UNAVAILABLE for a in analyses)
        or validated.summary.has_invalid_values
        or any(notice.code in WARNING_NOTICE_CODES for notice in notices)
    )
    return AnalysisStatus.COMPLETED_WITH_WARNINGS if has_warnings else AnalysisStatus.COMPLETED


def _source_notices(source: InputSource) -> tuple[Notice, ...]:
    if source is not InputSource.DEVELOPMENT_SAMPLE:
        return ()
    return (
        Notice(
            DEVELOPMENT_SAMPLE_USED,
            "No input was supplied; the development sample file was used.",
        ),
    )


def _estimate_notice() -> Notice:
    return Notice(
        ESTIMATE_NOT_REVENUE,
        "Room value is an estimate (price per night times total nights), not realized revenue.",
    )
