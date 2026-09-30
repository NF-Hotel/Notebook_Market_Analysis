"""Tests of the Ollama and LM Studio adapters and the registry against fake servers (ADR-0009)."""

import time

from hotel_booking_analysis.adapters.llm_registry import ConfiguredLlmProviders
from hotel_booking_analysis.adapters.lmstudio_provider import LmStudioProvider
from hotel_booking_analysis.adapters.ollama_provider import OllamaProvider
from hotel_booking_analysis.application.configuration import LlmConfiguration
from hotel_booking_analysis.application.ports import LlmProvider
from hotel_booking_analysis.domain.llm import ProviderName, ProviderReason, ProviderStatus
from tests.adapters import fake_servers as servers

GENEROUS = 5.0
SHORT = 0.3

OLLAMA_TAGS = {"models": [{"name": "llama3:8b", "size": 1}, {"name": "qwen2:7b"}]}
LMSTUDIO_MODELS = {"object": "list", "data": [{"id": "phi-3", "object": "model"}, {"id": "gemma"}]}


def _names(status: ProviderStatus) -> list[str]:
    return [model.name for model in status.models]


def test_ollama_lists_the_names_of_api_tags() -> None:
    with servers.serve(servers.json_answer(OLLAMA_TAGS)) as server:
        status = OllamaProvider(server.base_url).list_models(GENEROUS)

        assert server.requests == ["/api/tags"]
    assert status.reachable
    assert status.reason is None
    assert status.provider.name is ProviderName.OLLAMA
    assert status.provider.base_url == server.base_url
    assert _names(status) == ["llama3:8b", "qwen2:7b"]
    assert status.first_model() is not None
    assert status.offers("qwen2:7b")


def test_lmstudio_lists_the_ids_of_v1_models() -> None:
    with servers.serve(servers.json_answer(LMSTUDIO_MODELS)) as server:
        status = LmStudioProvider(server.base_url + "/").list_models(GENEROUS)

        assert server.requests == ["/v1/models"]
    assert status.reachable
    assert status.provider.name is ProviderName.LMSTUDIO
    assert _names(status) == ["phi-3", "gemma"]


def test_provider_that_lists_no_model_is_reachable_with_no_models() -> None:
    with servers.serve(servers.json_answer({"models": []})) as ollama:
        status = OllamaProvider(ollama.base_url).list_models(GENEROUS)
    with servers.serve(servers.json_answer({"data": []})) as lmstudio:
        other = LmStudioProvider(lmstudio.base_url).list_models(GENEROUS)

    assert status.reachable
    assert status.models == ()
    assert other.reachable
    assert other.first_model() is None


def test_provider_is_unreachable_with_connection_refused_when_nothing_listens() -> None:
    for provider in (
        OllamaProvider(servers.closed_port_url()),
        LmStudioProvider(servers.closed_port_url()),
    ):
        status = provider.list_models(GENEROUS)

        assert not status.reachable
        assert status.reason is ProviderReason.CONNECTION_REFUSED
        assert status.models == ()


def test_provider_is_unreachable_with_timeout_when_the_server_never_answers() -> None:
    with servers.serve(servers.never_answers) as server:
        started = time.monotonic()
        status = OllamaProvider(server.base_url).list_models(SHORT)
        elapsed = time.monotonic() - started

    assert status.reason is ProviderReason.TIMEOUT
    assert elapsed < 2.0


def test_provider_is_unreachable_with_timeout_when_the_answer_trickles_in() -> None:
    with servers.serve(servers.trickling_body) as server:
        started = time.monotonic()
        status = LmStudioProvider(server.base_url).list_models(SHORT)
        elapsed = time.monotonic() - started

    assert status.reason is ProviderReason.TIMEOUT
    assert elapsed < 2.0


def test_provider_is_unreachable_with_unexpected_answer_for_http_500() -> None:
    with servers.serve(servers.json_answer({"error": "x"}, status=500)) as server:
        status = OllamaProvider(server.base_url).list_models(GENEROUS)

    assert status.reason is ProviderReason.UNEXPECTED_ANSWER


def test_provider_is_unreachable_with_unexpected_answer_for_malformed_json() -> None:
    with servers.serve(servers.raw_answer(b"<html>not json")) as server:
        status = LmStudioProvider(server.base_url).list_models(GENEROUS)

    assert status.reason is ProviderReason.UNEXPECTED_ANSWER


def test_provider_is_unreachable_with_unexpected_answer_for_the_wrong_structure() -> None:
    wrong_structures: list[object] = [
        [],
        "text",
        {"other": []},
        {"models": "llama"},
        {"models": ["llama"]},
        {"models": [{"id": "llama"}]},
        {"models": [{"name": 5}]},
        {"models": [{"name": ""}]},
    ]
    for document in wrong_structures:
        with servers.serve(servers.json_answer(document)) as server:
            status = OllamaProvider(server.base_url).list_models(GENEROUS)

        assert status.reason is ProviderReason.UNEXPECTED_ANSWER, document


def test_each_provider_reads_only_its_own_structure() -> None:
    with servers.serve(servers.json_answer(OLLAMA_TAGS)) as server:
        status = LmStudioProvider(server.base_url).list_models(GENEROUS)

    assert status.reason is ProviderReason.UNEXPECTED_ANSWER


def test_provider_is_unreachable_with_unexpected_answer_for_an_endless_body() -> None:
    with servers.serve(servers.endless_body) as server:
        status = OllamaProvider(server.base_url).list_models(GENEROUS)

    assert status.reason is ProviderReason.UNEXPECTED_ANSWER


def test_registry_creates_ollama_then_lmstudio_at_the_configured_addresses() -> None:
    configuration = LlmConfiguration(ollama_url="http://localhost:1", lmstudio_url="http://[::1]:2")

    providers: tuple[LlmProvider, ...] = ConfiguredLlmProviders().providers(configuration)

    assert [(p.provider().name, p.provider().base_url) for p in providers] == [
        (ProviderName.OLLAMA, "http://localhost:1"),
        (ProviderName.LMSTUDIO, "http://[::1]:2"),
    ]
