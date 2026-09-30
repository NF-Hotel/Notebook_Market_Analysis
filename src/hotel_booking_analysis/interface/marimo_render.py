"""Marimo rendering helpers shared by the notebook cells.

This module and the notebook are the only code that imports marimo. The helpers turn view
models into marimo output and hold no logic of their own.
"""

import html
from typing import Literal

import marimo as mo

from hotel_booking_analysis.interface.cancellation_view import SPLIT_LABELS as CANCELLATION_SPLITS
from hotel_booking_analysis.interface.cancellation_view import CancellationView
from hotel_booking_analysis.interface.figures import Row
from hotel_booking_analysis.interface.guest_mix_view import ATTRIBUTE_LABELS, GuestMixView
from hotel_booking_analysis.interface.holiday_view import HolidayView
from hotel_booking_analysis.interface.insight_view import (
    HYPOTHESIS_STATEMENT,
    STATE_AVAILABLE,
    STATE_NOT_APPLICABLE,
    STATE_SAVED_WITHOUT,
    InsightView,
)
from hotel_booking_analysis.interface.lead_time_view import SPLIT_LABELS as LEAD_TIME_SPLITS
from hotel_booking_analysis.interface.lead_time_view import LeadTimeView
from hotel_booking_analysis.interface.limitations import LimitationsNotice
from hotel_booking_analysis.interface.quality_view import DataQualityView
from hotel_booking_analysis.interface.room_value_view import ESTIMATE_HEADING, RoomValueView
from hotel_booking_analysis.interface.seasonality_view import (
    GRANULARITY_LABELS,
    SERIES_LABELS,
    SeasonalityView,
)


def render_limitations(notice: LimitationsNotice) -> mo.Html:
    """The limitations and association notice; every analysis view calls this."""
    return mo.callout(mo.md(notice.markdown()), kind="warn")


def render_quality(view: DataQualityView) -> mo.Html:
    """The data-quality section of one result."""
    parts: list[mo.Html] = [
        mo.md("## Data quality"),
        mo.md("\n".join(f"- {line}" for line in view.summary_lines())),
        mo.md("### Missing and invalid values per field"),
        mo.ui.table(view.field_table(), selection=None, page_size=30),
        mo.md("### Unavailable analyses"),
    ]
    if view.unavailable_analyses:
        parts.append(mo.ui.table(view.unavailable_table(), selection=None))
    else:
        parts.append(mo.md("All six analyses were available."))
    if view.notices:
        parts.append(mo.md("### Notices\n\n" + "\n".join(f"- {n}" for n in view.notices)))
    return mo.vstack(parts)


def _table(rows: list[Row]) -> mo.Html:
    if not rows:
        return mo.md("No rows to show.")
    return mo.ui.table(rows, selection=None, page_size=25)


def _bullets(lines: list[str]) -> mo.Html:
    return mo.md("\n".join(f"- {line}" for line in lines if line))


def _unavailable(title: str, message: str) -> mo.Html:
    return mo.vstack([mo.md(f"## {title}"), mo.callout(mo.md(message), kind="warn")])


def render_lead_time(view: LeadTimeView, split: str | None) -> mo.Html:
    """The lead-time section for the chosen split; `split` is a key of `SPLIT_LABELS`."""
    if view.message:
        return _unavailable("Lead time", view.message)
    chosen = split if split in view.splits else next(iter(view.splits), "")
    label = LEAD_TIME_SPLITS.get(chosen, chosen)
    return mo.vstack(
        [
            mo.md("## Lead time"),
            _bullets(view.statements()),
            mo.md(f"### Lead time by: {label}"),
            _table(view.summary_table(chosen)),
            mo.md(f"### Lead-time bands by: {label} (share of the group)"),
            _table(view.band_table(chosen)),
        ]
    )


def render_seasonality(
    view: SeasonalityView, series: str | None, granularity: str | None
) -> mo.Html:
    """The seasonality section for one series and granularity; partial periods are marked."""
    if view.message:
        return _unavailable("Seasonality", view.message)
    chosen = series if series in view.series else next(iter(view.series), "")
    grain = granularity if granularity in GRANULARITY_LABELS else "monthly"
    return mo.vstack(
        [
            mo.md("## Seasonality"),
            mo.md(view.note or ""),
            mo.md(f"### {SERIES_LABELS.get(chosen, chosen)}, {GRANULARITY_LABELS[grain].lower()}"),
            _bullets(view.statements(chosen)),
            _table(view.table(chosen, grain)),
        ]
    )


