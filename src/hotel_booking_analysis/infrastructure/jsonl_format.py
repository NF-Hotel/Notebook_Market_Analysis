"""Line-level rules of the JSONL history (ADR-0003 read rule and line format)."""

import json

from hotel_booking_analysis.domain.analysis import JsonValue
from hotel_booking_analysis.domain.history import REQUIRED_ENVELOPE_FIELDS

NEWLINE = b"\n"


def split_lines(content: bytes) -> list[bytes]:
    """Split on newline bytes only; a final unterminated fragment counts as a line.

    Blank lines are kept here so a rewrite can leave every line in place; callers that
    count or list results skip them.
    """
    lines = content.split(NEWLINE)
    if lines and lines[-1] == b"":
        lines.pop()
    return lines


def parse_valid_result(line: bytes) -> dict[str, JsonValue] | None:
    """Return the parsed result if the line is JSON with every envelope field, else None."""
    try:
        document = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(document, dict):
        return None
    if any(name not in document for name in REQUIRED_ENVELOPE_FIELDS):
        return None
    return document


def is_blank(line: bytes) -> bool:
    return not line.strip()
