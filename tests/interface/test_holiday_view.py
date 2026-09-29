"""Tests for the holiday view model (US-001.03)."""

from hotel_booking_analysis.domain.analysis import JsonValue
from hotel_booking_analysis.interface.holiday_view import build_holiday_view
from tests.interface.builders import Result


def _side(name: str, records: int, days: int, mean: float) -> dict[str, JsonValue]:
    figure: dict[str, JsonValue] = {
        "group": name,
        "numerator": records,
        "denominator": days,
        "small_sample": days < 5,
    }
    return {"figure": figure, "mean_per_day": mean}


def _comparison(kind: str, window: int | None) -> dict[str, JsonValue]:
    weekday: dict[str, JsonValue] = {
        "weekday": "Monday",
        "group": _side(kind, 4, 2, 2.0),
        "baseline": _side("baseline", 60, 20, 3.0),
    }
    return {
        "day_kind": kind,
        "window_days": window,
        "group": _side(kind, 30, 10, 3.0),
        "baseline_same_weekdays": _side("baseline", 200, 100, 2.0),
        "by_weekday": [weekday],
        "statement": f"Statement {kind} {window}.",
    }


def _section() -> dict[str, JsonValue]:
    return {
        "status": "available",
        "span": {"first": "2022-01-01", "last": "2023-12-31"},
        "years_used": [2022],
        "years_unavailable": [2023],
        "records_used": 90,
        "records_left_out_unavailable_years": 10,
        "days_left_out_unavailable_years": 365,
        "holiday_days": _comparison("holiday", None),
        "windows": [_comparison("before", 1), _comparison("after", 1), _comparison("before", 3)],
    }


def _hand_built() -> dict[str, JsonValue]:
    findings: dict[str, JsonValue] = {
        "calendar": "holidays package, country KH",
        "windows_days": [1, 3],
        "note": "Edge effects apply.",
        "booking_date": _section(),
        "arrival_date": {"status": "unavailable", "reason": "no arrival dates"},
    }
    return {"analyses": {"holidays": {"status": "available", "findings": findings}}}


def test_holiday_window_options_come_from_the_result() -> None:
    view = build_holiday_view(_hand_built())

    assert view.windows_days == (1, 3)
    assert view.window_options() == {"1 day": 1, "3 days": 3}


def test_holiday_sections_keep_booking_and_arrival_dates_separate() -> None:
    view = build_holiday_view(_hand_built())

    assert list(view.sections) == ["booking_date", "arrival_date"]
    assert view.sections["booking_date"].title.startswith("Booking-date")
    assert view.sections["arrival_date"].title.startswith("Arrival-date")
    assert view.sections["arrival_date"].unavailable == "no arrival dates"


def test_holiday_comparison_table_follows_window_selection_with_day_counts() -> None:
    section = build_holiday_view(_hand_built()).sections["booking_date"]

    rows = section.comparison_table(3)

    assert [r["comparison"] for r in rows] == ["On holidays", "3-day window before holidays"]
    assert rows[0]["days"] == "10"
    assert rows[0]["baseline days (same weekdays)"] == "100"
    assert rows[0]["baseline records"] == "200"
    assert [r["comparison"] for r in section.comparison_table(1)][1:] == [
        "1-day window before holidays",
        "1-day window after holidays",
    ]


def test_holiday_weekday_table_flags_small_samples() -> None:
    section = build_holiday_view(_hand_built()).sections["booking_date"]

    row = section.weekday_table(1)[0]

    assert row["weekday"] == "Monday"
    assert row["days"] == "2"
    assert row["small sample"] == "small sample"
    assert row["baseline small sample"] == ""


def test_holiday_coverage_lines_state_years_used_and_unavailable() -> None:
    lines = build_holiday_view(_hand_built()).sections["booking_date"].coverage_lines()

    assert "Years with holidays used: 2022" in lines
    assert "Years without holiday data: 2023" in lines
    assert any("10" in line and "365 days" in line for line in lines)


def test_holiday_view_keeps_note_and_statements() -> None:
    view = build_holiday_view(_hand_built())

    assert view.note == "Edge effects apply."
    assert view.sections["booking_date"].statements(3) == [
        "Statement holiday None.",
        "Statement before 3.",
    ]


def test_holiday_view_is_tolerant_of_missing_result() -> None:
    view = build_holiday_view({})

    assert view.message is not None
    assert view.window_options() == {}
    assert view.sections == {}


def test_holiday_view_reads_both_sections_of_a_real_result(development_result: Result) -> None:
    view = build_holiday_view(development_result)

    assert view.window_options() == {"1 day": 1, "3 days": 3, "7 days": 7}
    for section in view.sections.values():
        assert section.years_used
        assert len(section.comparison_table(7)) == 3
        assert len(section.weekday_table(7)) == 21
    assert view.note is not None and "neighbouring year" in view.note
