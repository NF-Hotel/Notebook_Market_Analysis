"""Tests for the seasonality view model (US-001.04)."""

from hotel_booking_analysis.domain.analysis import JsonValue
from hotel_booking_analysis.interface.seasonality_view import build_seasonality_view
from tests.interface.builders import Result


def _period(name: str, count: int, partial: bool) -> dict[str, JsonValue]:
    return {
        "figure": {"group": name, "numerator": count, "denominator": 50, "small_sample": count < 5},
        "partial_period": partial,
        "cancellation": {"group": "c", "numerator": 1, "denominator": count, "small_sample": True},
        "mean_price_per_night": {"value": "19", "count": count, "small_sample": False},
    }


def _hand_built() -> dict[str, JsonValue]:
    series: dict[str, JsonValue] = {
        "status": "available",
        "span": {"first": "2021-03-08", "last": "2021-04-02"},
        "summary": "50 bookings were observed.",
        "monthly": {"periods": [_period("2021-03", 3, True), _period("2021-04", 40, False)]},
        "iso_week": {"periods": [_period("2021-W10", 3, False)]},
        "incomplete_years": [{"year": 2021, "months_present": 2}],
        "unavailable_parts": {"weekday": "no data"},
    }
    return {
        "analyses": {
            "seasonality": {
                "status": "available",
                "findings": {"note": "Separate series.", "bookings": series},
            }
        }
    }


def test_seasonality_view_offers_only_series_present_and_both_granularities() -> None:
    view = build_seasonality_view(_hand_built())

    assert view.series_options() == {"By booking date (bookings)": "bookings"}
    assert view.granularity_options() == {"Monthly": "monthly", "ISO week": "iso_week"}


def test_seasonality_table_marks_partial_periods_and_shows_denominators() -> None:
    view = build_seasonality_view(_hand_built())

    monthly = view.table("bookings", "monthly")
    weekly = view.table("bookings", "iso_week")

    assert monthly[0]["partial period"] == "partial"
    assert monthly[1]["partial period"] == ""
    assert monthly[0]["small sample"] == "small sample"
    assert monthly[0]["of all records"] == "50"
    assert monthly[0]["cancelled"] == "1 of 3 (33.3%)"
    assert monthly[0]["mean price per night"] == "19 (n=3)"
    assert [r["period"] for r in weekly] == ["2021-W10"]


def test_seasonality_statements_state_span_incomplete_years_and_unavailable_parts() -> None:
    lines = build_seasonality_view(_hand_built()).statements("bookings")

    assert "Observed dates: 2021-03-08 to 2021-04-02" in lines
    assert "Year 2021 is incomplete: 2 months present." in lines
    assert "weekday: not available - no data" in lines


def test_seasonality_view_is_tolerant_of_missing_series() -> None:
    view = build_seasonality_view({})

    assert view.message is not None
    assert view.table("arrivals", "monthly") == []
    assert view.statements("arrivals") == []


def test_seasonality_view_has_both_series_with_partial_periods_in_real_result(
    development_result: Result,
) -> None:
    view = build_seasonality_view(development_result)

    assert set(view.series_options().values()) == {"bookings", "arrivals"}
    rows = view.table("bookings", "monthly")
    assert any(r["partial period"] == "partial" for r in rows)
    assert view.table("arrivals", "iso_week")
