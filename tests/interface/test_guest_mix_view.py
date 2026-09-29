"""Tests for the guest-mix view model (US-001.07)."""

from hotel_booking_analysis.domain.analysis import JsonValue
from hotel_booking_analysis.interface.guest_mix_view import build_guest_mix_view
from tests.interface.builders import Result


def _available(count: int) -> dict[str, JsonValue]:
    return {
        "status": "available",
        "mean_length_of_stay": {"value": "2.5", "count": count, "small_sample": False},
        "cancellation_share": {
            "group": "c",
            "numerator": 5,
            "denominator": count,
            "small_sample": False,
        },
        "mean_price_per_night": {"value": "21.5", "count": count, "small_sample": False},
    }


def _group(name: str, count: int, comparison: dict[str, JsonValue]) -> dict[str, JsonValue]:
    figure: dict[str, JsonValue] = {
        "group": name,
        "numerator": count,
        "denominator": 100,
        "small_sample": count < 30,
    }
    return {"figure": figure, "comparison": comparison}


def _hand_built() -> dict[str, JsonValue]:
    omitted: dict[str, JsonValue] = {
        "status": "omitted_small_sample",
        "statement": "No comparison is stated for group 'FR'; it is a small sample of 4 records.",
    }
    findings: dict[str, JsonValue] = {
        "note": "Distributions.",
        "distributions": {
            "country": {
                "status": "available",
                "records_used": 100,
                "groups": [_group("PT", 96, _available(96)), _group("FR", 4, omitted)],
            },
            "meal": {"status": "unavailable", "reason": "meal missing"},
        },
    }
    return {"analyses": {"guest_mix": {"status": "available", "findings": findings}}}


def test_guest_mix_table_shows_counts_shares_and_comparisons() -> None:
    rows = build_guest_mix_view(_hand_built()).table("country")

    assert rows[0]["group"] == "PT"
    assert rows[0]["records"] == "96"
    assert rows[0]["of all records"] == "100"
    assert rows[0]["share"] == "96.0%"
    assert rows[0]["mean length of stay (nights)"] == "2.5 (n=96)"
    assert rows[0]["cancelled"] == "5 of 96 (5.2%)"


def test_guest_mix_states_omitted_comparisons_for_small_samples() -> None:
    view = build_guest_mix_view(_hand_built())

    rows = view.table("country")
    lines = view.statements("country")

    assert rows[1]["small sample"] == "small sample"
    assert rows[1]["cancelled"] == "omitted: small sample"
    assert "No comparison is stated for group 'FR'; it is a small sample of 4 records." in lines


def test_guest_mix_offers_available_attributes_and_states_unavailable_ones() -> None:
    view = build_guest_mix_view(_hand_built())

    assert view.attribute_options() == {"Country": "country"}
    assert any("meal missing" in line for line in view.statements("country"))


def test_guest_mix_view_is_tolerant_of_missing_result() -> None:
    view = build_guest_mix_view({})

    assert view.message is not None
    assert view.table("country") == []


def test_guest_mix_view_reads_all_seven_distributions_of_a_real_result(
    development_result: Result,
) -> None:
    view = build_guest_mix_view(development_result)

    assert len(view.attribute_options()) == 7
    assert any("small sample" in line for line in view.statements("total_guests"))
