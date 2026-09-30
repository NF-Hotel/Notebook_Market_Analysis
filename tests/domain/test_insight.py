"""Tests of the AI insight values (DCD-001 domain part 1, ADR-0010 status and reason codes)."""

from datetime import UTC, datetime

from hotel_booking_analysis.domain.errors import InsightRejectedError, LlmError, LlmTimeoutError
from hotel_booking_analysis.domain.insight import (
    AI_LABEL,
    AiInsight,
    ExecutiveSummary,
    ImprovementSuggestion,
    InsightReason,
    InsightsMetadata,
    InsightStatus,
)

MOMENT = datetime(2026, 9, 30, 9, 0, tzinfo=UTC)
SUGGESTION = ImprovementSuggestion("It may help.", "1 of 2.", 2)


def test_status_and_reason_codes_are_pinned() -> None:
    assert [s.value for s in InsightStatus] == ["available", "unavailable", "not_applicable"]
    assert [r.value for r in InsightReason] == [
        "NO_PROVIDER",
        "NO_MODEL",
        "TIMEOUT",
        "MODEL_ERROR",
        "BAD_STRUCTURE",
        "GUARDRAIL_REJECTED",
    ]
    assert AI_LABEL == "AI-generated"


def test_available_insight_carries_text_provider_model_time_and_the_label() -> None:
    insight = AiInsight.available(
        "ollama", "llama3", MOMENT, ExecutiveSummary("Summary."), (SUGGESTION,)
    )

    assert insight.status is InsightStatus.AVAILABLE
    assert insight.reason is None
    assert (insight.provider, insight.model, insight.generated_at) == ("ollama", "llama3", MOMENT)
    assert insight.executive_summary == ExecutiveSummary("Summary.")
    assert insight.improvement_suggestions == (SUGGESTION,)
    assert insight.label() == "AI-generated"
    assert not insight.is_unavailable()


def test_unavailable_insight_has_a_reason_and_no_text_and_no_label() -> None:
    insight = AiInsight.unavailable(InsightReason.TIMEOUT, "lmstudio", "phi")

    assert insight.status is InsightStatus.UNAVAILABLE
    assert insight.reason is InsightReason.TIMEOUT
    assert (insight.provider, insight.model) == ("lmstudio", "phi")
    assert insight.generated_at is None
    assert insight.executive_summary is None
    assert insight.improvement_suggestions == ()
    assert insight.label() is None
    assert insight.is_unavailable()


def test_unavailable_insight_without_a_selected_model_has_no_provider_or_model() -> None:
    insight = AiInsight.unavailable(InsightReason.NO_PROVIDER)

    assert (insight.provider, insight.model) == (None, None)


def test_not_applicable_insight_has_nothing_and_is_not_unavailable() -> None:
    insight = AiInsight.not_applicable()

    assert insight.status is InsightStatus.NOT_APPLICABLE
    assert insight.reason is None
    assert (insight.provider, insight.model, insight.generated_at) == (None, None, None)
    assert insight.executive_summary is None
    assert insight.improvement_suggestions == ()
    assert insight.label() is None
    assert not insight.is_unavailable()


def test_insights_metadata_holds_the_result_level_values() -> None:
    metadata = InsightsMetadata(True, None, None, "1")

    assert (metadata.requested, metadata.provider, metadata.model) == (True, None, None)
    assert metadata.prompt_version == "1"


def test_rejection_error_carries_the_reason_and_detail() -> None:
    error = InsightRejectedError(InsightReason.BAD_STRUCTURE, "The answer is not valid JSON.")

    assert error.reason is InsightReason.BAD_STRUCTURE
    assert error.detail == "The answer is not valid JSON."
    assert str(error) == error.detail


def test_a_timeout_is_a_kind_of_llm_error() -> None:
    assert issubclass(LlmTimeoutError, LlmError)
    assert not issubclass(LlmError, LlmTimeoutError)
