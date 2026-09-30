"""Fakes of the language model ports and the schema validator for the insight tests (MIL-011)."""

import json
from collections.abc import Callable
from datetime import UTC, datetime

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from hotel_booking_analysis.adapters.json_result_serializer import (
    load_result_schema,
    load_result_schema_1_1,
)
from hotel_booking_analysis.application.build_result import assemble_result
from hotel_booking_analysis.application.configuration import AppConfiguration, LlmConfiguration
from hotel_booking_analysis.application.generate_insights import GenerateInsights
from hotel_booking_analysis.application.placeholder_analyses import run_analyses
from hotel_booking_analysis.application.ports import LlmProvider
from hotel_booking_analysis.application.validate_bookings import ValidatedBookings
from hotel_booking_analysis.domain.errors import LlmError, LlmTimeoutError
from hotel_booking_analysis.domain.insight_prompt import InsightPrompt
from hotel_booking_analysis.domain.insight_validation import sample_sizes
from hotel_booking_analysis.domain.llm import (
    LanguageModelProvider,
    ProviderName,
    ProviderReason,
    ProviderStatus,
)
from hotel_booking_analysis.domain.result import AnalysisResult
from tests.support import FixedClock

Responder = Callable[[InsightPrompt], str]


def valid_answer(prompt: InsightPrompt) -> str:
    """A deterministic answer that passes the validator for `prompt`.

    Its sample size is the largest one in the prompt's findings, so it always matches.
    """
    size = max(sample_sizes(json.loads(prompt.data_json)))
    return json.dumps(
        {
            "executive_summary": "The findings describe the observed data only.",
            "improvement_suggestions": [
                {
                    "suggestion": "Consider testing a change that may help; it is a hypothesis.",
                    "evidence": f"Observed in {size} records; treat a small sample with care.",
                    "sample_size": size,
                }
            ],
        }
    )


def raising(error: Exception) -> Responder:
    def respond(prompt: InsightPrompt) -> str:
        raise error

    return respond


def answering(text: str) -> Responder:
    def respond(prompt: InsightPrompt) -> str:
        return text

    return respond


class FakeModelProvider:
    """A provider that lists fixed models and answers each request with `respond`.

    `requests` records the model, prompt, temperature and deadline of every request.
    """

    def __init__(
        self,
        name: ProviderName = ProviderName.OLLAMA,
        models: tuple[str, ...] = ("m1",),
        reason: ProviderReason | None = None,
        respond: Responder = valid_answer,
    ) -> None:
        self._provider = LanguageModelProvider(name, f"http://localhost/{name.value}")
        self._models = models
        self._reason = reason
        self._respond = respond
        self.requests: list[tuple[str, InsightPrompt, float, float]] = []
        self.listed = 0

    def provider(self) -> LanguageModelProvider:
        return self._provider

    def list_models(self, timeout_seconds: float) -> ProviderStatus:
        self.listed += 1
        if self._reason is not None:
            return ProviderStatus.unreachable_because(self._provider, self._reason)
        return ProviderStatus.reachable_with(self._provider, self._models)

    def generate(
        self, model: str, prompt: InsightPrompt, temperature: float, timeout_seconds: float
    ) -> str:
        self.requests.append((model, prompt, temperature, timeout_seconds))
        return self._respond(prompt)


class FakeRegistry:
    """Supplies fixed providers and records the configurations it was asked about."""

    def __init__(self, *providers: LlmProvider) -> None:
        self._providers = providers
        self.configurations: list[LlmConfiguration] = []

    def providers(self, configuration: LlmConfiguration) -> tuple[LlmProvider, ...]:
        self.configurations.append(configuration)
        return self._providers


class UntouchableRegistry:
    """A registry that fails the test when anything asks it for a provider."""

    def providers(self, configuration: LlmConfiguration) -> tuple[LlmProvider, ...]:
        raise AssertionError("No provider may be contacted when insights are not requested.")


def failing_on_call(numbers: set[int], error: LlmError) -> Responder:
    """A responder that raises `error` on the given request numbers (from 1), else answers."""
    counter = {"calls": 0}

    def respond(prompt: InsightPrompt) -> str:
        counter["calls"] += 1
        if counter["calls"] in numbers:
            raise error
        return valid_answer(prompt)

    return respond


def timeout_on_call(*numbers: int) -> Responder:
    return failing_on_call(set(numbers), LlmTimeoutError("too slow"))


def result_1_1_validator() -> Draft202012Validator:
    """A validator of result 1.1 that can resolve the reference to the 1.0 schema."""
    old = load_result_schema()
    registry: Registry[object] = Registry().with_resource(
        old["$id"], Resource.from_contents(old, DRAFT202012)
    )
    return Draft202012Validator(load_result_schema_1_1(), registry=registry)


MOMENT = datetime(2026, 9, 29, 12, 0, 1, 250000, tzinfo=UTC)
RESULT_ID = "00000000-0000-0000-0000-000000000001"


def insight_result(
    validated: ValidatedBookings,
    *providers: FakeModelProvider,
    llm: LlmConfiguration | None = None,
) -> AnalysisResult:
    """A result with insights generated by `providers` for the placeholder analyses."""
    configuration = AppConfiguration(llm=llm or LlmConfiguration())
    analyses, notices = run_analyses(validated, configuration, ())
    batch = GenerateInsights(FakeRegistry(*providers), FixedClock()).generate(
        analyses, validated.summary, configuration
    )
    return assemble_result(validated, (), RESULT_ID, MOMENT, analyses, notices, batch)
