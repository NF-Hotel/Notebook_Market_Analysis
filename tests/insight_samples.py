"""Realistic analyses for the insight tests, and the scanner of prompts for raw data (ADR-0010).

`sample_analyses` runs the six real analyzers on the development sample. The marker functions do
the same on a fixture whose booking ids, file name, hash and unknown field are markers, so that a
test can prove that none of them reaches a prompt.
"""

import functools
import json
import re
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from hotel_booking_analysis.adapters.cancellation_analyzer import CancellationAnalyzer
from hotel_booking_analysis.adapters.csv_reader import DevelopmentCsvReader
from hotel_booking_analysis.adapters.guest_mix_analyzer import GuestMixAnalyzer
from hotel_booking_analysis.adapters.holiday_analyzer import HolidayAnalyzer
from hotel_booking_analysis.adapters.khmer_holiday_calendar import KhmerHolidayCalendar
from hotel_booking_analysis.adapters.lead_time_analyzer import LeadTimeAnalyzer
from hotel_booking_analysis.adapters.room_value_analyzer import RoomValueAnalyzer
from hotel_booking_analysis.adapters.seasonality_analyzer import SeasonalityAnalyzer
from hotel_booking_analysis.application.configuration import AppConfiguration
from hotel_booking_analysis.application.placeholder_analyses import run_analyses
from hotel_booking_analysis.application.ports import Analyzer
from hotel_booking_analysis.application.validate_bookings import (
    ValidatedBookings,
    validate_bookings,
)
from hotel_booking_analysis.domain.analysis import Analysis, AnalysisName, JsonValue
from hotel_booking_analysis.domain.booking import (
    FIELD_NAMES,
    BookingRecord,
    BookingSubmission,
    InputSource,
)
from hotel_booking_analysis.domain.insight_prompt import InsightPrompt

SAMPLE_CSV = Path(__file__).resolve().parents[1] / "data" / "example" / "nf_hotel_bookings.csv"

MARKER_ID_PREFIX = "MARKER-BID-"
MARKER_REFERENCE = "C:\\marker_dir\\MARKER_FILE_bookings.csv"
MARKER_SHA = "deadbeef" * 8
MARKER_UNKNOWN_FIELD = "MARKER_UNKNOWN_FIELD"
MARKERS = (MARKER_ID_PREFIX, "marker_dir", "MARKER_FILE", "deadbeef", MARKER_UNKNOWN_FIELD)
LONG_LABEL = "L" * 200
"""A data-derived label that is far longer than the 60 characters that may be sent."""

_BOOKING_DATE_KEYS = ("booking_date", "arrival_date")
_BOOKING_DETAIL_KEYS = ("price_per_night", "adults", "children", "babies")
_FULL_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def _analyzers() -> tuple[Analyzer, ...]:
    return (
        LeadTimeAnalyzer(),
        HolidayAnalyzer(KhmerHolidayCalendar()),
        SeasonalityAnalyzer(),
        CancellationAnalyzer(),
        RoomValueAnalyzer(),
        GuestMixAnalyzer(),
    )


def analyses_of(validated: ValidatedBookings) -> dict[AnalysisName, Analysis]:
    """Run the six analyzers with the default configuration."""
    analyses, _ = run_analyses(validated, AppConfiguration(), _analyzers())
    return {analysis.name: analysis for analysis in analyses}


@functools.cache
def sample_validated() -> ValidatedBookings:
    return validate_bookings(DevelopmentCsvReader().read(SAMPLE_CSV))


@functools.cache
def sample_analyses() -> dict[AnalysisName, Analysis]:
    """The six analyses of the development sample (8538 records), all available."""
    return analyses_of(sample_validated())


