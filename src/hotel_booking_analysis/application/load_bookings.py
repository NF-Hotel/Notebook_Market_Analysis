"""Choose the booking source and load it (ADR-0001 development fallback, UC-001 1a)."""

from dataclasses import dataclass
from pathlib import Path

from hotel_booking_analysis.application.configuration import Environment
from hotel_booking_analysis.application.ports import BookingReader
from hotel_booking_analysis.domain.booking import BookingSubmission
from hotel_booking_analysis.domain.errors import InputError


@dataclass(frozen=True, slots=True)
class BookingLoader:
    """Loads the supplied JSON file, or the development sample when allowed.

    The sample is used only when no input is supplied and the environment is development;
    otherwise no input is an input error (ADR-0001).
    """

    supplied_reader: BookingReader
    development_reader: BookingReader
    development_sample_path: Path

    def load(self, input_path: Path | None, environment: Environment) -> BookingSubmission:
        if input_path is not None:
            return self.supplied_reader.read(input_path)
        if environment is Environment.DEVELOPMENT:
            return self.development_reader.read(self.development_sample_path)
        raise InputError(
            "NO_INPUT",
            "No input file was supplied and the development fallback is only "
            "available when environment is 'development'.",
        )
