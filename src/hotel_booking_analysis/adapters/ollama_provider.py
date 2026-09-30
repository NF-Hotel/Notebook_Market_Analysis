"""Ollama through its own HTTP interface (ADR-0009): models from `GET /api/tags`."""

from hotel_booking_analysis.adapters.provider_listing import request_status
from hotel_booking_analysis.domain.llm import LanguageModelProvider, ProviderName, ProviderStatus


class OllamaProvider:
    """Lists the models of an Ollama server (`models[].name`)."""

    def __init__(self, base_url: str) -> None:
        self._provider = LanguageModelProvider(ProviderName.OLLAMA, base_url)

    def provider(self) -> LanguageModelProvider:
        return self._provider

    def list_models(self, timeout_seconds: float) -> ProviderStatus:
        return request_status(self._provider, "/api/tags", "models", "name", timeout_seconds)