def marker_record(number: int) -> BookingRecord:
    booking = date(2021, 1, 4) + timedelta(days=5 * number)
    return BookingRecord(
        booking_id=f"{MARKER_ID_PREFIX}{number:04d}",
        hotel="NF Hotel",
        is_canceled=number % 4 == 0,
        lead_time=10 + number,
        booking_date=booking,
        arrival_date=booking + timedelta(days=10 + number),
        stays_in_weekend_nights=number % 3,
        stays_in_week_nights=1 + number % 4,
        adults=1 + number % 3,
        children=number % 2,
        babies=0,
        meal="BB" if number % 2 else "HB",
        country=LONG_LABEL if number == 1 else ("PT" if number % 3 else "FR"),
        market_segment="Online",
        is_repeated_guest=number % 5 == 0,
        assigned_room_type="A" if number % 2 else "B",
        booking_changes=number % 2,
        deposit_type="No Deposit",
        customer_type="Transient",
        required_car_parking_spaces=0,
        total_of_special_requests=number % 3,
        price_per_night=Decimal("20") + number,
    )


def marker_validated() -> ValidatedBookings:
    """60 bookings whose identifiers, reference, hash and unknown field are markers."""
    submission = BookingSubmission(
        source=InputSource.SUPPLIED,
        reference=MARKER_REFERENCE,
        content_sha256=MARKER_SHA,
        records=tuple(marker_record(number) for number in range(60)),
        unknown_fields=(MARKER_UNKNOWN_FIELD,),
    )
    return validate_bookings(submission)


def marker_single_dates() -> tuple[str, str]:
    """The booking and arrival date of one booking that is neither first nor last."""
    record = marker_record(30)
    assert record.booking_date is not None
    assert record.arrival_date is not None
    return record.booking_date.isoformat(), record.arrival_date.isoformat()


def coverage_dates(validated: ValidatedBookings) -> frozenset[str]:
    """The data coverage dates (earliest and latest), which may be sent (ADR-0010)."""
    summary = validated.summary
    dates = (
        summary.earliest_booking_date,
        summary.latest_booking_date,
        summary.earliest_arrival_date,
        summary.latest_arrival_date,
    )
    return frozenset(d.isoformat() for d in dates if d is not None)


def find_leaks(
    prompt: InsightPrompt, markers: tuple[str, ...], allowed_dates: frozenset[str]
) -> list[str]:
    """Every raw-data problem in a prompt; an empty list means the prompt is clean.

    Looks for the markers in the whole prompt text, and in the data block for a full date that is
    not a coverage date, a booking-level object (a booking id, or a booking or arrival date next
    to a price or guest count, or an object shaped like a raw record) and a group labelled by a
    single date. The per-field counts of the data quality are objects of integers under the
    field names, not records, so they are not flagged.
    """
    text = prompt.instruction + prompt.data_json
    leaks = [f"marker {marker}" for marker in markers if marker in text]
    leaks.extend(
        f"date {found}"
        for found in _FULL_DATE.findall(prompt.data_json)
        if found not in allowed_dates
    )
    leaks.extend(_structure_leaks(json.loads(prompt.data_json)))
    return leaks


def _structure_leaks(node: JsonValue) -> list[str]:
    if isinstance(node, list):
        return [leak for child in node for leak in _structure_leaks(child)]
    if not isinstance(node, dict):
        return []
    leaks = _booking_level_leaks(node)
    for child in node.values():
        leaks.extend(_structure_leaks(child))
    return leaks


def _booking_level_leaks(node: dict[str, JsonValue]) -> list[str]:
    leaks: list[str] = []
    if isinstance(node.get("booking_id"), str):
        leaks.append("object with a booking id")
    has_date = any(isinstance(node.get(key), str) for key in _BOOKING_DATE_KEYS)
    if has_date and any(key in node for key in _BOOKING_DETAIL_KEYS):
        leaks.append("object with a booking date next to a price or guest count")
    group = node.get("group")
    if isinstance(group, str) and _FULL_DATE.fullmatch(group):
        leaks.append("group labelled by a single date")
    scalar_fields = [
        k for k, v in node.items() if k in FIELD_NAMES and not isinstance(v, dict | list | int)
    ]
    if len(scalar_fields) >= 3:
        leaks.append("object shaped like a raw booking record")
    return leaks
