"""Shared checks that the marimo view models show what a stored insight says (MIL-011, MIL-012)."""

from pathlib import Path
from typing import Any

from hotel_booking_analysis.interface.history_source import load_history
from hotel_booking_analysis.interface.history_view import build_history_view
from hotel_booking_analysis.interface.insight_view import (
    STATE_AVAILABLE,
    InsightView,
    build_insight_view,
)
from tests.interface.insight_builders import ANALYSES


def views_of_history(
    config: Path, working_directory: Path
) -> list[tuple[dict[str, Any], dict[str, InsightView]]]:
    """Every listed result (newest first) with its six insight views built from the history."""
    loaded = load_history(working_directory, {"HOTEL_ANALYSIS_CONFIG": str(config)})
    assert loaded.error is None
    listed = build_history_view(loaded.readout)
    return [
        (dict(result), {name: build_insight_view(result, name) for name in ANALYSES})
        for result in listed.results
    ]


def assert_view_matches_stored_insight(
    view: InsightView, stored: dict[str, Any], record_count: int
) -> None:
    assert view.state == STATE_AVAILABLE == stored["status"]
    assert (view.label, view.provider, view.model) == ("AI-generated", "ollama", "m1")
    assert view.label == stored["label"]
    assert view.provider == stored["provider"]
    assert view.model == stored["model"]
    assert view.generated_at == stored["generated_at"]
    assert view.executive_summary == stored["executive_summary"]
    assert [(s.suggestion, s.evidence, s.sample_size) for s in view.suggestions] == [
        (s["suggestion"], s["evidence"], s["sample_size"])
        for s in stored["improvement_suggestions"]
    ]
    assert [s.sample_size for s in view.suggestions] == [record_count]
    assert {row["sample size"] for row in view.suggestion_table()} == {str(record_count)}
