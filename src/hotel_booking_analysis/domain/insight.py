"""The AI insight of one analysis and its result-level data (UC-005, ADR-0010, ADR-0011).

An `AiInsight` holds no reference to its analysis; the analysis holds the insight.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

AI_LABEL = "AI-generated"
"""The label of every available insight (ADR-0010 "Label", ADR-0011 `insight.label`)."""


class InsightStatus(StrEnum):
    """The one state an insight ends in (ADR-0010 "Failure semantics")."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    NOT_APPLICABLE = "not_applicable"


class InsightReason(StrEnum):
    """Why an insight is unavailable (ADR-0010, ADR-0011 `insight.reason`)."""

    NO_PROVIDER = "NO_PROVIDER"
    NO_MODEL = "NO_MODEL"
    TIMEOUT = "TIMEOUT"
    MODEL_ERROR = "MODEL_ERROR"
    BAD_STRUCTURE = "BAD_STRUCTURE"
    GUARDRAIL_REJECTED = "GUARDRAIL_REJECTED"


@dataclass(frozen=True, slots=True)
class ExecutiveSummary:
    """The accepted summary text of an insight (at most 600 characters)."""

    text: str


@dataclass(frozen=True, slots=True)
class ImprovementSuggestion:
    """One accepted hypothesis with the evidence and the sample size it rests on."""

    suggestion: str
    evidence: str
    sample_size: int


@dataclass(frozen=True, slots=True)
class AiInsight:
    """The insight of one analysis: available, unavailable with a reason, or not applicable.

    Text of a rejected or failed answer is never held. Build it with `available`,
    `unavailable` or `not_applicable`.
    """

    status: InsightStatus
    reason: InsightReason | None = None
    provider: str | None = None
    model: str | None = None
    generated_at: datetime | None = None
    executive_summary: ExecutiveSummary | None = None
    improvement_suggestions: tuple[ImprovementSuggestion, ...] = ()

    @classmethod
    def available(
        cls,
        provider: str,
        model: str,
        generated_at: datetime,
        summary: ExecutiveSummary,
        suggestions: tuple[ImprovementSuggestion, ...],
    ) -> "AiInsight":
        """An insight whose answer passed the validator."""
        return cls(
            InsightStatus.AVAILABLE,
            None,
            provider,
            model,
            generated_at,
            summary,
            suggestions,
        )

    @classmethod
    def unavailable(
        cls, reason: InsightReason, provider: str | None = None, model: str | None = None
    ) -> "AiInsight":
        """An insight that failed for `reason`; provider and model are those tried, if any."""
        return cls(InsightStatus.UNAVAILABLE, reason, provider, model)

    @classmethod
    def not_applicable(cls) -> "AiInsight":
        """The insight of an analysis that is itself unavailable; nothing was requested."""
        return cls(InsightStatus.NOT_APPLICABLE)

    def is_unavailable(self) -> bool:
        return self.status is InsightStatus.UNAVAILABLE

    def label(self) -> str | None:
        """`AI-generated` for an available insight, else None."""
        return AI_LABEL if self.status is InsightStatus.AVAILABLE else None


@dataclass(frozen=True, slots=True)
class InsightsMetadata:
    """The result-level `insights` object of result 1.1 (ADR-0011).

    `provider` and `model` are the selected ones, or None when none could be selected.
    """

    requested: bool
    provider: str | None
    model: str | None
    prompt_version: str
