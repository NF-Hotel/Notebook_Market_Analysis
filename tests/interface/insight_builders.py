"""Hand-built result 1.1 documents for the insight view tests (MIL-011)."""

from typing import Any

from tests.interface.builders import Result

ANALYSES = ("lead_time", "seasonality", "holidays", "cancellations", "room_value", "guest_mix")
AI_TEXT = "Consider a change; it may help."


def available_insight(
    summary: str = "The findings describe the observed data only.",
    suggestion: str = AI_TEXT,
    sample_size: int | None = 7,
) -> dict[str, Any]:
    return {
        "status": "available",
        "reason": None,
        "label": "AI-generated",
        "provider": "ollama",
        "model": "m1",
        "generated_at": "2026-09-29T12:00:01.250Z",
        "executive_summary": summary,
        "improvement_suggestions": [
            {
                "suggestion": suggestion,
                "evidence": "Observed in 7 records.",
                "sample_size": sample_size,
            }
        ],
    }


def unavailable_insight(reason: str | None = "NO_PROVIDER") -> dict[str, Any]:
    return {
        "status": "unavailable",
        "reason": reason,
        "label": None,
        "provider": None,
        "model": None,
        "generated_at": None,
        "executive_summary": None,
        "improvement_suggestions": [],
    }


def with_insight(result: Result, insight: object, analysis: str = "lead_time") -> Result:
    """A copy of `result` whose `analysis` entry holds `insight`, as schema 1.1."""
    analyses = {name: dict(entry) for name, entry in result["analyses"].items()}
    analyses[analysis] = {**analyses.get(analysis, {}), "insight": insight}
    return {**result, "schema_version": "1.1", "analyses": analyses}


def with_insights(result: Result, insight: dict[str, Any] | None = None) -> Result:
    """A copy of `result` with the same insight on every analysis and the result-level object."""
    document = result
    for name in ANALYSES:
        document = with_insight(document, insight or available_insight(), name)
    return {
        **document,
        "insights": {
            "requested": True,
            "provider": "ollama",
            "model": "m1",
            "prompt_version": "1",
        },
    }
