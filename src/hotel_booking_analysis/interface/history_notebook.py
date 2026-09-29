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

    from hotel_booking_analysis.interface.history_view import HistoryView
    from hotel_booking_analysis.interface.json_access import Result


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
    from hotel_booking_analysis.interface.limitations import build_limitations
    from hotel_booking_analysis.interface.marimo_render import (
        render_limitations,
        render_quality,
    )
    from hotel_booking_analysis.interface.quality_view import build_quality_view

    mo.vstack(
        [
            render_quality(build_quality_view(selected)),
            render_limitations(build_limitations(selected)),
        ]
    ) if selected is not None else None


if __name__ == "__main__":
    app.run()
