"""Tests for the result builder (ADR-0002, US-001.08, UC-001 step 5)."""

from datetime import UTC, datetime

from hotel_booking_analysis.application.build_result import (
    CONFIG_UNKNOWN_KEYS,
    DEVELOPMENT_SAMPLE_USED,
    ESTIMATE_NOT_REVENUE,
    build_failed_result,
    build_result,
)
from hotel_booking_analysis.application.placeholder_analyses import (
    ANALYSIS_NOT_IMPLEMENTED,
    PLACEHOLDER_FINDINGS,
)
from hotel_booking_analysis.application.validate_bookings import validate_bookings
from hotel_booking_analysis.domain.analysis import AnalysisName, Availability
from hotel_booking_analysis.domain.booking import BookingRecord, BookingSubmission, InputSource
from hotel_booking_analysis.domain.errors import ConfigurationError, Notice
from hotel_booking_analysis.domain.result import AnalysisResult, AnalysisStatus
from tests.support import full_record, make_submission

MOMENT = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
ID = "00000000-0000-0000-0000-000000000001"


def _build(submission: BookingSubmission, notices: tuple[Notice, ...] = ()) -> AnalysisResult:
    return build_result(validate_bookings(submission), notices, ID, MOMENT)


def _codes(result: AnalysisResult) -> list[str]:
    return [notice.code for notice in result.notices]


def test_build_result_completed_when_every_analysis_is_available_and_data_is_clean() -> None:
    result = _build(make_submission(full_record()))

    assert result.status is AnalysisStatus.COMPLETED
    assert result.error is None
    assert result.result_id == ID
    assert result.generated_at == MOMENT


def test_build_result_has_all_six_analyses_in_every_result() -> None:
    result = _build(make_submission(full_record()))

    assert {a.name for a in result.analyses} == set(AnalysisName)
    assert len(result.analyses) == 6


def test_build_result_uses_placeholder_findings_and_notice_for_available_analyses() -> None:
    result = _build(make_submission(full_record()))

    assert all(a.availability is Availability.AVAILABLE for a in result.analyses)
    assert all(a.findings == PLACEHOLDER_FINDINGS for a in result.analyses)
    assert _codes(result).count(ANALYSIS_NOT_IMPLEMENTED) == 6


def test_build_result_marks_analysis_unavailable_without_findings_when_field_is_missing() -> None:
    record = BookingRecord(lead_time=5, missing_fields=frozenset({"is_canceled"}))

    result = _build(make_submission(record))

    cancellations = next(a for a in result.analyses if a.name is AnalysisName.CANCELLATIONS)
    assert cancellations.availability is Availability.UNAVAILABLE
    assert cancellations.reason is not None
    assert "is_canceled" in cancellations.reason
    assert cancellations.findings == {}
    assert result.status is AnalysisStatus.COMPLETED_WITH_WARNINGS
    assert _codes(result).count(ANALYSIS_NOT_IMPLEMENTED) == 1


def test_build_result_has_warnings_when_some_data_is_invalid() -> None:
    invalid = BookingRecord(invalid_fields=frozenset({"lead_time"}), adults=1)

    result = _build(make_submission(full_record(), invalid))

    assert result.data_quality is not None
    assert result.data_quality.has_invalid_values
    assert result.status is AnalysisStatus.COMPLETED_WITH_WARNINGS


def test_build_result_has_warnings_when_a_notice_carries_a_warning() -> None:
    notice = Notice(CONFIG_UNKNOWN_KEYS, "Unknown configuration keys ignored: x")

    result = _build(make_submission(full_record()), (notice,))

    assert result.status is AnalysisStatus.COMPLETED_WITH_WARNINGS
    assert result.notices[0] == notice


def test_build_result_keeps_informational_notices_from_changing_status() -> None:
    notice = Notice("CONFIG_FILE_NOT_FOUND", "No configuration file was found.")

    result = _build(make_submission(full_record()), (notice,))

    assert result.status is AnalysisStatus.COMPLETED


def test_build_result_always_carries_the_estimate_notice() -> None:
    result = _build(make_submission(full_record()))

    assert ESTIMATE_NOT_REVENUE in _codes(result)


def test_build_result_states_development_sample_use() -> None:
    submission = BookingSubmission(
        InputSource.DEVELOPMENT_SAMPLE, "nf.csv", "0" * 64, (full_record(),)
    )

    result = _build(submission)

    assert DEVELOPMENT_SAMPLE_USED in _codes(result)
    assert result.input is not None
    assert result.input.source is InputSource.DEVELOPMENT_SAMPLE


def test_build_result_reports_input_metadata_and_data_quality() -> None:
    result = _build(make_submission(full_record("1"), full_record("2")))

    assert result.input is not None
    assert result.input.reference == "bookings.json"
    assert result.input.record_count == 2
    assert result.input.content_sha256 == "0" * 64
    assert result.data_quality is not None
    assert result.data_quality.record_count == 2


def test_build_failed_result_carries_error_and_config_notices() -> None:
    error = ConfigurationError("'history.retention' must be an integer of at least 1.", "x")
    notice = Notice("CONFIG_UNKNOWN_KEYS", "ignored")

    result = build_failed_result(error, (notice,), ID, MOMENT)

    assert result.status is AnalysisStatus.FAILED
    assert result.error is not None
    assert result.error.code == "CONFIGURATION_ERROR"
    assert result.input is None
    assert result.data_quality is None
    assert result.analyses == ()
    assert result.notices == (notice,)
