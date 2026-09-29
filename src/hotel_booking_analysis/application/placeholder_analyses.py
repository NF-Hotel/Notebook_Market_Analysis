"""Placeholder for the six analyses until MIL-005 (ADR-0002 `analyses`, ADR-0007, UC-001 step 4).

MIL-004 delivers the core pipeline only. Every analysis whose fields are present is reported
as available with `PLACEHOLDER_FINDINGS` and an `ANALYSIS_NOT_IMPLEMENTED` notice. MIL-005
replaces `run_analyses` with the real analyzers; nothing else needs to change.
"""

from collections.abc import Mapping

from hotel_booking_analysis.application.validate_bookings import ValidatedBookings
from hotel_booking_analysis.domain.analysis import (
    Analysis,
    AnalysisAvailability,
    JsonValue,
)
from hotel_booking_analysis.domain.errors import Notice

ANALYSIS_NOT_IMPLEMENTED = "ANALYSIS_NOT_IMPLEMENTED"
PLACEHOLDER_FINDINGS: Mapping[str, JsonValue] = {"implemented": False}


def run_analyses(validated: ValidatedBookings) -> tuple[tuple[Analysis, ...], tuple[Notice, ...]]:
    """Return one analysis per name in availability order, plus the notices they raise."""
    analyses: list[Analysis] = []
    notices: list[Notice] = []
    for availability in validated.availability:
        analyses.append(_analysis(availability))
        if availability.is_available:
            notices.append(_not_implemented_notice(availability))
    return tuple(analyses), tuple(notices)


def _analysis(availability: AnalysisAvailability) -> Analysis:
    if not availability.is_available:
        return Analysis(availability.analysis, availability.availability, availability.reason)
    return Analysis(
        availability.analysis, availability.availability, findings=dict(PLACEHOLDER_FINDINGS)
    )


def _not_implemented_notice(availability: AnalysisAvailability) -> Notice:
    return Notice(
        ANALYSIS_NOT_IMPLEMENTED,
        f"Analysis '{availability.analysis}' has its required fields but is not implemented yet; "
        "its findings are a placeholder.",
    )
