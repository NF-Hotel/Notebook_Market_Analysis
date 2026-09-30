"""Tests of provider discovery with a fake `LlmProvider` (ADR-0009)."""

from hotel_booking_analysis.application.ports import LlmProvider
from hotel_booking_analysis.application.provider_discovery import discover_providers, find_provider
from hotel_booking_analysis.domain.llm import (
    LanguageModelProvider,
    ProviderName,
    ProviderReason,
    ProviderStatus,
)


class FakeProvider:
    """Answers with a fixed status and records the order and timeout of the calls."""

    def __init__(
        self,
        name: ProviderName,
        calls: list[tuple[ProviderName, float]],
        models: tuple[str, ...] = (),
        reason: ProviderReason | None = None,
    ) -> None:
        self._provider = LanguageModelProvider(name, f"http://localhost/{name.value}")
        self._calls = calls
        self._models = models
        self._reason = reason

    def provider(self) -> LanguageModelProvider:
        return self._provider

    def list_models(self, timeout_seconds: float) -> ProviderStatus:
        self._calls.append((self._provider.name, timeout_seconds))
        if self._reason is not None:
            return ProviderStatus.unreachable_because(self._provider, self._reason)
        return ProviderStatus.reachable_with(self._provider, self._models)


def test_discover_providers_checks_each_provider_in_order_with_the_deadline() -> None:
    calls: list[tuple[ProviderName, float]] = []
    providers: tuple[LlmProvider, ...] = (
        FakeProvider(ProviderName.OLLAMA, calls, ("a",)),
        FakeProvider(ProviderName.LMSTUDIO, calls, reason=ProviderReason.TIMEOUT),
    )

    statuses = discover_providers(providers, 1.5)

    assert calls == [(ProviderName.OLLAMA, 1.5), (ProviderName.LMSTUDIO, 1.5)]
    assert [s.provider.name for s in statuses] == [ProviderName.OLLAMA, ProviderName.LMSTUDIO]
    assert [s.reachable for s in statuses] == [True, False]


def test_discover_providers_of_no_provider_is_empty() -> None:
    assert discover_providers((), 2.0) == ()


def test_find_provider_returns_the_provider_with_the_name() -> None:
    calls: list[tuple[ProviderName, float]] = []
    ollama = FakeProvider(ProviderName.OLLAMA, calls)
    lmstudio = FakeProvider(ProviderName.LMSTUDIO, calls)

    assert find_provider((ollama, lmstudio), ProviderName.LMSTUDIO) is lmstudio
    assert calls == []


def test_find_provider_returns_none_when_no_provider_has_the_name() -> None:
    ollama = FakeProvider(ProviderName.OLLAMA, [])

    assert find_provider((ollama,), ProviderName.LMSTUDIO) is None
