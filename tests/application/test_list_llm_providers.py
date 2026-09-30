"""Tests for the list-LLM-providers use case with fakes of its ports (UC-004, ADR-0011)."""

from datetime import UTC, datetime
from pathlib import Path

from hotel_booking_analysis.application.analyze_bookings import RunStatus
from hotel_booking_analysis.application.configuration import (
    AppConfiguration,
    LlmConfiguration,
    LoadedConfiguration,
)
from hotel_booking_analysis.application.list_llm_providers import ListLlmProviders
from hotel_booking_analysis.application.ports import LlmProvider
from hotel_booking_analysis.domain.errors import ConfigurationError, Notice
from hotel_booking_analysis.domain.llm import (
    LanguageModelProvider,
    ProviderListing,
    ProviderName,
    ProviderReason,
    ProviderStatus,
)
from hotel_booking_analysis.domain.result import ResultError
from tests.support import (
    DiscoveryOnlyProvider,
    FakeConfigurationLoader,
    FixedClock,
    RecordingSink,
)

MOMENT = datetime(2026, 9, 30, 8, 0, tzinfo=UTC)


class FakeProvider(DiscoveryOnlyProvider):
    """A provider with a fixed answer; records that it was asked and with which deadline."""

    def __init__(
        self,
        name: ProviderName,
        events: list[str],
        models: tuple[str, ...] = (),
        reason: ProviderReason | None = None,
    ) -> None:
        self._provider = LanguageModelProvider(name, f"http://localhost/{name.value}")
        self._events = events
        self._models = models
        self._reason = reason
        self.timeouts: list[float] = []

    def provider(self) -> LanguageModelProvider:
        return self._provider

    def list_models(self, timeout_seconds: float) -> ProviderStatus:
        self._events.append(f"list:{self._provider.name.value}")
        self.timeouts.append(timeout_seconds)
        if self._reason is not None:
            return ProviderStatus.unreachable_because(self._provider, self._reason)
        return ProviderStatus.reachable_with(self._provider, self._models)


class FakeRegistry:
    """Hands out the given providers and records the configuration it was asked with."""

    def __init__(self, providers: tuple[LlmProvider, ...]) -> None:
        self._providers = providers
        self.configurations: list[LlmConfiguration] = []

    def providers(self, configuration: LlmConfiguration) -> tuple[LlmProvider, ...]:
        self.configurations.append(configuration)
        return self._providers


class FakeProviderSerializer:
    """Keeps what it was given and returns a marker line."""

    def __init__(self) -> None:
        self.listings: list[ProviderListing] = []
        self.failures: list[tuple[ResultError, tuple[Notice, ...], datetime]] = []

    def serialize(self, listing: ProviderListing) -> str:
        self.listings.append(listing)
        return "listing"

    def serialize_failure(
        self, error: ResultError, notices: tuple[Notice, ...], generated_at: datetime
    ) -> str:
        self.failures.append((error, notices, generated_at))
        return "failure"


class RecordingLoader(FakeConfigurationLoader):
    def __init__(self, loaded: LoadedConfiguration | ConfigurationError) -> None:
        super().__init__(loaded)
        self.calls: list[tuple[Path | None, bool]] = []

    def load(self, explicit_path: Path | None, with_llm: bool = False) -> LoadedConfiguration:
        self.calls.append((explicit_path, with_llm))
        return super().load(explicit_path, with_llm)


class Rig:
    """A use case wired to fakes; by default both providers are reachable."""

    def __init__(
        self,
        ollama_reason: ProviderReason | None = None,
        lmstudio_reason: ProviderReason | None = None,
        loaded: LoadedConfiguration | ConfigurationError | None = None,
        fail_delivery: bool = False,
    ) -> None:
        self.events: list[str] = []
        self.ollama = FakeProvider(
            ProviderName.OLLAMA, self.events, ("llama3", "qwen"), ollama_reason
        )
        self.lmstudio = FakeProvider(ProviderName.LMSTUDIO, self.events, ("phi",), lmstudio_reason)
        self.registry = FakeRegistry((self.ollama, self.lmstudio))
        self.loader = RecordingLoader(
            loaded
            or LoadedConfiguration(
                AppConfiguration(llm=LlmConfiguration(discovery_timeout_seconds=1.25))
            )
        )
        self.serializer = FakeProviderSerializer()
        self.sink = RecordingSink(self.events, fail=fail_delivery)
        self.use_case = ListLlmProviders(
            self.loader, self.registry, self.serializer, self.sink, FixedClock(MOMENT)
        )


