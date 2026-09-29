"""Tests for the lead-time view model (US-001.02)."""

from hotel_booking_analysis.domain.analysis import JsonValue
from hotel_booking_analysis.interface.lead_time_view import build_lead_time_view
from tests.interface.builders import Result


def _group(name: str, count: int, small: bool = False) -> dict[str, JsonValue]:
    band: dict[str, JsonValue] = {
        "group": "0-7",
        "numerator": 3,
        "denominator": count,
        "small_sample": True,
    }
    return {
        "figure": {"group": name, "numerator": count, "denominator": 100, "small_sample": small},
        "median_days": 12,
        "bands": [band],
    }


def _hand_built() -> dict[str, JsonValue]:
    return {
        "analyses": {
            "lead_time": {
                "status": "available",
                "findings": {
                    "overall": {**_group("all", 100), "summary": "The median was 12 days."},
                    "splits": {
                        "by_market_segment": {
                            "status": "available",
                            "groups": [_group("Online", 90), _group("Groups", 10, small=True)],
                        },
                        "by_customer_type": {"status": "unavailable", "reason": "no field"},
                    },
                    "date_comparison": {"status": "available", "summary": "0 of 100 differed."},
                },
            }
        }
    }


def test_lead_time_view_offers_only_splits_that_have_data() -> None:
    view = build_lead_time_view(_hand_built())

    assert view.split_options() == {"Overall": "overall", "Market segment": "by_market_segment"}
    assert "Customer type" in " ".join(view.statements())


def test_lead_time_view_shows_sample_sizes_and_small_sample_flags_per_group() -> None:
    view = build_lead_time_view(_hand_built())

    rows = view.summary_table("by_market_segment")

    assert [r["group"] for r in rows] == ["Online", "Groups"]
    assert rows[0]["records"] == "90"
    assert rows[1]["small sample"] == "small sample"
    assert rows[0]["median lead time (days)"] == "12"


def test_lead_time_band_table_shows_group_denominator_and_share() -> None:
    view = build_lead_time_view(_hand_built())

    band = view.band_table("by_market_segment")[0]

    assert band["of group"] == "90"
    assert band["share"] == "3.3%"
    assert band["small sample"] == "small sample"


def test_lead_time_view_includes_date_comparison_statement() -> None:
    view = build_lead_time_view(_hand_built())

    assert "0 of 100 differed." in view.statements()


def test_lead_time_view_is_tolerant_of_empty_and_unavailable_results() -> None:
    empty = build_lead_time_view({})
    gone = build_lead_time_view(
        {"analyses": {"lead_time": {"status": "unavailable", "reason": "no lead_time field"}}}
    )

    assert empty.message and not empty.split_options()
    assert gone.message is not None and "no lead_time field" in gone.message
    assert empty.summary_table("by_market_segment") == []


def test_lead_time_view_reads_every_split_of_a_real_result(development_result: Result) -> None:
    view = build_lead_time_view(development_result)

    assert set(view.split_options().values()) == {
        "overall",
        "by_cancellation_status",
        "by_arrival_month",
        "by_market_segment",
        "by_customer_type",
    }
    overall = view.summary_table("overall")[0]
    assert overall["records"] == str(development_result["data_quality"]["record_count"])
    assert view.band_table("by_arrival_month")
