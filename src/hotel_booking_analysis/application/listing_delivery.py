"""Shared hand-over of a listing line to the result sink (ADR-0011, ADR-0008)."""

from hotel_booking_analysis.application.analyze_bookings import RunStatus
from hotel_booking_analysis.application.listing_outcome import ListingOutcome
from hotel_booking_analysis.application.ports import ResultSink
from hotel_booking_analysis.domain.errors import InputError, ResultDeliveryError


def deliver_listing(sink: ResultSink, line: str, failure: InputError | None) -> ListingOutcome:
    """Write the line; map a delivery error or an input failure to the outcome."""
    try:
        sink.write(line)
    except ResultDeliveryError as delivery_error:
        what = "The listing" if failure is None else f"The failed listing ({failure.code})"
        return ListingOutcome(
            RunStatus.DELIVERY_FAILED,
            message=f"{what} could not be written to standard output; "
            f"nothing was stored: {delivery_error}",
        )
    if failure is not None:
        return ListingOutcome(RunStatus.INPUT_FAILED, line, failure.message)
    return ListingOutcome(RunStatus.SUCCEEDED, line)
