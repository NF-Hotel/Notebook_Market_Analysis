"""Tests that the service shares one process between requests safely (ADR-0013, ADR-0003).

A `with` block on the test client keeps one event loop for every request, so a route that
blocked the loop would stall the others; a plain-function route runs in the thread pool.
"""

import inspect
import json
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.routing import APIRoute

from hotel_booking_analysis.infrastructure.file_lock import FileLock
from hotel_booking_analysis.infrastructure.http_api import ServiceSettings, create_app
from hotel_booking_analysis.infrastructure.jsonl_history import lock_path_for
from tests.infrastructure.http_support import (
    HISTORY_NAME,
    bookings_body,
    history_lines,
    make_client,
    write_config,
)
from tests.infrastructure.insight_servers import answer_for, fake_providers, held_ollama

JSON = {"Content-Type": "application/json"}
RECORD_COUNT = 30
WAIT_SECONDS = 20.0


def _wait_until(condition: Callable[[], bool]) -> None:
    deadline = time.monotonic() + WAIT_SECONDS
    while not condition():
        assert time.monotonic() < deadline, "the condition did not become true in time"
        time.sleep(0.02)


def test_listings_are_served_while_a_slow_insight_request_runs(tmp_path: Path) -> None:
    release = threading.Event()
    with fake_providers(held_ollama(release, answer_for(RECORD_COUNT), WAIT_SECONDS)) as (
        ollama,
        llm_table,
    ):
        client = make_client(tmp_path, write_config(tmp_path, llm_table))
        with client, ThreadPoolExecutor(max_workers=1) as pool:
            try:
                slow = pool.submit(
                    client.post,
                    "/analyze",
                    params={"insights": "true"},
                    content=bookings_body(RECORD_COUNT),
                    headers=JSON,
                )
                _wait_until(lambda: "/api/chat" in ollama.requests)
                started = time.monotonic()

                holidays = client.get("/holidays", params={"years": "2025"})
                providers = client.get("/llm-providers")

                assert (holidays.status_code, providers.status_code) == (200, 200)
                assert time.monotonic() - started < WAIT_SECONDS / 2
                assert not slow.done()
            finally:
                release.set()
            response = slow.result(timeout=WAIT_SECONDS)
    assert response.status_code == 200
    assert history_lines(tmp_path) == [response.content]


def test_concurrent_analyses_append_whole_lines_under_the_history_lock(tmp_path: Path) -> None:
    count = 8
    with make_client(tmp_path) as client, ThreadPoolExecutor(max_workers=count) as pool:
        futures = [
            pool.submit(client.post, "/analyze", content=bookings_body(), headers=JSON)
            for _ in range(count)
        ]
        responses = [future.result(timeout=WAIT_SECONDS) for future in futures]

    assert [response.status_code for response in responses] == [200] * count
    lines = history_lines(tmp_path)
    assert sorted(lines) == sorted(response.content for response in responses)
    assert len({json.loads(line)["result_id"] for line in lines}) == count
    assert not lock_path_for(tmp_path / HISTORY_NAME).exists()


def test_history_lock_is_exclusive_between_threads_of_one_process(tmp_path: Path) -> None:
    path = tmp_path / "history.jsonl.lock"
    inside = 0
    overlaps = 0
    guard = threading.Lock()

    def critical_section() -> None:
        nonlocal inside, overlaps
        with FileLock(path, wait_seconds=WAIT_SECONDS):
            with guard:
                inside += 1
                overlaps += inside > 1
            time.sleep(0.01)
            with guard:
                inside -= 1

    with ThreadPoolExecutor(max_workers=6) as pool:
        for future in [pool.submit(critical_section) for _ in range(12)]:
            future.result(timeout=WAIT_SECONDS)

    assert overlaps == 0
    assert not path.exists()


def test_routes_are_plain_functions_so_they_run_in_the_thread_pool(tmp_path: Path) -> None:
    app = create_app(ServiceSettings(tmp_path, {}))

    handlers = [route.endpoint for route in app.routes if isinstance(route, APIRoute)]

    assert len(handlers) == 4
    assert not any(inspect.iscoroutinefunction(handler) for handler in handlers)
