"""Shared model-list request of the two provider adapters (ADR-0009)."""

from hotel_booking_analysis.adapters.http_json import HttpFailure, get_json
from hotel_booking_analysis.domain.analysis import JsonValue
from hotel_booking_analysis.domain.llm import LanguageModelProvider, ProviderReason, ProviderStatus


def request_status(
    provider: LanguageModelProvider,
    path: str,
    list_key: str,
    name_key: str,
    timeout_seconds: float,
) -> ProviderStatus:
    """List the models of `provider` with one GET; a failure becomes an unreachable status."""
    url = provider.base_url.rstrip("/") + path
    try:
        names = _model_names(get_json(url, timeout_seconds), list_key, name_key)
    except HttpFailure as failure:
        return ProviderStatus.unreachable_because(provider, failure.reason)
    return ProviderStatus.reachable_with(provider, names)


def _model_names(document: JsonValue, list_key: str, name_key: str) -> tuple[str, ...]:
    entries = document.get(list_key) if isinstance(document, dict) else None
    if not isinstance(entries, list):
        raise HttpFailure(ProviderReason.UNEXPECTED_ANSWER, f"'{list_key}' is not a list.")
    names: list[str] = []
    for entry in entries:
        name = entry.get(name_key) if isinstance(entry, dict) else None
        if not isinstance(name, str) or not name:
            raise HttpFailure(ProviderReason.UNEXPECTED_ANSWER, f"An entry has no '{name_key}'.")
        names.append(name)
    return tuple(names)
