"""Tests of the insight generator with fake providers (UC-005, ADR-0009, ADR-0010)."""

import json

import pytest

from hotel_booking_analysis.application.configuration import AppConfiguration, LlmConfiguration
from hotel_booking_analysis.application.generate_insights import GenerateInsights, InsightBatch
from hotel_booking_analysis.domain.analysis import Analysis, AnalysisName, Availability
from hotel_booking_analysis.domain.errors import LlmError
from hotel_booking_analysis.domain.insight import InsightReason, InsightStatus
from hotel_booking_analysis.domain.insight_prompt import PROMPT_VERSION
from hotel_booking_analysis.domain.llm import ProviderName, ProviderReason
from tests.insight_fakes import (
    FakeModelProvider,
    FakeRegistry,
    answering,
    failing_on_call,
    raising,
    timeout_on_call,
)
from tests.insight_samples import find_leaks, sample_analyses, sample_validated
from tests.support import FixedClock

SUMMARY = sample_validated().summary
ANALYSES = tuple(sample_analyses().values())
NAMES = list(AnalysisName)


def _generate(
    *providers: FakeModelProvider,
    analyses: tuple[Analysis, ...] = ANALYSES,
    llm: LlmConfiguration | None = None,
) -> InsightBatch:
    registry = FakeRegistry(*providers)
    configuration = AppConfiguration(llm=llm or LlmConfiguration())
    return GenerateInsights(registry, FixedClock()).generate(analyses, SUMMARY, configuration)


def _reasons(batch: InsightBatch) -> list[InsightReason | None]:
    return [batch.insights[name].reason for name in NAMES]


def test_generate_gives_all_six_analyses_an_available_insight_with_the_model_and_provider() -> None:
    ollama = FakeModelProvider(ProviderName.OLLAMA, ("m1",))

    batch = _generate(ollama)

    assert list(batch.insights) == NAMES
    for insight in batch.insights.values():
        assert insight.status is InsightStatus.AVAILABLE
        assert insight.provider == "ollama"
        assert insight.model == "m1"
        assert insight.generated_at == FixedClock().now()
        assert insight.label() == "AI-generated"
        assert insight.executive_summary is not None
        assert len(insight.improvement_suggestions) == 1
    assert batch.unavailable_count() == 0
    assert batch.metadata.requested is True
    assert (batch.metadata.provider, batch.metadata.model) == ("ollama", "m1")
    assert batch.metadata.prompt_version == PROMPT_VERSION


def test_generate_sends_one_sequential_request_per_analysis_with_the_configured_values() -> None:
    provider = FakeModelProvider()
    llm = LlmConfiguration(temperature=0.5, generation_timeout_seconds=7.0)

    _generate(provider, llm=llm)

    asked = [json.loads(prompt.data_json)["analysis"] for _, prompt, _, _ in provider.requests]
    assert asked == [name.value for name in NAMES]
    settings = {
        (model, temperature, timeout) for model, _, temperature, timeout in provider.requests
    }
    assert settings == {("m1", 0.5, 7.0)}


def test_generate_discovers_the_providers_once_with_the_discovery_timeout() -> None:
    first = FakeModelProvider(ProviderName.OLLAMA)
    second = FakeModelProvider(ProviderName.LMSTUDIO)
    registry = FakeRegistry(first, second)
    llm = LlmConfiguration(discovery_timeout_seconds=1.5)

    GenerateInsights(registry, FixedClock()).generate(ANALYSES, SUMMARY, AppConfiguration(llm=llm))

    assert (first.listed, second.listed) == (1, 1)
    assert registry.configurations == [llm]
    assert len(first.requests) == 6
    assert second.requests == []


def test_generate_prompts_contain_no_raw_booking_data() -> None:
    provider = FakeModelProvider()

    _generate(provider)

    allowed = frozenset(
        d.isoformat()
        for d in (
            SUMMARY.earliest_booking_date,
            SUMMARY.latest_booking_date,
            SUMMARY.earliest_arrival_date,
            SUMMARY.latest_arrival_date,
        )
        if d is not None
    )
    assert len(provider.requests) == 6
    for _, prompt, _, _ in provider.requests:
        assert find_leaks(prompt, ("MARKER",), allowed) == []


def test_generate_without_a_reachable_provider_marks_every_analysis_no_provider() -> None:
    down = FakeModelProvider(reason=ProviderReason.CONNECTION_REFUSED)

    batch = _generate(down)

    assert _reasons(batch) == [InsightReason.NO_PROVIDER] * 6
    assert all(i.status is InsightStatus.UNAVAILABLE for i in batch.insights.values())
    assert all(i.provider is None and i.model is None for i in batch.insights.values())
    assert down.requests == []
    assert batch.unavailable_count() == 6
    assert (batch.metadata.provider, batch.metadata.model) == (None, None)
    assert batch.metadata.requested is True


def test_generate_with_no_provider_at_all_marks_every_analysis_no_provider() -> None:
    assert _reasons(_generate()) == [InsightReason.NO_PROVIDER] * 6


