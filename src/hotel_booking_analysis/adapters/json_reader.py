"""JSON booking reader (ADR-0001, US-001.01, UC-001 steps 1-2 and extension 2a)."""

import hashlib
import json
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path

from hotel_booking_analysis.adapters.record_parsing import parse_record, unknown_field_names
from hotel_booking_analysis.domain.booking import BookingSubmission, InputSource
from hotel_booking_analysis.domain.errors import InputError


def build_submission(
    source: InputSource,
    location: Path,
    content: bytes,
    raw_records: Sequence[Mapping[str, object]],
) -> BookingSubmission:
    """Assemble a submission from raw records; shared by the JSON and CSV readers."""
    return BookingSubmission(
        source=source,
        reference=location.name,
        content_sha256=hashlib.sha256(content).hexdigest(),
        records=tuple(parse_record(raw) for raw in raw_records),
        unknown_fields=unknown_field_names(raw_records),
    )


def read_input_bytes(location: Path) -> bytes:
    """Read the input file, turning I/O problems into an input error (ADR-0005)."""
    try:
        return location.read_bytes()
    except FileNotFoundError:
        raise InputError("INPUT_NOT_FOUND", f"Input file not found: {location.name}") from None
    except OSError as error:
        raise InputError(
            "INPUT_UNREADABLE", f"Input file cannot be read: {location.name} ({error})"
        ) from error


def _reject_constant(name: str) -> object:
    raise ValueError(f"{name} is not valid JSON")


class JsonBookingReader:
    """Reads a UTF-8 JSON file whose top level is an array of booking objects (ADR-0001).

    Non-integer numbers are read as exact `Decimal`.
    """

    def read(self, location: Path) -> BookingSubmission:
        content = read_input_bytes(location)
        document = self._decode(content)
        if not isinstance(document, list):
            raise InputError("INPUT_NOT_ARRAY", "The top level of the input must be an array.")
        if not document:
            raise InputError("INPUT_EMPTY", "The input array contains no booking records.")
        raw_records: list[Mapping[str, object]] = []
        for index, item in enumerate(document):
            if not isinstance(item, dict):
                raise InputError(
                    "INPUT_RECORD_NOT_OBJECT", f"Input item {index} is not a JSON object."
                )
            raw_records.append(item)
        return build_submission(InputSource.SUPPLIED, location, content, raw_records)

    @staticmethod
    def _decode(content: bytes) -> object:
        try:
            return json.loads(
                content.decode("utf-8"),
                parse_float=Decimal,
                parse_constant=_reject_constant,
            )
        except (UnicodeDecodeError, ValueError) as error:
            raise InputError(
                "INPUT_INVALID_JSON", f"The input is not valid JSON: {error}"
            ) from error
