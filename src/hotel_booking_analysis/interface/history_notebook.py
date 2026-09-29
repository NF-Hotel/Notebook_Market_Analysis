"""Read-only marimo notebook: review retained analysis results (US-001.10, UC-002, ADR-0006).

Run with `python -m marimo run src/hotel_booking_analysis/interface/history_notebook.py` from
the directory that holds `hotel_analysis.toml` (or set HOTEL_ANALYSIS_CONFIG). The notebook only
reads the history. Cells stay thin: they call the pure view-model functions and render.

To add an analysis view, add a cell that depends on `selected`, builds its view model, and shows
`render_limitations(build_limitations(selected, "<analysis name>"))` with it.
"""

import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")

with app.setup:
    from types import ModuleType

    from hotel_booking_analysis.interface.cancellation_view import build_cancellation_view
    from hotel_booking_analysis.interface.guest_mix_view import build_guest_mix_view
    from hotel_booking_analysis.interface.history_view import HistoryView
    from hotel_booking_analysis.interface.holiday_view import build_holiday_view
    from hotel_booking_analysis.interface.json_access import Result
    from hotel_booking_analysis.interface.lead_time_view import build_lead_time_view
    from hotel_booking_analysis.interface.limitations import build_limitations
    from hotel_booking_analysis.interface.marimo_render import (
        render_cancellations,
        render_guest_mix,
        render_holidays,
        render_lead_time,
        render_limitations,
        render_quality,
        render_room_value,
        render_seasonality,
    )
    from hotel_booking_analysis.interface.quality_view import build_quality_view
    from hotel_booking_analysis.interface.room_value_view import build_room_value_view
    from hotel_booking_analysis.interface.seasonality_view import build_seasonality_view


@app.cell
def _() -> tuple[ModuleType]:
    import marimo as mo

    return (mo,)


@app.cell
def _(mo: ModuleType) -> tuple[HistoryView]:
    import os
    from pathlib import Path

    from hotel_booking_analysis.interface.history_source import load_history
    from hotel_booking_analysis.interface.history_view import build_history_view

    loaded = load_history(Path.cwd(), os.environ)
    history = build_history_view(loaded.readout)
    messages = [text for text in (loaded.error, history.empty_message) if text]
    if history.malformed_message:
        messages.append(history.malformed_message)
    mo.vstack(
        [
            mo.md("# Hotel booking analysis: saved results"),
            mo.md(f"History file: `{loaded.location}`"),
            *[mo.callout(mo.md(text), kind="warn") for text in messages],
        ]
    )
    return (history,)


@app.cell
def _(history: HistoryView, mo: ModuleType) -> tuple[marimo.ui.dropdown]:
    labels = history.labels()
    picker = mo.ui.dropdown(options=labels, value=labels[0] if labels else None, label="Result")
    table = mo.ui.table([row.as_table_row() for row in history.rows], selection=None)
    mo.vstack([table, picker] if history.rows else [])
    return (picker,)


@app.cell
def _(history: HistoryView, mo: ModuleType, picker: marimo.ui.dropdown) -> tuple[Result | None]:
    from hotel_booking_analysis.interface.history_view import version_notice

    selected: Result | None = None
    if picker.value is not None:
        selected = history.results[history.labels().index(picker.value)]
    notice = version_notice(selected) if selected is not None else None
    mo.callout(mo.md(notice or ""), kind="warn") if notice else None
    return (selected,)


@app.cell
def _(mo: ModuleType, selected: Result | None) -> None:
    mo.vstack(
        [
            render_quality(build_quality_view(selected)),
            render_limitations(build_limitations(selected)),
        ]
    ) if selected is not None else None


@app.cell
def _(mo: ModuleType, selected: Result | None) -> tuple[marimo.ui.dropdown]:
    _options = build_lead_time_view(selected).split_options() if selected is not None else {}
    lead_time_split = mo.ui.dropdown(
        options=_options, value=next(iter(_options), None), label="Lead time: split by"
    )
    mo.hstack([lead_time_split], justify="start") if _options else None
    return (lead_time_split,)


