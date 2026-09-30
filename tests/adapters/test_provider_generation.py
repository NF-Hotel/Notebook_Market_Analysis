"""Tests of the generation request of both provider adapters against fake servers (ADR-0009)."""

import time
from collections.abc import Callable
from dataclasses import dataclass

import pytest

from hotel_booking_analysis.adapters.lmstudio_provider import LmStudioProvider
from hotel_booking_analysis.adapters.ollama_provider import OllamaProvider
from hotel_booking_analysis.application.ports import LlmProvider
from hotel_booking_analysis.domain.analysis import JsonValue
from hotel_booking_analysis.domain.errors import LlmError, LlmTimeoutError
from hotel_booking_analysis.domain.insight_prompt import InsightPrompt
from tests.adapters import fake_servers as servers

GENEROUS = 5.0
SHORT = 0.3
PROMPT = InsightPrompt("Be brief.", '{"analysis":"lead_time"}')
ANSWER = '{"executive_summary":"x"}'


@dataclass(frozen=True)
class Flavor:
    """What differs between the providers: address, answer shape and body checks."""

    name: str
    make: Callable[[str], LlmProvider]
    path: str
    reply: Callable[[JsonValue], JsonValue]
    no_text: JsonValue


FLAVORS = [
    Flavor(
        "ollama",
        OllamaProvider,
        "/api/chat",
        lambda text: {"message": {"role": "assistant", "content": text}, "done": True},
        {"message": {"role": "assistant"}},
    ),
    Flavor(
        "lmstudio",
        LmStudioProvider,
        "/v1/chat/completions",
        lambda text: {"choices": [{"message": {"role": "assistant", "content": text}}]},
        {"choices": []},
    ),
]


@pytest.fixture(params=FLAVORS, ids=lambda flavor: flavor.name)
def flavor(request: pytest.FixtureRequest) -> Flavor:
    chosen: Flavor = request.param
    return chosen


def test_generate_returns_the_text_of_the_reply(flavor: Flavor) -> None:
    with servers.serve(servers.json_answer(flavor.reply(ANSWER))) as server:
        text = flavor.make(server.base_url + "/").generate("m1", PROMPT, 0.0, GENEROUS)

        assert server.requests == [flavor.path]
    assert text == ANSWER


def test_generate_sends_model_messages_and_temperature_as_json(flavor: Flavor) -> None:
    with servers.serve(servers.json_answer(flavor.reply(ANSWER))) as server:
        flavor.make(server.base_url).generate("m1", PROMPT, 0.25, GENEROUS)

        (body,) = server.posted_documents()
    assert body["model"] == "m1"
    assert body["messages"] == [
        {"role": "system", "content": "Be brief."},
        {"role": "user", "content": '{"analysis":"lead_time"}'},
    ]
    assert 0.25 in (body.get("temperature"), body.get("options", {}).get("temperature"))


def test_ollama_asks_for_a_non_streamed_json_answer() -> None:
    with servers.serve(servers.json_answer(FLAVORS[0].reply(ANSWER))) as server:
        OllamaProvider(server.base_url).generate("m1", PROMPT, 0.0, GENEROUS)

        (body,) = server.posted_documents()
    assert body["stream"] is False
    assert body["format"] == "json"
    assert body["options"] == {"temperature": 0.0}
    assert "temperature" not in body


def test_lmstudio_puts_the_temperature_at_the_top_level() -> None:
    with servers.serve(servers.json_answer(FLAVORS[1].reply(ANSWER))) as server:
        LmStudioProvider(server.base_url).generate("m1", PROMPT, 0.5, GENEROUS)

        (body,) = server.posted_documents()
    assert body["temperature"] == 0.5
    assert "options" not in body


def test_generate_raises_timeout_when_the_server_never_answers(flavor: Flavor) -> None:
    with servers.serve(servers.never_answers) as server:
        started = time.monotonic()
        with pytest.raises(LlmTimeoutError):
            flavor.make(server.base_url).generate("m1", PROMPT, 0.0, SHORT)
        elapsed = time.monotonic() - started

    assert elapsed < 2.0


def test_generate_raises_timeout_when_the_answer_trickles_in(flavor: Flavor) -> None:
    with servers.serve(servers.trickling_body) as server:
        started = time.monotonic()
        with pytest.raises(LlmTimeoutError):
            flavor.make(server.base_url).generate("m1", PROMPT, 0.0, SHORT)
        elapsed = time.monotonic() - started

    assert elapsed < 2.0


def test_generate_raises_llm_error_for_http_500_without_retry(flavor: Flavor) -> None:
    with servers.serve(servers.json_answer({"error": "boom"}, status=500)) as server:
        with pytest.raises(LlmError) as raised:
            flavor.make(server.base_url).generate("m1", PROMPT, 0.0, GENEROUS)

        assert len(server.requests) == 1
    assert not isinstance(raised.value, LlmTimeoutError)


def test_generate_raises_llm_error_for_a_malformed_body(flavor: Flavor) -> None:
    with (
        servers.serve(servers.raw_answer(b"<html>not json")) as server,
        pytest.raises(LlmError) as raised,
    ):
        flavor.make(server.base_url).generate("m1", PROMPT, 0.0, GENEROUS)

    assert not isinstance(raised.value, LlmTimeoutError)


@pytest.mark.parametrize("document", [[], "text", {"other": 1}, {"message": "x"}, {"choices": {}}])
def test_generate_raises_llm_error_for_json_of_the_wrong_shape(
    flavor: Flavor, document: JsonValue
) -> None:
    with servers.serve(servers.json_answer(document)) as server, pytest.raises(LlmError):
        flavor.make(server.base_url).generate("m1", PROMPT, 0.0, GENEROUS)


def test_generate_raises_llm_error_when_the_reply_holds_no_text(flavor: Flavor) -> None:
    with servers.serve(servers.json_answer(flavor.no_text)) as server, pytest.raises(LlmError):
        flavor.make(server.base_url).generate("m1", PROMPT, 0.0, GENEROUS)


def test_generate_raises_llm_error_when_the_text_is_not_a_string(flavor: Flavor) -> None:
    with servers.serve(servers.json_answer(flavor.reply(5))) as server, pytest.raises(LlmError):
        flavor.make(server.base_url).generate("m1", PROMPT, 0.0, GENEROUS)


def test_generate_raises_llm_error_when_nothing_listens(flavor: Flavor) -> None:
    with pytest.raises(LlmError) as raised:
        flavor.make(servers.closed_port_url()).generate("m1", PROMPT, 0.0, GENEROUS)

    assert not isinstance(raised.value, LlmTimeoutError)


def test_generate_raises_llm_error_for_an_endless_body(flavor: Flavor) -> None:
    with servers.serve(servers.endless_body) as server, pytest.raises(LlmError) as raised:
        flavor.make(server.base_url).generate("m1", PROMPT, 0.0, GENEROUS)

    assert not isinstance(raised.value, LlmTimeoutError)


def test_generate_returns_an_empty_text_for_the_validator_to_reject(flavor: Flavor) -> None:
    with servers.serve(servers.json_answer(flavor.reply(""))) as server:
        assert flavor.make(server.base_url).generate("m1", PROMPT, 0.0, GENEROUS) == ""
