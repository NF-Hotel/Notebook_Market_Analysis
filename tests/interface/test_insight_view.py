"""Tests of the insight view model and its plain-text rendering (UC-002, ADR-0010, ADR-0011)."""

import html
from typing import Any

import pytest

from hotel_booking_analysis.domain.insight import InsightReason
from hotel_booking_analysis.interface.insight_view import (
    HYPOTHESIS_STATEMENT,
    NO_REASON_MESSAGE,
    SAVED_WITHOUT_MESSAGE,
    STATE_AVAILABLE,
    STATE_NOT_APPLICABLE,
    STATE_SAVED_WITHOUT,
    STATE_UNAVAILABLE,
    UNKNOWN_REASON_MESSAGE,
    build_insight_view,
    reason_text,
)
from hotel_booking_analysis.interface.marimo_render import render_insight
from tests.interface.builders import Result
from tests.interface.insight_builders import (
    available_insight,
    unavailable_insight,
    with_insight,
)

HOSTILE = '<script>alert(1)</script> <marimo-ui-element object-id="x"> **bold** {{ x }} &amp;'
BASE: Result = {"analyses": {"lead_time": {"status": "available"}}}


def _result(insight: object) -> Result:
    return with_insight(BASE, insight)


def _rendered(insight: object) -> str:
    return str(render_insight(build_insight_view(_result(insight), "lead_time")).text)


def test_available_insight_is_labeled_with_provider_model_and_sample_size() -> None:
    view = build_insight_view(_result(available_insight()), "lead_time")

    assert view.state == STATE_AVAILABLE
    assert (view.label, view.provider, view.model) == ("AI-generated", "ollama", "m1")
    assert view.generated_at == "2026-09-29T12:00:01.250Z"
    assert view.executive_summary == "The findings describe the observed data only."
    assert [s.sample_size for s in view.suggestions] == [7]
    row = view.suggestion_table()[0]
    assert (row["label"], row["provider"], row["model"], row["sample size"]) == (
        "AI-generated",
        "ollama",
        "m1",
        "7",
    )
    text = "\n".join(view.lines())
    assert HYPOTHESIS_STATEMENT in text
    assert "AI-generated | provider: ollama | model: m1" in text
    assert "Sample size: 7." in text


@pytest.mark.parametrize(
    "result",
    [
        {},
        {"analyses": {}},
        BASE,
        {"analyses": {"lead_time": "odd"}},
        {"analyses": ["odd"]},
        _result(None),
        _result("odd"),
        _result({"status": 5}),
        _result({"status": "surprise"}),
    ],
)
def test_missing_or_odd_insight_is_saved_without_insights(result: Result) -> None:
    view = build_insight_view(result, "lead_time")

    assert view.state == STATE_SAVED_WITHOUT
    assert view.lines() == [SAVED_WITHOUT_MESSAGE]
    assert view.suggestion_table() == []
    assert view.label is None


@pytest.mark.parametrize("reason", [reason.value for reason in InsightReason])
def test_unavailable_insight_states_the_reason_in_plain_language(reason: str) -> None:
    view = build_insight_view(_result(unavailable_insight(reason)), "lead_time")

    assert view.state == STATE_UNAVAILABLE
    assert view.reason == reason
    assert view.reason_text == reason_text(reason)
    assert view.reason_text not in (NO_REASON_MESSAGE, UNKNOWN_REASON_MESSAGE)
    assert view.executive_summary is None
    assert view.lines() == [f"AI insight unavailable: {view.reason_text}"]


def test_reason_texts_are_distinct_and_odd_codes_have_their_own_text() -> None:
    texts = {reason_text(reason.value) for reason in InsightReason}

    assert len(texts) == len(InsightReason)
    assert reason_text(None) == NO_REASON_MESSAGE
    assert reason_text("SOMETHING_NEW") == UNKNOWN_REASON_MESSAGE


def test_not_applicable_insight_says_the_analysis_is_not_available() -> None:
    view = build_insight_view(_result({"status": "not_applicable"}), "lead_time")

    assert view.state == STATE_NOT_APPLICABLE
    assert "not available" in view.lines()[0]


def test_available_insight_with_odd_parts_keeps_what_can_be_read() -> None:
    odd: dict[str, Any] = {
        "status": "available",
        "provider": 3,
        "executive_summary": ["not text"],
        "improvement_suggestions": [
            "odd",
            {"evidence": "no text"},
            {"suggestion": "kept", "sample_size": "many"},
        ],
    }

    view = build_insight_view(_result(odd), "lead_time")

    assert view.label == "AI-generated"
    assert view.provider is None
    assert view.executive_summary is None
    assert [(s.suggestion, s.sample_size) for s in view.suggestions] == [("kept", None)]
    assert view.suggestion_table()[0]["sample size"] == "unknown"
    assert any("not stated" in line for line in view.lines())


def test_insight_of_another_analysis_is_not_mixed_in() -> None:
    result = with_insight(_result(available_insight()), unavailable_insight(), "seasonality")

    assert build_insight_view(result, "lead_time").state == STATE_AVAILABLE
    assert build_insight_view(result, "seasonality").state == STATE_UNAVAILABLE
    assert build_insight_view(result, "holidays").state == STATE_SAVED_WITHOUT


def test_render_shows_label_hypothesis_statement_and_suggestion_of_an_available_insight() -> None:
    text = _rendered(available_insight())

    assert "AI insight" in text
    assert "AI-generated" in text
    assert "provider: ollama" in text
    assert "model: m1" in text
    assert html.escape(HYPOTHESIS_STATEMENT) in text
    assert "The findings describe the observed data only." in text
    assert "Consider a change" in text


@pytest.mark.parametrize("field", ["summary", "suggestion"])
def test_render_shows_model_text_as_plain_text_never_as_markup(field: str) -> None:
    insight = available_insight(
        summary=HOSTILE if field == "summary" else "Fine.",
        suggestion=HOSTILE if field == "suggestion" else "Fine.",
    )

    text = _rendered(insight)

    assert "<script>" not in text
    assert '<marimo-ui-element object-id="x">' not in text
    if field == "summary":
        assert html.escape(HOSTILE) in text
    else:
        assert "u003cscript" in text  # escaped inside the table data, where it is only data


@pytest.mark.parametrize(
    ("insight", "expected"),
    [
        (None, SAVED_WITHOUT_MESSAGE),
        (unavailable_insight("TIMEOUT"), reason_text("TIMEOUT")),
        ({"status": "not_applicable"}, "not available in the result"),
    ],
)
def test_render_shows_states_without_ai_text(insight: object, expected: str) -> None:
    text = _rendered(insight)

    assert expected in text
    assert "Executive summary" not in text
