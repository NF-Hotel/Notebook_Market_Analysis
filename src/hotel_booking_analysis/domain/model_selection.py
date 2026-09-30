"""Choice of the provider and model for insights (ADR-0009 "Model choice")."""

from dataclasses import dataclass

from hotel_booking_analysis.domain.insight import InsightReason
from hotel_booking_analysis.domain.llm import ProviderName, ProviderStatus


@dataclass(frozen=True, slots=True)
class ModelSelection:
    """The chosen provider and model, or the reason none was chosen (no model is contacted)."""

    provider: ProviderName | None = None
    model: str | None = None
    reason: InsightReason | None = None

    def is_selected(self) -> bool:
        return self.provider is not None and self.model is not None

    @classmethod
    def chosen(cls, provider: ProviderName, model: str) -> "ModelSelection":
        return cls(provider, model)

    @classmethod
    def none_because(cls, reason: InsightReason) -> "ModelSelection":
        return cls(reason=reason)


def select_model(
    statuses: tuple[ProviderStatus, ...], provider: ProviderName | None, model: str | None
) -> ModelSelection:
    """Apply the four rules of ADR-0009 to the discovered `statuses`, in their order.

    `provider` and `model` are the configured values (None for automatic). `NO_PROVIDER` means no
    provider can be reached; `NO_MODEL` means one is reachable but the model is not offered.
    """
    candidates = [s for s in statuses if provider is None or s.provider.name is provider]
    reachable = [s for s in candidates if s.reachable]
    if not reachable:
        return ModelSelection.none_because(InsightReason.NO_PROVIDER)
    if model is not None:
        return _selection_of_named_model(reachable, model)
    first = reachable[0]
    chosen = first.first_model()
    if chosen is None:
        return ModelSelection.none_because(InsightReason.NO_MODEL)
    return ModelSelection.chosen(first.provider.name, chosen.name)


def _selection_of_named_model(reachable: list[ProviderStatus], model: str) -> ModelSelection:
    for status in reachable:
        if status.offers(model):
            return ModelSelection.chosen(status.provider.name, model)
    return ModelSelection.none_because(InsightReason.NO_MODEL)
