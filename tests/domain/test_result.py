"""Tests for the analysis result entity (ADR-0002)."""

from datetime import UTC, datetime

import pytest

from hotel_booking_analysis.domain.result import AnalysisResult, AnalysisStatus, ResultError

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_result_requires_timezone_aware_generated_time() -> None:
    with pytest.raises(ValueError):
        AnalysisResult("r", datetime(2026, 1, 1), AnalysisStatus.COMPLETED, None, None)


def test_result_error_present_only_when_failed() -> None:
    with pytest.raises(ValueError):
        AnalysisResult("r", NOW, AnalysisStatus.FAILED, None, None)
    with pytest.raises(ValueError):
        AnalysisResult("r", NOW, AnalysisStatus.COMPLETED, None, None, error=ResultError("c", "m"))


def test_failed_result_with_error_is_valid_and_has_no_analyses() -> None:
    result = AnalysisResult(
        "r", NOW, AnalysisStatus.FAILED, None, None, error=ResultError("INPUT_EMPTY", "empty")
    )

    assert result.schema_version == "1.0"
    assert result.analyses == ()
