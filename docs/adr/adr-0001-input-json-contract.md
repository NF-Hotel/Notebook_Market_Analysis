# ADR-0001: Input JSON Contract

## Metadata
| Key | Value |
| --- | --- |
| ID | ADR-0001 |
| CrossReference | [US-001], [UC-001], [DM-001], [ADR-0004], [ADR-0007] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-29 | Proposed | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-29 | Proposed | Jens Tirsvad Nielsen | Team2 (S04) |

---

## Context

The Calling system supplies booking records as a JSON file, but no production schema exists in the repository (open issue OI-05 in [PP-001]). The example CSV `data/example/nf_hotel_bookings.csv` is only a sample. Facts observed in the sample: 8538 rows; semicolon-delimited; dates as `dd-mm-yyyy`; `is_canceled` as 0 or 1; no duplicate `booking_id`; every `lead_time` equals arrival date minus booking date; arrival dates from 2022-01-01 to 2025-12-31 and booking dates from 2021-03-08 to 2025-12-29; 87 blank `meal` values; 91 rows with `price_per_night` 0; one hotel.

Options for the JSON shape: a top-level array of records; an object wrapping the array with a version; or newline-delimited JSON. The file must be simple for a caller to produce and unambiguous to validate.

## Decision

The input is a UTF-8 JSON file whose top level is an array of booking objects, using the sample's field names (snake_case). Dates are ISO 8601 calendar dates (`YYYY-MM-DD`) without a time zone; numbers are JSON numbers, and `price_per_night` is read as an exact decimal. `is_canceled` and `is_repeated_guest` accept `true`, `false`, `1` or `0`. This is a proposal that the Calling-system owner (S02) must confirm; until then ADR-0001 stays Proposed.

Field requirements per analysis (a missing required field makes that analysis unavailable, and the field is named):

| Analysis | Required fields | Optional fields used when present |
| --- | --- | --- |
| Data quality | none (each check is skipped if its field is absent) | `booking_id`, `booking_date`, `arrival_date` |
| Lead time | `lead_time` | `is_canceled`, `arrival_date`, `market_segment`, `customer_type`; date comparison needs `booking_date` and `arrival_date` |
| Cambodian holidays | `booking_date` (booking side) or `arrival_date` (arrival side); each side is reported independently | `is_canceled` |
| Seasonality and booking pace | `booking_date` (booking series) or `arrival_date` (arrival series) | `is_canceled`, `price_per_night` |
| Cancellations | `is_canceled` | `lead_time`, `deposit_type`, `market_segment`, `customer_type`, `arrival_date`, `total_of_special_requests`, `booking_changes` |
| Room value and stay | `stays_in_weekend_nights`, `stays_in_week_nights`; value also needs `price_per_night` | `is_canceled` |
| Guest and booking mix | at least one of `adults`, `children`, `babies`, `country`, `meal`, `assigned_room_type`, `is_repeated_guest`, `required_car_parking_spaces`, `total_of_special_requests` | `stays_in_weekend_nights`, `stays_in_week_nights`, `is_canceled`, `price_per_night` |

Value rules: a null or absent value counts as missing; a wrongly typed value or an unparseable date counts as invalid; both are counted per field in the data-quality summary and that record is left out of the analyses that need the field. A `price_per_night` of 0 is valid and is counted separately. Unknown fields are ignored and their names reported. `booking_id` values must be unique; duplicates are counted and all copies are kept. An empty array, a top-level value that is not an array, or a file that is not valid JSON fails the run with an input error.

Development fallback: when no input file is supplied and the configuration `environment` is `development` ([ADR-0004]), the system reads `data/example/nf_hotel_bookings.csv` (semicolon-delimited, dates `dd-mm-yyyy`, UTF-8) and converts it to the same records. In any other environment, no input is an error. The result states the source (`supplied` or `development_sample`).

## Consequences

**Positive:**

- Validation and every analysis have one unambiguous field list and one missing-value rule.
- Sample-data behavior (blank meal, zero price) is handled by declared rules rather than by accident.
- The fallback cannot silently run in production.

**Negative:**

- If the real caller sends another shape (wrapper object, other names, other date format), this ADR must be superseded before coding.
- Accepting several boolean spellings adds a small amount of validation code.
- Reading the CSV needs a second, development-only reader.

## Affected Artifacts

- [US-001] — stories 01 to 07 depend on the field matrix.
- [UC-001] — steps 1 to 4 and extensions 1a, 2a, 2b, 4a.
- [DM-001] — Booking Record attributes.
- [ADR-0004] — the `environment` setting controls the fallback.
- [ADR-0007] — methods use these fields.

---

[US-001]: ../user-stories.md
[UC-001]: ../use-cases/uc-001-analyze-hotel-bookings.md
[DM-001]: ../domain-model.md
[PP-001]: ../project-plan.md
[ADR-0004]: ./adr-0004-configuration-file.md
[ADR-0007]: ./adr-0007-analysis-methods.md
