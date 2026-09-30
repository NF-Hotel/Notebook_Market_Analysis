"""LM Studio through its OpenAI-compatible interface (ADR-0009): models from `GET /v1/models`,
text from `POST /v1/chat/completions`."""

from hotel_booking_analysis.adapters.chat_generation import chat_messages, request_text
from hotel_booking_analysis.adapters.provider_listing import request_status
from hotel_booking_analysis.domain.analysis import JsonValue
from hotel_booking_analysis.domain.insight_prompt import InsightPrompt
from hotel_booking_analysis.domain.llm import LanguageModelProvider, ProviderName, ProviderStatus

_TEXT_PATH: tuple[str | int, ...] = ("choices", 0, "message", "content")


class LmStudioProvider:
    """Lists the models of an LM Studio server (`data[].id`) and generates with its chat API."""

    def __init__(self, base_url: str) -> None:
        self._provider = LanguageModelProvider(ProviderName.LMSTUDIO, base_url)

    def provider(self) -> LanguageModelProvider:
        return self._provider

    def list_models(self, timeout_seconds: float) -> ProviderStatus:
        return request_status(self._provider, "/v1/models", "data", "id", timeout_seconds)

    def generate(
        self, model: str, prompt: InsightPrompt, temperature: float, timeout_seconds: float
    ) -> str:
        """Ask for the reply text (`choices[0].message.content`); raises `LlmError` or timeout."""
        body = self._chat_body(model, prompt, temperature)
        return request_text(
            self._provider, "/v1/chat/completions", body, _TEXT_PATH, timeout_seconds
        )

    @staticmethod
    def _chat_body(model: str, prompt: InsightPrompt, temperature: float) -> dict[str, JsonValue]:
        return {"model": model, "messages": chat_messages(prompt), "temperature": temperature}
