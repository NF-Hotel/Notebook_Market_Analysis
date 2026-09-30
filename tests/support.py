"""Shared test builders and fakes."""

import json
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

from hotel_booking_analysis.application.configuration import LoadedConfiguration
from hotel_booking_analysis.domain.booking import (
    BookingRecord,
    BookingSubmission,
    InputSource,
)
from hotel_booking_analysis.domain.errors import (
    HistoryError,
    InputError,
    ResultDeliveryError,
)
from hotel_booking_analysis.domain.history import HistoryReadout, RetentionPolicy
from hotel_booking_analysis.domain.result import AnalysisResult


def make_submission(*records: BookingRecord, unknown: tuple[str, ...] = ()) -> BookingSubmission:
    return BookingSubmission(
        source=InputSource.SUPPLIED,
        reference="bookings.json",
        content_sha256="0" * 64,
        records=tuple(records),
        unknown_fields=unknown,
    )


def write_json(path: Path, document: object) -> Path:
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


class FakeBookingReader:
    """Records the locations it was asked to read and returns a fixed submission."""

    def __init__(self, submission: BookingSubmission) -> None:
        self.submission = submission
        self.locations: list[Path] = []

    def read(self, location: Path) -> BookingSubmission:
        self.locations.append(location)
        return self.submission


def full_record(booking_id: str = "1") -> BookingRecord:
    """A record with a valid value in every field the six analyses need."""
    return BookingRecord(
        booking_id=booking_id,
        is_canceled=False,
        lead_time=10,
        booking_date=date(2021, 3, 8),
        arrival_date=date(2021, 3, 18),
        stays_in_weekend_nights=1,
        stays_in_week_nights=2,
        adults=2,
    )


def make_line(result_id: str, status: str = "completed") -> str:
    """A compact JSON line that carries every envelope field of a stored result."""
    document = {
        "schema_version": "1.0",
        "result_id": result_id,
        "generated_at": "2026-09-29T12:00:00.000Z",
        "status": status,
        "input": {},
        "data_quality": {},
        "analyses": {},
        "notices": [],
    }
    return json.dumps(document, separators=(",", ":"))


class FixedClock:
    def __init__(self, moment: datetime = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)) -> None:
        self.moment = moment

    def now(self) -> datetime:
        return self.moment


class SequentialIds:
    """Result IDs that are valid UUIDs and predictable."""

    def __init__(self) -> None:
        self.count = 0

    def new_id(self) -> str:
        self.count += 1
        return str(uuid.UUID(int=self.count))


class FakeConfigurationLoader:
    def __init__(self, loaded: LoadedConfiguration | InputError) -> None:
        self.loaded = loaded

    def load(self, explicit_path: Path | None, with_llm: bool = False) -> LoadedConfiguration:
        if isinstance(self.loaded, InputError):
            raise self.loaded
        return self.loaded


class FakeSerializer:
    """Serializes to a compact line that carries the envelope fields of `make_line`."""

    def serialize(self, result: AnalysisResult) -> str:
        return make_line(result.result_id, result.status.value)


class FakeHistoryWriter:
    """Records appended lines; fails with `error` after recording the attempt if given."""

    def __init__(self, events: list[str], error: HistoryError | None = None) -> None:
        self.events = events
        self.error = error
        self.lines: list[str] = []
        self.locations: list[Path] = []
        self.retentions: list[RetentionPolicy] = []

    def append(self, location: Path, line: str, retention: RetentionPolicy) -> None:
        self.events.append("history")
        self.locations.append(location)
        self.retentions.append(retention)
        if self.error is not None:
            raise self.error
        self.lines.append(line)


class FakeHistoryReader:
    def __init__(self, readout: HistoryReadout | None = None) -> None:
        self.readout = readout or HistoryReadout((), 0)

    def read(self, location: Path) -> HistoryReadout:
        return self.readout


class RecordingSink:
    """Records delivered lines; fails when `fail` is set."""

    def __init__(self, events: list[str], fail: bool = False) -> None:
        self.events = events
        self.fail = fail
        self.lines: list[str] = []

    def write(self, line: str) -> None:
        self.events.append("sink")
        if self.fail:
            raise ResultDeliveryError("broken pipe")
        self.lines.append(line)
