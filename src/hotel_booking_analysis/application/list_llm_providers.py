"""List-LLM-providers use case (UC-004, ADR-0009, ADR-0011, ADR-0008).

Order of a run: configuration (with the `[llm]` values validated), discovery, listing, hand-over.
It never touches the history, never asks a model to generate text and sends no booking data.
An unreachable provider is a normal entry, not a failure.
"""

from dataclasses import dataclass
from pathlib import Path

from hotel_booking_analysis.application.listing_delivery import deliver_listing
from hotel_booking_analysis.application.listing_outcome import ListingOutcome
from hotel_booking_analysis.application.ports import (
    Clock,
    ConfigurationLoader,
    LlmProviderRegistry,
    ProviderListingSerializer,
    ResultSink,
)
from hotel_booking_analysis.application.provider_discovery import discover_providers
from hotel_booking_analysis.domain.errors import InputError, Notice
from hotel_booking_analysis.domain.llm import ProviderListing
from hotel_booking_analysis.domain.result import ResultError

NO_PROVIDER_REACHABLE = "NO_PROVIDER_REACHABLE"


@dataclass(frozen=True, slots=True)
class ListLlmProviders:
    """Returns the status and models of each configured provider (UC-004)."""

    configuration_loader: ConfigurationLoader
    registry: LlmProviderRegistry
    serializer: ProviderListingSerializer
    sink: ResultSink
    clock: Clock

    def run(self, config_path: Path | None) -> ListingOutcome:
        try:
            llm = self.configuration_loader.load(config_path, with_llm=True).configuration.llm
        except InputError as error:
            return self._deliver(self._failure_line(error, ()), error)
        statuses = discover_providers(self.registry.providers(llm), llm.discovery_timeout_seconds)
        listing = ProviderListing(self.clock.now(), statuses)
        if not listing.any_reachable():
            listing = ProviderListing(
                listing.generated_at,
                statuses,
                (Notice(NO_PROVIDER_REACHABLE, "No language model provider could be reached."),),
            )
        return self._deliver(self.serializer.serialize(listing), None)

    def _failure_line(self, error: InputError, notices: tuple[Notice, ...]) -> str:
        return self.serializer.serialize_failure(
            ResultError(error.code, error.message), notices, self.clock.now()
        )

    def _deliver(self, line: str, failure: InputError | None) -> ListingOutcome:
        return deliver_listing(self.sink, line, failure)
