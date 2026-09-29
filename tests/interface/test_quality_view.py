"""Tests for the data-quality view model (US-001.01, UC-002)."""

from pathlib import Path

from hotel_booking_analysis.domain.analysis import JsonValue
from hotel_booking_analysis.domain.wording import forbidden_words_in
from hotel_booking_analysis.interface.quality_view import NOT_SUPPLIED, build_quality_view
from tests.interface.builders import run_analysis


def _hand_built() -> dict[str, JsonValue]:
    return {
        "data_quality": {
            "record_count": 12,
            "earliest_booking_date": "2021-03-08",
            "latest_booking_date": "2025-12-29",
            "earliest_arrival_date": None,
            "latest_arrival_date": None,
            "duplicate_booking_id_count": 2,
            "missing_counts": {"adults": 3, "country": 0},
            "invalid_counts": {"adults": 1, "country": 4},
            "zero_price_count": 5,
            "unknown_fields": ["agent", "hotel"],
        },
        "analyses": {
            "lead_time": {"status": "available", "findings": {}},
            "room_value": {
                "status": "unavailable",
                "reason": "No record holds a valid value in every required field: 'price'",
                "findings": {},
            },
        },
        "notices": [{"code": "CONFIG_FILE_NOT_FOUND", "message": "Defaults were applied."}],
    }


def test_quality_view_shows_counts_and_coverage_from_hand_built_result() -> None:
    view = build_quality_view(_hand_built())

    assert view.record_count == 12
    assert view.booking_dates == ("2021-03-08", "2025-12-29")
    assert view.arrival_dates == (NOT_SUPPLIED, NOT_SUPPLIED)
    assert view.duplicate_booking_id_count == 2
    assert view.zero_price_count == 5
    assert view.unknown_fields == ("agent", "hotel")


def test_quality_view_has_one_table_row_per_field_with_missing_and_invalid() -> None:
    view = build_quality_view(_hand_built())

    assert view.field_table() == [
        {"field": "adults", "missing": 3, "invalid": 1},
        {"field": "country", "missing": 0, "invalid": 4},
    ]


def test_quality_view_lists_unavailable_analyses_with_reasons() -> None:
    view = build_quality_view(_hand_built())

    assert view.unavailable_table() == [
        {
            "analysis": "room_value",
            "reason": "No record holds a valid value in every required field: 'price'",
        }
    ]


def test_quality_view_carries_notices() -> None:
    view = build_quality_view(_hand_built())

    assert view.notices == ("CONFIG_FILE_NOT_FOUND: Defaults were applied.",)


def test_quality_view_summary_lines_state_every_headline_figure() -> None:
    lines = build_quality_view(_hand_built()).summary_lines()

    assert lines == [
        "Records: 12",
        "Booking dates: 2021-03-08 to 2025-12-29",
        "Arrival dates: not supplied to not supplied",
        "Duplicate booking IDs: 2",
        "Records with a price per night of zero: 5",
        "Unknown fields: agent, hotel",
    ]


def test_quality_view_of_an_empty_result_does_not_raise() -> None:
    view = build_quality_view({})

    assert view.record_count is None
    assert view.fields == ()
    assert view.unavailable_analyses == ()
    assert "Records: unknown" in view.summary_lines()
    assert "Unknown fields: none" in view.summary_lines()


def test_quality_view_of_a_real_result_matches_the_stored_summary(tmp_path: Path) -> None:
    result = run_analysis(tmp_path, without=("lead_time",))

    view = build_quality_view(result)

    assert view.record_count == 7
    assert view.booking_dates == ("2023-03-01", "2023-03-07")
    assert view.arrival_dates == ("2023-04-01", "2023-04-07")
    assert view.duplicate_booking_id_count == 0
    fields = {row["field"]: row for row in view.field_table()}
    assert fields["lead_time"]["missing"] == 7
    assert [u.analysis for u in view.unavailable_analyses] == ["lead_time"]
    assert "lead_time" in view.unavailable_analyses[0].reason


def test_quality_view_text_never_contains_forbidden_words(tmp_path: Path) -> None:
    view = build_quality_view(run_analysis(tmp_path, without=("lead_time",)))

    text = " ".join(
        view.summary_lines() + list(view.notices) + [u.reason for u in view.unavailable_analyses]
    )

    assert forbidden_words_in(text) == ()
