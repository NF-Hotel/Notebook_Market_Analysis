"""Shared test builders and fakes."""

import json
from pathlib import Path

from hotel_booking_analysis.domain.booking import (
    BookingRecord,
    BookingSubmission,
    InputSource,
)


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
