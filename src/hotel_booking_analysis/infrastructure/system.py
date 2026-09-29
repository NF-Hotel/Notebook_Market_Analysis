"""System clock, result identifiers and standard-output sink (ADR-0002, ADR-0005)."""

import uuid
from datetime import UTC, datetime
from typing import BinaryIO

from hotel_booking_analysis.domain.errors import ResultDeliveryError


class SystemClock:
    """Current time in UTC."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class UuidGenerator:
    """Random UUID4 identifiers (ADR-0002 `result_id`)."""

    def new_id(self) -> str:
        return str(uuid.uuid4())


class StreamResultSink:
    """Writes the serialized result and one newline to a binary stream and flushes.

    A binary stream keeps the bytes identical to the history line on every platform
    (no newline translation).
    """

    def __init__(self, stream: BinaryIO) -> None:
        self._stream = stream

    def write(self, line: str) -> None:
        try:
            self._stream.write(line.encode("utf-8") + b"\n")
            self._stream.flush()
        except (OSError, ValueError) as error:
            raise ResultDeliveryError(str(error)) from error
