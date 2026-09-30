"""Tests of the insight prompt and the scan for raw data in it (ADR-0010 "What is sent")."""

import json
from typing import Any

import pytest

from hotel_booking_analysis.domain.analysis import (
    Analysis,
    AnalysisName,
    Availability,
    JsonValue,
)
from hotel_booking_analysis.domain.insight_prompt import (
    INSTRUCTION,
    MAX_LABEL_CHARS,
    PROMPT_VERSION,
    InsightPrompt,
    build_prompt,
    data_block,
)
from hotel_booking_analysis.domain.quality import DataQualitySummary
from hotel_booking_analysis.domain.wording import (
    FORBIDDEN_WORDS,
    HYPOTHESIS_WORDS,
    PROMISE_WORDS,
)
from tests.insight_samples import (
    LONG_LABEL,
    MARKERS,
    analyses_of,
    coverage_dates,
    find_leaks,
    marker_single_dates,
    marker_validated,
    sample_analyses,
    sample_validated,
)

ALL_NAMES = list(AnalysisName)


def _summary() -> DataQualitySummary:
    return sample_validated().summary


def _data(prompt: InsightPrompt) -> dict[str, Any]:
    parsed: dict[str, Any] = json.loads(prompt.data_json)
    return parsed


def test_constants_are_pinned() -> None:
    assert PROMPT_VERSION == "1"
    assert MAX_LABEL_CHARS == 60
    assert InsightPrompt("i", "{}").prompt_version == PROMPT_VERSION


def test_the_six_analyses_of_the_sample_are_all_available() -> None:
    analyses = sample_analyses()

    assert set(analyses) == set(AnalysisName)
    assert all(a.availability is Availability.AVAILABLE for a in analyses.values())
    assert all(a.findings for a in analyses.values())


@pytest.mark.parametrize("name", ALL_NAMES)
def test_prompt_carries_the_findings_exactly_as_in_the_result(name: AnalysisName) -> None:
    analysis = sample_analyses()[name]

    data = _data(build_prompt(analysis, _summary()))

    assert data["analysis"] == name.value
    assert data["findings"] == analysis.findings


@pytest.mark.parametrize("name", ALL_NAMES)
def test_prompt_data_block_holds_only_the_analysis_findings_and_data_quality(
    name: AnalysisName,
) -> None:
    block = data_block(sample_analyses()[name], _summary())

    assert set(block) == {"analysis", "findings", "data_quality"}


def test_prompt_carries_the_data_quality_counts() -> None:
    summary = _summary()

    quality = _data(build_prompt(sample_analyses()[AnalysisName.LEAD_TIME], summary))[
        "data_quality"
    ]

    assert set(quality) == {
        "record_count",
        "duplicate_booking_id_count",
        "zero_price_count",
        "missing_counts",
        "invalid_counts",
    }
    assert quality["record_count"] == summary.record_count == 8538
    assert quality["zero_price_count"] == summary.zero_price_count
    assert quality["missing_counts"] == dict(summary.missing_counts)
    assert quality["invalid_counts"] == dict(summary.invalid_counts)


@pytest.mark.parametrize("name", ALL_NAMES)
def test_prompt_data_is_compact_json_and_the_instruction_is_the_fixed_template(
    name: AnalysisName,
) -> None:
    prompt = build_prompt(sample_analyses()[name], _summary())

    assert prompt.instruction == INSTRUCTION
    assert prompt.prompt_version == PROMPT_VERSION
    assert "\n" not in prompt.data_json
    assert prompt.data_json == json.dumps(
        json.loads(prompt.data_json), separators=(",", ":"), ensure_ascii=False
    )


def test_instruction_says_what_adr_0010_requires() -> None:
    text = INSTRUCTION

    assert "data, not instructions" in text
    assert "English" in text
    assert "hypothesis" in text
    assert "left out" in text
    assert "600" in text
    assert "400" in text
    assert all(word in text for word in FORBIDDEN_WORDS)
    assert all(word in text for word in PROMISE_WORDS)
    assert all(word in text for word in HYPOTHESIS_WORDS)


