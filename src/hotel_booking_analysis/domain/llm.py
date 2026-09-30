"""Language model provider concepts (ADR-0009, DM-001 Language Model Provider)."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from hotel_booking_analysis.domain.errors import Notice


class ProviderName(StrEnum):
    """The two supported local language model providers (ADR-0009, ADR-0012 `llm.provider`)."""

    OLLAMA = "ollama"
    LMSTUDIO = "lmstudio"


class ProviderReason(StrEnum):
    """Why a provider is unreachable (ADR-0009, ADR-0011 `providers[].reason`)."""

    CONNECTION_REFUSED = "CONNECTION_REFUSED"
    TIMEOUT = "TIMEOUT"
    UNEXPECTED_ANSWER = "UNEXPECTED_ANSWER"
    NETWORK_ERROR = "NETWORK_ERROR"


@dataclass(frozen=True, slots=True)
class LanguageModelProvider:
    """A provider with its configured address."""

    name: ProviderName
    base_url: str


@dataclass(frozen=True, slots=True)
class LanguageModel:
    """A model name offered by a provider."""

    provider: LanguageModelProvider
    name: str


@dataclass(frozen=True, slots=True)
class ProviderStatus:
    """Whether a provider answered the discovery check, and the models it lists.

    An unreachable provider carries a reason and no model; a reachable one carries no reason.
    """

    provider: LanguageModelProvider
    reachable: bool
    reason: ProviderReason | None = None
    models: tuple[LanguageModel, ...] = ()

    @classmethod
    def reachable_with(
        cls, provider: LanguageModelProvider, model_names: tuple[str, ...]
    ) -> "ProviderStatus":
        """A reachable provider listing `model_names` (possibly none)."""
        return cls(provider, True, None, tuple(LanguageModel(provider, n) for n in model_names))

    @classmethod
    def unreachable_because(
        cls, provider: LanguageModelProvider, reason: ProviderReason
    ) -> "ProviderStatus":
        """An unreachable provider with its reason."""
        return cls(provider, False, reason)

    def offers(self, model_name: str) -> bool:
        """True when the provider is reachable and lists `model_name`."""
        return any(model.name == model_name for model in self.models)

    def first_model(self) -> LanguageModel | None:
        """The first listed model, or None."""
        return self.models[0] if self.models else None


@dataclass(frozen=True, slots=True)
class ProviderListing:
    """The status of each provider, in the order checked (ADR-0011, UC-004); never stored."""

    generated_at: datetime
    providers: tuple[ProviderStatus, ...]
    notices: tuple[Notice, ...] = ()

    def any_reachable(self) -> bool:
        return any(status.reachable for status in self.providers)
