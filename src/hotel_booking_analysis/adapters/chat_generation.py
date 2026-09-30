"""Shared generation request of the two provider adapters (ADR-0009 "Generation")."""

from collections.abc import Mapping

from hotel_booking_analysis.adapters.http_json import HttpFailure, post_json
from hotel_booking_analysis.domain.analysis import JsonValue
from hotel_booking_analysis.domain.errors import LlmError, LlmTimeoutError
from hotel_booking_analysis.domain.insight_prompt import InsightPrompt
from hotel_booking_analysis.domain.llm import LanguageModelProvider, ProviderReason


def chat_messages(prompt: InsightPrompt) -> list[JsonValue]:
    """The instruction as the system message and the data block as the user message."""
    return [
        {"role": "system", "content": prompt.instruction},
        {"role": "user", "content": prompt.data_json},
    ]


def request_text(
    provider: LanguageModelProvider,
    path: str,
    body: Mapping[str, JsonValue],
    text_path: tuple[str | int, ...],
    timeout_seconds: float,
) -> str:
    """POST `body` once and return the text at `text_path` of the answer; never retried.

    Raises `LlmTimeoutError` when the total deadline passes and `LlmError` for a refused
    connection, an error status or an answer without text.
    """
    url = provider.base_url.rstrip("/") + path
    try:
        document = post_json(url, body, timeout_seconds)
    except HttpFailure as failure:
        if failure.reason is ProviderReason.TIMEOUT:
            raise LlmTimeoutError(str(failure)) from failure
        raise LlmError(f"{failure.reason.value}: {failure}") from failure
    text = _dig(document, text_path)
    if not isinstance(text, str):
        raise LlmError("The answer holds no text.")
    return text


def _dig(document: JsonValue, path: tuple[str | int, ...]) -> JsonValue:
    for step in path:
        if isinstance(step, str) and isinstance(document, dict):
            document = document.get(step)
        elif isinstance(step, int) and isinstance(document, list) and len(document) > step:
            document = document[step]
        else:
            return None
    return document
