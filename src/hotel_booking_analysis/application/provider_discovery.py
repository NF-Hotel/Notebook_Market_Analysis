"""Discovery of the language model providers (ADR-0009), shared by the listing and the insights."""

from hotel_booking_analysis.application.ports import LlmProvider
from hotel_booking_analysis.domain.llm import ProviderName, ProviderStatus


def discover_providers(
    providers: tuple[LlmProvider, ...], discovery_timeout_seconds: float
) -> tuple[ProviderStatus, ...]:
    """Check the providers one after the other, in the given order, each within the deadline."""
    return tuple(provider.list_models(discovery_timeout_seconds) for provider in providers)


def find_provider(providers: tuple[LlmProvider, ...], name: ProviderName) -> LlmProvider | None:
    """The provider with the given name, or None."""
    for provider in providers:
        if provider.provider().name is name:
            return provider
    return None
