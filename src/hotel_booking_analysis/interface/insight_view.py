"""View model of the AI insight of one analysis (UC-002, UC-005, ADR-0010, ADR-0011).

Pure functions from a parsed result to a view model and lines; no marimo. A result saved without
insights (1.0, or 1.1 without the `insight` object) is a state of the view, not an error. The
text of the model is carried as data; the renderer shows it as plain text, never as markup.
"""

from dataclasses import dataclass

from hotel_booking_analysis.domain.analysis import JsonValue
from hotel_booking_analysis.domain.insight import AI_LABEL, InsightReason, InsightStatus
from hotel_booking_analysis.interface.figures import Row, count_text
from hotel_booking_analysis.interface.json_access import (
    Result,
    as_int,
    as_list,
    as_mapping,
    as_text,
)

STATE_AVAILABLE = InsightStatus.AVAILABLE.value
STATE_UNAVAILABLE = InsightStatus.UNAVAILABLE.value
STATE_NOT_APPLICABLE = InsightStatus.NOT_APPLICABLE.value
STATE_SAVED_WITHOUT = "saved without insights"

HYPOTHESIS_STATEMENT = (
    "AI-generated text is a hypothesis to check against the findings and their record counts, "
    "not a forecast, a cause or a promise of earnings. It can be wrong even when the figures it "
    "quotes are correct."
)
SAVED_WITHOUT_MESSAGE = (
    "This result was saved without AI insights (they were not requested). "
    "The findings are shown as saved."
)
NOT_APPLICABLE_MESSAGE = "No AI insight: this analysis is not available in the result."
UNKNOWN_REASON_MESSAGE = "The reason for the missing AI insight is not recognised by this viewer."
NO_REASON_MESSAGE = "No reason was recorded for the missing AI insight."

_REASON_TEXTS: dict[str, str] = {
    InsightReason.NO_PROVIDER.value: (
        "No language model provider could be reached when the analysis ran."
    ),
    InsightReason.NO_MODEL.value: (
        "A provider was reachable, but it offered no model that could be used."
    ),
    InsightReason.TIMEOUT.value: "The language model did not answer within the time allowed.",
    InsightReason.MODEL_ERROR.value: "The language model or its provider reported an error.",
    InsightReason.BAD_STRUCTURE.value: (
        "The answer of the language model did not have the required structure and was discarded."
    ),
    InsightReason.GUARDRAIL_REJECTED.value: (
        "The answer of the language model broke a wording or figure rule and was discarded."
    ),
}


@dataclass(frozen=True, slots=True)
class SuggestionView:
    """One AI suggestion with the evidence text and the sample size it rests on."""

    suggestion: str
    evidence: str
    sample_size: int | None


@dataclass(frozen=True, slots=True)
class InsightView:
    """What the notebook shows for the insight of `analysis`.

    `state` is `available`, `unavailable`, `not_applicable` or `saved without insights`; the
    label, provider, model, summary and suggestions are set only for an available insight.
    """

    analysis: str
    state: str
    reason: str | None = None
    reason_text: str | None = None
    label: str | None = None
    provider: str | None = None
    model: str | None = None
    generated_at: str | None = None
    executive_summary: str | None = None
    suggestions: tuple[SuggestionView, ...] = ()

    def attribution(self) -> str:
        """Label, provider, model and time of an available insight, else an empty text."""
        if self.label is None:
            return ""
        parts = [self.label, f"provider: {self.provider or 'unknown'}"]
        parts.append(f"model: {self.model or 'unknown'}")
        if self.generated_at:
            parts.append(f"generated at: {self.generated_at}")
        return " | ".join(parts)

    def suggestion_table(self) -> list[Row]:
        """One row per suggestion; each row repeats the label, provider, model and sample size."""
        return [
            {
                "label": self.label or "",
                "suggestion": item.suggestion,
                "evidence": item.evidence,
                "sample size": count_text(item.sample_size),
                "provider": self.provider or "unknown",
                "model": self.model or "unknown",
            }
            for item in self.suggestions
        ]

    def lines(self) -> list[str]:
        """Every statement in display order, as plain text."""
        if self.state == STATE_SAVED_WITHOUT:
            return [SAVED_WITHOUT_MESSAGE]
        if self.state == STATE_NOT_APPLICABLE:
            return [NOT_APPLICABLE_MESSAGE]
        if self.state != STATE_AVAILABLE:
            return [f"AI insight unavailable: {self.reason_text or NO_REASON_MESSAGE}"]
        lines = [self.attribution(), HYPOTHESIS_STATEMENT]
        lines.append(f"Executive summary: {self.executive_summary or 'not stated'}")
        for number, item in enumerate(self.suggestions, start=1):
            lines.append(
                f"Suggestion {number} ({self.label}, {self.provider or 'unknown'}, "
                f"{self.model or 'unknown'}): {item.suggestion} Evidence: {item.evidence} "
                f"Sample size: {count_text(item.sample_size)}."
            )
        return lines


def reason_text(reason: str | None) -> str:
    """Plain-language text for a reason code; a missing or unknown code has its own text."""
    if reason is None:
        return NO_REASON_MESSAGE
    return _REASON_TEXTS.get(reason, UNKNOWN_REASON_MESSAGE)


def _suggestion(entry: JsonValue) -> SuggestionView | None:
    item = as_mapping(entry)
    text = as_text(item.get("suggestion"))
    if text is None:
        return None
    return SuggestionView(
        suggestion=text,
        evidence=as_text(item.get("evidence")) or "",
        sample_size=as_int(item.get("sample_size")),
    )


def build_insight_view(result: Result, analysis: str) -> InsightView:
    """The insight of `analysis` in the stored result; never raises on missing or odd parts."""
    entry = as_mapping(as_mapping(result.get("analyses")).get(analysis))
    stored = as_mapping(entry.get("insight"))
    status = as_text(stored.get("status"))
    if status == STATE_NOT_APPLICABLE:
        return InsightView(analysis, STATE_NOT_APPLICABLE)
    if status == STATE_UNAVAILABLE:
        reason = as_text(stored.get("reason"))
        return InsightView(
            analysis,
            STATE_UNAVAILABLE,
            reason=reason,
            reason_text=reason_text(reason),
            provider=as_text(stored.get("provider")),
            model=as_text(stored.get("model")),
        )
    if status != STATE_AVAILABLE:
        return InsightView(analysis, STATE_SAVED_WITHOUT)
    suggestions = (_suggestion(item) for item in as_list(stored.get("improvement_suggestions")))
    return InsightView(
        analysis,
        STATE_AVAILABLE,
        label=as_text(stored.get("label")) or AI_LABEL,
        provider=as_text(stored.get("provider")),
        model=as_text(stored.get("model")),
        generated_at=as_text(stored.get("generated_at")),
        executive_summary=as_text(stored.get("executive_summary")),
        suggestions=tuple(item for item in suggestions if item is not None),
    )
