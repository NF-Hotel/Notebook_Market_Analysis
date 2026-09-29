"""Tests for the association-only wording rules (ADR-0007, MIL-005 criterion 5)."""

from hotel_booking_analysis.domain import wording
from hotel_booking_analysis.domain.analysis import JsonValue
from hotel_booking_analysis.domain.wording import (
    FORBIDDEN_WORDS,
    finding_texts,
    forbidden_words_in,
    forbidden_words_in_findings,
)

TEMPLATES: tuple[str, ...] = (
    wording.LEAD_TIME_MEDIAN,
    wording.LEAD_TIME_DATE_DIFFERENCE,
    wording.HOLIDAY_HIGHER,
    wording.HOLIDAY_LOWER,
    wording.HOLIDAY_SAME,
    wording.HOLIDAY_SMALL_SAMPLE,
    wording.HOLIDAY_SUBJECT_WINDOW,
    wording.HOLIDAY_SUBJECT_HOLIDAY,
    wording.HOLIDAY_ASSOCIATION_NOTE,
)


def test_forbidden_words_are_the_six_from_adr_0007() -> None:
    assert set(FORBIDDEN_WORDS) == {
        "caused",
        "because",
        "due to",
        "effect of",
        "leads to",
        "drives",
    }


def test_forbidden_words_in_ignores_case() -> None:
    assert forbidden_words_in("Sales rose BECAUSE of it; this Leads To more") == (
        "because",
        "leads to",
    )


def test_forbidden_words_in_is_empty_for_association_wording() -> None:
    assert forbidden_words_in("Cancellations were higher in summer; this was observed.") == ()


def test_every_wording_template_is_free_of_forbidden_words() -> None:
    assert [t for t in TEMPLATES if forbidden_words_in(t)] == []


def test_finding_texts_collects_nested_keys_and_values() -> None:
    findings: dict[str, JsonValue] = {"a": {"b": ["x", {"c": "y"}]}, "n": 3, "flag": True}

    assert sorted(finding_texts(findings)) == ["a", "b", "c", "flag", "n", "x", "y"]


def test_forbidden_words_in_findings_finds_words_in_nested_values() -> None:
    findings: dict[str, JsonValue] = {"a": [{"text": "It happened due to rain"}]}

    assert forbidden_words_in_findings(findings) == ("due to",)
