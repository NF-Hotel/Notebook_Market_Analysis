"""Tests of the guardrail validator: every rule of ADR-0010 passes and fails (no model needed)."""

import json
from collections.abc import Callable
from typing import Any

import pytest

from hotel_booking_analysis.domain.analysis import AnalysisName, JsonValue
from hotel_booking_analysis.domain.errors import InsightRejectedError
from hotel_booking_analysis.domain.insight import (
    ExecutiveSummary,
    ImprovementSuggestion,
    InsightReason,
)
from hotel_booking_analysis.domain.insight_prompt import InsightPrompt, build_prompt
from hotel_booking_analysis.domain.insight_validation import (
    MAX_EVIDENCE_CHARS,
    MAX_SUGGESTION_CHARS,
    MAX_SUGGESTIONS,
    MAX_SUMMARY_CHARS,
    MIN_SUGGESTIONS,
    SAMPLE_SIZE_FIELDS,
    check_guardrails,
    parse_structure,
    sample_sizes,
    validate_answer,
)
from hotel_booking_analysis.domain.wording import (
    FORBIDDEN_WORDS,
    HYPOTHESIS_WORDS,
    PROMISE_WORDS,
    SMALL_SAMPLE_PHRASE,
)
from tests.insight_samples import sample_analyses, sample_validated

MIN_GROUP = 30
BAD = InsightReason.BAD_STRUCTURE
REJECTED = InsightReason.GUARDRAIL_REJECTED

DATA: dict[str, Any] = {
    "analysis": "cancellations",
    "findings": {
        "records_used": 8538,
        "overall": {"group": "all", "numerator": 1691, "denominator": 8538},
        "groups": [{"group": "Refundable", "numerator": 12, "denominator": 20}],
        "median_days": 17,
        "windows_days": [1, 3, 7],
        "days_left_out_unavailable_years": 2,
        "total": "91467.27",
        "mean": "54.0906",
        "share": 35.5,
    },
    "data_quality": {"record_count": 9000, "zero_price_count": 91},
}
PROMPT = InsightPrompt("Instruction.", json.dumps(DATA))


def _answer(
    summary: str = "Cancellations were seen in 1691 of 8538 bookings.",
    suggestion: str = "Consider testing a deposit rule for the 8538 bookings.",
    evidence: str = "1691 of 8538 bookings were cancelled.",
    sample_size: object = 8538,
) -> dict[str, Any]:
    return {
        "executive_summary": summary,
        "improvement_suggestions": [
            {"suggestion": suggestion, "evidence": evidence, "sample_size": sample_size}
        ],
    }


def _validate(
    document: object, min_group_size: int = MIN_GROUP
) -> tuple[ExecutiveSummary, tuple[ImprovementSuggestion, ...]]:
    text = document if isinstance(document, str) else json.dumps(document)
    return validate_answer(text, PROMPT, min_group_size)


def _reason_of(document: object, min_group_size: int = MIN_GROUP) -> InsightReason:
    with pytest.raises(InsightRejectedError) as raised:
        _validate(document, min_group_size)
    return raised.value.reason


def test_constants_are_pinned() -> None:
    assert FORBIDDEN_WORDS == ("caused", "because", "due to", "effect of", "leads to", "drives")
    assert PROMISE_WORDS == (
        "will increase",
        "will grow",
        "will raise",
        "will boost",
        "guarantee",
        "ensure",
        "certainly",
        "definitely",
        "forecast",
        "predict",
    )
    assert HYPOTHESIS_WORDS == ("may", "might", "could", "suggests", "consider testing")
    assert SMALL_SAMPLE_PHRASE == "small sample"
    assert (MAX_SUMMARY_CHARS, MAX_SUGGESTION_CHARS, MAX_EVIDENCE_CHARS) == (600, 400, 400)
    assert (MIN_SUGGESTIONS, MAX_SUGGESTIONS) == (1, 5)
    assert SAMPLE_SIZE_FIELDS == ("numerator", "denominator", "records_used")


def test_valid_answer_is_accepted_and_returned_as_values() -> None:
    summary, suggestions = _validate(_answer())

    assert summary == ExecutiveSummary("Cancellations were seen in 1691 of 8538 bookings.")
    assert suggestions == (
        ImprovementSuggestion(
            "Consider testing a deposit rule for the 8538 bookings.",
            "1691 of 8538 bookings were cancelled.",
            8538,
        ),
    )