def render_holidays(view: HolidayView, window: int | None) -> mo.Html:
    """The holiday section: booking-date and arrival-date behaviour in separate parts."""
    if view.message:
        return _unavailable("Holidays", view.message)
    parts: list[mo.Html] = [
        mo.md("## Holidays"),
        mo.md(f"Calendar: {view.calendar or 'not stated'}"),
        mo.callout(mo.md(view.note or ""), kind="info") if view.note else mo.md(""),
    ]
    for section in view.sections.values():
        parts.extend(
            [
                mo.md(f"### {section.title}"),
                _bullets(section.coverage_lines()),
                _bullets(section.statements(window)),
                mo.md("#### Windows against the baseline on the same weekdays"),
                _table(section.comparison_table(window)),
                mo.md("#### By weekday"),
                _table(section.weekday_table(window)),
            ]
        )
    return mo.vstack(parts)


def render_cancellations(view: CancellationView, split: str | None) -> mo.Html:
    """The cancellation section for the chosen split."""
    if view.message:
        return _unavailable("Cancellations", view.message)
    chosen = split if split in view.splits else next(iter(view.splits), "")
    return mo.vstack(
        [
            mo.md("## Cancellations"),
            mo.md(view.note or ""),
            mo.md(f"### Cancellation share by: {CANCELLATION_SPLITS.get(chosen, chosen)}"),
            _bullets(view.statements(chosen)),
            _table(view.table(chosen)),
        ]
    )


def render_room_value(view: RoomValueView) -> mo.Html:
    """The room-value section; the estimate label is shown before any figure."""
    if view.message:
        return _unavailable("Room value", view.message)
    return mo.vstack(
        [
            mo.md("## Room value"),
            mo.callout(mo.md(f"**{ESTIMATE_HEADING}.** {view.estimate_label}"), kind="danger"),
            mo.md(f"### Estimated value by cancellation status ({ESTIMATE_HEADING.lower()})"),
            _bullets(view.statements()[1:]),
            _table(view.value_table()),
            mo.md("### Length of stay (nights)"),
            _bullets(view.count_lines()),
            _table(view.stay_length_table()),
        ]
    )


def render_guest_mix(view: GuestMixView, attribute: str | None) -> mo.Html:
    """The guest-mix section for the chosen attribute, with comparisons and omissions."""
    if view.message:
        return _unavailable("Guest mix", view.message)
    chosen = attribute if attribute in view.distributions else next(iter(view.distributions), "")
    return mo.vstack(
        [
            mo.md("## Guest mix"),
            mo.md(view.note or ""),
            mo.md(f"### Distribution of: {ATTRIBUTE_LABELS.get(chosen, chosen)}"),
            _bullets(view.statements(chosen)),
            _table(view.table(chosen)),
        ]
    )


def _plain(text: str) -> mo.Html:
    """`text` as a paragraph of plain text: every markup and marimo character is escaped."""
    return mo.Html(f'<p style="white-space: pre-wrap">{html.escape(text)}</p>')


def render_insight(view: InsightView) -> mo.Html:
    """The AI insight of one analysis, labeled, as plain text and next to its findings."""
    title = mo.md("### AI insight")
    if view.state != STATE_AVAILABLE:
        kind: Literal["info", "warn"] = (
            "info" if view.state in (STATE_SAVED_WITHOUT, STATE_NOT_APPLICABLE) else "warn"
        )
        return mo.vstack([title, mo.callout(_plain(" ".join(view.lines())), kind=kind)])
    return mo.vstack(
        [
            title,
            mo.callout(_plain(view.attribution()), kind="info"),
            mo.callout(_plain(HYPOTHESIS_STATEMENT), kind="warn"),
            mo.md("#### Executive summary (AI-generated)"),
            _plain(view.executive_summary or "not stated"),
            mo.md("#### Improvement suggestions (AI-generated hypotheses)"),
            _table(view.suggestion_table()),
        ]
    )
