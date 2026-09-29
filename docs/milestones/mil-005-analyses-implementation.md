# Gateway 5: Analyses Implementation

## Metadata
| Key | Value |
| --- | --- |
| ID | MIL-005 |
| CrossReference | [BC-001], [US-001] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | TBD (S-ID pending SA-001) |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |

---

## Purpose

Decide whether each analysis is correct, honest about its limits and included in the result contract. Analyses are built on the working core from MIL-004 and follow the definitions in ADR-0007. Code follows the same Python rules and `python-developer` agent as MIL-004.

## Deliverable

Six analyses (lead time, Cambodian holidays, seasonality and booking pace, cancellations, room value and stay patterns, guest and booking mix) implemented in the application layer and included in the result JSON, each with denominators, sample-size flags, unavailable-marker behavior and tests.

## Go / No-Go Criteria

| # | Criterion (objectively checkable) | Go | No-Go |
| --- | --- | --- | --- |
| 1 | Each analysis has tests against a small hand-computed fixture and passes | All pass | Any failure |
| 2 | Every reported rate or comparison includes its denominator, and groups below the ADR-0007 minimum sample are flagged | Verified by test | Missing denominator or flag |
| 3 | Holiday analysis uses the `holidays` package for `KH` for the years in the data, separates booking date from arrival date, and reports unavailable when the package lacks the year | Verified by test | Invented or merged dates |
| 4 | Room value is reported as an estimate (price per night times total nights), cancelled bookings are separated, and the label states it is not realized revenue | Verified by test | Unlabeled figure |
| 5 | No finding text claims causation; wording follows ADR-0007 | Checked by test on fixed wording | Causal wording found |
| 6 | The result JSON with all analyses still validates against the ADR-0002 schema and equals the history line | Valid and identical | Invalid or different |
| 7 | Lead-time analysis compares supplied lead time with the booking-to-arrival date difference when both exist | Verified by test | Not compared |

## Dependencies

| Depends on | Reason |
| --- | --- |
| MIL-004 | Core pipeline, result builder and validation must work first |
| MIL-003 | ADR-0007 defines the methods |

## Traceability

| Business Case objective / KPI / user story | Reference |
| --- | --- |
| BC-001 objectives 2 and 3 (analyses) | US-001.02 to US-001.07 |

## Ownership

| Role | Stakeholder ID (SA) |
| --- | --- |
| Owner | S01 |
| Approving reviewer | S04 |

## Target Date

TBD, open issue OI-01 in PP-001.

## Tasks

| # | Task | Summary | Needs its own Use Case/User Story? | Reference |
| --- | --- | --- | --- | --- |
| 1 | Implement shared analysis helpers | Build the reusable pieces the analyses need: banding, group rates with denominators, small-sample flags, partial-year coverage and the unavailable marker. Sharing them keeps every analysis consistent with ADR-0007. | No | ADR-0007, DM-001 |
| 2 | Implement lead-time analysis | Summarize booking windows overall and by cancellation status, arrival period, market segment and customer type where fields exist, and compare supplied lead time with the date difference. | Yes | US-001.02, ADR-0007 |
| 3 | Implement Cambodian holiday analysis | Use the `holidays` package for `KH` per year in the data, compare holiday and configurable 1, 3 and 7 day windows with non-holiday periods for booking date and arrival date separately, and describe association only. | Yes | US-001.03, ADR-0007 |
| 4 | Implement seasonality and booking pace analysis | Distinguish bookings by booking date from arrivals by arrival date, summarize weekly and monthly patterns, cancellation rates and prices, and account for partial-year coverage. | Yes | US-001.04, ADR-0007 |
| 5 | Implement cancellation analysis | Compare cancellation rates by lead-time band, deposit type, market segment, customer type, arrival period, special requests and booking changes, with sample sizes and no causal claims. | Yes | US-001.05, ADR-0007 |
| 6 | Implement room value and stay analysis | Derive length of stay from weekend and weekday nights and estimate booking value as price per night times total nights using `Decimal`, separating cancelled bookings and labeling the result an estimate. | Yes | US-001.06, ADR-0007 |
| 7 | Implement guest and booking mix analysis | Inspect guest composition, country, meal, room type, repeat-guest status, parking and special requests, compared with stay length, cancellation or price when meaningful. | Yes | US-001.07, ADR-0007 |
| 8 | Wire analyses into result and add tests | Include all analyses in the result envelope and add fixture tests for each analysis plus a schema test for the full result. | No | ADR-0002, ADR-0007 |

---

[BC-001]: ../business-case.md
[US-001]: ../user-stories.md
