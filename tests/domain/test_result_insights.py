"""Tests of the insight parts of the analysis and result entities (ADR-0011)."""

from datetime import UTC, datetime

import pytest

from hotel_booking_analysis.domain.analysis import Analysis, AnalysisName, Availability
from hotel_booking_analysis.domain.insight import AiInsight, InsightReason, InsightsMetadata
from hotel_booking_analysis.domain.result import (
    SCHEMA_VERSION_WITH_INSIGHTS,
    AnalysisResult,
    AnalysisStatus,
    ResultError,
)

MOMENT = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
METADATA = InsightsMetadata(True, None, None, "1")


def _result(
    status: AnalysisStatus = AnalysisStatus.COMPLETED,
    version: str = "1.0",
    insights: InsightsMetadata | None = None,
    error: ResultError | None = None,
) -> AnalysisResult:
    return AnalysisResult(
        "id", MOMENT, status, None, None, schema_version=version, insights=insights, error=error
    )


def test_with_insight_returns_a_copy_and_leaves_the_analysis_unchanged() -> None:
    analysis = Analysis(AnalysisName.LEAD_TIME, Availability.AVAILABLE, findings={"n": 1})
    insight = AiInsight.unavailable(InsightReason.NO_PROVIDER)

    copy = analysis.with_insight(insight)

    assert analysis.insight is None
    assert copy.insight is insight
    assert (copy.name, copy.availability, copy.findings) == (
        analysis.name,
        analysis.availability,
        analysis.findings,
    )


def test_result_without_insights_defaults_to_version_1_0() -> None:
    result = _result()

    assert result.schema_version == "1.0"
    assert result.insights is None


@pytest.mark.parametrize(
    "status", [AnalysisStatus.COMPLETED, AnalysisStatus.COMPLETED_WITH_WARNINGS]
)
def test_result_with_insights_uses_version_1_1(status: AnalysisStatus) -> None:
    result = _result(status, SCHEMA_VERSION_WITH_INSIGHTS, METADATA)

    assert result.schema_version == "1.1"


def test_result_with_insights_but_version_1_0_is_rejected() -> None:
    with pytest.raises(ValueError, match=r"schema version 1.1"):
        _result(insights=METADATA)


def test_result_version_1_1_without_insights_is_rejected() -> None:
    with pytest.raises(ValueError, match=r"schema version 1.1"):
        _result(version="1.1")


def test_failed_result_cannot_hold_insights() -> None:
    with pytest.raises(ValueError, match="failed result has no insights"):
        _result(AnalysisStatus.FAILED, "1.1", METADATA, ResultError("X", "y"))


def test_failed_result_stays_version_1_0() -> None:
    failed = _result(AnalysisStatus.FAILED, error=ResultError("X", "y"))

    assert failed.schema_version == "1.0"
