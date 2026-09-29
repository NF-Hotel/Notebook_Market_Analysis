"""Day classification around holidays (ADR-0007 Cambodian holidays, US-001.03).

Every calendar day in a span is a holiday, within a window before a holiday, within a window
after one, or baseline. A day near two holidays takes the closest; a tie and a holiday itself
take the holiday class. A day inside the largest window but outside a smaller one belongs to
the wider window groups only and never to the baseline.
"""

from bisect import bisect_left
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum


class DayKind(StrEnum):
    """Class of a calendar day relative to holidays."""

    HOLIDAY = "holiday"
    BEFORE = "before"
    AFTER = "after"
    BASELINE = "baseline"


@dataclass(frozen=True, slots=True)
class DayClass:
    """Class of one day; `distance` is the days to the closest holiday.

    `distance` is 0 for a holiday and None for a baseline day.
    """

    day: date
    kind: DayKind
    distance: int | None = None

    def in_window(self, kind: DayKind, window_days: int) -> bool:
        """Tell whether the day is within `window_days` before or after a holiday."""
        return self.kind is kind and self.distance is not None and self.distance <= window_days


def classify_days(
    first: date, last: date, holidays: Iterable[date], windows: tuple[int, ...]
) -> tuple[DayClass, ...]:
    """Classify every day from `first` to `last` inclusive, in date order."""
    holiday_set = frozenset(holidays)
    ordered = sorted(holiday_set)
    largest = max(windows, default=0)
    count = (last - first).days + 1
    days = (first + timedelta(days=offset) for offset in range(count))
    return tuple(_classify(day, holiday_set, ordered, largest) for day in days)


def _classify(
    day: date, holiday_set: frozenset[date], ordered: list[date], largest: int
) -> DayClass:
    if day in holiday_set:
        return DayClass(day, DayKind.HOLIDAY, 0)
    index = bisect_left(ordered, day)
    until_next = (ordered[index] - day).days if index < len(ordered) else None
    since_previous = (day - ordered[index - 1]).days if index > 0 else None
    if until_next is not None and (since_previous is None or until_next < since_previous):
        return _within(day, DayKind.BEFORE, until_next, largest)
    if since_previous is not None and (until_next is None or since_previous < until_next):
        return _within(day, DayKind.AFTER, since_previous, largest)
    if until_next is None:
        return DayClass(day, DayKind.BASELINE)
    return _within(day, DayKind.HOLIDAY, until_next, largest)  # tie takes the holiday class


def _within(day: date, kind: DayKind, distance: int, largest: int) -> DayClass:
    if distance > largest:
        return DayClass(day, DayKind.BASELINE)
    return DayClass(day, kind, distance)
