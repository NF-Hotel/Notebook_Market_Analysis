# Use Case: Analyze Hotel Bookings

## Metadata
| Key | Value |
| --- | --- |
| ID | UC-001 |
| CrossReference | [UCD-001], [US-001], [SA-001], [DM-001], [SSD-001], [UC-005] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | TBD (S04 not yet named) |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | TBD (S04 not yet named) |
| 2026-09-30 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-30 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |

---

**Format:** Fully Dressed

## Fully Dressed

- **Scope:** Hotel Booking Analysis (the system)
- **Level:** user-goal
- **Primary Actor:** Calling system
- **Stakeholders and Interests:**
  - S01 — the analyses are complete, honest about their limits, and delivered in a controlled way
  - S02 — the input is accepted as agreed, and the result and failures are dependable and versioned
  - S03 — booking data is used correctly and data problems are reported
- **Preconditions:**
  - The Calling system has a JSON file of booking records.
  - A configuration file may exist; if it does not, defaults apply.
- **Postconditions (success guarantee):**
  - The Calling system holds a JSON result describing the analysis.
  - The same result is the newest entry in the local JSONL history.
  - The history holds no more than the configured number of results, and 10 when none is configured.
  - Analyses that lacked required fields are marked unavailable.

### Main Success Scenario

1. The Calling system supplies a JSON file of booking records.
2. The system checks the records and prepares them for analysis.
3. The system records the data-quality summary: record count, date coverage, missing or invalid values, duplicate booking IDs.
4. The system runs each analysis whose required fields are present: lead time, Cambodian holidays, seasonality and booking pace, cancellations, room value and stay patterns, guest and booking mix.
5. The system assembles one result containing its identifier, version, generated time, status, input reference, data-quality summary and findings.
6. The system appends the result to the history as one JSON line.
7. The system applies the retention limit to the history.
8. The system returns the result to the Calling system as JSON, and reports success.

**Extension point: insights requested**, after step 4 and before step 5. When the Calling system asked for AI insights together with its request, [UC-005] extends this use case at that point; otherwise steps 4 and 5 follow one another as written.

The system also reads the configuration file before step 2. After a successful run it reads the history once more, only to count malformed lines and warn about them; this does not change the history.

### Extensions (Alternative / Exception Flows)

- 1a. No JSON file is supplied:
  1. In development only, the system uses `./data/example/nf_hotel_bookings.csv`, and the result states that the fallback was used.
  2. Outside development, the system returns a failed result with the error code `NO_INPUT`; nothing is stored in the history ([ADR-0005] defines the outcome).
- 2a. The file is not valid JSON or does not match the input contract:
  1. The system returns a failed result naming the problem and does not append a history entry for an analysis that did not run.
- 2b. Some records are invalid:
  1. The system reports the invalid values in the data-quality summary and continues with the valid records, or stops if none remain.
- 4a. A required field is missing for an analysis:
  1. The system marks that analysis unavailable with the missing field, and does not fabricate values.
- 4b. The holiday calendar has no data for a year in the data:
  1. The system marks the holiday analysis unavailable for that year, and does not invent holidays.
- 6a. The history cannot be written, or another run holds the history for longer than the allowed wait:
  1. The system reports the failure, does not claim the history was updated, and delivers no result; the remaining readable results stay intact.
- 6b. A line in the history is malformed or an earlier write was interrupted:
  1. The system isolates the partial line, keeps every malformed line, continues the run, and warns the operator of the Calling system about the malformed lines.
- 7a. The configuration file is missing:
  1. The system applies the default retention of 10.
- 7b. The retention value is invalid:
  1. The system reports the configuration error, before any analysis runs, as a failed result, and does not apply a guessed limit.
- 7c. Retention cannot be applied after the result was appended:
  1. The appended result stays in the history; the system reports the failure and delivers no result.
- 8a. The result cannot be returned to the Calling system:
  1. The system reports the delivery failure and does not report success. The result stays saved in the history, so a retry by the Calling system creates a second result ([ADR-0005]). If the failed result of an input error cannot be delivered, nothing was stored.

### Special Requirements / Business Rules

| Step | Rule |
| --- | --- |
| 2 | Production input is JSON. Required and optional fields per analysis are defined in ADR-0001. |
| 3 | Missing analyses are shown as unavailable, not estimated. |
| 4 | Findings describe associations, never causes. Every rate shows its numerator and denominator, and small samples are flagged. |
| 4 | The estimated room value is price per night times total nights, labeled an estimate and not realized revenue, with cancelled bookings separate. |
| 4 | Booking-date behavior and arrival-date behavior are analyzed separately. |
| 5 | The result contains no raw booking records unless a documented need exists. |
| 6, 8 | The history entry and the returned result are the same serialized result. |
| 7 | Retention keeps the latest N results and never deletes more than needed. N comes from a configuration file. |

### Open Issues

- Invocation mechanism from the Calling system (OI-04): a command line as built; whether subcommands or an HTTP service is decided in ADR-0008 (planned).
- Exact input and result schemas, history location and configuration location are decided in ADR-0001 to ADR-0004.
- What counts as one retained result and behavior with concurrent callers (OI-10) are undecided.

---

[UCD-001]: ../use-case-diagram.md
[US-001]: ../user-stories.md
[SA-001]: ../stakeholder-analysis.md
[DM-001]: ../domain-model.md
[SSD-001]: ../ssd.md
[ADR-0005]: ../adr/adr-0005-delivery-and-failure-semantics.md
[UC-005]: ./uc-005-get-ai-insights-for-analyses.md
