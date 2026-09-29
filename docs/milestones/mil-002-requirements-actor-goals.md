# Gateway 2: Requirements and Actor Goals

## Metadata
| Key | Value |
| --- | --- |
| ID | MIL-002 |
| CrossReference | [BC-001] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-29 | Proposed | Jens Tirsvad Nielsen | TBD (S-ID pending SA-001) |
| 2026-09-29 | Proposed | Jens Tirsvad Nielsen | TBD (S04 not yet named) |

---

## Purpose

Decide whether the actor goals are specified precisely enough to design contracts and code against. This gateway turns the candidate goals (data understanding, lead time, Cambodian holidays, seasonality, cancellations, room value, guest mix, JSON result delivery, bounded history and history review) into testable stories and use cases.

## Deliverable

One User Story document (US-001) with stories US-001.01 to US-001.10, two Use Case documents (UC-001 Analyze Hotel Bookings, UC-002 Review Analysis History), and an SQA Review Record for each, all traced to UCD-001 and BC-001.

## Go / No-Go Criteria

| # | Criterion (objectively checkable) | Go | No-Go |
| --- | --- | --- | --- |
| 1 | Every story US-001.NN has Given/When/Then acceptance criteria and traces to a use case or to MIL-002 | 10 of 10 | Any story untraced or without criteria |
| 2 | Every story role and use case actor matches an actor in UCD-001 exactly | All match | Any mismatch |
| 3 | UC-001 is Fully Dressed and covers the main flow: JSON supplied, validated, analyzed, result returned as JSON, result appended to history, retention applied; extensions cover invalid input, missing fields, history write failure and delivery failure | Covered | Any extension missing |
| 4 | Stories for analyses state that results are associations, not causal claims, that denominators are shown, and that unavailable analyses are reported rather than fabricated | Stated in every relevant story | Any story silent on this |
| 5 | The room-value story labels the figure as an estimate, not realized revenue | Stated | Absent |
| 6 | RC records exist for US-001, UC-001 and UC-002 with verdict Go, and TM-001 rows are updated | All Go | Any No-Go verdict |
| 7 | Open issues OI-03, OI-04 and OI-10 in PP-001 are resolved or explicitly deferred with an owner | Resolved | Unowned |

## Dependencies

| Depends on | Reason |
| --- | --- |
| MIL-001 | Actors (UCD-001), stakeholder IDs (SA-001) and scope (BC-001) must be approved first |

## Traceability

| Business Case objective / KPI / user story | Reference |
| --- | --- |
| BC-001 objectives on analysis, result delivery and history (planned in MIL-001) | US-001.01 to US-001.10 |

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
| 1 | Write US-001 user stories | One document holding ten stories: load and understand data, explore lead time, analyze Cambodian holidays, seasonality and booking pace, cancellations, room value and stay patterns, guest and booking mix, receive the result as JSON, keep a bounded history, and review prior results in marimo. Each has testable acceptance criteria. | No | US-001 |
| 2 | Write UC-001 Analyze Hotel Bookings | Fully dressed use case for the primary goal: the Calling system supplies JSON records and receives a JSON analysis result that is also appended to the JSONL history. Extensions cover invalid input, unavailable analyses and delivery or history failures. | No | UC-001, UCD-001 |
| 3 | Write UC-002 Review Analysis History | Use case for opening the marimo interface, selecting a retained result and seeing when it was produced. Its actor depends on open issue OI-03. | No | UC-002, UCD-001 |
| 4 | Review US-001 | Produce the RC record against QC-US-001 checking INVEST, acceptance criteria and actor match. | No | US-001, QC-US-001 |
| 5 | Review UC-001 | Produce the RC record against QC-UC-001 for the primary use case. | No | UC-001, QC-UC-001 |
| 6 | Review UC-002 | Produce the RC record against QC-UC-001 for the history-review use case. | No | UC-002, QC-UC-001 |

---

[BC-001]: ../business-case.md
