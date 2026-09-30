"""LM Studio through its OpenAI-compatible interface (ADR-0009): models from `GET /v1/models`."""

from hotel_booking_analysis.adapters.provider_listing import request_status
from hotel_booking_analysis.domain.llm import LanguageModelProvider, ProviderName, ProviderStatus


class LmStudioProvider:
    """Lists the models of an LM Studio server (`data[].id`)."""

    def __init__(self, base_url: str) -> None:
        self._provider = LanguageModelProvider(ProviderName.LMSTUDIO, base_url)

    def provider(self) -> LanguageModelProvider:
        return self._provider

    def list_models(self, timeout_seconds: float) -> ProviderStatus:
        return request_status(self._provider, "/v1/models", "data", "id", timeout_seconds)
