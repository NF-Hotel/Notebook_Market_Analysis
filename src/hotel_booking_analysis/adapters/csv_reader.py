"""Development-only CSV booking reader (ADR-0001 development fallback, UC-001 extension 1a)."""

import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import polars as pl

from hotel_booking_analysis.adapters.json_reader import build_submission, read_input_bytes
from hotel_booking_analysis.domain.booking import (
    BOOLEAN_FIELDS,
    DATE_FIELDS,
    INTEGER_FIELDS,
    BookingSubmission,
    InputSource,
)
from hotel_booking_analysis.domain.errors import InputError

_DAY_FIRST_DATE = re.compile(r"\d{2}-\d{2}-\d{4}")
_INTEGER = re.compile(r"-?\d+")


def _convert(name: str, text: str | None) -> object | None:
    """Convert a CSV cell to the JSON-shaped value the record parser expects.

    A cell that does not fit its field type is passed on as text so the parser counts it as
    invalid instead of losing it.
    """
    if text is None or not text.strip():
        return None
    text = text.strip()
    if name in DATE_FIELDS:
        return _iso_date(text)
    if name in INTEGER_FIELDS or name == "booking_id" or name == "agent":
        return int(text) if _INTEGER.fullmatch(text) else text
    if name in BOOLEAN_FIELDS:
        return _boolean(text)
    if name == "price_per_night":
        return _decimal(text)
    return text


def _iso_date(text: str) -> str:
    if _DAY_FIRST_DATE.fullmatch(text):
        try:
            return datetime.strptime(text, "%d-%m-%Y").date().isoformat()
        except ValueError:
            return text
    return text


def _boolean(text: str) -> object:
    lowered = text.lower()
    if lowered in ("0", "1"):
        return int(lowered)
    if lowered in ("true", "false"):
        return lowered == "true"
    return text


def _decimal(text: str) -> object:
    try:
        return Decimal(text)
    except InvalidOperation:
        return text


class DevelopmentCsvReader:
    """Reads the sample CSV (semicolon, `dd-mm-yyyy`, UTF-8) as `development_sample` records.

    Cells are read as text and converted per field, so blank cells are missing values and
    unparseable cells are invalid values, as for JSON input.
    """

    def read(self, location: Path) -> BookingSubmission:
        content = read_input_bytes(location)
        try:
            frame = pl.read_csv(
                io.BytesIO(content), separator=";", infer_schema=False, encoding="utf8"
            )
        except (pl.exceptions.PolarsError, UnicodeDecodeError) as error:
            raise InputError(
                "INPUT_INVALID_CSV", f"The CSV file cannot be read: {error}"
            ) from error
        if frame.height == 0:
            raise InputError("INPUT_EMPTY", "The CSV file contains no booking records.")
        # Row iteration is acceptable here: development-only fallback, per-cell conversion.
        raw_records = [
            {name: _convert(name, cell) for name, cell in row.items()}
            for row in frame.iter_rows(named=True)
        ]
        return build_submission(InputSource.DEVELOPMENT_SAMPLE, location, content, raw_records)
