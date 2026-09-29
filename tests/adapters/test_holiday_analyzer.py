"""Tests for the Cambodian holiday analysis (US-001.03, ADR-0007, MIL-005 criteria 1-3, 5)."""

from datetime import date
from typing import Any

from hotel_booking_analysis.adapters.holiday_analyzer import HolidayAnalyzer
from hotel_booking_analysis.application.configuration import AppConfiguration
from hotel_booking_analysis.application.validate_bookings import validate_bookings
from hotel_booking_analysis.domain.analysis import Analysis, AnalysisName, Availability, Holiday
from hotel_booking_analysis.domain.booking import BookingRecord
from hotel_booking_analysis.domain.wording import forbidden_words_in_findings
from tests.support import make_submission

Findings = dict[str, Any]  # findings are JSON-shaped; tests index into them

HOLIDAY = date(2021, 6, 10)  # a Thursday


class FakeHolidayCalendar:
    """Holidays by year; a year that is not listed has no data. Records the years asked for."""

    def __init__(self, holidays: dict[int, tuple[date, ...]]) -> None:
        self.holidays = holidays
        self.requested: list[int] = []

    def holidays_in_year(self, year: int) -> tuple[Holiday, ...]:
        self.requested.append(year)
        return tuple(Holiday(day, "fake") for day in self.holidays.get(year, ()))


def _june(day: int) -> date:
    return date(2021, 6, day)


def _arrival(day: date, count: int = 1, canceled: int = 0) -> list[BookingRecord]:
    return [BookingRecord(arrival_date=day, is_canceled=index < canceled) for index in range(count)]


def _fixture() -> list[BookingRecord]:
    """Arrivals in June 2021: the 1st, 2nd, 9th x3 (one canceled), 10th, 16th x3 and 20th."""
    return [
        *_arrival(_june(1)),
        *_arrival(_june(2)),
        *_arrival(_june(9), 3, canceled=1),
        *_arrival(_june(10)),
        *_arrival(_june(16), 3),
        *_arrival(_june(20)),
    ]


def _analyze(
    records: list[BookingRecord],
    calendar: FakeHolidayCalendar | None = None,
    minimum: int = 1,
    windows: tuple[int, ...] = (1, 3),
) -> Analysis:
    validated = validate_bookings(make_submission(*records))
    configuration = AppConfiguration(min_group_size=minimum, holiday_windows_days=windows)
    fake = calendar or FakeHolidayCalendar({2021: (HOLIDAY,)})
    return HolidayAnalyzer(fake).analyze(validated, configuration)


def _as_findings(analysis: Analysis) -> Findings:
    findings: Findings = dict(analysis.findings)
    return findings


def _findings(records: list[BookingRecord], **kwargs: Any) -> Findings:  # noqa: ANN401
    findings: Findings = dict(_analyze(records, **kwargs).findings)
    return findings


def _window(side: Findings, kind: str, window: int) -> Findings:
    entries = [e for e in side["windows"] if e["day_kind"] == kind and e["window_days"] == window]
    assert len(entries) == 1
    entry: Findings = entries[0]
    return entry


def _figure(numerator: int, denominator: int, group: str, small: bool = False) -> Findings:
    return {
        "group": group,
        "numerator": numerator,
        "denominator": denominator,
        "small_sample": small,
    }


def test_analyze_is_the_holiday_analysis() -> None:
    analysis = _analyze(_fixture())

    assert HolidayAnalyzer(FakeHolidayCalendar({})).name is AnalysisName.HOLIDAYS
    assert analysis.availability is Availability.AVAILABLE


def test_analyze_states_date_span_years_and_calendar_of_the_arrival_side() -> None:
    side = _findings(_fixture())["arrival_date"]

    assert side["span"] == {"first": "2021-06-01", "last": "2021-06-20"}
    assert side["years_used"] == [2021]
    assert side["years_unavailable"] == []
    assert side["measure"] == "arrivals"
    assert side["records_used"] == 10


