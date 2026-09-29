"""The one shared limitations and association notice of every analysis view (ADR-0007).

`build_limitations` derives the data limitations of one analysis (or of the whole result) from
its stored findings: small samples, partial periods and unavailable parts. The association
statement is always present, and room value carries the estimate label. Pure text, no marimo.
"""

from dataclasses import dataclass, field

from hotel_booking_analysis.domain.analysis import AnalysisName, JsonValue
from hotel_booking_analysis.domain.wording import ROOM_VALUE_LABEL
from hotel_booking_analysis.interface.json_access import Result, as_mapping, as_text

ASSOCIATION_STATEMENT = (
    "Findings describe associations observed in the supplied records; they are not causes, "
    "and other factors are not adjusted for."
)
SAMPLE_SIZE_STATEMENT = (
    "Every figure is shown with the number of records it rests on; groups below the "
    "minimum group size are small samples."
)
ESTIMATE_LABEL = "Estimate, not realized revenue. " + ROOM_VALUE_LABEL
NO_FLAGS_STATEMENT = "No small samples, partial periods or unavailable parts were flagged."


@dataclass(frozen=True, slots=True)
class LimitationsNotice:
    """The visible statement: `analysis` is None for a notice about the whole result."""

    analysis: str | None
    data_limitations: tuple[str, ...]
    association_statement: str
    estimate_label: str | None

    def lines(self) -> list[str]:
        """Every statement in display order."""
        lines = [*self.data_limitations, self.association_statement]
        if self.estimate_label is not None:
            lines.append(self.estimate_label)
        return lines

    def markdown(self) -> str:
        """The notice as a heading and a bullet list."""
        bullets = "\n".join(f"- {line}" for line in self.lines())
        return f"**Limitations of these figures**\n\n{bullets}"


@dataclass(slots=True)
class _Flags:
    small_samples: int = 0
    partial_periods: int = 0
    unavailable: list[str] = field(default_factory=list)

    def add_unavailable(self, text: str) -> None:
        if text not in self.unavailable:
            self.unavailable.append(text)


def _scan(value: JsonValue, path: str, flags: _Flags) -> None:
    if isinstance(value, list):
        for item in value:
            _scan(item, path, flags)
    elif isinstance(value, dict):
        _scan_mapping(value, path, flags)


def _scan_mapping(value: dict[str, JsonValue], path: str, flags: _Flags) -> None:
    if value.get("small_sample") is True or value.get("status") == "omitted_small_sample":
        flags.small_samples += 1
    if value.get("partial_period") is True:
        flags.partial_periods += 1
    if value.get("status") == "unavailable":
        reason = as_text(value.get("reason")) or "no reason was recorded"
        flags.add_unavailable(f"{path or 'analysis'}: {reason}")
        return
    for key, item in value.items():
        _scan(item, f"{path} / {key}" if path else key, flags)


def _selected(result: Result, analysis: str | None) -> dict[str, JsonValue]:
    analyses = as_mapping(result.get("analyses"))
    if analysis is None:
        return dict(analyses)
    return {analysis: analyses[analysis]} if analysis in analyses else {}


def build_limitations(result: Result, analysis: str | None = None) -> LimitationsNotice:
    """Build the notice for one analysis by name, or for the whole result if None."""
    flags = _Flags()
    for name, entry in _selected(result, analysis).items():
        _scan(entry, name if analysis is None else "", flags)
    limitations = [SAMPLE_SIZE_STATEMENT]
    if flags.small_samples:
        limitations.append(
            f"{flags.small_samples} group(s) are small samples; they are flagged and not "
            "compared with other groups."
        )
    if flags.partial_periods:
        limitations.append(
            f"{flags.partial_periods} period(s) are partial: the observed dates do not cover "
            "them fully, so they are not comparable with complete periods."
        )
    limitations.extend(f"Not available - {text}" for text in flags.unavailable)
    if not (flags.small_samples or flags.partial_periods or flags.unavailable):
        limitations.append(NO_FLAGS_STATEMENT)
    has_value = AnalysisName.ROOM_VALUE in as_mapping(result.get("analyses"))
    is_value = analysis == AnalysisName.ROOM_VALUE or (analysis is None and has_value)
    return LimitationsNotice(
        analysis=analysis,
        data_limitations=tuple(limitations),
        association_statement=ASSOCIATION_STATEMENT,
        estimate_label=ESTIMATE_LABEL if is_value else None,
    )
