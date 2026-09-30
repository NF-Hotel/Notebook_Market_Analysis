"""End-to-end acceptance of the HTTP API (MIL-012 criteria 2, 3 and 5; UC-001, UC-005, ADR-0005).

`python -m hotel_booking_analysis serve` runs as a subprocess against a fake Ollama server, and
the development sample is sent as the JSON array of ADR-0001. The response, the history line
and the view models built from the history are the same result, a history of 1.0 and 1.1
results is listed by the notebook, and a long insight request does not block the listings.
"""

import csv
import json
import threading
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import httpx
import pytest

from hotel_booking_analysis.application.configuration import LlmConfiguration
from hotel_booking_analysis.domain.booking import BOOLEAN_FIELDS, DATE_FIELDS, INTEGER_FIELDS
from hotel_booking_analysis.interface.history_source import load_history
from hotel_booking_analysis.interface.history_view import build_history_view
from hotel_booking_analysis.interface.insight_view import (
    STATE_AVAILABLE,
    STATE_SAVED_WITHOUT,
    STATE_UNAVAILABLE,
    reason_text,
)
from tests.adapters import fake_servers as servers
from tests.infrastructure.http_scenarios import repo_validator
from tests.infrastructure.insight_servers import (
    answer_for,
    fake_providers,
    held_ollama,
    ollama_answering,
)
from tests.infrastructure.service_process import RunningService, running_service
from tests.insight_samples import SAMPLE_CSV
from tests.interface.builders import export_notebook
from tests.interface.conftest import REPO_ROOT
from tests.interface.insight_builders import ANALYSES
from tests.interface.insight_view_checks import assert_view_matches_stored_insight, views_of_history

RECORD_COUNT = 8538
JSON = {"Content-Type": "application/json"}
ANALYZE_SECONDS = 90.0
LISTING_SECONDS = 5.0
HOLD_SECONDS = 60.0
ADR_0013 = REPO_ROOT / "docs" / "adr" / "adr-0013-http-api.md"

pytestmark = pytest.mark.skipif(not SAMPLE_CSV.is_file(), reason="development CSV is not present")


def _cell(name: str, text: str) -> object:
    if name in DATE_FIELDS:
        return datetime.strptime(text, "%d-%m-%Y").date().isoformat()
    if name in INTEGER_FIELDS:
        return int(text)
    if name in BOOLEAN_FIELDS:
        return text == "1"
    return float(text) if name == "price_per_night" else text


def sample_body() -> bytes:
    """The development sample as the JSON array of bookings of ADR-0001."""
    with SAMPLE_CSV.open(encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle, delimiter=";")
        records = [
            {name: _cell(name, text) for name, text in row.items() if text.strip()} for row in rows
        ]
    return json.dumps(records).encode("utf-8")


def _analyze(service: RunningService, body: bytes, insights: bool) -> httpx.Response:
    return httpx.post(
        f"{service.base_url}/analyze",
        params={"insights": str(insights).lower()},
        content=body,
        headers=JSON,
        timeout=ANALYZE_SECONDS,
    )


def _get(service: RunningService, path: str) -> httpx.Response:
    return httpx.get(f"{service.base_url}{path}", timeout=LISTING_SECONDS)


def _history_lines(service: RunningService) -> list[bytes]:
    if not service.history.exists():
        return []
    return service.history.read_bytes().splitlines(keepends=True)


def _unreachable_table() -> str:
    return (
        f'[llm]\nollama_url = "{servers.closed_port_url()}"\n'
        f'lmstudio_url = "{servers.closed_port_url()}"\n'
    )


@pytest.fixture(scope="module")
def body() -> bytes:
    return sample_body()


@dataclass(frozen=True, slots=True)
class Run:
    """What one service answered to the plain and the insight analysis and to the listings."""

    service: RunningService
    plain: httpx.Response
    insight: httpx.Response
    holidays: httpx.Response
    providers: httpx.Response
    requests_after_plain: list[str]
    requests_after_insight: list[str]


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory, body: bytes) -> Iterator[Run]:
    directory = tmp_path_factory.mktemp("service")
    with fake_providers(ollama_answering(answer_for(RECORD_COUNT))) as (ollama, llm_table):
        with running_service(directory, llm_table) as service:
            plain = _analyze(service, body, insights=False)
            requests_after_plain = list(ollama.requests)
            insight = _analyze(service, body, insights=True)
            requests_after_insight = list(ollama.requests)
            holidays = _get(service, "/holidays?years=2025,2026")
            providers = _get(service, "/llm-providers")
        yield Run(
            service,
            plain,
            insight,
            holidays,
            providers,
            requests_after_plain,
            requests_after_insight,
        )


def test_analysis_without_insights_is_result_1_0_and_the_line_appended_to_the_history(
    run: Run,
) -> None:
    document = run.plain.json()

    repo_validator("AnalysisResult_1_0").validate(document)
    assert run.plain.status_code == 200
    assert document["schema_version"] == "1.0"
    assert document["input"]["record_count"] == RECORD_COUNT
    assert _history_lines(run.service)[0] == run.plain.content
    assert run.requests_after_plain == []


def test_analysis_with_insights_is_result_1_1_and_the_line_appended_to_the_history(
    run: Run,
) -> None:
    document = run.insight.json()

    repo_validator("AnalysisResult_1_1").validate(document)
    assert run.insight.status_code == 200
    assert (document["schema_version"], document["status"]) == ("1.1", "completed")
    assert _history_lines(run.service)[1] == run.insight.content
    assert run.requests_after_insight == ["/api/tags", *["/api/chat"] * 6]