def test_analyze_requests_the_calendar_for_exactly_the_years_in_the_data() -> None:
    calendar = FakeHolidayCalendar({2021: (HOLIDAY,), 2023: (date(2023, 1, 1),)})
    records = [*_arrival(date(2021, 6, 1)), *_arrival(date(2023, 1, 5))]

    _analyze(records, calendar)

    assert sorted(set(calendar.requested)) == [2021, 2023]


def test_analyze_holiday_group_counts_events_over_days() -> None:
    side = _findings(_fixture())["arrival_date"]

    assert side["holiday_days"]["group"]["figure"] == _figure(1, 1, "holiday")
    assert side["holiday_days"]["group"]["mean_per_day"] == 1.0


def test_analyze_one_day_window_before_compares_with_baseline_on_the_same_weekday() -> None:
    entry = _window(_findings(_fixture())["arrival_date"], "before", 1)

    assert entry["group"]["figure"] == _figure(3, 1, "before_1_days")  # the 9th, a Wednesday
    assert entry["group"]["mean_per_day"] == 3.0
    # Baseline Wednesdays: the 2nd (1 arrival) and the 16th (3 arrivals).
    assert entry["baseline_same_weekdays"]["figure"] == _figure(4, 2, "baseline_same_weekdays")
    assert entry["baseline_same_weekdays"]["mean_per_day"] == 2.0
    assert entry["by_weekday"] == [
        {
            "weekday": "Wednesday",
            "group": {
                "figure": _figure(3, 1, "before_1_days"),
                "mean_per_day": 3.0,
                "cancellation_share": _figure(1, 3, "cancellation_share"),
            },
            "baseline": {
                "figure": _figure(4, 2, "baseline"),
                "mean_per_day": 2.0,
                "cancellation_share": _figure(0, 4, "cancellation_share"),
            },
        }
    ]
    assert entry["statement"].startswith("Mean arrivals per day was higher in the 1-day window")


def test_analyze_wider_window_matches_baseline_on_every_weekday_of_the_window() -> None:
    entry = _window(_findings(_fixture())["arrival_date"], "before", 3)

    # Window days: Monday 7th, Tuesday 8th, Wednesday 9th.
    assert entry["group"]["figure"] == _figure(3, 3, "before_3_days")
    # Baseline: Monday 14th (0), Tuesdays 1st (1) and 15th (0), Wednesdays 2nd (1), 16th (3).
    assert entry["baseline_same_weekdays"]["figure"] == _figure(5, 5, "baseline_same_weekdays")
    assert [d["weekday"] for d in entry["by_weekday"]] == ["Monday", "Tuesday", "Wednesday"]
    assert entry["statement"].startswith("Mean arrivals per day was the same in the 3-day window")


def test_analyze_after_window_and_lower_wording() -> None:
    records = [*_arrival(_june(4), 2), *_arrival(_june(11)), *_arrival(_june(18), 2)]

    side = _findings(records)["arrival_date"]
    entry = _window(side, "after", 1)

    # The 11th (Friday) has 1 arrival; baseline Fridays: the 4th (2) and the 18th (2).
    assert entry["group"]["figure"] == _figure(1, 1, "after_1_days")
    assert entry["baseline_same_weekdays"]["figure"] == _figure(4, 2, "baseline_same_weekdays")
    assert entry["statement"].startswith("Mean arrivals per day was lower in the 1-day window")


def test_analyze_reports_cancellation_share_of_the_arrival_side() -> None:
    side = _findings(_fixture())["arrival_date"]

    assert side["baseline"]["figure"] == _figure(6, 13, "baseline")
    assert side["baseline"]["cancellation_share"] == _figure(0, 6, "cancellation_share")
    window = _window(side, "before", 1)
    assert window["group"]["cancellation_share"] == _figure(1, 3, "cancellation_share")


def test_analyze_flags_small_samples_by_days_and_withholds_the_comparison() -> None:
    entry = _window(_findings(_fixture(), minimum=2)["arrival_date"], "before", 1)

    assert entry["group"]["figure"]["small_sample"] is True  # one day only
    assert entry["baseline_same_weekdays"]["figure"]["small_sample"] is False
    assert entry["statement"].startswith("No comparison is stated in the 1-day window")


