"""Tests for running analyzers with placeholders for the rest (MIL-005 task 1, UC-001 step 4)."""

from hotel_booking_analysis.application.configuration import AppConfiguration
from hotel_booking_analysis.application.placeholder_analyses import (
    ANALYSIS_NOT_IMPLEMENTED,
    PLACEHOLDER_FINDINGS,
    run_analyses,
)
from hotel_booking_analysis.application.validate_bookings import (
    ValidatedBookings,
    validate_bookings,
)
from hotel_booking_analysis.domain.analysis import Analysis, AnalysisName, Availability
from hotel_booking_analysis.domain.booking import BookingRecord
from tests.support import full_record, make_submission


class RecordingAnalyzer:
    """Analyzer fake returning fixed findings and recording what it was given."""

    def __init__(self, name: AnalysisName) -> None:
        self._name = name
        self.calls: list[tuple[ValidatedBookings, AppConfiguration]] = []

    @property
    def name(self) -> AnalysisName:
        return self._name

    def analyze(self, validated: ValidatedBookings, configuration: AppConfiguration) -> Analysis:
        self.calls.append((validated, configuration))
        return Analysis(self._name, Availability.AVAILABLE, findings={"real": True})


def test_run_analyses_uses_the_analyzer_and_placeholders_for_the_rest() -> None:
    validated = validate_bookings(make_submission(full_record()))
    analyzer = RecordingAnalyzer(AnalysisName.LEAD_TIME)

    analyses, notices = run_analyses(validated, AppConfiguration(), (analyzer,))

    by_name = {a.name: a for a in analyses}
    assert by_name[AnalysisName.LEAD_TIME].findings == {"real": True}
    assert all(
        a.findings == PLACEHOLDER_FINDINGS
        for n, a in by_name.items()
        if n is not AnalysisName.LEAD_TIME
    )
    assert [n.code for n in notices] == [ANALYSIS_NOT_IMPLEMENTED] * 5
    assert not any("lead_time" in n.message for n in notices)


def test_run_analyses_passes_validated_bookings_and_configuration_to_the_analyzer() -> None:
    validated = validate_bookings(make_submission(full_record()))
    configuration = AppConfiguration(min_group_size=7, holiday_windows_days=(2,))
    analyzer = RecordingAnalyzer(AnalysisName.HOLIDAYS)

    run_analyses(validated, configuration, (analyzer,))

    assert analyzer.calls == [(validated, configuration)]


def test_run_analyses_keeps_availability_order_with_all_six_analyses() -> None:
    validated = validate_bookings(make_submission(full_record()))

    analyses, _ = run_analyses(validated, AppConfiguration())

    assert [a.name for a in analyses] == [a.analysis for a in validated.availability]
    assert len(analyses) == 6


def test_run_analyses_does_not_call_an_analyzer_whose_fields_are_missing() -> None:
    record = BookingRecord(lead_time=5, missing_fields=frozenset({"is_canceled"}))
    validated = validate_bookings(make_submission(record))
    analyzer = RecordingAnalyzer(AnalysisName.CANCELLATIONS)

    analyses, notices = run_analyses(validated, AppConfiguration(), (analyzer,))

    cancellations = next(a for a in analyses if a.name is AnalysisName.CANCELLATIONS)
    assert analyzer.calls == []
    assert cancellations.availability is Availability.UNAVAILABLE
    assert cancellations.findings == {}
    assert "cancellations" not in " ".join(n.message for n in notices)
