"""Association-only wording for findings (ADR-0007 common rules, MIL-005 criterion 5).

Every finding sentence is built from these templates. `forbidden_words_in_findings` lets a test
prove that no produced text claims causation.
"""

from collections.abc import Mapping

from hotel_booking_analysis.domain.analysis import JsonValue

FORBIDDEN_WORDS: tuple[str, ...] = (
    "caused",
    "because",
    "due to",
    "effect of",
    "leads to",
    "drives",
)

LEAD_TIME_MEDIAN = (
    "The median lead time was {median} days across {count} records; "
    "this describes the observed distribution."
)
LEAD_TIME_DATE_DIFFERENCE = (
    "The supplied lead time differed from the days between booking date and arrival date "
    "in {differing} of {total} records."
)
HOLIDAY_HIGHER = (
    "Mean {measure} per day was higher {subject} ({window_mean}) than on baseline days of the "
    "same weekdays ({baseline_mean}); this is an observed association only."
)
HOLIDAY_LOWER = (
    "Mean {measure} per day was lower {subject} ({window_mean}) than on baseline days of the "
    "same weekdays ({baseline_mean}); this is an observed association only."
)
HOLIDAY_SAME = (
    "Mean {measure} per day was the same {subject} ({window_mean}) as on baseline days of the "
    "same weekdays ({baseline_mean}); this is an observed association only."
)
HOLIDAY_SMALL_SAMPLE = "No comparison is stated {subject}; a group is a small sample."
HOLIDAY_SUBJECT_WINDOW = "in the {window}-day window {side} holidays"
HOLIDAY_SUBJECT_HOLIDAY = "on holidays"
HOLIDAY_ASSOCIATION_NOTE = (
    "Holiday figures describe associations between dates and activity; other factors are "
    "not adjusted for. Holidays are taken only for the years present in the data, so days at "
    "the start or end of the date span may lie near a holiday of a neighbouring year that is "
    "not considered."
)

SEASONALITY_NOTE = (
    "Bookings are counted by booking date and arrivals by arrival date, as separate series. "
    "Figures describe observed counts per period; no seasons are defined, and a partial period "
    "is not fully covered by the observed dates."
)
SEASONALITY_SERIES_SUMMARY = (
    "{count} {measure} were observed from {first} to {last}, in {months} months and {weeks} "
    "ISO weeks; {partial} of these periods are partial. This describes the observed data only."
)
CANCELLATION_NOTE = (
    "Cancellation shares are observed associations between a booking attribute and "
    "cancellation status; other factors are not adjusted for, and nothing is predicted."
)
CANCELLATION_SPLIT_SUMMARY = (
    "Cancellation share by {split}: {canceled} of {total} bookings were cancelled overall; "
    "groups are shown with their counts and small groups are flagged."
)
ROOM_VALUE_LABEL = (
    "Estimate in the price units of the input: price per night times total nights. "
    "It is not realized revenue; payments, taxes, discounts and adjustments are not supplied."
)
ROOM_VALUE_GROUP_SUMMARY = (
    "Estimated value of {count} {status} bookings: total {total}, mean {mean} "
    "in the price units of the input (an estimate, not realized revenue)."
)
CANCELLATION_STATUS_UNKNOWN = "cancellation status unknown"
ROOM_VALUE_STATUS_UNKNOWN_NOTE = (
    "Cancellation status is not available, so one group labelled 'cancellation status unknown' "
    "is reported; cancelled and other bookings are never combined into one figure."
)
GUEST_MIX_NOTE = (
    "Distributions show how bookings are spread over each attribute. A comparison is stated "
    "only for groups that are not small samples; it describes an observed association only."
)
GUEST_MIX_COMPARISON_OMITTED = (
    "No comparison is stated for group '{group}'; it is a small sample of {count} records."
)


def forbidden_words_in(text: str) -> tuple[str, ...]:
    """Return the forbidden words found in a text, ignoring case."""
    lowered = text.lower()
    return tuple(word for word in FORBIDDEN_WORDS if word in lowered)


def finding_texts(value: JsonValue) -> list[str]:
    """Collect every string, keys and values, in a findings structure."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        texts: list[str] = []
        for key, item in value.items():
            texts.append(key)
            texts.extend(finding_texts(item))
        return texts
    if isinstance(value, list):
        return [text for item in value for text in finding_texts(item)]
    return []


def forbidden_words_in_findings(findings: Mapping[str, JsonValue]) -> tuple[str, ...]:
    """Return the forbidden words found anywhere in a findings structure."""
    found: list[str] = []
    for text in finding_texts(dict(findings)):
        found.extend(forbidden_words_in(text))
    return tuple(found)
