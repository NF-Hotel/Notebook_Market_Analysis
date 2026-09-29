"""Tests for the shared limitations and association notice (ADR-0007, MIL-006 task 6)."""

from pathlib import Path

import pytest

from hotel_booking_analysis.domain.analysis import AnalysisName, JsonValue
from hotel_booking_analysis.domain.wording import ROOM_VALUE_LABEL, forbidden_words_in
from hotel_booking_analysis.interface.limitations import (
    ASSOCIATION_STATEMENT,
    NO_FLAGS_STATEMENT,
    SAMPLE_SIZE_STATEMENT,
    build_limitations,
)
from tests.interface.builders import run_analysis


def _result(findings: dict[str, JsonValue], name: str = "cancellations") -> dict[str, JsonValue]:
    return {"analyses": {name: {"status": "available", "findings": findings}}}


def test_notice_always_states_sample_sizes_and_association_not_cause() -> None:
    notice = build_limitations(_result({}), "cancellations")

    assert SAMPLE_SIZE_STATEMENT in notice.lines()
    assert ASSOCIATION_STATEMENT in notice.lines()
    assert "not causes" in notice.association_statement


def test_notice_says_nothing_was_flagged_when_findings_are_clean() -> None:
    notice = build_limitations(_result({"groups": [{"small_sample": False}]}), "cancellations")

    assert NO_FLAGS_STATEMENT in notice.data_limitations


def test_notice_counts_small_samples_including_omitted_comparisons() -> None:
    findings: dict[str, JsonValue] = {
        "groups": [
            {"figure": {"small_sample": True}},
            {"figure": {"small_sample": False}, "comparison": {"status": "omitted_small_sample"}},
        ]
    }

    notice = build_limitations(_result(findings), "cancellations")

    assert any("2 group(s) are small samples" in line for line in notice.data_limitations)
    assert NO_FLAGS_STATEMENT not in notice.data_limitations


def test_notice_counts_partial_periods() -> None:
    findings: dict[str, JsonValue] = {
        "by_month": [{"partial_period": True}, {"partial_period": True}]
    }

    notice = build_limitations(_result(findings, "seasonality"), "seasonality")

    assert any("2 period(s) are partial" in line for line in notice.data_limitations)


def test_notice_lists_unavailable_parts_and_years_with_reasons() -> None:
    findings: dict[str, JsonValue] = {
        "by_segment": {"status": "unavailable", "reason": "'market_segment' is missing"},
        "years_unavailable": [
            {
                "year": 2030,
                "status": "unavailable",
                "reason": "The holiday calendar has no data for 2030.",
            }
        ],
    }

    notice = build_limitations(_result(findings, "holidays"), "holidays")

    text = "\n".join(notice.data_limitations)
    assert "by_segment: 'market_segment' is missing" in text
    assert "The holiday calendar has no data for 2030." in text


def test_notice_reports_a_wholly_unavailable_analysis() -> None:
    result: dict[str, JsonValue] = {
        "analyses": {"room_value": {"status": "unavailable", "reason": "price missing"}}
    }

    notice = build_limitations(result, "room_value")

    assert "Not available - analysis: price missing" in notice.data_limitations


def test_notice_only_scans_the_named_analysis() -> None:
    result: dict[str, JsonValue] = {
        "analyses": {
            "lead_time": {"status": "available", "findings": {"g": {"small_sample": True}}},
            "cancellations": {"status": "available", "findings": {}},
        }
    }

    assert NO_FLAGS_STATEMENT in build_limitations(result, "cancellations").data_limitations
    assert NO_FLAGS_STATEMENT not in build_limitations(result).data_limitations


def test_room_value_notice_carries_the_estimate_label() -> None:
    notice = build_limitations(_result({}, "room_value"), AnalysisName.ROOM_VALUE)

    assert notice.estimate_label is not None
    assert "not realized revenue" in notice.estimate_label
    assert ROOM_VALUE_LABEL in notice.estimate_label
    assert notice.estimate_label in notice.lines()


def test_other_analysis_notice_has_no_estimate_label() -> None:
    assert build_limitations(_result({}), "cancellations").estimate_label is None


def test_whole_result_notice_carries_estimate_label_when_room_value_is_present() -> None:
    assert build_limitations(_result({}, "room_value")).estimate_label is not None
    assert build_limitations(_result({}, "lead_time")).estimate_label is None


def test_markdown_lists_every_line_as_a_bullet() -> None:
    notice = build_limitations(_result({}, "room_value"), "room_value")

    markdown = notice.markdown()

    assert markdown.startswith("**Limitations of these figures**")
    assert all(f"- {line}" in markdown for line in notice.lines())


def test_notice_of_an_empty_result_does_not_raise() -> None:
    notice = build_limitations({}, "lead_time")

    assert ASSOCIATION_STATEMENT in notice.lines()


@pytest.mark.parametrize("without", [(), ("price_per_night",), ("lead_time",)])
def test_notice_text_for_real_results_never_contains_forbidden_words(
    tmp_path: Path, without: tuple[str, ...]
) -> None:
    result = run_analysis(tmp_path, without=without)
    names = [None, *(name.value for name in AnalysisName)]

    for name in names:
        notice = build_limitations(result, name)
        assert forbidden_words_in(notice.markdown()) == (), name


def test_notice_for_a_real_result_flags_small_samples_and_room_value_estimate(
    tmp_path: Path,
) -> None:
    result = run_analysis(tmp_path)

    cancellations = build_limitations(result, "cancellations")
    room_value = build_limitations(result, "room_value")

    assert any("small samples" in line for line in cancellations.data_limitations)
    assert room_value.estimate_label is not None
    assert cancellations.estimate_label is None