def test_other_keys_are_dropped() -> None:
    document = _answer()
    document["note"] = "extra"
    document["improvement_suggestions"][0]["confidence"] = "high"

    summary, suggestions = _validate(document)

    assert summary == ExecutiveSummary("Cancellations were seen in 1691 of 8538 bookings.")
    assert suggestions == (
        ImprovementSuggestion(
            "Consider testing a deposit rule for the 8538 bookings.",
            "1691 of 8538 bookings were cancelled.",
            8538,
        ),
    )


@pytest.mark.parametrize(
    "fence", ["```json\n{body}\n```", "```\n{body}\n```", "```JSON\r\n{body}```"]
)
def test_a_single_surrounding_code_fence_is_tolerated(fence: str) -> None:
    text = "  " + fence.replace("{body}", json.dumps(_answer())) + "\n"

    summary, _ = validate_answer(text, PROMPT, MIN_GROUP)

    assert summary.text.startswith("Cancellations")


@pytest.mark.parametrize(
    "text",
    [
        "",
        "not json",
        "Here is the answer: " + json.dumps(_answer()),
        "```json\n```json\n" + json.dumps(_answer()) + "\n```\n```",
        "[]",
        '"text"',
        "null",
        "{",
    ],
)
def test_text_that_is_not_a_json_object_is_bad_structure(text: str) -> None:
    assert _reason_of(text) is BAD


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.pop("executive_summary"),
        lambda d: d.update(executive_summary=5),
        lambda d: d.update(executive_summary=""),
        lambda d: d.update(executive_summary="   "),
        lambda d: d.update(executive_summary="x" * (MAX_SUMMARY_CHARS + 1)),
        lambda d: d.pop("improvement_suggestions"),
        lambda d: d.update(improvement_suggestions="text"),
        lambda d: d.update(improvement_suggestions={}),
        lambda d: d.update(improvement_suggestions=[]),
        lambda d: d.update(improvement_suggestions=d["improvement_suggestions"] * 6),
        lambda d: d.update(improvement_suggestions=["text"]),
        lambda d: d["improvement_suggestions"][0].pop("suggestion"),
        lambda d: d["improvement_suggestions"][0].update(suggestion=7),
        lambda d: d["improvement_suggestions"][0].update(suggestion=""),
        lambda d: d["improvement_suggestions"][0].update(suggestion="x" * 401),
        lambda d: d["improvement_suggestions"][0].pop("evidence"),
        lambda d: d["improvement_suggestions"][0].update(evidence=None),
        lambda d: d["improvement_suggestions"][0].update(evidence=" "),
        lambda d: d["improvement_suggestions"][0].update(evidence="x" * 401),
        lambda d: d["improvement_suggestions"][0].pop("sample_size"),
        lambda d: d["improvement_suggestions"][0].update(sample_size=0),
        lambda d: d["improvement_suggestions"][0].update(sample_size=-3),
        lambda d: d["improvement_suggestions"][0].update(sample_size="8538"),
        lambda d: d["improvement_suggestions"][0].update(sample_size=8538.0),
        lambda d: d["improvement_suggestions"][0].update(sample_size=True),
        lambda d: d["improvement_suggestions"][0].update(sample_size=None),
    ],
)
def test_a_structure_violation_is_bad_structure(
    mutate: Callable[[dict[str, Any]], object],
) -> None:
    document = _answer()
    mutate(document)

    assert _reason_of(document) is BAD


def test_texts_at_their_limits_and_five_suggestions_are_accepted() -> None:
    document = _answer(summary="s" * MAX_SUMMARY_CHARS)
    item = {
        "suggestion": "It may help. " + "x" * (MAX_SUGGESTION_CHARS - 13),
        "evidence": "e" * MAX_EVIDENCE_CHARS,
        "sample_size": 8538,
    }
    document["improvement_suggestions"] = [item] * MAX_SUGGESTIONS

    summary, suggestions = _validate(document)

    assert len(summary.text) == MAX_SUMMARY_CHARS
    assert len(suggestions) == MAX_SUGGESTIONS
    assert len(suggestions[0].suggestion) == MAX_SUGGESTION_CHARS


