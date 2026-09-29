# User Story

## Metadata
| Key | Value |
| --- | --- |
| ID | US-001 |
| CrossReference | [UCD-001], [BC-001], [MIL-001], [MIL-002], [MIL-003], [MIL-004], [MIL-005], [MIL-006], [UC-001], [UC-002] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |

---

## Purpose and Scope

Stories for the epic in [MIL-002]: analyze hotel bookings supplied as JSON by the Calling system, return and keep the result, and review prior results. Roles match the actors in [UCD-001]. The Analyst is provisional (open issue OI-03 in [PP-001]). Field names below come from the example CSV and are not the production schema, which is decided in ADR-0001. Where a field is missing, the dependent analysis is reported as unavailable, never estimated.

## Story List

### US-001.01 — Load and understand data

**As a** Calling system, **I want** a data-quality summary of the booking records I supply, **so that** I know how far the analyses can be trusted.

**Acceptance Criteria**

- Given a JSON file of booking records, when the analysis runs, then the result reports the record count, the earliest and latest booking and arrival dates, and the count of missing and invalid values per field.
- Given records with the same booking ID, when the analysis runs, then the result reports the number of duplicate booking IDs.
- Given a field an analysis needs is absent from all records, when the analysis runs, then that analysis is marked unavailable with the missing field named, and no value is produced for it.

| Traces to | Size | INVEST exceptions |
| --- | --- | --- |
| [UC-001], [MIL-002] | fits one iteration | none |

### US-001.02 — Explore lead time

**As a** Calling system, **I want** a lead-time analysis, **so that** I understand how far ahead guests book.

**Acceptance Criteria**

- Given lead time is present, when the analysis runs, then the result shows the lead-time distribution overall and split by cancellation status, arrival period, market segment and customer type for the fields that exist.
- Given both booking date and arrival date are present, when the analysis runs, then the result compares the supplied lead time with the date difference and reports the count of records that differ.
- Given a group has too few records, when the analysis runs, then the group is flagged as a small sample with its count.

| Traces to | Size | INVEST exceptions |
| --- | --- | --- |
| [UC-001], [MIL-002] | fits one iteration | none |

### US-001.03 — Analyze Cambodian holidays

**As a** Calling system, **I want** booking and arrival behavior compared around Cambodian holidays, **so that** I can see whether activity is associated with holidays.

**Acceptance Criteria**

- Given bookings spanning some years, when the analysis runs, then Cambodian public holidays come from a maintained holiday calendar (the source is fixed in ADR-0007) for exactly the years present in the data.
- Given holiday dates, when the analysis runs, then booking-date behavior and arrival-date behavior are reported separately, each compared for the holiday itself and for configurable windows before and after it with non-holiday periods.
- Given the calendar has no data for a year, when the analysis runs, then that year is reported as unavailable and no holiday is invented.
- Given results are shown, then each comparison shows its counts, and the wording states an association and does not state a cause.

| Traces to | Size | INVEST exceptions |
| --- | --- | --- |
| [UC-001], [MIL-002] | fits one iteration | none |

### US-001.04 — Understand seasonality and booking pace

**As a** Calling system, **I want** seasonality and booking-pace summaries, **so that** I see when bookings are made and when guests arrive.

**Acceptance Criteria**

- Given booking and arrival dates, when the analysis runs, then bookings are summarized by booking date and arrivals by arrival date, as separate series, by week and month.
- Given cancellation status and price are present, when the analysis runs, then cancellation rate and price are summarized per period with the record count.
- Given the data covers part of a year, when the analysis runs, then the result states which periods are incomplete.

| Traces to | Size | INVEST exceptions |
| --- | --- | --- |
| [UC-001], [MIL-002] | fits one iteration | none |

### US-001.05 — Investigate cancellations

**As a** Calling system, **I want** cancellation rates compared across booking attributes, **so that** I can see which groups cancel more often.

**Acceptance Criteria**

- Given cancellation status is present, when the analysis runs, then cancellation rates are reported by lead-time band, deposit type, market segment, customer type, arrival period, special requests and booking changes for the fields that exist.
- Given each rate, then its numerator, denominator and small-sample flag are shown.
- Given results are shown, then wording states associations only and makes no causal or predictive claim.

