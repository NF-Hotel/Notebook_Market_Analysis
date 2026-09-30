"""Tests for the holiday day classification (ADR-0007 Cambodian holidays, US-001.03)."""

from datetime import date

from hotel_booking_analysis.domain.holiday_days import DayClass, DayKind, classify_days


def _june(day: int) -> date:
    return date(2021, 6, day)


def _is(day_class: DayClass, kind: DayKind, distance: int) -> bool:
    return day_class.kind is kind and day_class.distance == distance


def _by_day(
    first: date, last: date, holidays: list[date], windows: tuple[int, ...]
) -> dict[date, DayClass]:
    return {c.day: c for c in classify_days(first, last, holidays, windows)}


def test_classify_days_single_holiday_windows_and_baseline() -> None:
    classes = _by_day(_june(1), _june(20), [_june(10)], (1, 3))

    assert classes[_june(10)].kind is DayKind.HOLIDAY
    assert _is(classes[_june(9)], DayKind.BEFORE, 1)
    assert _is(classes[_june(7)], DayKind.BEFORE, 3)
    assert _is(classes[_june(11)], DayKind.AFTER, 1)
    assert _is(classes[_june(13)], DayKind.AFTER, 3)
    assert classes[_june(6)].kind is DayKind.BASELINE
    assert classes[_june(14)].kind is DayKind.BASELINE


def test_classify_days_covers_every_day_of_the_span_in_order() -> None:
    result = classify_days(_june(1), _june(20), [_june(10)], (1,))

    assert [c.day for c in result] == [_june(d) for d in range(1, 21)]


def test_classify_days_day_between_windows_is_not_baseline() -> None:
    classes = _by_day(_june(1), _june(20), [_june(10)], (1, 3))

    assert classes[_june(8)].kind is DayKind.BEFORE
    assert classes[_june(8)].distance == 2


def test_classify_days_overlapping_windows_take_the_closest_holiday() -> None:
    classes = _by_day(_june(1), _june(20), [_june(10), _june(14)], (1, 3))

    assert _is(classes[_june(11)], DayKind.AFTER, 1)  # 1 after the 10th, 3 before the 14th
    assert _is(classes[_june(13)], DayKind.BEFORE, 1)  # 1 before the 14th, 3 after the 10th


def test_classify_days_tie_between_two_holidays_takes_the_holiday_class() -> None:
    classes = _by_day(_june(1), _june(20), [_june(10), _june(14)], (1, 3))

    assert classes[_june(12)].kind is DayKind.HOLIDAY
    assert classes[_june(12)].distance == 2


def test_classify_days_tie_beyond_the_largest_window_is_baseline() -> None:
    classes = _by_day(_june(1), _june(30), [_june(5), _june(15)], (1, 3))

    assert classes[_june(10)].kind is DayKind.BASELINE


def test_classify_days_baseline_is_outside_the_largest_window_of_every_holiday() -> None:
    classes = _by_day(_june(1), _june(20), [_june(10), _june(14)], (1, 3))

    baseline = [c.day for c in classes.values() if c.kind is DayKind.BASELINE]

    assert baseline == [_june(d) for d in (1, 2, 3, 4, 5, 6, 18, 19, 20)]


def test_classify_days_without_holidays_is_all_baseline() -> None:
    classes = classify_days(_june(1), _june(3), [], (1, 3))

    assert {c.kind for c in classes} == {DayKind.BASELINE}