def test_parse_structure_does_not_apply_the_guardrails() -> None:
    document = _answer(summary="Growth because of x.", sample_size=99999)

    summary, suggestions = parse_structure(json.dumps(document))

    assert summary.text == "Growth because of x."
    assert suggestions[0].sample_size == 99999


def _texts(place: str, text: str) -> dict[str, Any]:
    if place == "summary":
        return _answer(summary=text)
    if place == "suggestion":
        return _answer(suggestion="It may help: " + text)
    return _answer(evidence=text)


PLACES = ["summary", "suggestion", "evidence"]


@pytest.mark.parametrize("place", PLACES)
@pytest.mark.parametrize("word", FORBIDDEN_WORDS)
def test_each_causal_word_is_rejected_in_each_text(word: str, place: str) -> None:
    assert _reason_of(_texts(place, f"Cancellations rose {word.upper()} the deposit.")) is REJECTED


@pytest.mark.parametrize("place", PLACES)
@pytest.mark.parametrize(
    "phrase",
    [
        *PROMISE_WORDS,
        "Will Increase",
        "will   grow",
        "will boosts",
        "guaranteed",
        "guarantees",
        "ensures",
        "ensuring",
        "ensured",
        "predicted",
        "predicts",
        "forecasts",
        "forecasting",
        "CERTAINLY",
    ],
)
def test_each_promise_or_forecast_word_is_rejected_in_each_text(phrase: str, place: str) -> None:
    assert _reason_of(_texts(place, f"Then it {phrase} more earnings.")) is REJECTED


def test_will_without_a_promise_verb_is_accepted() -> None:
    _validate(_answer(summary="The team will review the 8538 bookings."))


@pytest.mark.parametrize(
    "text",
    [
        "Cancellations were 12345.6789% of bookings.",
        "Cancellations were 12345.6789 percent of bookings.",
        "Cancellations were 4 % of bookings.",
        "Revenue was $777.77.",
        "Revenue was 777 USD.",
        "Revenue was €1,000.50 in total.",
        "Revenue was 500 EUR.",
    ],
)
def test_a_percentage_or_amount_that_is_not_in_the_findings_is_rejected(text: str) -> None:
    assert _reason_of(_answer(summary=text)) is REJECTED
    assert _reason_of(_answer(evidence=text)) is REJECTED


@pytest.mark.parametrize(
    "text",
    [
        "The share was 35.5% of bookings.",
        "The share was 35.5 percent of bookings.",
        "The estimated total was $91,467.27 in price units.",
        "The estimated total was 91467.27 USD.",
        "The mean was 54.0906 EUR.",
        "About 17% of the 8538 bookings.",
        "A count of 1,691 bookings.",
    ],
)
def test_a_percentage_or_amount_that_is_in_the_findings_is_accepted(text: str) -> None:
    _validate(_answer(summary=text))


@pytest.mark.parametrize("size", [8538, 1691, 20, 12, 1, 3, 7, 9000])
def test_a_sample_size_present_in_the_findings_is_accepted(size: int) -> None:
    _validate(_answer(sample_size=size), min_group_size=1)


@pytest.mark.parametrize("size", [17, 2, 91, 35, 5, 8539, 100000])
def test_a_sample_size_absent_from_the_findings_is_rejected(size: int) -> None:
    assert _reason_of(_answer(sample_size=size), min_group_size=1) is REJECTED


def test_sample_sizes_are_exactly_the_counts_and_day_counts_and_the_record_count() -> None:
    assert sample_sizes(DATA) == frozenset({8538, 1691, 12, 20, 1, 3, 7, 9000})


def test_sample_sizes_ignore_medians_means_rates_and_booleans() -> None:
    data: JsonValue = {
        "findings": {
            "median_days": 17,
            "mean_days": 4,
            "mean_per_day": 5,
            "rate": 40,
            "small_sample": True,
            "numerator": True,
            "records_used": "8",
            "denominator": 6.5,
            "window_days": None,
        },
        "data_quality": {"record_count": True},
    }

    assert sample_sizes(data) == frozenset()