@app.cell
def _(lead_time_split: marimo.ui.dropdown, mo: ModuleType, selected: Result | None) -> None:
    mo.vstack(
        [
            render_lead_time(build_lead_time_view(selected), lead_time_split.value),
            render_limitations(build_limitations(selected, "lead_time")),
        ]
    ) if selected is not None else None


@app.cell
def _(mo: ModuleType, selected: Result | None) -> tuple[marimo.ui.dropdown, marimo.ui.dropdown]:
    _view = build_seasonality_view(selected) if selected is not None else None
    _series = _view.series_options() if _view else {}
    _grains = _view.granularity_options() if _view else {}
    seasonality_series = mo.ui.dropdown(
        options=_series, value=next(iter(_series), None), label="Seasonality: series"
    )
    seasonality_grain = mo.ui.dropdown(
        options=_grains, value=next(iter(_grains), None), label="Seasonality: granularity"
    )
    mo.hstack([seasonality_series, seasonality_grain], justify="start") if _series else None
    return seasonality_grain, seasonality_series


@app.cell
def _(
    mo: ModuleType,
    seasonality_grain: marimo.ui.dropdown,
    seasonality_series: marimo.ui.dropdown,
    selected: Result | None,
) -> None:
    mo.vstack(
        [
            render_seasonality(
                build_seasonality_view(selected),
                seasonality_series.value,
                seasonality_grain.value,
            ),
            render_limitations(build_limitations(selected, "seasonality")),
        ]
    ) if selected is not None else None


@app.cell
def _(mo: ModuleType, selected: Result | None) -> tuple[marimo.ui.dropdown]:
    _options = build_holiday_view(selected).window_options() if selected is not None else {}
    holiday_window = mo.ui.dropdown(
        options=_options, value=next(iter(_options), None), label="Holidays: window size"
    )
    mo.hstack([holiday_window], justify="start") if _options else None
    return (holiday_window,)


@app.cell
def _(holiday_window: marimo.ui.dropdown, mo: ModuleType, selected: Result | None) -> None:
    mo.vstack(
        [
            render_holidays(build_holiday_view(selected), holiday_window.value),
            render_limitations(build_limitations(selected, "holidays")),
        ]
    ) if selected is not None else None


@app.cell
def _(mo: ModuleType, selected: Result | None) -> tuple[marimo.ui.dropdown]:
    _options = build_cancellation_view(selected).split_options() if selected is not None else {}
    cancellation_split = mo.ui.dropdown(
        options=_options, value=next(iter(_options), None), label="Cancellations: split by"
    )
    mo.hstack([cancellation_split], justify="start") if _options else None
    return (cancellation_split,)


@app.cell
def _(cancellation_split: marimo.ui.dropdown, mo: ModuleType, selected: Result | None) -> None:
    mo.vstack(
        [
            render_cancellations(build_cancellation_view(selected), cancellation_split.value),
            render_limitations(build_limitations(selected, "cancellations")),
        ]
    ) if selected is not None else None


@app.cell
def _(mo: ModuleType, selected: Result | None) -> None:
    mo.vstack(
        [
            render_room_value(build_room_value_view(selected)),
            render_limitations(build_limitations(selected, "room_value")),
        ]
    ) if selected is not None else None


@app.cell
def _(mo: ModuleType, selected: Result | None) -> tuple[marimo.ui.dropdown]:
    _options = build_guest_mix_view(selected).attribute_options() if selected is not None else {}
    guest_mix_attribute = mo.ui.dropdown(
        options=_options, value=next(iter(_options), None), label="Guest mix: attribute"
    )
    mo.hstack([guest_mix_attribute], justify="start") if _options else None
    return (guest_mix_attribute,)


@app.cell
def _(guest_mix_attribute: marimo.ui.dropdown, mo: ModuleType, selected: Result | None) -> None:
    mo.vstack(
        [
            render_guest_mix(build_guest_mix_view(selected), guest_mix_attribute.value),
            render_limitations(build_limitations(selected, "guest_mix")),
        ]
    ) if selected is not None else None


if __name__ == "__main__":
    app.run()