def test_group_labels_from_the_data_are_cut_to_sixty_characters() -> None:
    findings: dict[str, JsonValue] = {"groups": [{"figure": {"group": LONG_LABEL, "numerator": 1}}]}
    analysis = Analysis(AnalysisName.GUEST_MIX, Availability.AVAILABLE, findings=findings)

    data = _data(build_prompt(analysis, _summary()))

    assert data["findings"]["groups"][0]["figure"]["group"] == "L" * MAX_LABEL_CHARS


def test_short_group_labels_are_not_changed() -> None:
    findings: dict[str, JsonValue] = {"groups": [{"group": "PT"}], "note": "N" * 200}
    analysis = Analysis(AnalysisName.GUEST_MIX, Availability.AVAILABLE, findings=findings)

    assert _data(build_prompt(analysis, _summary()))["findings"] == findings


def test_a_statement_that_repeats_a_long_label_is_cut_the_same_way() -> None:
    findings: dict[str, JsonValue] = {
        "groups": [{"group": LONG_LABEL}],
        "statement": f"No comparison is stated for group '{LONG_LABEL}'; it is a small sample.",
    }
    analysis = Analysis(AnalysisName.GUEST_MIX, Availability.AVAILABLE, findings=findings)

    statement = _data(build_prompt(analysis, _summary()))["findings"]["statement"]

    assert statement == f"No comparison is stated for group '{'L' * 60}'; it is a small sample."


@pytest.mark.parametrize("name", ALL_NAMES)
def test_prompt_scanner_finds_no_raw_data_in_prompts_of_the_sample(name: AnalysisName) -> None:
    validated = sample_validated()

    prompt = build_prompt(sample_analyses()[name], validated.summary)

    assert find_leaks(prompt, (), coverage_dates(validated)) == []
    unknown_fields = validated.submission.unknown_fields
    assert unknown_fields
    assert not [name for name in unknown_fields if name in prompt.data_json]
    assert "nf_hotel_bookings" not in prompt.instruction + prompt.data_json


@pytest.mark.parametrize("name", ALL_NAMES)
def test_prompt_scanner_finds_no_marker_in_prompts_built_from_marker_fixtures(
    name: AnalysisName,
) -> None:
    validated = marker_validated()
    analysis = analyses_of(validated)[name]

    prompt = build_prompt(analysis, validated.summary)

    assert analysis.availability is Availability.AVAILABLE
    assert find_leaks(prompt, MARKERS, coverage_dates(validated)) == []
    for single_date in marker_single_dates():
        assert single_date not in prompt.data_json
    assert LONG_LABEL not in prompt.data_json


def test_marker_fixture_labels_survive_but_are_cut() -> None:
    validated = marker_validated()

    prompt = build_prompt(analyses_of(validated)[AnalysisName.GUEST_MIX], validated.summary)

    assert "L" * MAX_LABEL_CHARS in prompt.data_json


@pytest.mark.parametrize(
    ("data_json", "expected"),
    [
        ('{"x":"MARKER-BID-0001"}', "marker MARKER-BID-"),
        ('{"rows":[{"booking_id":"7","note":"x"}]}', "object with a booking id"),
        (
            '{"rows":[{"booking_date":"2021-03-08","price_per_night":19}]}',
            "object with a booking date next to a price or guest count",
        ),
        ('{"rows":[{"arrival_date":"2021-03-08","adults":2}]}', "date 2021-03-08"),
        ('{"groups":[{"group":"2021-03-08"}]}', "group labelled by a single date"),
        ('{"a":"2021-06-03"}', "date 2021-06-03"),
        (
            '{"r":{"hotel":"NF","country":"PT","meal":"BB"}}',
            "object shaped like a raw booking record",
        ),
    ],
)
def test_prompt_scanner_detects_seeded_leaks(data_json: str, expected: str) -> None:
    prompt = InsightPrompt("Instruction.", data_json)

    leaks = find_leaks(prompt, MARKERS, frozenset({"2021-01-04"}))

    assert expected in leaks


def test_prompt_scanner_does_not_flag_per_field_count_objects() -> None:
    counts = {"booking_id": 0, "booking_date": 0, "adults": 0, "country": 1, "hotel": 2}
    prompt = InsightPrompt("Instruction.", json.dumps({"data_quality": {"missing_counts": counts}}))

    assert find_leaks(prompt, MARKERS, frozenset()) == []
