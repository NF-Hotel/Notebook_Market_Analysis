"""Analyze-bookings use case (UC-001, ADR-0005, ADR-0006, US-001.08, US-001.09).

Order of a run: configuration, load, validate, build the result, serialize it once, append to
the history and apply retention, and only then hand the same serialized line to the caller.
Success is reported only after both the history write and the hand-over completed. When AI
insights are requested (UC-005, ADR-0010) they are generated after the analyses and before the
result is serialized, so the history line is the delivered line; their failure never changes
the outcome.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path

from hotel_booking_analysis.application.build_result import (
    assemble_result,
    build_failed_result,
    build_result,
)
from hotel_booking_analysis.application.configuration import AppConfiguration
from hotel_booking_analysis.application.generate_insights import GenerateInsights
from hotel_booking_analysis.application.load_bookings import BookingLoader
from hotel_booking_analysis.application.placeholder_analyses import run_analyses
from hotel_booking_analysis.application.ports import (
    Analyzer,
    Clock,
    ConfigurationLoader,
    HistoryReader,
    HistoryWriter,
    ResultIdGenerator,
    ResultSerializer,
    ResultSink,
)
from hotel_booking_analysis.application.validate_bookings import (
    ValidatedBookings,
    validate_bookings,
)
from hotel_booking_analysis.domain.errors import (
    HistoryError,
    HistoryRetentionError,
    InputError,
    Notice,
    ResultDeliveryError,
)
from hotel_booking_analysis.domain.result import AnalysisResult


class RunStatus(StrEnum):
    """How a run ended (ADR-0005 outcomes)."""

    SUCCEEDED = "succeeded"
    INPUT_FAILED = "input_failed"
    HISTORY_FAILED = "history_failed"
    DELIVERY_FAILED = "delivery_failed"


@dataclass(frozen=True, slots=True)
class AnalyzeOutcome:
    """What a run produced.

    `serialized` is the exact line written to the history and handed to the caller; it is None
    when the history step failed and no result was delivered. `message` describes a failure and
    is never set on success. `malformed_history_lines` is None when it is unknown.
    `insights_unavailable` counts the analyses whose AI insight could not be produced.
    """

    status: RunStatus
    result_id: str
    serialized: str | None = None
    message: str | None = None
    malformed_history_lines: int | None = None
    insights_unavailable: int = 0


@dataclass(frozen=True, slots=True)
class AnalyzeBookings:
    """Runs one analysis end to end (UC-001 main scenario and extensions)."""

    configuration_loader: ConfigurationLoader
    booking_loader: BookingLoader
    serializer: ResultSerializer
    history_writer: HistoryWriter
    history_reader: HistoryReader
    sink: ResultSink
    clock: Clock
    ids: ResultIdGenerator
    analyzers: tuple[Analyzer, ...] = ()
    insight_generator: GenerateInsights | None = None

    def run(
        self, input_path: Path | None, config_path: Path | None, insights: bool = False
    ) -> AnalyzeOutcome:
        """Analyze the input; with `insights` also ask a language model about each analysis."""
        try:
            loaded = self.configuration_loader.load(config_path, with_llm=insights)
        except InputError as error:
            return self._deliver_failure(error, ())
        configuration = loaded.configuration
        try:
            submission = self.booking_loader.load(input_path, configuration.environment)
            validated = validate_bookings(submission)
        except InputError as error:
            return self._deliver_failure(error, loaded.notices)
        if insights:
            result = self._assemble_with_insights(
                validated, loaded.notices, self.ids.new_id(), self.clock.now(), configuration
            )
        else:
            result = build_result(
                validated,
                loaded.notices,
                self.ids.new_id(),
                self.clock.now(),
                configuration,
                self.analyzers,
            )
        return self._store_and_deliver(result, configuration)

    def _assemble_with_insights(
        self,
        validated: ValidatedBookings,
        notices: tuple[Notice, ...],
        result_id: str,
        generated_at: datetime,
        configuration: AppConfiguration,
    ) -> AnalysisResult:
        analyses, analysis_notices = run_analyses(validated, configuration, self.analyzers)
        generator = self.insight_generator
        batch = None
        if generator is not None:
            batch = generator.generate(analyses, validated.summary, configuration)
        return assemble_result(
            validated, notices, result_id, generated_at, analyses, analysis_notices, batch
        )

    def _store_and_deliver(
        self, result: AnalysisResult, configuration: AppConfiguration
    ) -> AnalyzeOutcome:
        line = self.serializer.serialize(result)
        try:
            self.history_writer.append(configuration.history_path, line, configuration.retention)
        except HistoryError as error:
            return self._history_failure(result, error)
        try:
            self.sink.write(line)
        except ResultDeliveryError as error:
            return AnalyzeOutcome(
                RunStatus.DELIVERY_FAILED,
                result.result_id,
                line,
                f"Result {result.result_id} was saved to the history but could not be "
                f"written to standard output, so it was not delivered: {error}",
                self._malformed_lines(configuration),
            )
        return AnalyzeOutcome(
            RunStatus.SUCCEEDED,
            result.result_id,
            line,
            malformed_history_lines=self._malformed_lines(configuration),
            insights_unavailable=result.unavailable_insight_count(),
        )

    @staticmethod
    def _history_failure(result: AnalysisResult, error: HistoryError) -> AnalyzeOutcome:
        if isinstance(error, HistoryRetentionError):
            detail = (
                f"Result {result.result_id} was appended to the history but retention "
                f"failed: {error}"
            )
        else:
            detail = f"The history was not updated: {error}"
        return AnalyzeOutcome(
            RunStatus.HISTORY_FAILED,
            result.result_id,
            message=f"{detail} No result was delivered.",
        )

    def _deliver_failure(self, error: InputError, notices: tuple[Notice, ...]) -> AnalyzeOutcome:
        result = build_failed_result(error, notices, self.ids.new_id(), self.clock.now())
        line = self.serializer.serialize(result)
        try:
            self.sink.write(line)
        except ResultDeliveryError as delivery_error:
            return AnalyzeOutcome(
                RunStatus.DELIVERY_FAILED,
                result.result_id,
                message=f"Failed result {result.result_id} ({error.code}: {error.message}) "
                f"could not be written to standard output; it was not stored: {delivery_error}",
            )
        return AnalyzeOutcome(RunStatus.INPUT_FAILED, result.result_id, line, error.message)

    def _malformed_lines(self, configuration: AppConfiguration) -> int | None:
        try:
            return self.history_reader.read(configuration.history_path).malformed_line_count
        except HistoryError:
            return None