| Traces to | Size | INVEST exceptions |
| --- | --- | --- |
| [UC-001], [MIL-002] | fits one iteration | none |

### US-001.06 — Estimate room value and stay patterns

**As a** Calling system, **I want** length of stay and an estimated room value, **so that** I understand stay patterns and approximate booking value.

**Acceptance Criteria**

- Given weekend and weekday night counts, when the analysis runs, then length of stay is their sum.
- Given price per night and total nights, when the analysis runs, then estimated booking value is price per night times total nights, with cancelled bookings reported separately from the others.
- Given any value is shown, then it is labeled an estimate and not realized revenue, and the result states that payments, taxes, discounts and adjustments are not supplied.

| Traces to | Size | INVEST exceptions |
| --- | --- | --- |
| [UC-001], [MIL-002] | fits one iteration | none |

### US-001.07 — Explore guest and booking mix

**As a** Calling system, **I want** guest and booking composition summaries, **so that** I understand who books and how.

**Acceptance Criteria**

- Given the fields exist, when the analysis runs, then the result summarizes guest composition, country, meal, room type, repeat-guest status, parking and special requests.
- Given a mix is compared with length of stay, cancellation or price, then the comparison is shown only when each group meets the small-sample rule and includes the counts.
- Given a field is missing, then the related summary is marked unavailable.

| Traces to | Size | INVEST exceptions |
| --- | --- | --- |
| [UC-001], [MIL-002] | fits one iteration | none |

### US-001.08 — Receive the analysis result as JSON

**As a** Calling system, **I want** the completed analysis returned as JSON, **so that** I can process it automatically.

**Acceptance Criteria**

- Given a completed analysis, when it finishes, then a JSON result is returned with a schema version, a result identifier, the generated time, a status, input reference metadata and the findings.
- Given the result, then it contains no raw booking records.
- Given the result cannot be returned or the history cannot be written, then the outcome reports the failure and does not report success.

| Traces to | Size | INVEST exceptions |
| --- | --- | --- |
| [UC-001], [MIL-002] | fits one iteration | none |

### US-001.09 — Keep a bounded analysis history

**As a** Calling system, **I want** each result kept in a local history limited to the latest N results, **so that** past results stay available without unbounded growth.

**Acceptance Criteria**

- Given a completed analysis, when it finishes, then the same result that was returned is appended to the history as one JSON object on one line.
- Given a configuration file with a retention value, when results exceed it, then only the latest N results remain and nothing more is removed than required.
- Given no retention value is configured, then the limit is 10.
- Given an invalid retention value, then the run reports the configuration error instead of using a guess.
- Given a malformed line or an interrupted write, then the remaining results stay readable and the problem is reported.

| Traces to | Size | INVEST exceptions |
| --- | --- | --- |
| [UC-001], [MIL-002] | fits one iteration | none |

### US-001.10 — Review prior results in marimo

**As an** Analyst, **I want** to open marimo and select a retained result, **so that** I can review an earlier analysis and when it was produced.

**Acceptance Criteria**

- Given a history with results, when marimo opens, then all retained results are listed with their generated time and one can be selected.
- Given a result is selected, then its data-quality summary and each available analysis are shown with counts and limitation notes, and estimates are labeled.
- Given the history is empty or contains a malformed line, then marimo shows a clear message and the readable results.

| Traces to | Size | INVEST exceptions |
| --- | --- | --- |
| [UC-002], [MIL-002] | fits one iteration | none |

## INVEST Check

Independent, Negotiable, Valuable, Estimable, Small and Testable hold for all ten stories. Note: stories US-001.02 to US-001.07 share the result contract and the small-sample rule (ADR-0002, ADR-0007), so they are independent in behavior but not in schema; the dependency is recorded in [MIL-003] and does not block estimation.

---

[UCD-001]: ./use-case-diagram.md
[UC-001]: ./use-cases/uc-001-analyze-hotel-bookings.md
[UC-002]: ./use-cases/uc-002-review-analysis-history.md
[MIL-002]: ./milestones/mil-002-requirements-actor-goals.md
[MIL-003]: ./milestones/mil-003-contracts-and-design.md
[PP-001]: ./project-plan.md