def test_analyze_missing_booking_date_makes_only_the_booking_side_unavailable() -> None:
    findings = _findings(_fixture())

    assert findings["booking_date"]["status"] == "unavailable"
    assert "booking_date" in findings["booking_date"]["reason"]
    assert findings["arrival_date"]["status"] == "available"


def test_analyze_missing_arrival_date_makes_only_the_arrival_side_unavailable() -> None:
    records = [BookingRecord(booking_date=_june(d)) for d in (1, 9, 10)]

    analysis = _analyze(records)

    assert analysis.availability is Availability.AVAILABLE
    assert _as_findings(analysis)["arrival_date"]["status"] == "unavailable"
    assert _as_findings(analysis)["booking_date"]["status"] == "available"


def test_analyze_keeps_booking_and_arrival_behavior_separate() -> None:
    records = [
        BookingRecord(booking_date=_june(1), arrival_date=_june(10), is_canceled=False),
        BookingRecord(booking_date=_june(10), arrival_date=_june(15), is_canceled=True),
        BookingRecord(booking_date=_june(20), arrival_date=_june(20), is_canceled=False),
    ]

    findings = _findings(records)

    booking, arrival = findings["booking_date"], findings["arrival_date"]
    assert booking["measure"] == "bookings"
    assert arrival["measure"] == "arrivals"
    assert booking["span"]["first"] == "2021-06-01"
    assert arrival["span"]["first"] == "2021-06-10"
    assert "cancellation_share" not in booking["baseline"]
    assert "cancellation_share" in arrival["baseline"]
    assert booking["holiday_days"]["group"]["figure"] == _figure(
        1, 1, "holiday"
    )  # booked on the 10th


def test_analyze_year_without_holidays_is_unavailable_and_nothing_is_invented() -> None:
    calendar = FakeHolidayCalendar({2021: (HOLIDAY,)})
    records = [*_arrival(_june(9)), *_arrival(HOLIDAY), *_arrival(date(2022, 1, 2))]

    side = _findings(records, calendar=calendar)["arrival_date"]

    assert calendar.requested.count(2022) >= 1
    assert side["years_used"] == [2021]
    assert side["years_unavailable"] == [
        {
            "year": 2022,
            "status": "unavailable",
            "reason": "The holiday calendar has no data for 2022.",
        }
    ]
    assert side["records_used"] == 2
    assert side["records_left_out_unavailable_years"] == 1
    assert side["days_left_out_unavailable_years"] == 2  # 1 and 2 January 2022
    assert side["baseline"]["figure"]["numerator"] == 0  # nothing from 2022 leaks into a group


def test_analyze_every_year_without_holidays_makes_the_analysis_unavailable() -> None:
    analysis = _analyze(_fixture(), calendar=FakeHolidayCalendar({}))

    assert analysis.availability is Availability.UNAVAILABLE
    assert analysis.reason is not None
    assert _as_findings(analysis)["arrival_date"]["status"] == "unavailable"
    assert "2021" in _as_findings(analysis)["arrival_date"]["reason"]


def test_analyze_reports_every_configured_window_on_both_sides_sorted() -> None:
    findings = _findings(_fixture(), windows=(3, 1))

    side = findings["arrival_date"]
    assert findings["windows_days"] == [1, 3]
    assert [(e["day_kind"], e["window_days"]) for e in side["windows"]] == [
        ("before", 1),
        ("after", 1),
        ("before", 3),
        ("after", 3),
    ]


def test_analyze_default_windows_are_one_three_and_seven() -> None:
    validated = validate_bookings(make_submission(*_fixture()))
    calendar = FakeHolidayCalendar({2021: (HOLIDAY,)})

    analysis = HolidayAnalyzer(calendar).analyze(validated, AppConfiguration())

    assert _as_findings(analysis)["windows_days"] == [1, 3, 7]


def test_analyze_findings_state_association_only_and_use_no_forbidden_words() -> None:
    analysis = _analyze(_fixture())

    assert forbidden_words_in_findings(analysis.findings) == ()
    assert "association" in str(analysis.findings["note"])
