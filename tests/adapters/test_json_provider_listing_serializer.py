"""Tests for the provider listing serializer and its schema (ADR-0011, UC-004)."""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest
from jsonschema import Draft202012Validator, ValidationError

from hotel_booking_analysis.adapters.json_provider_listing_serializer import (
    JsonProviderListingSerializer,
    load_provider_listing_schema,
)
from hotel_booking_analysis.domain.errors import Notice
from hotel_booking_analysis.domain.llm import (
    LanguageModelProvider,
    ProviderListing,
    ProviderName,
    ProviderReason,
    ProviderStatus,
)
from hotel_booking_analysis.domain.result import ResultError

MOMENT = datetime(2026, 9, 30, 8, 0, 1, 250000, tzinfo=UTC)
VALIDATOR = Draft202012Validator(load_provider_listing_schema())
OLLAMA = LanguageModelProvider(ProviderName.OLLAMA, "http://localhost:11434")
LMSTUDIO = LanguageModelProvider(ProviderName.LMSTUDIO, "http://localhost:1234")
NONE_REACHABLE = Notice("NO_PROVIDER_REACHABLE", "No language model provider could be reached.")


def _document(line: str) -> dict[str, Any]:  # JSON document, shape checked by the schema
    parsed: dict[str, Any] = json.loads(line)
    return parsed


def _listing(*statuses: ProviderStatus, notices: tuple[Notice, ...] = ()) -> dict[str, Any]:
    line = JsonProviderListingSerializer().serialize(ProviderListing(MOMENT, statuses, notices))
    return _document(line)


def _reachable() -> tuple[ProviderStatus, ProviderStatus]:
    return (
        ProviderStatus.reachable_with(OLLAMA, ("llama3", "qwen")),
        ProviderStatus.reachable_with(LMSTUDIO, ()),
    )


def test_schema_is_a_valid_json_schema() -> None:
    Draft202012Validator.check_schema(load_provider_listing_schema())


def test_serialize_reachable_providers_has_the_adr_0011_shape() -> None:
    document = _listing(*_reachable())

    VALIDATOR.validate(document)
    assert document == {
        "schema_version": "1.0",
        "kind": "llm_providers",
        "status": "completed",
        "generated_at": "2026-09-30T08:00:01.250Z",
        "notices": [],
        "providers": [
            {
                "provider": "ollama",
                "base_url": "http://localhost:11434",
                "status": "reachable",
                "reason": None,
                "models": [{"name": "llama3"}, {"name": "qwen"}],
            },
            {
                "provider": "lmstudio",
                "base_url": "http://localhost:1234",
                "status": "reachable",
                "reason": None,
                "models": [],
            },
        ],
    }


@pytest.mark.parametrize("reason", list(ProviderReason))
def test_serialize_unreachable_provider_carries_its_reason(reason: ProviderReason) -> None:
    document = _listing(
        ProviderStatus.unreachable_because(OLLAMA, reason),
        ProviderStatus.reachable_with(LMSTUDIO, ("phi",)),
    )

    VALIDATOR.validate(document)
    assert document["providers"][0]["status"] == "unreachable"
    assert document["providers"][0]["reason"] == reason.value
    assert document["providers"][0]["models"] == []


def test_serialize_no_provider_reachable_with_notice_validates() -> None:
    document = _listing(
        ProviderStatus.unreachable_because(OLLAMA, ProviderReason.CONNECTION_REFUSED),
        ProviderStatus.unreachable_because(LMSTUDIO, ProviderReason.TIMEOUT),
        notices=(NONE_REACHABLE,),
    )

    VALIDATOR.validate(document)
    assert document["status"] == "completed"
    assert document["notices"][0]["code"] == "NO_PROVIDER_REACHABLE"


def test_serialize_writes_one_compact_ascii_line() -> None:
    status = ProviderStatus.reachable_with(OLLAMA, ("modèle",))
    line = JsonProviderListingSerializer().serialize(ProviderListing(MOMENT, (status, status)))

    assert "\n" not in line
    assert ": " not in line
    assert ", " not in line
    assert line.isascii()
    assert json.loads(line)["providers"][0]["models"][0]["name"] == "modèle"


def test_serialize_failure_has_error_and_no_providers_and_validates() -> None:
    line = JsonProviderListingSerializer().serialize_failure(
        ResultError("CONFIGURATION_ERROR", "'llm.ollama_url' names a remote host."), (), MOMENT
    )

    document = _document(line)

    VALIDATOR.validate(document)
    assert document == {
        "schema_version": "1.0",
        "kind": "llm_providers",
        "status": "failed",
        "generated_at": "2026-09-30T08:00:01.250Z",
        "notices": [],
        "error": {
            "code": "CONFIGURATION_ERROR",
            "message": "'llm.ollama_url' names a remote host.",
        },
    }


def _valid() -> dict[str, Any]:
    return _listing(*_reachable())


def _no_providers(document: dict[str, Any]) -> None:
    document["providers"].clear()


def _swap_order(document: dict[str, Any]) -> None:
    document["providers"].reverse()


def _third_provider(document: dict[str, Any]) -> None:
    document["providers"].append(document["providers"][0])


def _reachable_with_reason(document: dict[str, Any]) -> None:
    document["providers"][0]["reason"] = "TIMEOUT"


def _unreachable_without_reason(document: dict[str, Any]) -> None:
    document["providers"][0]["status"] = "unreachable"
    document["providers"][0]["models"] = []


def _unknown_reason(document: dict[str, Any]) -> None:
    document["providers"][0].update(status="unreachable", reason="BROKEN", models=[])


def _model_without_name(document: dict[str, Any]) -> None:
    document["providers"][0]["models"] = [{"id": "x"}]


def _extra_field(document: dict[str, Any]) -> None:
    document["providers"][0]["extra"] = 1


def _missing_base_url(document: dict[str, Any]) -> None:
    del document["providers"][0]["base_url"]


def _wrong_kind(document: dict[str, Any]) -> None:
    document["kind"] = "holiday_calendar"


def _wrong_version(document: dict[str, Any]) -> None:
    document["schema_version"] = "1.1"


def _missing_notice_when_none_reachable(document: dict[str, Any]) -> None:
    for provider in document["providers"]:
        provider.update(status="unreachable", reason="TIMEOUT", models=[])


def _notice_when_reachable(document: dict[str, Any]) -> None:
    document["notices"] = [{"code": NONE_REACHABLE.code, "message": NONE_REACHABLE.message}]


def _completed_with_error(document: dict[str, Any]) -> None:
    document["error"] = {"code": "CONFIGURATION_ERROR", "message": "x"}


def _failed_with_providers(document: dict[str, Any]) -> None:
    document["status"] = "failed"
    document["error"] = {"code": "CONFIGURATION_ERROR", "message": "x"}


@pytest.mark.parametrize(
    "corrupt",
    [
        _no_providers,
        _swap_order,
        _third_provider,
        _reachable_with_reason,
        _unreachable_without_reason,
        _unknown_reason,
        _model_without_name,
        _extra_field,
        _missing_base_url,
        _wrong_kind,
        _wrong_version,
        _missing_notice_when_none_reachable,
        _notice_when_reachable,
        _completed_with_error,
        _failed_with_providers,
    ],
)
def test_schema_rejects_a_document_that_breaks_the_contract(
    corrupt: Callable[[dict[str, Any]], None],
) -> None:
    document = _valid()
    corrupt(document)

    with pytest.raises(ValidationError):
        VALIDATOR.validate(document)


def test_schema_accepts_a_listing_with_one_provider() -> None:
    document = _valid()
    document["providers"].pop()

    VALIDATOR.validate(document)
