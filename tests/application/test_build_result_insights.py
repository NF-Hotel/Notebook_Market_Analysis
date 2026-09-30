"""Tests of the result assembly with AI insights (ADR-0011, UC-005)."""

from hotel_booking_analysis.adapters.json_result_serializer import JsonResultSerializer
from hotel_booking_analysis.application.build_result import (
    INSIGHTS_UNAVAILABLE,
    assemble_result,
    build_result,
)
from hotel_booking_analysis.application.configuration import AppConfiguration
from hotel_booking_analysis.application.placeholder_analyses import run_analyses
from hotel_booking_analysis.application.validate_bookings import validate_bookings
from hotel_booking_analysis.domain.analysis import AnalysisName, Availability
from hotel_booking_analysis.domain.booking import BookingRecord
from hotel_booking_analysis.domain.insight import InsightReason, InsightStatus
from hotel_booking_analysis.domain.llm import ProviderReason
from hotel_booking_analysis.domain.result import AnalysisResult, AnalysisStatus
from tests.insight_fakes import (
    MOMENT,
    RESULT_ID,
    FakeModelProvider,
    insight_result,
    timeout_on_call,
)
from tests.support import full_record, make_submission

VALIDATED = validate_bookings(make_submission(full_record()))
PARTLY_AVAILABLE = BookingRecord(lead_time=5, missing_fields=frozenset({"is_canceled"}))


def _codes(result: AnalysisResult) -> list[str]:
    return [notice.code for notice in result.notices]


def test_assemble_result_without_insights_is_byte_identical_to_build_result() -> None:
    analyses, notices = run_analyses(VALIDATED, AppConfiguration(), ())
    built = build_result(VALIDATED, (), RESULT_ID, MOMENT)

    assembled = assemble_result(VALIDATED, (), RESULT_ID, MOMENT, analyses, notices)

    assert assembled == built
    assert JsonResultSerializer().serialize(assembled) == JsonResultSerializer().serialize(built)
    assert built.schema_version == "1.0"
    assert built.insights is None
    assert all(a.insight is None for a in built.analyses)


def test_assemble_result_with_all_insights_available_is_completed_version_1_1() -> None:
    result = insight_result(VALIDATED, FakeModelProvider())

    assert result.schema_version == "1.1"
    assert result.status is AnalysisStatus.COMPLETED
    assert INSIGHTS_UNAVAILABLE not in _codes(result)
    assert result.insights is not None
    assert result.insights.requested is True
    assert [a.name for a in result.analyses] == list(AnalysisName)
    assert all(
        a.insight is not None and a.insight.status is InsightStatus.AVAILABLE
        for a in result.analyses
    )
    assert result.unavailable_insight_count() == 0


def test_assemble_result_keeps_the_analyses_unchanged_when_insights_are_attached() -> None:
    plain = build_result(VALIDATED, (), RESULT_ID, MOMENT)
    result = insight_result(VALIDATED, FakeModelProvider())

    assert [(a.name, a.availability, a.reason, a.findings) for a in result.analyses] == [
        (a.name, a.availability, a.reason, a.findings) for a in plain.analyses
    ]


def test_assemble_result_with_unavailable_insights_warns_and_says_how_many() -> None:
    result = insight_result(VALIDATED, FakeModelProvider(respond=timeout_on_call(1, 2)))

    assert result.status is AnalysisStatus.COMPLETED_WITH_WARNINGS
    (notice,) = [n for n in result.notices if n.code == INSIGHTS_UNAVAILABLE]
    assert "2 of the available analyses" in notice.message
    assert result.unavailable_insight_count() == 2
    assert result.schema_version == "1.1"


def test_assemble_result_without_provider_marks_every_available_analysis() -> None:
    result = insight_result(VALIDATED, FakeModelProvider(reason=ProviderReason.CONNECTION_REFUSED))

    assert result.status is AnalysisStatus.COMPLETED_WITH_WARNINGS
    assert result.insights is not None
    assert (result.insights.provider, result.insights.model) == (None, None)
    assert {a.insight.reason for a in result.analyses if a.insight} == {InsightReason.NO_PROVIDER}
    assert "6 of the available analyses" in result.notices[-1].message


def test_assemble_result_unavailable_analysis_gets_not_applicable_and_no_insight_warning() -> None:
    result = insight_result(
        validate_bookings(make_submission(PARTLY_AVAILABLE)), FakeModelProvider()
    )

    cancellations = next(a for a in result.analyses if a.name is AnalysisName.CANCELLATIONS)
    assert cancellations.availability is Availability.UNAVAILABLE
    assert cancellations.insight is not None
    assert cancellations.insight.status is InsightStatus.NOT_APPLICABLE
    assert INSIGHTS_UNAVAILABLE not in _codes(result)
    assert result.unavailable_insight_count() == 0
