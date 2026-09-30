"""Tests of the optional AI insights in the analyze-bookings use case (UC-005, ADR-0010)."""

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pytest

from hotel_booking_analysis.adapters.json_result_serializer import JsonResultSerializer
from hotel_booking_analysis.application.analyze_bookings import (
    AnalyzeBookings,
    AnalyzeOutcome,
    RunStatus,
)
from hotel_booking_analysis.application.configuration import AppConfiguration, LoadedConfiguration
from hotel_booking_analysis.application.generate_insights import GenerateInsights
from hotel_booking_analysis.application.load_bookings import BookingLoader
from hotel_booking_analysis.application.ports import LlmProviderRegistry
from hotel_booking_analysis.domain.errors import ConfigurationError
from hotel_booking_analysis.domain.llm import ProviderReason
from tests.insight_fakes import (
    FakeModelProvider,
    FakeRegistry,
    UntouchableRegistry,
    timeout_on_call,
)
from tests.support import (
    FakeBookingReader,
    FakeConfigurationLoader,
    FakeHistoryReader,
    FakeHistoryWriter,
    FixedClock,
    RecordingSink,
    SequentialIds,
    full_record,
    make_submission,
)

SAMPLE = Path("sample.csv")


class _LlmCheckingLoader(FakeConfigurationLoader):
    """Records `with_llm` and rejects the `[llm]` table only when it is read."""

    def __init__(self) -> None:
        super().__init__(LoadedConfiguration(AppConfiguration()))
        self.with_llm_flags: list[bool] = []

    def load(self, explicit_path: Path | None, with_llm: bool = False) -> LoadedConfiguration:
        self.with_llm_flags.append(with_llm)
        if with_llm:
            raise ConfigurationError(
                "The value of llm.temperature must be 0 to 2.", "llm.temperature"
            )
        return super().load(explicit_path, with_llm)


@dataclass
class Harness:
    use_case: AnalyzeBookings
    writer: FakeHistoryWriter
    sink: RecordingSink


def _harness(
    registry: LlmProviderRegistry, loader: FakeConfigurationLoader | None = None
) -> Harness:
    events: list[str] = []
    writer = FakeHistoryWriter(events)
    sink = RecordingSink(events)
    reader = FakeBookingReader(make_submission(full_record()))
    use_case = AnalyzeBookings(
        configuration_loader=loader
        or FakeConfigurationLoader(LoadedConfiguration(AppConfiguration())),
        booking_loader=BookingLoader(reader, reader, SAMPLE),
        serializer=JsonResultSerializer(),
        history_writer=writer,
        history_reader=FakeHistoryReader(),
        sink=sink,
        clock=FixedClock(),
        ids=SequentialIds(),
        insight_generator=GenerateInsights(registry, FixedClock()),
    )
    return Harness(use_case, writer, sink)


def _document(outcome: AnalyzeOutcome) -> dict[str, Any]:  # JSON document
    assert outcome.serialized is not None
    parsed: dict[str, Any] = json.loads(outcome.serialized)
    return parsed


def test_run_without_insights_contacts_no_provider_and_gives_a_version_1_0_result() -> None:
    harness = _harness(UntouchableRegistry())

    outcome = harness.use_case.run(Path("in.json"), None)

    document = _document(outcome)
    assert outcome.status is RunStatus.SUCCEEDED
    assert document["schema_version"] == "1.0"
    assert "insights" not in document
    assert all("insight" not in entry for entry in document["analyses"].values())
    assert outcome.insights_unavailable == 0


def test_run_without_insights_is_identical_to_a_run_without_a_generator() -> None:
    with_generator = _harness(UntouchableRegistry())
    plain = replace(_harness(UntouchableRegistry()).use_case, insight_generator=None)

    first = with_generator.use_case.run(Path("in.json"), None)
    second = plain.run(Path("in.json"), None)

    assert first.serialized == second.serialized


def test_run_with_insights_generates_them_and_the_history_line_is_the_delivered_line() -> None:
    provider = FakeModelProvider()
    harness = _harness(FakeRegistry(provider))

    outcome = harness.use_case.run(Path("in.json"), None, insights=True)

    document = _document(outcome)
    assert outcome.status is RunStatus.SUCCEEDED
    assert document["schema_version"] == "1.1"
    assert document["status"] == "completed"
    assert len(provider.requests) == 6
    assert harness.writer.lines == harness.sink.lines == [outcome.serialized]


def test_run_without_insights_does_not_read_the_llm_configuration() -> None:
    loader = _LlmCheckingLoader()

    _harness(UntouchableRegistry(), loader).use_case.run(Path("in.json"), None)

    assert loader.with_llm_flags == [False]


def test_run_with_insights_and_invalid_llm_configuration_fails_naming_the_key() -> None:
    loader = _LlmCheckingLoader()
    harness = _harness(UntouchableRegistry(), loader)

    outcome = harness.use_case.run(Path("in.json"), None, insights=True)

    document = _document(outcome)
    assert loader.with_llm_flags == [True]
    assert outcome.status is RunStatus.INPUT_FAILED
    assert document["status"] == "failed"
    assert document["schema_version"] == "1.0"
    assert "llm.temperature" in document["error"]["message"]
    assert "insights" not in document
    assert harness.writer.lines == []


@pytest.mark.parametrize(
    "provider",
    [
        FakeModelProvider(reason=ProviderReason.CONNECTION_REFUSED),
        FakeModelProvider(respond=timeout_on_call(1, 2, 3, 4, 5, 6)),
    ],
    ids=["unreachable", "timeouts"],
)
def test_run_with_unavailable_insights_still_succeeds_with_warnings_and_exit_status_ok(
    provider: FakeModelProvider,
) -> None:
    harness = _harness(FakeRegistry(provider))

    outcome = harness.use_case.run(Path("in.json"), None, insights=True)

    document = _document(outcome)
    assert outcome.status is RunStatus.SUCCEEDED
    assert outcome.message is None
    assert document["status"] == "completed_with_warnings"
    assert document["schema_version"] == "1.1"
    assert document["notices"][-1]["code"] == "INSIGHTS_UNAVAILABLE"
    assert outcome.insights_unavailable == 6
    assert harness.writer.lines == [outcome.serialized]
    assert harness.sink.lines == [outcome.serialized]


def test_run_with_insights_and_one_failure_keeps_the_other_insights_and_counts_one() -> None:
    harness = _harness(FakeRegistry(FakeModelProvider(respond=timeout_on_call(3))))

    outcome = harness.use_case.run(Path("in.json"), None, insights=True)

    statuses = [e["insight"]["status"] for e in _document(outcome)["analyses"].values()]
    assert statuses.count("available") == 5
    assert statuses[2] == "unavailable"
    assert outcome.insights_unavailable == 1