def test_sample_sizes_of_a_prompt_without_findings_is_empty() -> None:
    assert sample_sizes({}) == frozenset()
    assert sample_sizes([1, 2]) == frozenset()


def test_a_sample_below_the_minimum_needs_the_words_small_sample() -> None:
    assert _reason_of(_answer(sample_size=20, evidence="12 of 20 bookings.")) is REJECTED

    _validate(_answer(sample_size=20, evidence="12 of 20 bookings; this is a Small Sample."))


def test_a_sample_at_the_minimum_needs_no_small_sample_words() -> None:
    _validate(_answer(sample_size=20, evidence="12 of 20 bookings."), min_group_size=20)
    assert _reason_of(_answer(sample_size=20, evidence="12 of 20."), min_group_size=21) is REJECTED


@pytest.mark.parametrize("word", HYPOTHESIS_WORDS)
def test_each_hypothesis_word_makes_a_suggestion_acceptable(word: str) -> None:
    _validate(_answer(suggestion=f"The team {word.upper()} look at the 8538 bookings."))


@pytest.mark.parametrize(
    "suggestion",
    [
        "Raise the price of the 8538 bookings.",
        "Maybe raise the price.",
        "Improve the deposit policy.",
        "The mayor is here.",
    ],
)
def test_a_suggestion_without_hypothesis_wording_is_rejected(suggestion: str) -> None:
    assert _reason_of(_answer(suggestion=suggestion)) is REJECTED


def test_hypothesis_wording_is_required_of_every_suggestion() -> None:
    document = _answer()
    document["improvement_suggestions"].append(
        {"suggestion": "Do this.", "evidence": "1691 of 8538.", "sample_size": 8538}
    )

    assert _reason_of(document) is REJECTED


def test_the_first_failing_rule_is_named_in_the_detail() -> None:
    document = _answer(
        summary="Because of it $777.77.", suggestion="Do it.", sample_size=17, evidence="x"
    )

    with pytest.raises(InsightRejectedError) as raised:
        _validate(document)

    assert raised.value.reason is REJECTED
    assert raised.value.detail.startswith("Rule 2")


def test_the_detail_never_quotes_the_answer() -> None:
    marker = "ZZQ-secret-figure"
    for document in (
        _answer(summary=f"{marker} because 777%"),
        _answer(suggestion=f"{marker} guarantee"),
        _answer(summary=f"{marker} 777%"),
        _answer(evidence=marker, sample_size=17),
        _answer(suggestion=marker),
        f"{marker} not json",
        {"executive_summary": marker},
    ):
        with pytest.raises(InsightRejectedError) as raised:
            _validate(document)

        assert marker not in raised.value.detail
        assert marker not in str(raised.value)


def test_check_guardrails_rejects_parsed_values_that_break_a_rule() -> None:
    summary, suggestions = parse_structure(json.dumps(_answer(summary="It works because.")))

    with pytest.raises(InsightRejectedError) as raised:
        check_guardrails(summary, suggestions, PROMPT, MIN_GROUP)

    assert raised.value.reason is REJECTED


@pytest.mark.parametrize("name", list(AnalysisName))
def test_an_answer_built_on_a_real_prompt_of_each_analysis_is_accepted_or_rejected_by_content(
    name: AnalysisName,
) -> None:
    validated = sample_validated()
    prompt = build_prompt(sample_analyses()[name], validated.summary)
    good = _answer(
        summary=f"Findings cover {validated.summary.record_count} bookings.",
        suggestion="Consider testing a change for all bookings.",
        evidence="The findings describe all records.",
        sample_size=validated.summary.record_count,
    )
    invented = _answer(
        summary="Findings show 12345.6789% of bookings.",
        suggestion="Consider testing a change for all bookings.",
        evidence="All records.",
        sample_size=validated.summary.record_count,
    )

    summary, suggestions = validate_answer(json.dumps(good), prompt, MIN_GROUP)
    with pytest.raises(InsightRejectedError) as raised:
        validate_answer(json.dumps(invented), prompt, MIN_GROUP)

    assert suggestions[0].sample_size == validated.summary.record_count
    assert summary.text.startswith("Findings cover")
    assert raised.value.reason is REJECTED
