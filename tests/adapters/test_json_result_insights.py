"""Tests of the result 1.1 serialization and its schema (ADR-0011 "Result schema version 1.1")."""

import json
from collections.abc import Callable
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from hotel_booking_analysis.adapters.json_result_serializer import (
    JsonResultSerializer,
    load_result_schema,
)
from hotel_booking_analysis.application.build_result import build_result
from hotel_booking_analysis.application.validate_bookings import (
    ValidatedBookings,
    validate_bookings,
)
from hotel_booking_analysis.domain.booking import BookingRecord
from hotel_booking_analysis.domain.llm import ProviderName, ProviderReason
from hotel_booking_analysis.domain.result import AnalysisResult
from tests.insight_fakes import (
    MOMENT,
    RESULT_ID,
    FakeModelProvider,
    answering,
    insight_result,
    result_1_1_validator,
    timeout_on_call,
)
from tests.support import full_record, make_submission

VALIDATOR = result_1_1_validator()
ANALYSIS_KEYS = ["lead_time", "holidays", "seasonality", "cancellations", "room_value", "guest_mix"]
PARTLY_AVAILABLE = BookingRecord(lead_time=5, missing_fields=frozenset({"is_canceled"}))


def _document(result: AnalysisResult) -> dict[str, Any]:  # JSON document, shape checked by schema
    parsed: dict[str, Any] = json.loads(JsonResultSerializer().serialize(result))
    return parsed


def _validated(*records: BookingRecord) -> ValidatedBookings:
    return validate_bookings(make_submission(*records))


def _all_available() -> AnalysisResult:
    return insight_result(_validated(full_record()), FakeModelProvider())


def _no_provider() -> AnalysisResult:
    down = FakeModelProvider(reason=ProviderReason.TIMEOUT)
    return insight_result(_validated(full_record()), down)


def _one_timeout() -> AnalysisResult:
    return insight_result(
        _validated(full_record()), FakeModelProvider(respond=timeout_on_call(1, 4))
    )


def _rejected() -> AnalysisResult:
    provider = FakeModelProvider(respond=answering("no json"))
    return insight_result(_validated(full_record()), provider)


def _with_unavailable_analysis() -> AnalysisResult:
    return insight_result(_validated(PARTLY_AVAILABLE), FakeModelProvider())


VARIANTS: list[Callable[[], AnalysisResult]] = [
    _all_available,
    _no_provider,
    _one_timeout,
    _rejected,
    _with_unavailable_analysis,
]


def test_schema_1_1_is_a_valid_json_schema() -> None:
    Draft202012Validator.check_schema(VALIDATOR.schema)


@pytest.mark.parametrize("make", VARIANTS, ids=lambda make: make.__name__.strip("_"))
def test_serialize_every_insight_variant_validates_against_schema_1_1(
    make: Callable[[], AnalysisResult],
) -> None:
    document = _document(make())

    VALIDATOR.validate(document)
    assert document["schema_version"] == "1.1"
    assert list(document["analyses"]) == ANALYSIS_KEYS


def test_serialize_available_insight_is_labeled_with_provider_model_and_time() -> None:
    document = _document(_all_available())

    assert document["insights"] == {
        "requested": True,
        "provider": "ollama",
        "model": "m1",
        "prompt_version": "1",
    }
    for entry in document["analyses"].values():
        insight = entry["insight"]
        assert insight["status"] == "available"
        assert insight["reason"] is None
        assert insight["label"] == "AI-generated"
        assert (insight["provider"], insight["model"]) == ("ollama", "m1")
        assert insight["generated_at"] == "2026-09-29T12:00:00.000Z"
        assert insight["executive_summary"]
        (suggestion,) = insight["improvement_suggestions"]
        assert set(suggestion) == {"suggestion", "evidence", "sample_size"}
        assert suggestion["sample_size"] == 1


def test_serialize_without_provider_gives_null_metadata_and_unavailable_insights() -> None:
    document = _document(_no_provider())

    assert document["insights"]["provider"] is None
    assert document["insights"]["model"] is None
    for entry in document["analyses"].values():
        assert entry["insight"] == {
            "status": "unavailable",
            "reason": "NO_PROVIDER",
            "label": None,
            "provider": None,
            "model": None,
            "generated_at": None,
            "executive_summary": None,
            "improvement_suggestions": [],
        }
    assert document["status"] == "completed_with_warnings"
    assert [n["code"] for n in document["notices"]][-1] == "INSIGHTS_UNAVAILABLE"


