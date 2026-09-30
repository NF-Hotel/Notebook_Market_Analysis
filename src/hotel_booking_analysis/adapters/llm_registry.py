"""Creates the provider adapters from the configured addresses (ADR-0009, ADR-0012)."""

from hotel_booking_analysis.adapters.lmstudio_provider import LmStudioProvider
from hotel_booking_analysis.adapters.ollama_provider import OllamaProvider
from hotel_booking_analysis.application.configuration import LlmConfiguration
from hotel_booking_analysis.application.ports import LlmProvider


class ConfiguredLlmProviders:
    """The two providers, always in the order ollama, lmstudio."""

    def providers(self, configuration: LlmConfiguration) -> tuple[LlmProvider, ...]:
        return (
            OllamaProvider(configuration.ollama_url),
            LmStudioProvider(configuration.lmstudio_url),
        )
