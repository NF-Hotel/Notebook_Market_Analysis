"""Tests of the provider status and listing values (DCD-001 domain part 2)."""

from datetime import UTC, datetime

from hotel_booking_analysis.domain.llm import (
    LanguageModelProvider,
    ProviderListing,
    ProviderName,
    ProviderReason,
    ProviderStatus,
)

OLLAMA = LanguageModelProvider(ProviderName.OLLAMA, "http://localhost:11434")
LMSTUDIO = LanguageModelProvider(ProviderName.LMSTUDIO, "http://localhost:1234")
MOMENT = datetime(2026, 9, 30, tzinfo=UTC)


def test_reachable_status_lists_models_in_order_and_offers_them() -> None:
    status = ProviderStatus.reachable_with(OLLAMA, ("b", "a"))

    assert status.reachable
    assert status.reason is None
    assert [model.name for model in status.models] == ["b", "a"]
    assert all(model.provider == OLLAMA for model in status.models)
    assert status.offers("a")
    assert not status.offers("c")


def test_first_model_is_the_first_listed_model() -> None:
    first = ProviderStatus.reachable_with(OLLAMA, ("b", "a")).first_model()

    assert first is not None
    assert first.name == "b"


def test_first_model_is_none_when_no_model_is_listed() -> None:
    assert ProviderStatus.reachable_with(OLLAMA, ()).first_model() is None


def test_unreachable_status_has_reason_and_no_models() -> None:
    status = ProviderStatus.unreachable_because(OLLAMA, ProviderReason.TIMEOUT)

    assert not status.reachable
    assert status.reason is ProviderReason.TIMEOUT
    assert status.models == ()
    assert not status.offers("a")
    assert status.first_model() is None


def test_any_reachable_is_true_when_one_provider_is_reachable() -> None:
    listing = ProviderListing(
        MOMENT,
        (
            ProviderStatus.unreachable_because(OLLAMA, ProviderReason.CONNECTION_REFUSED),
            ProviderStatus.reachable_with(LMSTUDIO, ()),
        ),
    )

    assert listing.any_reachable()


def test_any_reachable_is_false_when_no_provider_is_reachable() -> None:
    listing = ProviderListing(
        MOMENT,
        (
            ProviderStatus.unreachable_because(OLLAMA, ProviderReason.CONNECTION_REFUSED),
            ProviderStatus.unreachable_because(LMSTUDIO, ProviderReason.NETWORK_ERROR),
        ),
    )

    assert not listing.any_reachable()
    assert listing.notices == ()
