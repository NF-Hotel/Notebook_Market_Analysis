"""Tests of the model choice of ADR-0009: the four rules and both reasons."""

from hotel_booking_analysis.domain.insight import InsightReason
from hotel_booking_analysis.domain.llm import (
    LanguageModelProvider,
    ProviderName,
    ProviderReason,
    ProviderStatus,
)
from hotel_booking_analysis.domain.model_selection import ModelSelection, select_model

OLLAMA = LanguageModelProvider(ProviderName.OLLAMA, "http://localhost:11434")
LMSTUDIO = LanguageModelProvider(ProviderName.LMSTUDIO, "http://localhost:1234")


def _up(provider: LanguageModelProvider, *models: str) -> ProviderStatus:
    return ProviderStatus.reachable_with(provider, models)


def _down(provider: LanguageModelProvider) -> ProviderStatus:
    return ProviderStatus.unreachable_because(provider, ProviderReason.CONNECTION_REFUSED)


def _chosen(provider: ProviderName, model: str) -> ModelSelection:
    return ModelSelection(provider, model, None)


def test_provider_and_model_selects_that_pair_when_offered() -> None:
    statuses = (_up(OLLAMA, "a", "b"), _up(LMSTUDIO, "b", "c"))

    selection = select_model(statuses, ProviderName.LMSTUDIO, "b")

    assert selection == _chosen(ProviderName.LMSTUDIO, "b")
    assert selection.is_selected()


def test_provider_and_model_is_no_provider_when_that_provider_is_unreachable() -> None:
    statuses = (_up(OLLAMA, "a"), _down(LMSTUDIO))

    selection = select_model(statuses, ProviderName.LMSTUDIO, "a")

    assert selection == ModelSelection(None, None, InsightReason.NO_PROVIDER)
    assert not selection.is_selected()


def test_provider_and_model_is_no_model_when_the_provider_does_not_list_the_model() -> None:
    statuses = (_up(OLLAMA, "a"), _up(LMSTUDIO, "c"))

    selection = select_model(statuses, ProviderName.OLLAMA, "c")

    assert selection == ModelSelection(None, None, InsightReason.NO_MODEL)


def test_model_only_uses_the_first_reachable_provider_that_lists_it() -> None:
    statuses = (_up(OLLAMA, "a"), _up(LMSTUDIO, "m", "a"))

    assert select_model(statuses, None, "a") == _chosen(ProviderName.OLLAMA, "a")
    assert select_model(statuses, None, "m") == _chosen(ProviderName.LMSTUDIO, "m")


def test_model_only_skips_an_unreachable_provider() -> None:
    statuses = (_down(OLLAMA), _up(LMSTUDIO, "m"))

    assert select_model(statuses, None, "m") == _chosen(ProviderName.LMSTUDIO, "m")


def test_model_only_is_no_model_when_no_reachable_provider_lists_it() -> None:
    statuses = (_up(OLLAMA, "a"), _down(LMSTUDIO))

    assert select_model(statuses, None, "z").reason is InsightReason.NO_MODEL


def test_model_only_is_no_provider_when_none_is_reachable() -> None:
    selection = select_model((_down(OLLAMA), _down(LMSTUDIO)), None, "z")

    assert selection.reason is InsightReason.NO_PROVIDER


def test_provider_only_uses_the_first_model_it_lists() -> None:
    statuses = (_up(OLLAMA, "a"), _up(LMSTUDIO, "x", "y"))

    selection = select_model(statuses, ProviderName.LMSTUDIO, None)

    assert selection == _chosen(ProviderName.LMSTUDIO, "x")


def test_provider_only_is_no_provider_when_it_is_unreachable_even_if_another_is_up() -> None:
    statuses = (_up(OLLAMA, "a"), _down(LMSTUDIO))

    assert select_model(statuses, ProviderName.LMSTUDIO, None).reason is InsightReason.NO_PROVIDER


def test_provider_only_is_no_model_when_it_lists_no_model() -> None:
    statuses = (_up(OLLAMA, "a"), _up(LMSTUDIO))

    assert select_model(statuses, ProviderName.LMSTUDIO, None).reason is InsightReason.NO_MODEL


def test_neither_uses_the_first_reachable_provider_and_its_first_model() -> None:
    both_up = (_up(OLLAMA, "a"), _up(LMSTUDIO, "x"))
    first_down = (_down(OLLAMA), _up(LMSTUDIO, "x", "y"))

    assert select_model(first_down, None, None) == _chosen(ProviderName.LMSTUDIO, "x")
    assert select_model(both_up, None, None) == _chosen(ProviderName.OLLAMA, "a")


def test_neither_is_no_model_when_the_first_reachable_provider_lists_no_model() -> None:
    statuses = (_up(OLLAMA), _up(LMSTUDIO, "x"))

    assert select_model(statuses, None, None).reason is InsightReason.NO_MODEL


def test_neither_is_no_provider_when_none_is_reachable_or_none_is_given() -> None:
    both_down = select_model((_down(OLLAMA), _down(LMSTUDIO)), None, None)

    assert both_down.reason is InsightReason.NO_PROVIDER
    assert select_model((), None, None).reason is InsightReason.NO_PROVIDER


def test_the_configured_provider_missing_from_the_statuses_is_no_provider() -> None:
    selection = select_model((_up(OLLAMA, "a"),), ProviderName.LMSTUDIO, None)

    assert selection.reason is InsightReason.NO_PROVIDER
