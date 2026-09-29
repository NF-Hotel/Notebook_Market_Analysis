# Gateway 6: marimo UI and Acceptance

## Metadata
| Key | Value |
| --- | --- |
| ID | MIL-006 |
| CrossReference | [BC-001] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-29 | Proposed | Jens Tirsvad Nielsen | TBD (S-ID pending SA-001) |
| 2026-09-29 | Proposed | Jens Tirsvad Nielsen | TBD (S04 not yet named) |

---

## Purpose

Decide whether the application is ready for hand-over: the marimo interface shows the analyses and the retained history, states the data limitations, and the whole flow works end to end from a caller's JSON input.

## Deliverable

A marimo notebook that displays the data-quality summary, the six analyses and prior results from the JSONL history (with selection and generated time), plus an end-to-end acceptance test and run instructions for the caller and for local demonstration with the example CSV.

## Go / No-Go Criteria

| # | Criterion (objectively checkable) | Go | No-Go |
| --- | --- | --- | --- |
| 1 | The notebook loads and lists retained results from the history file, each with its generated time, and displays the selected one | Verified | Not displayed |
| 2 | With a malformed history line or empty history the notebook shows a clear message and does not crash | Verified by test | Crash |
| 3 | Every analysis view shows sample sizes and a visible statement of data limitations, and states associations are not causal | Present in every view | Missing in any view |
| 4 | The room-value view labels the figure an estimate, not realized revenue | Present | Absent |
| 5 | The end-to-end test runs a JSON file through the caller entry point and shows the same result in the returned JSON, the history and the notebook | Passes | Fails |
| 6 | The development fallback to the example CSV works only when no JSON is supplied and is documented | Verified | Fallback used in production path |
| 7 | All tests pass and import-linter reports no violation | Clean | Any failure |

## Dependencies

| Depends on | Reason |
| --- | --- |
| MIL-005 | The analyses and the full result contract must exist |
| MIL-004 | History repository, configuration and delivery must exist |

## Traceability

| Business Case objective / KPI / user story | Reference |
| --- | --- |
| Interactive, understandable presentation and history display objectives (BC-001) | US-001.10, US-001.01 to US-001.07; UC-002 |

## Ownership

| Role | Stakeholder ID (SA) |
| --- | --- |
| Owner | TBD, pending SA-001 (open issue OI-02) |
| Approving reviewer | TBD, pending SA-001 (open issue OI-02) |

## Target Date

TBD, open issue OI-01 in PP-001.

## Tasks

| # | Task | Summary | Needs its own Use Case/User Story? | Reference |
| --- | --- | --- | --- | --- |
| 1 | Implement marimo app shell and history viewer | Create the marimo notebook at the edge of the architecture, load results through the history repository, let the user pick a retained result and show when it was produced. | Yes | US-001.10, UC-002, ADR-0006 |
| 2 | Implement data-quality view | Show record count, date coverage, missing or invalid values, duplicate IDs and the list of unavailable analyses for the selected result. | Yes | US-001.01, UC-002 |
| 3 | Implement lead-time and seasonality views | Present the lead-time and seasonality analyses with denominators and interactive selection of groupings. | Yes | US-001.02, US-001.04 |
| 4 | Implement holiday view | Present holiday and window comparisons with a control for window size, keeping booking date and arrival date separate. | Yes | US-001.03 |
| 5 | Implement cancellation, value and guest-mix views | Present cancellation rates, the labeled room-value estimate and guest mix with sample sizes. | Yes | US-001.05, US-001.06, US-001.07 |
| 6 | Implement limitations and association notice component | Provide one shared component that states data limitations, small-sample flags and that findings are associations, not causes, reused by every view. | No | ADR-0007 |
| 7 | Add end-to-end acceptance test | Run a sample JSON file through the caller entry point and check the returned JSON, the history line and the notebook loading of the same result. | No | UC-001, UC-002, ADR-0005 |
| 8 | Write run instructions and development fallback notes | Document how the caller invokes the app, how the configuration file is set and how to demo with the example CSV in development. | No | ADR-0006, ADR-0004 |

---

[BC-001]: ../business-case.md