def test_listings_answer_200_with_their_schemas(run: Run) -> None:
    repo_validator("HolidayCalendar_1_0").validate(run.holidays.json())
    repo_validator("LlmProviders_1_0").validate(run.providers.json())
    assert (run.holidays.status_code, run.providers.status_code) == (200, 200)
    assert [entry["year"] for entry in run.holidays.json()["years"]] == [2025, 2026]
    assert run.providers.json()["providers"][0]["status"] == "reachable"


def test_insights_are_the_same_in_the_response_the_history_line_and_the_views(run: Run) -> None:
    returned = run.insight.json()

    (stored, views), _ = views_of_history(run.service.config, run.service.history.parent)

    assert stored == returned
    assert set(views) == set(returned["analyses"]) == set(ANALYSES)
    for name, view in views.items():
        assert_view_matches_stored_insight(
            view, returned["analyses"][name]["insight"], RECORD_COUNT
        )
    assert (returned["insights"]["provider"], returned["insights"]["model"]) == ("ollama", "m1")


def test_a_history_of_a_1_0_and_a_1_1_result_is_listed_by_the_notebook(run: Run) -> None:
    directory = run.service.history.parent
    environment = {"HOTEL_ANALYSIS_CONFIG": str(run.service.config)}
    listed = build_history_view(load_history(directory, environment).readout)

    (newer, newer_views), (older, older_views) = views_of_history(run.service.config, directory)
    html = export_notebook(directory, environment)

    assert [row.schema_version for row in listed.rows] == ["1.1", "1.0"]
    assert (newer["result_id"], older["result_id"]) == (
        run.insight.json()["result_id"],
        run.plain.json()["result_id"],
    )
    assert {view.state for view in newer_views.values()} == {STATE_AVAILABLE}
    assert {view.state for view in older_views.values()} == {STATE_SAVED_WITHOUT}
    assert newer["result_id"] in html
    assert older["result_id"] in html
    assert "provider: ollama" in html


def test_unreachable_provider_is_200_with_warnings_and_invalid_input_is_422_and_not_stored(
    tmp_path: Path, body: bytes
) -> None:
    with running_service(tmp_path, _unreachable_table()) as service:
        answer = _analyze(service, body, insights=True)
        lines_after_analysis = _history_lines(service)
        failed = _analyze(service, b"{}", insights=False)
        lines_after_failure = _history_lines(service)

    returned = answer.json()
    repo_validator("AnalysisResult_1_1").validate(returned)
    assert answer.status_code == 200
    assert returned["status"] == "completed_with_warnings"
    assert returned["notices"][-1]["code"] == "INSIGHTS_UNAVAILABLE"
    assert returned["insights"]["provider"] is None
    assert all(entry["findings"] for entry in returned["analyses"].values())
    assert lines_after_analysis == [answer.content]
    [(stored, views)] = views_of_history(service.config, tmp_path)
    assert stored == returned
    for name, view in views.items():
        assert returned["analyses"][name]["insight"]["reason"] == "NO_PROVIDER"
        assert (view.state, view.reason_text) == (STATE_UNAVAILABLE, reason_text("NO_PROVIDER"))
    repo_validator("AnalysisResult_1_0").validate(failed.json())
    assert failed.status_code == 422
    assert failed.json()["status"] == "failed"
    assert failed.json()["error"]["code"] == "INPUT_NOT_ARRAY"
    assert lines_after_failure == lines_after_analysis


def _wait_for_chat(ollama: servers.FakeServer) -> None:
    deadline = time.monotonic() + ANALYZE_SECONDS
    while "/api/chat" not in ollama.requests:
        assert time.monotonic() < deadline, "the request never reached the model"
        time.sleep(0.05)


def test_a_long_insight_request_does_not_block_the_listings(tmp_path: Path, body: bytes) -> None:
    release = threading.Event()
    behavior = held_ollama(release, answer_for(RECORD_COUNT), HOLD_SECONDS)
    with (
        fake_providers(behavior) as (ollama, llm_table),
        running_service(tmp_path, llm_table) as service,
        ThreadPoolExecutor(1) as pool,
    ):
        try:
            slow = pool.submit(_analyze, service, body, True)
            _wait_for_chat(ollama)
            started = time.monotonic()

            holidays = _get(service, "/holidays?years=2025")
            providers = _get(service, "/llm-providers")

            assert (holidays.status_code, providers.status_code) == (200, 200)
            assert time.monotonic() - started < LISTING_SECONDS
            assert not slow.done()
        finally:
            release.set()
        response = slow.result(timeout=ANALYZE_SECONDS)
    assert response.status_code == 200
    assert _history_lines(service) == [response.content]


def test_the_documented_timeout_is_the_bound_of_the_configured_defaults() -> None:
    defaults = LlmConfiguration()
    bound = 2 * defaults.discovery_timeout_seconds + 6 * defaults.generation_timeout_seconds

    text = ADR_0013.read_text(encoding="utf-8").replace(chr(0xD7), "x")

    assert (bound // 60, bound % 60) == (12, 4)
    assert "2 x `llm.discovery_timeout_seconds`" in text
    assert "6 x `llm.generation_timeout_seconds`" in text
    assert "12 minutes and 4 seconds" in text
