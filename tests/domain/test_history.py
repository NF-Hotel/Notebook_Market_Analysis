"""Tests for the retention policy (ADR-0004, US-001.09)."""

import pytest

from hotel_booking_analysis.domain.history import RetentionPolicy


def test_retention_defaults_to_ten() -> None:
    assert RetentionPolicy().limit == 10


@pytest.mark.parametrize("limit", [0, -1, True])
def test_retention_rejects_values_below_one_or_booleans(limit: int) -> None:
    with pytest.raises(ValueError):
        RetentionPolicy(limit)
