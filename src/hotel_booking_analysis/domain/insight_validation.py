"""The guardrail validator of AI answers (ADR-0010 "Required answer" and "Validator").

Deterministic rules, no model needed. The whole answer is rejected when any rule fails, and no
text of it is kept. Error details name the rule and never quote the answer.
"""

import json
import re
from collections.abc import Callable, Iterator
from decimal import Decimal
from typing import TypeGuard

from hotel_booking_analysis.domain.analysis import JsonValue
from hotel_booking_analysis.domain.errors import InsightRejectedError
from hotel_booking_analysis.domain.insight import (
    ExecutiveSummary,
    ImprovementSuggestion,
    InsightReason,
)
from hotel_booking_analysis.domain.insight_prompt import InsightPrompt
from hotel_booking_analysis.domain.wording import (
    HYPOTHESIS_WORDS,
    PROMISE_WORDS,
    SMALL_SAMPLE_PHRASE,
    forbidden_words_in,
)

MAX_SUMMARY_CHARS = 600
MAX_SUGGESTION_CHARS = 400
MAX_EVIDENCE_CHARS = 400
MIN_SUGGESTIONS = 1
MAX_SUGGESTIONS = 5
SAMPLE_SIZE_FIELDS = ("numerator", "denominator", "records_used")
"""Fields whose values are sample sizes, besides day counts and the record count."""

_FENCE = re.compile(r"\A```(?:json)?[ \t]*\r?\n(.*?)\r?\n?```\Z", re.DOTALL | re.IGNORECASE)
_NUMBER = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
_CURRENCY_SYMBOL = r"[$€£¥₹]"
_CURRENCY_CODE = r"(?:USD|EUR|GBP|KHR|DKK|SEK|NOK|CHF|JPY|CNY|THB|VND|AUD|CAD|INR)"
_PLAIN_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_PERCENT = re.compile(rf"({_NUMBER})\s*(?:%|percent)", re.IGNORECASE)
_AMOUNT_AFTER_SYMBOL = re.compile(rf"(?:{_CURRENCY_SYMBOL}|\b{_CURRENCY_CODE}\b)\s*({_NUMBER})")
_AMOUNT_BEFORE_SYMBOL = re.compile(rf"({_NUMBER})\s*(?:{_CURRENCY_SYMBOL}|\b{_CURRENCY_CODE}\b)")
_HYPOTHESIS = re.compile(
    r"\b(?:" + "|".join(re.escape(word) for word in HYPOTHESIS_WORDS) + r")\b", re.IGNORECASE
)


def _promise_pattern(phrase: str) -> str:
    *lead, last = phrase.split()
    stem = re.escape(last.removesuffix("e")) + r"\w*"
    return r"\s+".join([*(re.escape(word) for word in lead), stem])


_PROMISE = re.compile(
    r"\b(?:" + "|".join(_promise_pattern(phrase) for phrase in PROMISE_WORDS) + r")", re.IGNORECASE
)


def validate_answer(
    answer_text: str, prompt: InsightPrompt, min_group_size: int
) -> tuple[ExecutiveSummary, tuple[ImprovementSuggestion, ...]]:
    """Parse and check an answer; raises `InsightRejectedError` when any rule fails."""
    summary, suggestions = parse_structure(answer_text)
    check_guardrails(summary, suggestions, prompt, min_group_size)
    return summary, suggestions


def parse_structure(
    answer_text: str,
) -> tuple[ExecutiveSummary, tuple[ImprovementSuggestion, ...]]:
    """Rule 1: read the required structure; other keys are dropped. Raises `BAD_STRUCTURE`."""
    document = _load(answer_text)
    if not isinstance(document, dict):
        raise _bad_structure("The answer is not a JSON object.")
    summary = ExecutiveSummary(_text(document, "executive_summary", MAX_SUMMARY_CHARS))
    items = document.get("improvement_suggestions")
    if not isinstance(items, list) or not MIN_SUGGESTIONS <= len(items) <= MAX_SUGGESTIONS:
        raise _bad_structure(
            f"'improvement_suggestions' is not a list of {MIN_SUGGESTIONS} to "
            f"{MAX_SUGGESTIONS} items."
        )
    return summary, tuple(_suggestion(item) for item in items)


def check_guardrails(
    summary: ExecutiveSummary,
    suggestions: tuple[ImprovementSuggestion, ...],
    prompt: InsightPrompt,
    min_group_size: int,
) -> None:
    """Rules 2 to 7. Raises `GUARDRAIL_REJECTED` naming the first rule that fails."""
    data = json.loads(prompt.data_json)
    figures = _numbers_in(prompt.data_json)
    sizes = sample_sizes(data)
    texts = _texts(summary, suggestions)
    checks: tuple[Callable[[], str | None], ...] = (
        lambda: _causal_word(texts),
        lambda: _promise(texts),
        lambda: _invented_figure(texts, figures),
        lambda: _unknown_sample_size(suggestions, sizes),
        lambda: _small_sample_unmarked(suggestions, min_group_size),
        lambda: _no_hypothesis(suggestions),
    )
    for check in checks:
        problem = check()
        if problem is not None:
            raise InsightRejectedError(InsightReason.GUARDRAIL_REJECTED, problem)


