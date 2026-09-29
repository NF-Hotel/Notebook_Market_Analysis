"""Tests for the cancellation view model (US-001.05)."""

from hotel_booking_analysis.domain.analysis import JsonValue
from hotel_booking_analysis.interface.cancellation_view import build_cancellation_view
from tests.interface.builders import Result


def _group(name: str, cancelled: int, total: int, small: bool = False) -> dict[str, JsonValue]:
    figure: dict[str, JsonValue] = {
        "group": name,
        "numerator": cancelled,
        "denominator": total,
        "small_sample": small,
    }
    return {"figure": figure}


def _hand_built() -> dict[str, JsonValue]:
    findings: dict[str, JsonValue] = {
        "note": "Observed associations.",
        "overall": {"group": "all", "numerator": 30, "denominator": 100, "small_sample": False},
        "splits": {
            "by_deposit_type": {
                "status": "available",
                "records_used": 95,
                "records_left_out": 5,
                "summary": "Cancellation share by deposit type.",
                "groups": [_group("No Deposit", 20, 80), _group("Refundable", 1, 4, small=True)],
            },
            "by_market_segment": {"status": "unavailable", "reason": "market_segment missing"},
        },
    }
    return {"analyses": {"cancellations": {"status": "available", "findings": findings}}}


def test_cancellation_table_has_overall_row_then_groups_with_counts() -> None:
    view = build_cancellation_view(_hand_built())

    rows = view.table("by_deposit_type")

    assert [r["group"] for r in rows] == ["All bookings", "No Deposit", "Refundable"]
    assert rows[1]["cancelled"] == "20"
    assert rows[1]["bookings in group"] == "80"
    assert rows[1]["cancellation share"] == "25.0%"
    assert rows[2]["small sample"] == "small sample"


def test_cancellation_view_offers_available_splits_and_states_unavailable_ones() -> None:
    view = build_cancellation_view(_hand_built())

    assert view.split_options() == {"Deposit type": "by_deposit_type"}
    lines = view.statements("by_deposit_type")
    assert any("market_segment missing" in line for line in lines)
    assert any("5 records were left out" in line for line in lines)


def test_cancellation_view_is_tolerant_of_missing_result() -> None:
    view = build_cancellation_view({})

    assert view.message is not None
    assert view.table("by_deposit_type") == []


def test_cancellation_view_lists_all_seven_splits_of_a_real_result(
    development_result: Result,
) -> None:
    view = build_cancellation_view(development_result)

    assert len(view.split_options()) == 7
    assert view.table("by_customer_type")[0]["group"] == "All bookings"
