"""Years of the holiday listing (ADR-0011 `--years` value, UC-003).

Forms: a single year `2025`, a range `2024-2026` (inclusive) or a comma list of single years
`2024,2026`. Years are whole numbers from 1900 to 2100, at most 30 different ones.
"""

import re

from hotel_booking_analysis.domain.errors import InvalidYearsError

MIN_YEAR = 1900
MAX_YEAR = 2100
MAX_YEARS = 30

_NUMBER = re.compile(r"[0-9]+", re.ASCII)
_RANGE = re.compile(r"([0-9]+)-([0-9]+)", re.ASCII)


def parse_years(text: str | None, current_year: int) -> tuple[int, ...]:
    """Return the requested years, without duplicates and ascending.

    `None` means the current year. Raises `InvalidYearsError` for any other invalid form.
    """
    if text is None:
        return (current_year,)
    value = text.strip()
    if not value:
        raise InvalidYearsError("The years value is empty.")
    years = _range(value) if _RANGE.fullmatch(value) else _list(value)
    distinct = sorted(set(years))
    if len(distinct) > MAX_YEARS:
        raise InvalidYearsError(
            f"The years value names {len(distinct)} different years; "
            f"at most {MAX_YEARS} are allowed."
        )
    return tuple(distinct)


def _range(value: str) -> list[int]:
    first_text, last_text = value.split("-")
    first, last = _year(first_text), _year(last_text)
    if first > last:
        raise InvalidYearsError(f"The range {value} is reversed; the first year is after the last.")
    return list(range(first, last + 1))


def _list(value: str) -> list[int]:
    parts = value.split(",")
    if len(parts) > 1 and any("-" in part for part in parts):
        raise InvalidYearsError("A range of years is not allowed inside a comma list of years.")
    return [_year(part) for part in parts]


def _year(text: str) -> int:
    if not _NUMBER.fullmatch(text):
        raise InvalidYearsError(f"'{text}' is not a year; use a whole number such as 2025.")
    year = int(text)
    if not MIN_YEAR <= year <= MAX_YEAR:
        raise InvalidYearsError(f"The year {year} is outside {MIN_YEAR} to {MAX_YEAR}.")
    return year
