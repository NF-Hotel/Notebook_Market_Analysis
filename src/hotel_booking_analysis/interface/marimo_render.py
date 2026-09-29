"""Marimo rendering helpers shared by the notebook cells.

This module and the notebook are the only code that imports marimo. The helpers turn view
models into marimo output and hold no logic of their own.
"""

import marimo as mo

from hotel_booking_analysis.interface.limitations import LimitationsNotice
from hotel_booking_analysis.interface.quality_view import DataQualityView


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
