"""Generate-insights use case step (UC-005, ADR-0009, ADR-0010).

One model is chosen once for the run and asked one analysis after the other. A failure of one
analysis, of the model or of the choice of a model never stops the run and never reaches the
caller: it becomes an unavailable insight with its reason. Nothing is retried, and the text of a
rejected or failed answer is never kept.
"""

import logging
from collections.abc import Mapping
from dataclasses import dataclass

from hotel_booking_analysis.application.configuration import AppConfiguration
from hotel_booking_analysis.application.ports import Clock, LlmProvider, LlmProviderRegistry
from hotel_booking_analysis.application.provider_discovery import (
    discover_providers,
    find_provider,
)
from hotel_booking_analysis.domain.analysis import Analysis, AnalysisName, Availability
from hotel_booking_analysis.domain.errors import (
    InsightRejectedError,
    LlmError,
    LlmTimeoutError,
)
from hotel_booking_analysis.domain.insight import (
    AiInsight,
    InsightReason,
    InsightsMetadata,
)
from hotel_booking_analysis.domain.insight_prompt import PROMPT_VERSION, build_prompt
from hotel_booking_analysis.domain.insight_validation import validate_answer
from hotel_booking_analysis.domain.model_selection import ModelSelection, select_model
from hotel_booking_analysis.domain.quality import DataQualitySummary

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class InsightBatch:
    """The insights of one run by analysis name, with the result-level `insights` metadata."""

    metadata: InsightsMetadata
    insights: Mapping[AnalysisName, AiInsight]

    def insight_for(self, name: AnalysisName) -> AiInsight | None:
        return self.insights.get(name)

    def unavailable_count(self) -> int:
        """How many insights could not be produced (not-applicable ones are not counted)."""
        return sum(1 for insight in self.insights.values() if insight.is_unavailable())


@dataclass(frozen=True, slots=True)
class GenerateInsights:
    """Creates one insight per analysis; never raises to the caller (UC-005)."""

    registry: LlmProviderRegistry
    clock: Clock

    def generate(
        self,
        analyses: tuple[Analysis, ...],
        summary: DataQualitySummary,
        configuration: AppConfiguration,
    ) -> InsightBatch:
        """Ask the selected model about every available analysis, one request at a time."""
        llm = configuration.llm
        providers = self.registry.providers(llm)
        statuses = discover_providers(providers, llm.discovery_timeout_seconds)
        selection = select_model(statuses, llm.provider, llm.model)
        provider = find_provider(providers, selection.provider) if selection.provider else None
        insights = {
            analysis.name: self._insight_for(analysis, summary, selection, provider, configuration)
            for analysis in analyses
        }
        metadata = InsightsMetadata(
            requested=True,
            provider=selection.provider.value if selection.provider else None,
            model=selection.model,
            prompt_version=PROMPT_VERSION,
        )
        return InsightBatch(metadata, insights)

    def _insight_for(
        self,
        analysis: Analysis,
        summary: DataQualitySummary,
        selection: ModelSelection,
        provider: LlmProvider | None,
        configuration: AppConfiguration,
    ) -> AiInsight:
        if analysis.availability is not Availability.AVAILABLE:
            return AiInsight.not_applicable()
        if provider is None or selection.provider is None or selection.model is None:
            return AiInsight.unavailable(selection.reason or InsightReason.NO_PROVIDER)
        prompt = build_prompt(analysis, summary)
        name, model = selection.provider.value, selection.model
        try:
            answer = provider.generate(
                model,
                prompt,
                configuration.llm.temperature,
                configuration.llm.generation_timeout_seconds,
            )
            text, suggestions = validate_answer(answer, prompt, configuration.min_group_size)
        except LlmTimeoutError:
            return self._failed(analysis, InsightReason.TIMEOUT, name, model)
        except LlmError:
            return self._failed(analysis, InsightReason.MODEL_ERROR, name, model)
        except InsightRejectedError as rejected:
            return self._failed(analysis, rejected.reason, name, model, rejected.detail)
        return AiInsight.available(name, model, self.clock.now(), text, suggestions)

    @staticmethod
    def _failed(
        analysis: Analysis,
        reason: InsightReason,
        provider: str,
        model: str,
        detail: str = "",
    ) -> AiInsight:
        _LOGGER.info("No insight for %s: %s %s", analysis.name.value, reason.value, detail)
        return AiInsight.unavailable(reason, provider, model)
