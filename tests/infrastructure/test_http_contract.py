"""Contract tests of the HTTP API (ADR-0013, ADR-0011, MIL-012 criteria 2 and 4).

Every route and status of `SCENARIOS` is checked against the JSON Schema files of the repository,
against the command's output for the same input, and against the response schema that the OpenAPI
description gives it. The OpenAPI schemas must be the repository files and must not be vacuous.
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.openapi.models import OpenAPI
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from hotel_booking_analysis.infrastructure.http_api import ServiceSettings, create_app
from tests.infrastructure.http_scenarios import (
    ERROR_OBJECT,
    FRAMEWORK_ERROR,
    REPO_SCHEMAS,
    SCENARIOS,
    Outcome,
    Scenario,
    repo_validator,
    run_scenario,
)
from tests.support import FixedClock, SequentialIds

OPENAPI_URI = "urn:openapi"
SCHEMA_PREFIX = "#/components/schemas/"
SCENARIO_IDS = [scenario.name for scenario in SCENARIOS]
COMMAND_SCENARIOS = [scenario for scenario in SCENARIOS if scenario.cli is not None]
REPO_SCENARIOS = [scenario for scenario in SCENARIOS if scenario.schema in REPO_SCHEMAS]


@pytest.fixture(scope="module")
def outcomes(tmp_path_factory: pytest.TempPathFactory) -> Iterator[dict[str, Outcome]]:
    """Every scenario run once, with the same time and result identifiers for both interfaces."""
    with pytest.MonkeyPatch.context() as patch:
        base = "hotel_booking_analysis.infrastructure.bootstrap"
        patch.setattr(f"{base}.SystemClock", FixedClock)
        patch.setattr(f"{base}.UuidGenerator", SequentialIds)
        yield {
            scenario.name: run_scenario(tmp_path_factory.mktemp(scenario.name), scenario)
            for scenario in SCENARIOS
        }


@pytest.fixture(scope="module")
def description() -> dict[str, Any]:
    document: dict[str, Any] = create_app(ServiceSettings(Path.cwd(), {})).openapi()
    return document


def _registry(description: dict[str, Any]) -> Registry[object]:
    registry: Registry[object] = Registry()
    described: Registry[object] = registry.with_resource(
        OPENAPI_URI, Resource.from_contents(description, DRAFT202012)
    )
    return described


def _response_pointer(scenario: Scenario) -> str:
    path, method = scenario.route
    escaped = path.replace("/", "~1")
    return (
        f"{OPENAPI_URI}#/paths/{escaped}/{method}/responses/{scenario.status}"
        "/content/application~1json/schema"
    )


def _openapi_validator(description: dict[str, Any], scenario: Scenario) -> Draft202012Validator:
    return Draft202012Validator(
        {"$ref": _response_pointer(scenario)}, registry=_registry(description)
    )


def _references(node: object) -> Iterator[str]:
    if isinstance(node, dict):
        if isinstance(node.get("$ref"), str):
            yield node["$ref"]
        for child in node.values():
            yield from _references(child)
    elif isinstance(node, list):
        for child in node:
            yield from _references(child)


def _without(document: dict[str, Any], key: str) -> dict[str, Any]:
    return {name: value for name, value in document.items() if name != key}


@pytest.mark.parametrize("scenario", SCENARIOS, ids=SCENARIO_IDS)
def test_route_answers_with_the_documented_status(
    outcomes: dict[str, Outcome], scenario: Scenario
) -> None:
    assert outcomes[scenario.name].response.status_code == scenario.status


@pytest.mark.parametrize("scenario", REPO_SCENARIOS, ids=[s.name for s in REPO_SCENARIOS])
def test_route_body_validates_against_the_schema_file_of_the_repository(
    outcomes: dict[str, Outcome], scenario: Scenario
) -> None:
    validator = repo_validator(scenario.schema)
    document = outcomes[scenario.name].response.json()

    validator.validate(document)

    assert not validator.is_valid(_without(document, scenario.drop))


@pytest.mark.parametrize("scenario", COMMAND_SCENARIOS, ids=[s.name for s in COMMAND_SCENARIOS])
def test_route_body_equals_the_command_output_for_the_same_input(
    outcomes: dict[str, Outcome], scenario: Scenario
) -> None:
    outcome = outcomes[scenario.name]

    assert outcome.response.content == outcome.cli_output
    assert outcome.cli_code == {200: 0, 422: 2}[scenario.status]


def test_the_insight_scenarios_answer_result_1_1_and_the_plain_one_1_0(
    outcomes: dict[str, Outcome],
) -> None:
    versions = {
        name: outcomes[name].response.json()["schema_version"]
        for name in ("analyze_1_0", "analyze_1_1", "analyze_insights_unavailable")
    }

    assert versions == {
        "analyze_1_0": "1.0",
        "analyze_1_1": "1.1",
        "analyze_insights_unavailable": "1.1",
    }


def test_the_openapi_description_is_a_valid_openapi_3_1_document(
    description: dict[str, Any],
) -> None:
    OpenAPI.model_validate(description)
    registry = _registry(description)

    references = set(_references(description["paths"]))

    assert description["openapi"].startswith("3.1")
    assert references
    for reference in references:
        assert reference.removeprefix(SCHEMA_PREFIX) in description["components"]["schemas"]
        registry.resolver().lookup(f"{OPENAPI_URI}{reference}")


def _restored(node: Any, own: str, ids: dict[str, str]) -> Any:  # noqa: ANN401 - JSON
    """The inverse of the rebasing of `$ref`s: a pointer into the OpenAPI document to `$id` form."""
    if isinstance(node, list):
        return [_restored(child, own, ids) for child in node]
    if not isinstance(node, dict):
        return node
    restored = {key: _restored(child, own, ids) for key, child in node.items()}
    reference = node.get("$ref")
    if isinstance(reference, str):
        name, _, pointer = reference.removeprefix(SCHEMA_PREFIX).partition("/")
        restored["$ref"] = f"{'' if name == own else ids[name]}#/{pointer}"
    return restored


@pytest.mark.parametrize("name", sorted(REPO_SCHEMAS))
def test_the_openapi_schema_is_the_schema_file_of_the_repository_with_rebased_references(
    description: dict[str, Any], name: str
) -> None:
    repo = {key: load() for key, load in REPO_SCHEMAS.items()}
    ids = {key: document["$id"] for key, document in repo.items()}
    component = description["components"]["schemas"][name]

    restored = {
        "$schema": repo[name]["$schema"],
        "$id": ids[name],
        **_restored(component, name, ids),
    }

    assert restored == repo[name]


def test_the_result_1_1_schema_refers_to_the_result_1_0_schema_that_the_description_holds(
    description: dict[str, Any],
) -> None:
    references = set(_references(description["components"]["schemas"]["AnalysisResult_1_1"]))

    assert f"{SCHEMA_PREFIX}AnalysisResult_1_0/properties/result_id" in references
    assert not any(ref.startswith("http") for ref in references)


@pytest.mark.parametrize(
    ("route", "status", "expected"),
    [
        (("/analyze", "post"), "200", {"AnalysisResult_1_0", "AnalysisResult_1_1"}),
        (("/analyze", "post"), "422", {"AnalysisResult_1_0", FRAMEWORK_ERROR}),
        (("/analyze", "post"), "500", {ERROR_OBJECT}),
        (("/holidays", "get"), "200", {"HolidayCalendar_1_0"}),
        (("/holidays", "get"), "422", {"HolidayCalendar_1_0", FRAMEWORK_ERROR}),
        (("/llm-providers", "get"), "200", {"LlmProviders_1_0"}),
        (("/llm-providers", "get"), "422", {"LlmProviders_1_0", FRAMEWORK_ERROR}),
    ],
)
def test_each_documented_response_names_the_schemas_of_its_documents(
    description: dict[str, Any], route: tuple[str, str], status: str, expected: set[str]
) -> None:
    path, method = route
    response = description["paths"][path][method]["responses"][status]

    schema = response["content"]["application/json"]["schema"]

    assert {ref.removeprefix(SCHEMA_PREFIX) for ref in _references(schema)} == expected


@pytest.mark.parametrize("scenario", SCENARIOS, ids=SCENARIO_IDS)
def test_openapi_response_schema_accepts_the_body_and_rejects_a_corrupted_one(
    outcomes: dict[str, Outcome], description: dict[str, Any], scenario: Scenario
) -> None:
    validator = _openapi_validator(description, scenario)
    document = outcomes[scenario.name].response.json()

    validator.validate(document)

    assert not validator.is_valid(_without(document, scenario.drop))
    assert not validator.is_valid({"unexpected": True})