def test_serialize_failed_insight_keeps_the_tried_provider_and_model_but_no_text() -> None:
    document = _document(_one_timeout())

    insights = [entry["insight"] for entry in document["analyses"].values()]
    assert [i["reason"] for i in insights] == ["TIMEOUT", None, None, "TIMEOUT", None, None]
    failed = insights[0]
    assert (failed["provider"], failed["model"]) == ("ollama", "m1")
    assert failed["executive_summary"] is None
    assert failed["label"] is None


def test_serialize_unavailable_analysis_has_a_not_applicable_insight_without_provider() -> None:
    document = _document(_with_unavailable_analysis())

    entry = document["analyses"]["cancellations"]
    assert entry["status"] == "unavailable"
    assert entry["insight"]["status"] == "not_applicable"
    assert entry["insight"]["provider"] is None
    assert entry["insight"]["model"] is None
    assert entry["insight"]["reason"] is None
    assert document["analyses"]["lead_time"]["insight"]["status"] == "available"


def test_serialize_lmstudio_provider_is_named_in_the_metadata() -> None:
    provider = FakeModelProvider(ProviderName.LMSTUDIO, ("phi-3",))

    document = _document(insight_result(_validated(full_record()), provider))

    assert document["insights"]["provider"] == "lmstudio"
    assert document["insights"]["model"] == "phi-3"


def test_result_without_insights_is_identical_to_the_version_1_0_result() -> None:
    plain = build_result(_validated(full_record()), (), RESULT_ID, MOMENT)

    document = _document(plain)

    assert document["schema_version"] == "1.0"
    assert "insights" not in document
    assert all("insight" not in entry for entry in document["analyses"].values())
    Draft202012Validator(load_result_schema()).validate(document)


def _drop_analysis_insight(d: dict[str, Any]) -> None:
    del d["analyses"]["lead_time"]["insight"]


def _drop_insights(d: dict[str, Any]) -> None:
    del d["insights"]


def _label_unavailable(d: dict[str, Any]) -> None:
    d["analyses"]["lead_time"]["insight"].update(status="unavailable", reason="TIMEOUT")


def _unavailable_without_reason(d: dict[str, Any]) -> None:
    d["analyses"]["lead_time"]["insight"].update(
        status="unavailable", label=None, generated_at=None, executive_summary=None
    )
    d["analyses"]["lead_time"]["insight"]["improvement_suggestions"] = []


def _available_without_suggestions(d: dict[str, Any]) -> None:
    d["analyses"]["lead_time"]["insight"]["improvement_suggestions"] = []


def _suggestion_without_sample_size(d: dict[str, Any]) -> None:
    del d["analyses"]["lead_time"]["insight"]["improvement_suggestions"][0]["sample_size"]


def _unknown_reason(d: dict[str, Any]) -> None:
    d["analyses"]["lead_time"]["insight"].update(status="unavailable", reason="SLOW")


def _failed_with_1_1(d: dict[str, Any]) -> None:
    d["status"] = "failed"


@pytest.mark.parametrize(
    "mutate",
    [
        _drop_analysis_insight,
        _drop_insights,
        _label_unavailable,
        _unavailable_without_reason,
        _available_without_suggestions,
        _suggestion_without_sample_size,
        _unknown_reason,
        _failed_with_1_1,
        lambda d: d.update(schema_version="1.0"),
        lambda d: d["insights"].update(requested=False),
        lambda d: d["analyses"]["lead_time"]["insight"].update(extra=1),
    ],
)
def test_schema_1_1_rejects_a_document_that_breaks_a_rule(
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    document = _document(_all_available())
    mutate(document)

    assert not VALIDATOR.is_valid(document)


def test_schema_1_1_rejects_an_available_insight_on_an_unavailable_analysis() -> None:
    document = _document(_with_unavailable_analysis())
    document["analyses"]["cancellations"]["insight"] = document["analyses"]["lead_time"]["insight"]

    assert not VALIDATOR.is_valid(document)
