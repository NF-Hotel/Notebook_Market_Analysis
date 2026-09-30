"""One table of HTTP requests, each with its expected status and schema (ADR-0013, ADR-0011).

The contract tests and the OpenAPI tests run the same scenarios, so a route, a status code and
the schema that describes its body are named once.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from httpx import Response
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from hotel_booking_analysis.adapters.json_holiday_listing_serializer import (
    load_holiday_listing_schema,
)
from hotel_booking_analysis.adapters.json_provider_listing_serializer import (
    load_provider_listing_schema,
)
from hotel_booking_analysis.adapters.json_result_serializer import (
    load_result_schema,
    load_result_schema_1_1,
)
from hotel_booking_analysis.infrastructure.http_api import (
    BODY_REFERENCE,
    HOLIDAY_LISTING,
    PROVIDER_LISTING,
    RESULT_1_0,
    RESULT_1_1,
)
from tests.infrastructure.cli_support import BrokenStdout
from tests.infrastructure.http_support import (
    bookings_body,
    make_client,
    run_command,
    unreachable_llm_table,
    write_config,
)
from tests.infrastructure.insight_servers import answer_for, fake_providers, ollama_answering

JSON = {"Content-Type": "application/json"}
ERROR_OBJECT = "ErrorObject"
FRAMEWORK_ERROR = "FrameworkError"
INSIGHT_RECORDS = 30

REPO_SCHEMAS: dict[str, Callable[[], dict[str, Any]]] = {
    RESULT_1_0: load_result_schema,
    RESULT_1_1: load_result_schema_1_1,
    HOLIDAY_LISTING: load_holiday_listing_schema,
    PROVIDER_LISTING: load_provider_listing_schema,
}
UNREACHABLE = "unreachable"
FAKE_OLLAMA = "fake_ollama"
BAD_LLM = "bad_llm"
BLOCKED_HISTORY = "blocked_history"


@dataclass(frozen=True, slots=True)
class Scenario:
    """A request, the state of the service, and what the answer must be.

    `cli` is the equivalent command (`{input}` names the body file), or None when there is no
    command with the same input. `drop` is a top-level key of the answer whose removal must make
    the schema of the route reject it.
    """

    name: str
    method: str
    url: str
    status: int
    schema: str
    drop: str
    body: bytes = field(default_factory=bookings_body)
    headers: dict[str, str] = field(default_factory=lambda: dict(JSON))
    llm: str = UNREACHABLE
    cli: tuple[str, ...] | None = None
    broken_stream: bool = False

    @property
    def route(self) -> tuple[str, str]:
        return self.url.split("?")[0], self.method.lower()


@dataclass(frozen=True, slots=True)
class Outcome:
    response: Response
    cli_code: int | None
    cli_output: bytes | None


SCENARIOS = (
    Scenario(
        "analyze_1_0",
        "POST",
        "/analyze",
        200,
        RESULT_1_0,
        "schema_version",
        cli=("analyze", "--input", "{input}"),
    ),
    Scenario(
        "analyze_1_1",
        "POST",
        "/analyze?insights=true",
        200,
        RESULT_1_1,
        "schema_version",
        body=bookings_body(INSIGHT_RECORDS),
        llm=FAKE_OLLAMA,
        cli=("analyze", "--input", "{input}", "--insights"),
    ),
    Scenario(
        "analyze_insights_unavailable",
        "POST",
        "/analyze?insights=true",
        200,
        RESULT_1_1,
        "schema_version",
        cli=("analyze", "--input", "{input}", "--insights"),
    ),
    Scenario(
        "analyze_invalid_json",
        "POST",
        "/analyze",
        422,
        RESULT_1_0,
        "schema_version",
        body=b"not json",
        cli=("analyze", "--input", "{input}"),
    ),
    Scenario(
        "analyze_invalid_llm_config",
        "POST",
        "/analyze?insights=true",
        422,
        RESULT_1_0,
        "schema_version",
        llm=BAD_LLM,
        cli=("analyze", "--input", "{input}", "--insights"),
    ),
    Scenario(
        "analyze_malformed_flag", "POST", "/analyze?insights=maybe", 422, FRAMEWORK_ERROR, "detail"
    ),
    Scenario(
        "analyze_wrong_content_type",
        "POST",
        "/analyze",
        415,
        FRAMEWORK_ERROR,
        "detail",
        headers={"Content-Type": "text/plain"},
    ),
    Scenario(
        "analyze_history_failure",
        "POST",
        "/analyze",
        500,
        ERROR_OBJECT,
        "error",
        llm=BLOCKED_HISTORY,
    ),
    Scenario(
        "analyze_delivery_failure",
        "POST",
        "/analyze",
        500,
        ERROR_OBJECT,
        "error",
        broken_stream=True,
    ),
    Scenario(
        "holidays",
        "GET",
        "/holidays?years=2024-2026",
        200,
        HOLIDAY_LISTING,
        "schema_version",
        cli=("holidays", "--years", "2024-2026"),
    ),
    Scenario(
        "holidays_default_years",
        "GET",
        "/holidays",
        200,
        HOLIDAY_LISTING,
        "schema_version",
        cli=("holidays",),
    ),
    Scenario(
        "holidays_invalid_years",
        "GET",
        "/holidays?years=abc",
        422,
        HOLIDAY_LISTING,
        "schema_version",
        cli=("holidays", "--years", "abc"),
    ),
    Scenario(
        "holidays_delivery_failure",
        "GET",
        "/holidays?years=2025",
        500,
        ERROR_OBJECT,
        "error",
        broken_stream=True,
    ),
    Scenario(
        "providers_unreachable",
        "GET",
        "/llm-providers",
        200,
        PROVIDER_LISTING,
        "schema_version",
        cli=("llm-providers",),
    ),
    Scenario(
        "providers_reachable",
        "GET",
        "/llm-providers",
        200,
        PROVIDER_LISTING,
        "schema_version",
        llm=FAKE_OLLAMA,
        cli=("llm-providers",),
    ),
    Scenario(
        "providers_invalid_llm_config",
        "GET",
        "/llm-providers",
        422,
        PROVIDER_LISTING,
        "schema_version",
        llm=BAD_LLM,
        cli=("llm-providers",),
    ),
)


def repo_validator(name: str) -> Draft202012Validator:
    """A validator of the schema file of the repository that `name` denotes (ADR-0011)."""
    old = load_result_schema()
    registry: Registry[object] = Registry().with_resource(
        old["$id"], Resource.from_contents(old, DRAFT202012)
    )
    return Draft202012Validator(REPO_SCHEMAS[name](), registry=registry)


def _config(tmp_path: Path, scenario: Scenario, fake_table: str) -> Path:
    tables = {
        UNREACHABLE: unreachable_llm_table(),
        FAKE_OLLAMA: fake_table,
        BAD_LLM: "[llm]\ntemperature = 9\n",
        BLOCKED_HISTORY: "",
    }
    if scenario.llm == BLOCKED_HISTORY:
        (tmp_path / "blocker").write_text("a file, not a directory", encoding="utf-8")
        return write_config(tmp_path, tables[BLOCKED_HISTORY], "blocker/history.jsonl")
    return write_config(tmp_path, tables[scenario.llm])


@contextmanager
def _providers(scenario: Scenario) -> Iterator[str]:
    """The `[llm]` table of a fake Ollama when the scenario needs one, else an empty string."""
    if scenario.llm != FAKE_OLLAMA:
        yield ""
        return
    with fake_providers(ollama_answering(answer_for(INSIGHT_RECORDS))) as (_, table):
        yield table


def run_scenario(tmp_path: Path, scenario: Scenario) -> Outcome:
    """Send the request to the service and run the equivalent command, on one configuration."""
    with _providers(scenario) as fake_table:
        config = _config(tmp_path, scenario, fake_table)
        settings: dict[str, Any] = (
            {"stream_factory": BrokenStdout} if scenario.broken_stream else {}
        )
        client = make_client(tmp_path, config, **settings)
        response = client.request(
            scenario.method, scenario.url, content=scenario.body, headers=scenario.headers
        )
        if scenario.cli is None:
            return Outcome(response, None, None)
        (tmp_path / "cli").mkdir()
        input_file = tmp_path / "cli" / BODY_REFERENCE
        input_file.write_bytes(scenario.body)
        args = [arg.replace("{input}", str(input_file)) for arg in scenario.cli]
        code, output = run_command(tmp_path, config, *args)
        return Outcome(response, code, output)