def test_run_lists_both_reachable_providers_in_order_with_their_models() -> None:
    rig = Rig()

    outcome = rig.use_case.run(None)

    assert outcome.status is RunStatus.SUCCEEDED
    assert outcome.serialized == "listing"
    assert outcome.message is None
    assert rig.sink.lines == ["listing"]
    (listing,) = rig.serializer.listings
    assert listing.generated_at == MOMENT
    assert [s.provider.name for s in listing.providers] == [
        ProviderName.OLLAMA,
        ProviderName.LMSTUDIO,
    ]
    assert [[m.name for m in s.models] for s in listing.providers] == [["llama3", "qwen"], ["phi"]]
    assert listing.notices == ()
    assert rig.events == ["list:ollama", "list:lmstudio", "sink"]


def test_run_loads_the_llm_configuration_and_uses_the_discovery_timeout() -> None:
    rig = Rig()
    path = Path("custom.toml")

    rig.use_case.run(path)

    assert rig.loader.calls == [(path, True)]
    assert rig.registry.configurations == [LlmConfiguration(discovery_timeout_seconds=1.25)]
    assert rig.ollama.timeouts == [1.25]
    assert rig.lmstudio.timeouts == [1.25]


def test_run_reports_an_unreachable_provider_as_an_entry_and_still_succeeds() -> None:
    rig = Rig(ollama_reason=ProviderReason.CONNECTION_REFUSED)

    outcome = rig.use_case.run(None)

    assert outcome.status is RunStatus.SUCCEEDED
    (listing,) = rig.serializer.listings
    unreachable, reachable = listing.providers
    assert unreachable.reason is ProviderReason.CONNECTION_REFUSED
    assert reachable.reachable
    assert listing.notices == ()
    assert rig.lmstudio.timeouts == [1.25]


def test_run_adds_notice_when_no_provider_is_reachable_and_still_succeeds() -> None:
    rig = Rig(ProviderReason.TIMEOUT, ProviderReason.NETWORK_ERROR)

    outcome = rig.use_case.run(None)

    assert outcome.status is RunStatus.SUCCEEDED
    (listing,) = rig.serializer.listings
    assert [n.code for n in listing.notices] == ["NO_PROVIDER_REACHABLE"]
    assert [s.reason for s in listing.providers] == [
        ProviderReason.TIMEOUT,
        ProviderReason.NETWORK_ERROR,
    ]


def test_run_with_invalid_configuration_gives_failed_document_and_contacts_no_provider() -> None:
    error = ConfigurationError("'llm.ollama_url' names a remote host.", "llm.ollama_url")
    rig = Rig(loaded=error)

    outcome = rig.use_case.run(None)

    assert outcome.status is RunStatus.INPUT_FAILED
    assert outcome.serialized == "failure"
    assert outcome.message == error.message
    (failure_error, notices, generated_at) = rig.serializer.failures[0]
    assert failure_error == ResultError("CONFIGURATION_ERROR", error.message)
    assert notices == ()
    assert generated_at == MOMENT
    assert rig.serializer.listings == []
    assert rig.events == ["sink"]
    assert rig.registry.configurations == []


def test_run_delivery_failure_of_the_listing_gives_delivery_failed() -> None:
    rig = Rig(fail_delivery=True)

    outcome = rig.use_case.run(None)

    assert outcome.status is RunStatus.DELIVERY_FAILED
    assert outcome.serialized is None
    assert outcome.message is not None
    assert "nothing was stored" in outcome.message
    assert "The listing could not" in outcome.message


def test_run_delivery_failure_of_the_failed_document_gives_delivery_failed() -> None:
    rig = Rig(loaded=ConfigurationError("bad", "llm.model"), fail_delivery=True)

    outcome = rig.use_case.run(None)

    assert outcome.status is RunStatus.DELIVERY_FAILED
    assert outcome.message is not None
    assert "CONFIGURATION_ERROR" in outcome.message
