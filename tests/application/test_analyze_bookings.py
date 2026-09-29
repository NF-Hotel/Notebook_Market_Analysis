"""Tests for the analyze-bookings use case (UC-001, ADR-0005, US-001.08, US-001.09)."""

from dataclasses import dataclass, field
from pathlib import Path

from hotel_booking_analysis.application.analyze_bookings import (
    AnalyzeBookings,
    AnalyzeOutcome,
    RunStatus,
)
from hotel_booking_analysis.application.configuration import (
    AppConfiguration,
    Environment,
    LoadedConfiguration,
)
from hotel_booking_analysis.application.load_bookings import BookingLoader
from hotel_booking_analysis.domain.errors import (
    ConfigurationError,
    HistoryError,
    HistoryRetentionError,
    HistoryWriteError,
    InputError,
    Notice,
)
from hotel_booking_analysis.domain.history import HistoryReadout, RetentionPolicy
from tests.support import (
    FakeBookingReader,
    FakeConfigurationLoader,
    FakeHistoryReader,
    FakeHistoryWriter,
    FakeSerializer,
    FixedClock,
    RecordingSink,
    SequentialIds,
    full_record,
    make_submission,
)

SAMPLE = Path("sample.csv")


@dataclass
class Harness:
    use_case: AnalyzeBookings
    writer: FakeHistoryWriter
    sink: RecordingSink
    events: list[str] = field(default_factory=list)


class _FailingReader:
    def read(self, location: Path) -> object:
        raise InputError("INPUT_INVALID_JSON", "The input is not valid JSON: x")


def _harness(
    loaded: LoadedConfiguration | InputError | None = None,
    history_error: HistoryError | None = None,
    sink_fails: bool = False,
    reader_error: bool = False,
    readout: HistoryReadout | None = None,
) -> Harness:
    events: list[str] = []
    writer = FakeHistoryWriter(events, history_error)
    sink = RecordingSink(events, sink_fails)
    supplied = FakeBookingReader(make_submission(full_record()))
    loader = BookingLoader(
        _FailingReader() if reader_error else supplied,  # type: ignore[arg-type]
        supplied,
        SAMPLE,
    )
    use_case = AnalyzeBookings(
        configuration_loader=FakeConfigurationLoader(
            loaded or LoadedConfiguration(AppConfiguration())
        ),
        booking_loader=loader,
        serializer=FakeSerializer(),
        history_writer=writer,
        history_reader=FakeHistoryReader(readout),
        sink=sink,
        clock=FixedClock(),
        ids=SequentialIds(),
    )
    return Harness(use_case, writer, sink, events)


def _run(harness: Harness, input_path: Path | None = Path("in.json")) -> AnalyzeOutcome:
    return harness.use_case.run(input_path, None)


def test_run_writes_history_first_then_delivers_the_same_line() -> None:
    harness = _harness()

    outcome = _run(harness)

    assert outcome.status is RunStatus.SUCCEEDED
    assert harness.events == ["history", "sink"]
    assert harness.writer.lines == harness.sink.lines
    assert outcome.serialized == harness.sink.lines[0]
    assert outcome.message is None


def test_run_passes_configured_history_path_and_retention_to_the_history() -> None:
    configuration = AppConfiguration(
        history_path=Path("custom/history.jsonl"), retention=RetentionPolicy(3)
    )
    harness = _harness(LoadedConfiguration(configuration))

    _run(harness)

    assert harness.writer.locations == [Path("custom/history.jsonl")]
    assert harness.writer.retentions == [RetentionPolicy(3)]


def test_run_reports_malformed_history_line_count() -> None:
    outcome = _run(_harness(readout=HistoryReadout((), 2)))

    assert outcome.malformed_history_lines == 2


def test_run_delivers_failed_result_and_leaves_history_untouched_on_input_error() -> None:
    harness = _harness(reader_error=True)

    outcome = _run(harness)

    assert outcome.status is RunStatus.INPUT_FAILED
    assert harness.events == ["sink"]
    assert harness.writer.lines == []
    assert outcome.serialized is not None
    assert '"status":"failed"' in outcome.serialized
    assert outcome.message == "The input is not valid JSON: x"


def test_run_delivers_failed_result_on_configuration_error() -> None:
    harness = _harness(ConfigurationError("'history.retention' is bad.", "history.retention"))

    outcome = _run(harness)

    assert outcome.status is RunStatus.INPUT_FAILED
    assert harness.events == ["sink"]


def test_run_fails_with_input_error_when_no_input_outside_development() -> None:
    harness = _harness()

    outcome = _run(harness, input_path=None)

    assert outcome.status is RunStatus.INPUT_FAILED
    assert harness.writer.lines == []


def test_run_uses_sample_in_development_when_no_input() -> None:
    configuration = AppConfiguration(environment=Environment.DEVELOPMENT)
    harness = _harness(LoadedConfiguration(configuration, (Notice("N", "m"),)))

    outcome = _run(harness, input_path=None)

    assert outcome.status is RunStatus.SUCCEEDED


def test_run_reports_history_failure_and_delivers_nothing() -> None:
    harness = _harness(history_error=HistoryWriteError("disk full"))

    outcome = _run(harness)

    assert outcome.status is RunStatus.HISTORY_FAILED
    assert harness.sink.lines == []
    assert harness.events == ["history"]
    assert outcome.serialized is None
    assert outcome.message is not None
    assert "disk full" in outcome.message
    assert "No result was delivered" in outcome.message


def test_run_reports_retention_failure_as_history_failure_naming_the_saved_result() -> None:
    harness = _harness(history_error=HistoryRetentionError("locked"))

    outcome = _run(harness)

    assert outcome.status is RunStatus.HISTORY_FAILED
    assert harness.sink.lines == []
    assert outcome.message is not None
    assert outcome.result_id in outcome.message
    assert "retention" in outcome.message


def test_run_reports_delivery_failure_naming_result_id_and_keeps_history() -> None:
    harness = _harness(sink_fails=True)

    outcome = _run(harness)

    assert outcome.status is RunStatus.DELIVERY_FAILED
    assert len(harness.writer.lines) == 1
    assert outcome.message is not None
    assert outcome.result_id in outcome.message
    assert "not delivered" in outcome.message
