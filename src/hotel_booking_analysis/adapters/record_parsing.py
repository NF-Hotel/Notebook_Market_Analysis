"""Turn raw JSON-shaped records into booking records (ADR-0001 value rules, US-001.01).

A null, absent or blank value is missing; a wrongly typed value, an unparseable date or a
negative count or price is invalid. Both leave the field empty on the record and are named
in `missing_fields` or `invalid_fields`.
"""

import re
from collections.abc import Iterable, Mapping
from datetime import date
from decimal import Decimal

from hotel_booking_analysis.domain.booking import FIELD_NAMES, BookingRecord

_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


class _FieldReader:
    """Reads typed fields from one raw record and remembers which were missing or invalid."""

    def __init__(self, raw: Mapping[str, object]) -> None:
        self._raw = raw
        self.missing: set[str] = set()
        self.invalid: set[str] = set()

    def _take(self, name: str) -> object | None:
        value = self._raw.get(name)
        if value is None or (isinstance(value, str) and not value.strip()):
            self.missing.add(name)
            return None
        return value

    def _reject(self, name: str) -> None:
        self.invalid.add(name)

    def text(self, name: str) -> str | None:
        value = self._take(name)
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip()
        self._reject(name)
        return None

    def identifier(self, name: str) -> str | None:
        """Booking ID or agent: a string or an integer, kept as text."""
        value = self._take(name)
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, int) and not isinstance(value, bool):
            return str(value)
        self._reject(name)
        return None

    def integer(self, name: str) -> int | None:
        value = self._take(name)
        if value is None:
            return None
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            return value
        self._reject(name)
        return None

    def boolean(self, name: str) -> bool | None:
        """Accepts true, false, 1 or 0."""
        value = self._take(name)
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, int) and value in (0, 1):
            return value == 1
        self._reject(name)
        return None

    def iso_date(self, name: str) -> date | None:
        """Accepts an ISO 8601 calendar date `YYYY-MM-DD`."""
        value = self._take(name)
        if value is None:
            return None
        if isinstance(value, str) and _ISO_DATE.fullmatch(value.strip()):
            try:
                return date.fromisoformat(value.strip())
            except ValueError:
                pass
        self._reject(name)
        return None

    def decimal(self, name: str) -> Decimal | None:
        """Accepts a JSON number; floats arrive as exact `Decimal` from the JSON parser."""
        value = self._take(name)
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int | Decimal):
            self._reject(name)
            return None
        number = Decimal(value)
        if not number.is_finite() or number < 0:
            self._reject(name)
            return None
        return number


def parse_record(raw: Mapping[str, object]) -> BookingRecord:
    """Parse one raw record; never raises for bad values (ADR-0001)."""
    r = _FieldReader(raw)
    return BookingRecord(
        booking_id=r.identifier("booking_id"),
        hotel=r.text("hotel"),
        is_canceled=r.boolean("is_canceled"),
        lead_time=r.integer("lead_time"),
        booking_date=r.iso_date("booking_date"),
        arrival_date=r.iso_date("arrival_date"),
        stays_in_weekend_nights=r.integer("stays_in_weekend_nights"),
        stays_in_week_nights=r.integer("stays_in_week_nights"),
        adults=r.integer("adults"),
        children=r.integer("children"),
        babies=r.integer("babies"),
        meal=r.text("meal"),
        country=r.text("country"),
        market_segment=r.text("market_segment"),
        is_repeated_guest=r.boolean("is_repeated_guest"),
        previous_cancellations=r.integer("previous_cancellations"),
        assigned_room_type=r.text("assigned_room_type"),
        booking_changes=r.integer("booking_changes"),
        deposit_type=r.text("deposit_type"),
        agent=r.identifier("agent"),
        customer_type=r.text("customer_type"),
        required_car_parking_spaces=r.integer("required_car_parking_spaces"),
        total_of_special_requests=r.integer("total_of_special_requests"),
        price_per_night=r.decimal("price_per_night"),
        missing_fields=frozenset(r.missing),
        invalid_fields=frozenset(r.invalid),
    )


def unknown_field_names(raws: Iterable[Mapping[str, object]]) -> tuple[str, ...]:
    """Return the sorted names used by any record that are not contract fields."""
    known = set(FIELD_NAMES)
    return tuple(sorted({name for raw in raws for name in raw if name not in known}))