def test_generate_without_a_model_marks_every_analysis_no_model_and_contacts_no_model() -> None:
    empty = FakeModelProvider(models=())
    named = FakeModelProvider(ProviderName.LMSTUDIO, models=("other",))

    listed = _generate(empty, llm=LlmConfiguration(provider=ProviderName.OLLAMA))
    missing = _generate(named, llm=LlmConfiguration(model="wanted"))

    assert _reasons(listed) == [InsightReason.NO_MODEL] * 6
    assert _reasons(missing) == [InsightReason.NO_MODEL] * 6
    assert empty.requests == [] and named.requests == []


def test_generate_uses_the_configured_model_of_the_configured_provider() -> None:
    ollama = FakeModelProvider(ProviderName.OLLAMA, ("a",))
    lmstudio = FakeModelProvider(ProviderName.LMSTUDIO, ("b", "c"))

    batch = _generate(ollama, lmstudio, llm=LlmConfiguration(model="c"))

    assert ollama.requests == []
    assert {request[0] for request in lmstudio.requests} == {"c"}
    assert (batch.metadata.provider, batch.metadata.model) == ("lmstudio", "c")


def test_generate_timeout_of_one_analysis_leaves_the_next_ones_tried() -> None:
    provider = FakeModelProvider(respond=timeout_on_call(2))

    batch = _generate(provider)

    assert _reasons(batch) == [
        None,
        InsightReason.TIMEOUT,
        None,
        None,
        None,
        None,
    ]
    assert len(provider.requests) == 6
    failed = batch.insights[NAMES[1]]
    assert (failed.provider, failed.model) == ("ollama", "m1")
    assert failed.executive_summary is None
    assert failed.improvement_suggestions == ()
    assert batch.unavailable_count() == 1


def test_generate_model_error_is_reported_as_model_error() -> None:
    provider = FakeModelProvider(respond=failing_on_call({1, 6}, LlmError("HTTP 500")))

    batch = _generate(provider)

    assert _reasons(batch)[0] is InsightReason.MODEL_ERROR
    assert _reasons(batch)[5] is InsightReason.MODEL_ERROR
    assert batch.unavailable_count() == 2


@pytest.mark.parametrize(
    ("answer", "reason"),
    [
        ("not json at all", InsightReason.BAD_STRUCTURE),
        ('{"executive_summary": "x"}', InsightReason.BAD_STRUCTURE),
        (
            '{"executive_summary":"Cancellations are due to price.","improvement_suggestions":'
            '[{"suggestion":"It may help.","evidence":"a small sample","sample_size":1}]}',
            InsightReason.GUARDRAIL_REJECTED,
        ),
    ],
)
def test_generate_rejected_answer_is_unavailable_and_its_text_is_never_kept(
    answer: str, reason: InsightReason
) -> None:
    provider = FakeModelProvider(respond=answering(answer))

    batch = _generate(provider)

    assert _reasons(batch) == [reason] * 6
    for insight in batch.insights.values():
        assert insight.executive_summary is None
        assert insight.improvement_suggestions == ()
        assert insight.generated_at is None
        assert insight.label() is None
    assert len(provider.requests) == 6


def test_generate_never_retries_a_failed_request() -> None:
    provider = FakeModelProvider(respond=raising(LlmError("down")))

    batch = _generate(provider)

    assert len(provider.requests) == 6
    assert batch.unavailable_count() == 6


def test_generate_unavailable_analysis_is_not_applicable_and_no_request_is_sent() -> None:
    unavailable = Analysis(AnalysisName.LEAD_TIME, Availability.UNAVAILABLE, "lead_time missing")
    analyses = (unavailable, *ANALYSES[1:])
    provider = FakeModelProvider()

    batch = _generate(provider, analyses=analyses)

    insight = batch.insights[AnalysisName.LEAD_TIME]
    assert insight.status is InsightStatus.NOT_APPLICABLE
    assert (insight.reason, insight.provider, insight.model) == (None, None, None)
    assert len(provider.requests) == 5
    assert batch.unavailable_count() == 0


def test_generate_unavailable_analysis_stays_not_applicable_when_no_provider_is_reachable() -> None:
    unavailable = Analysis(AnalysisName.LEAD_TIME, Availability.UNAVAILABLE, "lead_time missing")

    batch = _generate(analyses=(unavailable, *ANALYSES[1:]))

    assert batch.insights[AnalysisName.LEAD_TIME].status is InsightStatus.NOT_APPLICABLE
    assert batch.unavailable_count() == 5


def test_batch_insight_for_returns_none_for_an_unknown_analysis() -> None:
    batch = _generate(FakeModelProvider(), analyses=ANALYSES[:1])

    assert batch.insight_for(AnalysisName.LEAD_TIME) is batch.insights[AnalysisName.LEAD_TIME]
    assert batch.insight_for(AnalysisName.GUEST_MIX) is None
