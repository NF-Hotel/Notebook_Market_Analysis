"""Tests of the HTTP API routes, status codes and byte equality with the command (ADR-0013).

The service runs in process behind FastAPI's test client with the production adapters on
`tmp_path`; the language model providers are refused connections or local fake servers.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from hotel_booking_analysis.adapters.json_holiday_listing_serializer import (
    load_holiday_listing_schema,
)
from hotel_booking_analysis.adapters.json_result_serializer import load_result_schema
from hotel_booking_analysis.infrastructure.http_api import BODY_REFERENCE
from tests.infrastructure.cli_support import BrokenStdout
from tests.infrastructure.http_support import (
    bookings_body,
    history_lines,
    make_client,
    write_config,
)
from tests.infrastructure.insight_servers import answer_for, fake_providers, ollama_answering
from tests.insight_fakes import result_1_1_validator
from tests.support import FixedClock, SequentialIds

RESULT_VALIDATOR = Draft202012Validator(load_result_schema())
HOLIDAY_VALIDATOR = Draft202012Validator(load_holiday_listing_schema())
JSON = {"Content-Type": "application/json"}
RECORD_COUNT = 30


@pytest.fixture(autouse=True)
def fixed_clock_and_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    """The same time and result identifiers for the service and the command."""
    monkeypatch.setattr("hotel_booking_analysis.infrastructure.bootstrap.SystemClock", FixedClock)
    monkeypatch.setattr(
        "hotel_booking_analysis.infrastructure.bootstrap.UuidGenerator", SequentialIds
    )


def test_health_reports_ok(tmp_path: Path) -> None:
    response = make_client(tmp_path).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_returns_the_result_that_was_appended_to_the_history(tmp_path: Path) -> None:
    response = make_client(tmp_path).post("/analyze", content=bookings_body(), headers=JSON)

    document = response.json()
    RESULT_VALIDATOR.validate(document)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert document["status"] == "completed"
    assert document["input"]["source"] == "supplied"
    assert document["input"]["reference"] == BODY_REFERENCE
    assert document["input"]["record_count"] == 2
    assert history_lines(tmp_path) == [response.content]


def test_analyze_accepts_a_content_type_with_parameters(tmp_path: Path) -> None:
    headers = {"Content-Type": "application/json; charset=utf-8"}

    response = make_client(tmp_path).post("/analyze", content=bookings_body(), headers=headers)

    assert response.status_code == 200


@pytest.mark.parametrize(
    ("body", "code"),
    [
        (b"not json", "INPUT_INVALID_JSON"),
        (b"", "INPUT_INVALID_JSON"),
        (b"{}", "INPUT_NOT_ARRAY"),
        (b"[]", "INPUT_EMPTY"),
        (b"[1]", "INPUT_RECORD_NOT_OBJECT"),
    ],
)
def test_analyze_input_error_returns_422_with_the_failed_document(
    tmp_path: Path, body: bytes, code: str
) -> None:
    response = make_client(tmp_path).post("/analyze", content=body, headers=JSON)

    document = response.json()
    RESULT_VALIDATOR.validate(document)
    assert response.status_code == 422
    assert document["status"] == "failed"
    assert document["error"]["code"] == code
    assert history_lines(tmp_path) == []


def test_analyze_configuration_error_returns_422_with_the_failed_document(tmp_path: Path) -> None:
    config = tmp_path / "broken.toml"
    config.write_text("this is = not [ toml", encoding="utf-8")

    response = make_client(tmp_path, config).post("/analyze", content=bookings_body(), headers=JSON)

    assert response.status_code == 422
    assert response.json()["status"] == "failed"
    assert history_lines(tmp_path) == []


def test_analyze_history_failure_returns_500_and_never_the_result(tmp_path: Path) -> None:
    (tmp_path / "blocker").write_text("a file, not a directory", encoding="utf-8")
    config = write_config(tmp_path, history="blocker/history.jsonl")

    response = make_client(tmp_path, config).post("/analyze", content=bookings_body(), headers=JSON)

    document = response.json()
    assert response.status_code == 500
    assert document["status"] == "error"
    assert document["error"]["code"] == "HISTORY_FAILED"
    assert "No result was delivered" in document["error"]["message"]
    assert "result_id" not in document


@pytest.mark.parametrize(("body", "stored"), [(bookings_body(), 1), (b"not json", 0)])
def test_analyze_delivery_failure_returns_500_naming_the_result_id(
    tmp_path: Path, body: bytes, stored: int
) -> None:
    client = make_client(tmp_path, stream_factory=BrokenStdout)

    response = client.post("/analyze", content=body, headers=JSON)

    document = response.json()
    assert response.status_code == 500
    assert document["error"]["code"] == "DELIVERY_FAILED"
    assert document["result_id"] in document["error"]["message"]
    assert len(history_lines(tmp_path)) == stored
    if stored:
        assert json.loads(history_lines(tmp_path)[0])["result_id"] == document["result_id"]


@pytest.mark.parametrize("url", ["/holidays?years=2025", "/llm-providers"])
def test_listing_delivery_failure_returns_500_without_a_result_id(tmp_path: Path, url: str) -> None:
    response = make_client(tmp_path, stream_factory=BrokenStdout).get(url)

    document = response.json()
    assert response.status_code == 500
    assert document["error"]["code"] == "DELIVERY_FAILED"
    assert "result_id" not in document


def test_holidays_lists_the_requested_years(tmp_path: Path) -> None:
    response = make_client(tmp_path).get("/holidays", params={"years": "2025,2026"})

    document = response.json()
    HOLIDAY_VALIDATOR.validate(document)
    assert response.status_code == 200
    assert [entry["year"] for entry in document["years"]] == [2025, 2026]


@pytest.mark.parametrize("years", ["abc", "2026-2024", "1800"])
def test_holidays_with_invalid_years_returns_422_with_the_failed_document(
    tmp_path: Path, years: str
) -> None:
    response = make_client(tmp_path).get("/holidays", params={"years": years})

    document = response.json()
    HOLIDAY_VALIDATOR.validate(document)
    assert response.status_code == 422
    assert document["status"] == "failed"
    assert document["error"]["code"]


def test_llm_providers_with_no_reachable_provider_is_still_200(tmp_path: Path) -> None:
    response = make_client(tmp_path).get("/llm-providers")

    document = response.json()
    assert response.status_code == 200
    assert [n["code"] for n in document["notices"]] == ["NO_PROVIDER_REACHABLE"]


def test_llm_providers_with_a_bad_llm_value_returns_422(tmp_path: Path) -> None:
    config = write_config(tmp_path, "[llm]\ntemperature = 9\n")

    response = make_client(tmp_path, config).get("/llm-providers")

    assert response.status_code == 422
    assert "llm.temperature" in response.json()["error"]["message"]


def test_analyze_with_insights_returns_the_labeled_insights_and_stores_the_same_line(
    tmp_path: Path,
) -> None:
    with fake_providers(ollama_answering(answer_for(RECORD_COUNT))) as (ollama, llm_table):
        client = make_client(tmp_path, write_config(tmp_path, llm_table))

        response = client.post(
            "/analyze",
            params={"insights": "true"},
            content=bookings_body(RECORD_COUNT),
            headers=JSON,
        )

        assert ollama.requests == ["/api/tags", *["/api/chat"] * 6]
    document = response.json()
    result_1_1_validator().validate(document)
    assert response.status_code == 200
    assert document["schema_version"] == "1.1"
    assert {e["insight"]["status"] for e in document["analyses"].values()} == {"available"}
    assert history_lines(tmp_path) == [response.content]


def test_analyze_with_unavailable_insights_is_200_with_warnings(tmp_path: Path) -> None:
    response = make_client(tmp_path).post(
        "/analyze", params={"insights": "true"}, content=bookings_body(), headers=JSON
    )

    document = response.json()
    assert response.status_code == 200
    assert document["status"] == "completed_with_warnings"
    assert document["notices"][-1]["code"] == "INSIGHTS_UNAVAILABLE"
    assert history_lines(tmp_path) == [response.content]


def test_analyze_without_insights_never_contacts_a_provider(tmp_path: Path) -> None:
    with fake_providers(ollama_answering(answer_for(RECORD_COUNT))) as (ollama, llm_table):
        client = make_client(tmp_path, write_config(tmp_path, llm_table))

        response = client.post("/analyze", content=bookings_body(RECORD_COUNT), headers=JSON)

        assert ollama.requests == []
    assert response.status_code == 200
    assert response.json()["schema_version"] == "1.0"


@pytest.mark.parametrize("headers", [{"Content-Type": "text/plain"}, {}])
def test_analyze_requires_a_json_content_type(tmp_path: Path, headers: dict[str, str]) -> None:
    response = make_client(tmp_path).post("/analyze", content=bookings_body(), headers=headers)

    assert response.status_code == 415
    assert history_lines(tmp_path) == []


def test_analyze_with_a_malformed_insights_flag_is_rejected_by_the_framework(
    tmp_path: Path,
) -> None:
    response = make_client(tmp_path).post(
        "/analyze", params={"insights": "maybe"}, content=bookings_body(), headers=JSON
    )

    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.parametrize(
    ("method", "url", "status"),
    [("GET", "/unknown", 404), ("GET", "/analyze", 405), ("POST", "/holidays", 405)],
)
def test_unknown_routes_and_methods_use_the_framework_defaults(
    tmp_path: Path, method: str, url: str, status: int
) -> None:
    assert make_client(tmp_path).request(method, url).status_code == status


def test_openapi_description_and_docs_stay_enabled(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    description: dict[str, Any] = client.get("/openapi.json").json()

    assert client.get("/docs").status_code == 200
    assert set(description["paths"]) == {"/analyze", "/holidays", "/llm-providers", "/health"}
