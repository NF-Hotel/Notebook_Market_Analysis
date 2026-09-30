"""Tests for the `--years` value of the holiday listing (ADR-0011, UC-003)."""

import pytest

from hotel_booking_analysis.domain.errors import InputError, InvalidYearsError
from hotel_booking_analysis.domain.year_selection import parse_years

CURRENT = 2026


def test_parse_years_defaults_to_current_year_when_absent() -> None:
    assert parse_years(None, CURRENT) == (2026,)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2025", (2025,)),
        ("1900", (1900,)),
        ("2100", (2100,)),
        (" 2025 ", (2025,)),
        ("2024-2026", (2024, 2025, 2026)),
        ("2025-2025", (2025,)),
        ("2024,2026", (2024, 2026)),
        ("2026,2024", (2024, 2026)),
        ("2025,2025,2024", (2024, 2025)),
    ],
)
def test_parse_years_accepts_valid_forms_sorted_and_deduplicated(
    text: str, expected: tuple[int, ...]
) -> None:
    assert parse_years(text, CURRENT) == expected


def test_parse_years_accepts_exactly_thirty_years() -> None:
    assert len(parse_years("2000-2029", CURRENT)) == 30


def test_parse_years_counts_different_years_only() -> None:
    assert parse_years(",".join(["2025"] * 40), CURRENT) == (2025,)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "abc",
        "20x5",
        "2025.5",
        "-2025",
        "2025-",
        "2024-2025-2026",
        "2024,",
        ",2024",
        "2024 2026",
        "1899",
        "2101",
        "0",
        "2026-2024",
        "2024-2026,2028",
        "2024,2026-2028",
        "2000-2030",
        "1900-2100",
        "٢٠٢٥",
    ],
)
def test_parse_years_rejects_invalid_values_with_invalid_years_code(text: str) -> None:
    with pytest.raises(InvalidYearsError) as error:
        parse_years(text, CURRENT)

    assert error.value.code == "INVALID_YEARS"
    assert error.value.message
    assert isinstance(error.value, InputError)


def test_parse_years_rejects_more_than_thirty_different_years() -> None:
    text = ",".join(str(year) for year in range(2000, 2031))

    with pytest.raises(InvalidYearsError, match="31"):
        parse_years(text, CURRENT)
