"""Tests for the room-value view model (US-001.06, ADR-0007 Room value)."""

from hotel_booking_analysis.domain.analysis import JsonValue
from hotel_booking_analysis.domain.wording import ROOM_VALUE_LABEL
from hotel_booking_analysis.interface.limitations import ESTIMATE_LABEL
from hotel_booking_analysis.interface.room_value_view import build_room_value_view
from tests.interface.builders import Result


def _value_group(status: str, count: int, total: str) -> dict[str, JsonValue]:
    return {
        "figure": {"group": status, "numerator": count, "denominator": 10, "small_sample": False},
        "cancellation_status": status,
        "count": count,
        "total": total,
        "mean": "5.5",
        "zero_price_records": 1,
        "summary": f"Estimated value of {count} {status} bookings (an estimate).",
    }


def _hand_built() -> dict[str, JsonValue]:
    findings: dict[str, JsonValue] = {
        "estimate": {"notice_code": "ESTIMATE_NOT_REVENUE", "label": ROOM_VALUE_LABEL, "unit": "u"},
        "zero_night_records": 2,
        "length_of_stay": {
            "total_nights": 40,
            "buckets": [
                {"group": "1", "numerator": 6, "denominator": 8, "small_sample": False},
            ],
        },
        "estimated_value": {
            "status": "available",
            "records_without_price": 3,
            "zero_price_records": 2,
            "groups": [_value_group("cancelled", 4, "22"), _value_group("not cancelled", 6, "33")],
        },
    }
    return {"analyses": {"room_value": {"status": "available", "findings": findings}}}


def test_room_value_view_keeps_cancelled_and_not_cancelled_in_separate_rows() -> None:
    rows = build_room_value_view(_hand_built()).value_table()

    assert [r["cancellation status"] for r in rows] == ["cancelled", "not cancelled"]
    assert [r["estimated value, total (u)"] for r in rows] == ["22", "33"]


def test_room_value_view_carries_the_estimate_label_and_code() -> None:
    view = build_room_value_view(_hand_built())

    assert view.estimate_label == ROOM_VALUE_LABEL
    assert view.estimate_code == "ESTIMATE_NOT_REVENUE"
    assert "not realized revenue" in view.statements()[0]


def test_room_value_view_falls_back_to_the_estimate_label_when_result_lacks_it() -> None:
    view = build_room_value_view({"analyses": {"room_value": {"status": "available"}}})

    assert view.estimate_label == ESTIMATE_LABEL
    assert view.message is not None


def test_room_value_view_shows_zero_counts_and_stay_length_buckets() -> None:
    view = build_room_value_view(_hand_built())
    lines = view.count_lines()

    assert any("zero nights" in line and line.endswith("2") for line in lines)
    assert any("price per night of zero" in line and line.endswith("2") for line in lines)
    assert view.stay_length_table()[0]["of stays"] == "8"
    assert view.total_nights == 40


def test_room_value_view_states_when_the_estimate_is_unavailable() -> None:
    result: dict[str, JsonValue] = {
        "analyses": {
            "room_value": {
                "status": "available",
                "findings": {"estimated_value": {"status": "unavailable", "reason": "no price"}},
            }
        }
    }

    view = build_room_value_view(result)

    assert view.value_table() == []
    assert any("no price" in line for line in view.statements())


def test_room_value_view_of_a_real_result_has_both_statuses_and_zero_price_counts(
    development_result: Result,
) -> None:
    view = build_room_value_view(development_result)

    statuses = [r["cancellation status"] for r in view.value_table()]
    assert statuses == ["cancelled", "not cancelled"]
    assert view.zero_price_records is not None and view.zero_price_records > 0
    assert view.stay_length_table()
