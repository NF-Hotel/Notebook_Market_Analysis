"""Ollama through its own HTTP interface (ADR-0009): models from `GET /api/tags`, text from
`POST /api/chat`."""

from hotel_booking_analysis.adapters.chat_generation import chat_messages, request_text
from hotel_booking_analysis.adapters.provider_listing import request_status
from hotel_booking_analysis.domain.analysis import JsonValue
from hotel_booking_analysis.domain.insight_prompt import InsightPrompt
from hotel_booking_analysis.domain.llm import LanguageModelProvider, ProviderName, ProviderStatus


class OllamaProvider:
    """Lists the models of an Ollama server (`models[].name`) and generates with its chat API."""

    def __init__(self, base_url: str) -> None:
        self._provider = LanguageModelProvider(ProviderName.OLLAMA, base_url)

    def provider(self) -> LanguageModelProvider:
        return self._provider

    def list_models(self, timeout_seconds: float) -> ProviderStatus:
        return request_status(self._provider, "/api/tags", "models", "name", timeout_seconds)

    def generate(
        self, model: str, prompt: InsightPrompt, temperature: float, timeout_seconds: float
    ) -> str:
        """Ask for a JSON answer (`message.content`); raises `LlmError` or `LlmTimeoutError`."""
        body = self._chat_body(model, prompt, temperature)
        return request_text(
            self._provider, "/api/chat", body, ("message", "content"), timeout_seconds
        )

    @staticmethod
    def _chat_body(model: str, prompt: InsightPrompt, temperature: float) -> dict[str, JsonValue]:
        return {
            "model": model,
            "messages": chat_messages(prompt),
            "stream": False,
            "format": "json",
            "options": {"temperature": temperature},
        }
