"""Every analysis view states sample sizes and limitations and uses association wording.

Covers MIL-006 criteria 3 and 4 at the view-model level (the notebook smoke tests cover the
rendered page): each view's text has sample sizes, the shared notice has the association
statement, and no view or notice text uses a forbidden causal word.
"""

from collections.abc import Callable

import pytest

from hotel_booking_analysis.domain.wording import forbidden_words_in
from hotel_booking_analysis.interface.cancellation_view import build_cancellation_view
from hotel_booking_analysis.interface.figures import Row
from hotel_booking_analysis.interface.guest_mix_view import build_guest_mix_view
from hotel_booking_analysis.interface.holiday_view import build_holiday_view
from hotel_booking_analysis.interface.lead_time_view import build_lead_time_view
from hotel_booking_analysis.interface.limitations import (
    ASSOCIATION_STATEMENT,
    ESTIMATE_LABEL,
    SAMPLE_SIZE_STATEMENT,
    build_limitations,
)
from hotel_booking_analysis.interface.room_value_view import build_room_value_view
from hotel_booking_analysis.interface.seasonality_view import build_seasonality_view
from tests.interface.builders import Result, run_analysis

COUNT_COLUMNS = {"records", "bookings", "cancelled"}


def _cells(rows: list[Row]) -> list[str]:
    return [str(value) for row in rows for value in [*row.keys(), *row.values()]]


def _lead_time(result: Result) -> tuple[list[str], list[list[Row]]]:
    view = build_lead_time_view(result)
    keys = list(view.split_options().values())
    tables = [view.summary_table(k) for k in keys] + [view.band_table(k) for k in keys]
    return view.statements(), tables


def _seasonality(result: Result) -> tuple[list[str], list[list[Row]]]:
    view = build_seasonality_view(result)
    keys = list(view.series_options().values())
    grains = list(view.granularity_options().values())
    lines = [line for k in keys for line in view.statements(k)]
    return lines, [view.table(k, g) for k in keys for g in grains]


def _holidays(result: Result) -> tuple[list[str], list[list[Row]]]:
    view = build_holiday_view(result)
    windows = [*view.windows_days, None]
    lines = [view.note or ""]
    tables: list[list[Row]] = []
    for section in view.sections.values():
        lines.extend(section.coverage_lines())
        for window in windows:
            lines.extend(section.statements(window))
            tables.extend([section.comparison_table(window), section.weekday_table(window)])
    return lines, tables


def _cancellations(result: Result) -> tuple[list[str], list[list[Row]]]:
    view = build_cancellation_view(result)
    keys = list(view.split_options().values())
    return [view.note or "", *[t for k in keys for t in view.statements(k)]], [
        view.table(k) for k in keys
    ]


def _room_value(result: Result) -> tuple[list[str], list[list[Row]]]:
    view = build_room_value_view(result)
    return [*view.statements(), *view.count_lines()], [view.value_table(), view.stay_length_table()]


def _guest_mix(result: Result) -> tuple[list[str], list[list[Row]]]:
    view = build_guest_mix_view(result)
    keys = list(view.attribute_options().values())
    return [view.note or "", *[t for k in keys for t in view.statements(k)]], [
        view.table(k) for k in keys
    ]


VIEWS: dict[str, Callable[[Result], tuple[list[str], list[list[Row]]]]] = {
    "lead_time": _lead_time,
    "seasonality": _seasonality,
    "holidays": _holidays,
    "cancellations": _cancellations,
    "room_value": _room_value,
    "guest_mix": _guest_mix,
}


@pytest.fixture(scope="module")
def small_result(tmp_path_factory: pytest.TempPathFactory) -> Result:
    return run_analysis(tmp_path_factory.mktemp("small"))


@pytest.fixture(params=["development", "small"])
def result(request: pytest.FixtureRequest) -> Result:
    found: Result = request.getfixturevalue(f"{request.param}_result")
    return found


@pytest.mark.parametrize("analysis", list(VIEWS))
def test_view_shows_sample_sizes_in_every_table_with_rows(result: Result, analysis: str) -> None:
    _, tables = VIEWS[analysis](result)

    filled = [rows for rows in tables if rows]
    assert filled
    for rows in filled:
        assert COUNT_COLUMNS & set(rows[0]), (analysis, list(rows[0]))


@pytest.mark.parametrize("analysis", list(VIEWS))
def test_notice_of_each_view_states_sample_sizes_and_the_association(
    result: Result, analysis: str
) -> None:
    lines = build_limitations(result, analysis).lines()

    assert SAMPLE_SIZE_STATEMENT in lines
    assert ASSOCIATION_STATEMENT in lines
    assert "not causes" in ASSOCIATION_STATEMENT


@pytest.mark.parametrize("analysis", list(VIEWS))
def test_view_and_notice_text_use_no_causal_words(result: Result, analysis: str) -> None:
    lines, tables = VIEWS[analysis](result)
    notice = build_limitations(result, analysis).lines()

    text = "\n".join([*lines, *notice, *[c for rows in tables for c in _cells(rows)]])

    assert forbidden_words_in(text) == ()


def test_room_value_notice_and_view_label_the_figure_an_estimate(result: Result) -> None:
    notice = build_limitations(result, "room_value")
    lines, _ = _room_value(result)

    assert notice.estimate_label == ESTIMATE_LABEL
    assert any("not realized revenue" in line for line in lines)
    assert build_limitations(result, "lead_time").estimate_label is None


def test_views_render_without_error_for_an_empty_result() -> None:
    for build in VIEWS.values():
        lines, tables = build({})
        assert forbidden_words_in("\n".join(lines)) == ()
        assert not any(tables)


def test_render_helpers_produce_the_titles_and_estimate_label(development_result: Result) -> None:
    from hotel_booking_analysis.interface.marimo_render import (
        render_cancellations,
        render_guest_mix,
        render_holidays,
        render_lead_time,
        render_room_value,
        render_seasonality,
    )

    rendered = {
        "Lead time": render_lead_time(build_lead_time_view(development_result), None),
        "Seasonality": render_seasonality(build_seasonality_view(development_result), None, None),
        "Holidays": render_holidays(build_holiday_view(development_result), 3),
        "Cancellations": render_cancellations(build_cancellation_view(development_result), None),
        "Room value": render_room_value(build_room_value_view(development_result)),
        "Guest mix": render_guest_mix(build_guest_mix_view(development_result), None),
    }

    for title, output in rendered.items():
        assert title in output.text
    assert "Estimate, not realized revenue" in rendered["Room value"].text
    assert "Booking-date behaviour" in rendered["Holidays"].text
    assert "Arrival-date behaviour" in rendered["Holidays"].text
