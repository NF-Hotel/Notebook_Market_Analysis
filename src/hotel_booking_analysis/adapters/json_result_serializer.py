"""Serialize an analysis result to compact JSON (ADR-0002, ADR-0003 line format, US-001.08).

The schema for version 1.0 is `schemas/analysis_result_1_0.schema.json`.
"""

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from importlib import resources
from typing import Any

from hotel_booking_analysis.domain.analysis import Analysis, JsonValue
from hotel_booking_analysis.domain.errors import Notice
from hotel_booking_analysis.domain.quality import DataQualitySummary
from hotel_booking_analysis.domain.result import AnalysisResult

SCHEMA_RESOURCE = "analysis_result_1_0.schema.json"


# Any is justified: a JSON Schema document is free-form JSON consumed by jsonschema.
def load_result_schema() -> dict[str, Any]:
    """Return the JSON Schema of result version 1.0 (ADR-0002)."""
    text = (
        resources.files("hotel_booking_analysis.adapters")
        .joinpath("schemas", SCHEMA_RESOURCE)
        .read_text(encoding="utf-8")
    )
    document: dict[str, Any] = json.loads(text)
    return document


def _timestamp(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _iso(day: date | None) -> str | None:
    return day.isoformat() if day is not None else None


def _notice(notice: Notice) -> dict[str, JsonValue]:
    return {"code": notice.code, "message": notice.message}


def _data_quality(summary: DataQualitySummary) -> dict[str, JsonValue]:
    return {
        "record_count": summary.record_count,
        "earliest_booking_date": _iso(summary.earliest_booking_date),
        "latest_booking_date": _iso(summary.latest_booking_date),
        "earliest_arrival_date": _iso(summary.earliest_arrival_date),
        "latest_arrival_date": _iso(summary.latest_arrival_date),
        "duplicate_booking_id_count": summary.duplicate_booking_id_count,
        "missing_counts": dict(summary.missing_counts),
        "invalid_counts": dict(summary.invalid_counts),
        "zero_price_count": summary.zero_price_count,
        "unknown_fields": list(summary.unknown_fields),
    }


def _analysis(analysis: Analysis) -> dict[str, JsonValue]:
    entry: dict[str, JsonValue] = {"status": analysis.availability.value}
    if analysis.reason is not None:
        entry["reason"] = analysis.reason
    entry["findings"] = dict(analysis.findings)
    return entry


def result_to_document(result: AnalysisResult) -> dict[str, JsonValue]:
    """Convert a result to its JSON-shaped document; absent parts are left out (ADR-0002)."""
    document: dict[str, JsonValue] = {
        "schema_version": result.schema_version,
        "result_id": result.result_id,
        "generated_at": _timestamp(result.generated_at),
        "status": result.status.value,
    }
    if result.input is not None:
        document["input"] = {
            "source": result.input.source.value,
            "reference": result.input.reference,
            "record_count": result.input.record_count,
            "content_sha256": result.input.content_sha256,
        }
    if result.data_quality is not None:
        document["data_quality"] = _data_quality(result.data_quality)
    document["analyses"] = {a.name.value: _analysis(a) for a in result.analyses}
    document["notices"] = [_notice(n) for n in result.notices]
    if result.error is not None:
        document["error"] = {"code": result.error.code, "message": result.error.message}
    return document


def _default(value: object) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")  # money is a decimal string, never a float (ADR-0002)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


class JsonResultSerializer:
    """Serializes to one line of compact JSON without a trailing newline (ADR-0003).

    Output is ASCII-escaped, which is valid UTF-8 and keeps every line break out of the text.
    """

    def serialize(self, result: AnalysisResult) -> str:
        return json.dumps(
            result_to_document(result),
            separators=(",", ":"),
            ensure_ascii=True,
            default=_default,
        )
