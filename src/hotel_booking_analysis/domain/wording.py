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