def sample_sizes(data: JsonValue) -> frozenset[int]:
    """The sample sizes present in a data block (ADR-0010 rule 5).

    They are the values of the fields `numerator`, `denominator` and `records_used`, the day
    counts (fields ending in `_days`, except medians) in the findings, and the record count of
    the data-quality counts. Medians, means and rates are not sample sizes.
    """
    found: set[int] = set()
    if isinstance(data, dict):
        found.update(_collect_sizes(data.get("findings")))
        quality = data.get("data_quality")
        count = quality.get("record_count") if isinstance(quality, dict) else None
        if _is_int(count):
            found.add(count)
    return frozenset(found)


def _collect_sizes(value: JsonValue) -> Iterator[int]:
    if isinstance(value, dict):
        for key, item in value.items():
            if _is_sample_size_field(key):
                yield from _integers(item)
            else:
                yield from _collect_sizes(item)
    elif isinstance(value, list):
        for item in value:
            yield from _collect_sizes(item)


def _is_sample_size_field(name: str) -> bool:
    is_day_count = name.endswith("_days") and not name.startswith(("median_", "mean_"))
    return name in SAMPLE_SIZE_FIELDS or is_day_count


def _integers(value: JsonValue) -> Iterator[int]:
    if _is_int(value):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _integers(item)


def _is_int(value: object) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool)


def _load(answer_text: str) -> JsonValue:
    text = answer_text.strip()
    fenced = _FENCE.match(text)
    try:
        document: JsonValue = json.loads(fenced.group(1) if fenced else text)
    except ValueError as error:
        raise _bad_structure("The answer is not valid JSON.") from error
    return document


def _bad_structure(detail: str) -> InsightRejectedError:
    return InsightRejectedError(InsightReason.BAD_STRUCTURE, detail)


def _text(source: dict[str, JsonValue], key: str, limit: int) -> str:
    value = source.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _bad_structure(f"'{key}' is missing, not a string or empty.")
    if len(value.strip()) > limit:
        raise _bad_structure(f"'{key}' is longer than {limit} characters.")
    return value.strip()


def _suggestion(item: JsonValue) -> ImprovementSuggestion:
    if not isinstance(item, dict):
        raise _bad_structure("A suggestion is not an object.")
    size = item.get("sample_size")
    if not _is_int(size) or size < 1:
        raise _bad_structure("'sample_size' is not an integer of at least 1.")
    return ImprovementSuggestion(
        _text(item, "suggestion", MAX_SUGGESTION_CHARS),
        _text(item, "evidence", MAX_EVIDENCE_CHARS),
        size,
    )


def _texts(summary: ExecutiveSummary, suggestions: tuple[ImprovementSuggestion, ...]) -> list[str]:
    texts = [summary.text]
    for suggestion in suggestions:
        texts.extend((suggestion.suggestion, suggestion.evidence))
    return texts


def _causal_word(texts: list[str]) -> str | None:
    for text in texts:
        found = forbidden_words_in(text)
        if found:
            return f"Rule 2: a causal word is used: '{found[0]}'."
    return None


def _promise(texts: list[str]) -> str | None:
    for text in texts:
        if _PROMISE.search(text):
            return "Rule 3: the text promises or forecasts an outcome."
    return None


def _numbers_in(text: str) -> frozenset[Decimal]:
    return frozenset(Decimal(m) for m in _PLAIN_NUMBER.findall(text))


def _decimal(text: str) -> Decimal:
    return Decimal(text.replace(",", ""))


def _invented_figure(texts: list[str], figures: frozenset[Decimal]) -> str | None:
    for text in texts:
        for pattern in (_PERCENT, _AMOUNT_AFTER_SYMBOL, _AMOUNT_BEFORE_SYMBOL):
            for match in pattern.finditer(text):
                if _decimal(match.group(1)) not in figures:
                    return "Rule 4: a percentage or currency amount is not in the findings."
    return None


def _unknown_sample_size(
    suggestions: tuple[ImprovementSuggestion, ...], sizes: frozenset[int]
) -> str | None:
    if any(s.sample_size not in sizes for s in suggestions):
        return "Rule 5: a sample size is not a sample size present in the findings."
    return None


def _small_sample_unmarked(
    suggestions: tuple[ImprovementSuggestion, ...], min_group_size: int
) -> str | None:
    for s in suggestions:
        if s.sample_size < min_group_size and SMALL_SAMPLE_PHRASE not in s.evidence.lower():
            return f"Rule 6: a sample below {min_group_size} lacks '{SMALL_SAMPLE_PHRASE}'."
    return None


def _no_hypothesis(suggestions: tuple[ImprovementSuggestion, ...]) -> str | None:
    if any(not _HYPOTHESIS.search(s.suggestion) for s in suggestions):
        return "Rule 7: a suggestion has no hypothesis wording."
    return None
