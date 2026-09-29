"""Run the six analyses; those without an analyzer yet get a placeholder (ADR-0002, ADR-0007).

`run_analyses` is the single place where analyzers are applied. An available analysis for which
no analyzer is given is reported with `PLACEHOLDER_FINDINGS` and an `ANALYSIS_NOT_IMPLEMENTED`
notice, so a new analyzer only has to be added to the composition root.
"""

from collections.abc import Mapping

from hotel_booking_analysis.application.configuration import AppConfiguration
from hotel_booking_analysis.application.ports import Analyzer
from hotel_booking_analysis.application.validate_bookings import ValidatedBookings
from hotel_booking_analysis.domain.analysis import (
    Analysis,
    AnalysisAvailability,
    JsonValue,
)
from hotel_booking_analysis.domain.errors import Notice

ANALYSIS_NOT_IMPLEMENTED = "ANALYSIS_NOT_IMPLEMENTED"
PLACEHOLDER_FINDINGS: Mapping[str, JsonValue] = {"implemented": False}


def run_analyses(
    validated: ValidatedBookings,
    configuration: AppConfiguration,
    analyzers: tuple[Analyzer, ...] = (),
) -> tuple[tuple[Analysis, ...], tuple[Notice, ...]]:
    """Return one analysis per name in availability order, plus the notices they raise."""
    by_name = {analyzer.name: analyzer for analyzer in analyzers}
    analyses: list[Analysis] = []
    notices: list[Notice] = []
    for availability in validated.availability:
        analyzer = by_name.get(availability.analysis)
        if not availability.is_available:
            analyses.append(_unavailable(availability))
        elif analyzer is not None:
            analyses.append(analyzer.analyze(validated, configuration))
        else:
            analyses.append(_placeholder(availability))
            notices.append(_not_implemented_notice(availability))
    return tuple(analyses), tuple(notices)


def _unavailable(availability: AnalysisAvailability) -> Analysis:
    return Analysis(availability.analysis, availability.availability, availability.reason)


def _placeholder(availability: AnalysisAvailability) -> Analysis:
    return Analysis(
        availability.analysis, availability.availability, findings=dict(PLACEHOLDER_FINDINGS)
    )


def _not_implemented_notice(availability: AnalysisAvailability) -> Notice:
    return Notice(
        ANALYSIS_NOT_IMPLEMENTED,
        f"Analysis '{availability.analysis}' has its required fields but is not implemented yet; "
        "its findings are a placeholder.",
    )
