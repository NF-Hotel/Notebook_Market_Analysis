"""Data-quality summary and analysis availability rules (ADR-0001, US-001.01, UC-001 step 3)."""

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from hotel_booking_analysis.domain.analysis import (
    AnalysisAvailability,
    AnalysisName,
    Availability,
)
from hotel_booking_analysis.domain.booking import FIELD_NAMES, BookingRecord


@dataclass(frozen=True, slots=True)
class DataQualitySummary:
    """What is known about the completeness and validity of a submission (DM-001, ADR-0002).

    `duplicate_booking_id_count` is the number of surplus records that repeat an earlier
    booking ID; all copies stay in the data. `missing_counts` and `invalid_counts` hold one
    entry for every contract field, zero included.
    """

    record_count: int
    earliest_booking_date: date | None
    latest_booking_date: date | None
    earliest_arrival_date: date | None
    latest_arrival_date: date | None
    duplicate_booking_id_count: int
    missing_counts: Mapping[str, int]
    invalid_counts: Mapping[str, int]
    zero_price_count: int
    unknown_fields: tuple[str, ...]

    @property
    def has_invalid_values(self) -> bool:
        return any(self.invalid_counts.values())


@dataclass(frozen=True, slots=True)
class AnalysisRequirement:
    """Fields an analysis needs (ADR-0001 field matrix).

    All of `all_of` are required. If `any_of` is not empty, at least one of them is also
    required.
    """

    analysis: AnalysisName
    all_of: tuple[str, ...] = ()
    any_of: tuple[str, ...] = ()


ANALYSIS_REQUIREMENTS: tuple[AnalysisRequirement, ...] = (
    AnalysisRequirement(AnalysisName.LEAD_TIME, all_of=("lead_time",)),
    AnalysisRequirement(AnalysisName.HOLIDAYS, any_of=("booking_date", "arrival_date")),
    AnalysisRequirement(AnalysisName.SEASONALITY, any_of=("booking_date", "arrival_date")),
    AnalysisRequirement(AnalysisName.CANCELLATIONS, all_of=("is_canceled",)),
    AnalysisRequirement(
        AnalysisName.ROOM_VALUE,
        all_of=("stays_in_weekend_nights", "stays_in_week_nights"),
    ),
    AnalysisRequirement(
        AnalysisName.GUEST_MIX,
        any_of=(
            "adults",
            "children",
            "babies",
            "country",
            "meal",
            "assigned_room_type",
            "is_repeated_guest",
            "required_car_parking_spaces",
            "total_of_special_requests",
        ),
    ),
)


def records_with_valid(
    records: Iterable[BookingRecord], *field_names: str
) -> tuple[BookingRecord, ...]:
    """Return the records that hold a valid value in every named field (ADR-0001, ADR-0007)."""
    return tuple(record for record in records if record.has_valid(*field_names))


def summarize(
    records: tuple[BookingRecord, ...], unknown_fields: tuple[str, ...] = ()
) -> DataQualitySummary:
    """Build the data-quality summary of a set of records (US-001.01)."""
    booking_dates = [d for r in records if (d := r.booking_date) is not None]
    arrival_dates = [d for r in records if (d := r.arrival_date) is not None]
    return DataQualitySummary(
        record_count=len(records),
        earliest_booking_date=min(booking_dates, default=None),
        latest_booking_date=max(booking_dates, default=None),
        earliest_arrival_date=min(arrival_dates, default=None),
        latest_arrival_date=max(arrival_dates, default=None),
        duplicate_booking_id_count=_duplicate_id_count(records),
        missing_counts=_count_per_field(r.missing_fields for r in records),
        invalid_counts=_count_per_field(r.invalid_fields for r in records),
        zero_price_count=sum(1 for r in records if r.price_per_night == Decimal(0)),
        unknown_fields=tuple(sorted(unknown_fields)),
    )


def usable_fields(records: tuple[BookingRecord, ...]) -> frozenset[str]:
    """Return the fields for which at least one record holds a valid value."""
    return frozenset(
        name for name in FIELD_NAMES if any(r.value(name) is not None for r in records)
    )


def assess_availability(
    records: tuple[BookingRecord, ...],
) -> tuple[AnalysisAvailability, ...]:
    """Mark each analysis available or unavailable, naming the missing field (ADR-0001)."""
    usable = usable_fields(records)
    absent_everywhere = _fields_absent_from_all(records)
    return tuple(_assess(req, usable, absent_everywhere) for req in ANALYSIS_REQUIREMENTS)


def _assess(
    requirement: AnalysisRequirement, usable: frozenset[str], absent_everywhere: frozenset[str]
) -> AnalysisAvailability:
    missing_all_of = tuple(f for f in requirement.all_of if f not in usable)
    missing_any_of = tuple(f for f in requirement.any_of if f not in usable)
    any_of_unmet = bool(requirement.any_of) and len(missing_any_of) == len(requirement.any_of)
    missing = (*missing_all_of, *missing_any_of)
    if not missing_all_of and not any_of_unmet:
        return AnalysisAvailability(
            requirement.analysis, Availability.AVAILABLE, missing_fields=missing_any_of
        )
    named = missing_all_of if missing_all_of else missing_any_of
    reason = _reason(named, any_of_only=not missing_all_of, absent=absent_everywhere)
    return AnalysisAvailability(
        requirement.analysis, Availability.UNAVAILABLE, reason=reason, missing_fields=missing
    )


def _reason(names: tuple[str, ...], any_of_only: bool, absent: frozenset[str]) -> str:
    quoted = ", ".join(f"'{name}'" for name in names)
    state = "missing" if all(name in absent for name in names) else "missing or invalid"
    if any_of_only:
        return f"At least one of these fields is required and all are {state}: {quoted}"
    return f"Required field is {state}: {quoted}"


def _fields_absent_from_all(records: tuple[BookingRecord, ...]) -> frozenset[str]:
    """Fields that are missing (not merely invalid) in every record."""
    return frozenset(name for name in FIELD_NAMES if all(name in r.missing_fields for r in records))


def _duplicate_id_count(records: tuple[BookingRecord, ...]) -> int:
    ids = [r.booking_id for r in records if r.booking_id is not None]
    return len(ids) - len(set(ids))


def _count_per_field(field_sets: Iterable[frozenset[str]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for names in field_sets:
        counter.update(names)
    return {name: counter.get(name, 0) for name in FIELD_NAMES}
