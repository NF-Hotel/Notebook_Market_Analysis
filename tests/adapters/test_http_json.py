"""Tests of the deadline-bounded JSON GET against real local servers (ADR-0009)."""

import time

import pytest

from hotel_booking_analysis.adapters.http_json import MAX_RESPONSE_BYTES, HttpFailure, get_json
from hotel_booking_analysis.domain.llm import ProviderReason
from tests.adapters import fake_servers as servers

GENEROUS = 5.0
SHORT = 0.3
# The whole call must stay near the timeout: the bound leaves room for a slow test machine.
BOUND = 2.0


def _failure(url: str, timeout: float) -> tuple[HttpFailure, float]:
    started = time.monotonic()
    with pytest.raises(HttpFailure) as info:
        get_json(url, timeout)
    return info.value, time.monotonic() - started


def test_get_json_returns_the_parsed_document() -> None:
    with servers.serve(servers.json_answer({"models": [{"name": "a"}]})) as server:
        assert get_json(server.base_url + "/api/tags", GENEROUS) == {"models": [{"name": "a"}]}
        assert server.requests == ["/api/tags"]


def test_get_json_reads_an_answer_of_a_keep_alive_connection() -> None:
    with servers.serve(servers.json_answer({"data": []}), keep_alive=True) as server:
        assert get_json(server.base_url + "/v1/models", GENEROUS) == {"data": []}


def test_get_json_keeps_the_query_string() -> None:
    with servers.serve(servers.json_answer([])) as server:
        get_json(server.base_url + "/x?y=1", GENEROUS)

        assert server.requests == ["/x?y=1"]


def test_get_json_reports_connection_refused_when_nothing_listens() -> None:
    failure, _ = _failure(servers.closed_port_url() + "/api/tags", GENEROUS)

    assert failure.reason is ProviderReason.CONNECTION_REFUSED


def test_get_json_reports_timeout_within_the_deadline_when_the_server_never_answers() -> None:
    with servers.serve(servers.never_answers) as server:
        failure, elapsed = _failure(server.base_url + "/x", SHORT)

    assert failure.reason is ProviderReason.TIMEOUT
    assert elapsed < BOUND


def test_get_json_hits_the_total_deadline_when_the_body_trickles_in_slowly() -> None:
    with servers.serve(servers.trickling_body) as server:
        failure, elapsed = _failure(server.base_url + "/x", SHORT)

    assert failure.reason is ProviderReason.TIMEOUT
    assert SHORT <= elapsed < BOUND


def test_get_json_hits_the_total_deadline_when_the_headers_trickle_in_slowly() -> None:
    with servers.serve(servers.trickling_headers) as server:
        failure, elapsed = _failure(server.base_url + "/x", SHORT)

    assert failure.reason is ProviderReason.TIMEOUT
    assert SHORT <= elapsed < BOUND


def test_get_json_reports_unexpected_answer_for_http_error_status() -> None:
    with servers.serve(servers.json_answer({"error": "boom"}, status=500)) as server:
        failure, _ = _failure(server.base_url + "/x", GENEROUS)

    assert failure.reason is ProviderReason.UNEXPECTED_ANSWER


def test_get_json_does_not_follow_redirects() -> None:
    with servers.serve(servers.json_answer({}, status=302)) as server:
        failure, _ = _failure(server.base_url + "/x", GENEROUS)

    assert failure.reason is ProviderReason.UNEXPECTED_ANSWER


@pytest.mark.parametrize("body", [b"not json {", b"", b"\xff\xfe"])
def test_get_json_reports_unexpected_answer_for_a_body_that_is_not_json(body: bytes) -> None:
    with servers.serve(servers.raw_answer(body)) as server:
        failure, _ = _failure(server.base_url + "/x", GENEROUS)

    assert failure.reason is ProviderReason.UNEXPECTED_ANSWER


def test_get_json_reports_unexpected_answer_for_a_declared_body_over_the_cap() -> None:
    with servers.serve(servers.raw_answer(b" " * (MAX_RESPONSE_BYTES + 1))) as server:
        failure, _ = _failure(server.base_url + "/x", GENEROUS)

    assert failure.reason is ProviderReason.UNEXPECTED_ANSWER
    assert "large" in str(failure)


def test_get_json_stops_reading_an_endless_body_at_the_cap() -> None:
    with servers.serve(servers.endless_body) as server:
        failure, elapsed = _failure(server.base_url + "/x", GENEROUS)

    assert failure.reason is ProviderReason.UNEXPECTED_ANSWER
    assert elapsed < GENEROUS


def test_get_json_reports_network_error_for_a_name_that_does_not_resolve() -> None:
    failure, _ = _failure("http://no-such-host.invalid:1/x", GENEROUS)

    assert failure.reason is ProviderReason.NETWORK_ERROR


def test_get_json_reports_network_error_for_a_url_without_a_host() -> None:
    failure, _ = _failure("http:///x", GENEROUS)

    assert failure.reason is ProviderReason.NETWORK_ERROR
