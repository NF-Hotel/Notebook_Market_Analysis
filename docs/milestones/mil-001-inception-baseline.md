# Gateway 1: Inception Baseline

## Metadata
| Key | Value |
| --- | --- |
| ID | MIL-001 |
| CrossReference | [BC-001] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-29 | Proposed | Jens Tirsvad Nielsen | TBD (S-ID pending SA-001) |
| 2026-09-29 | Proposed | Jens Tirsvad Nielsen | TBD (S04 not yet named) |

---

## Purpose

Decide whether the project's scope, stakeholders, actors and plan are agreed well enough to start writing requirements. This gateway establishes the planning baseline for the marimo hotel-booking analysis application: who the stakeholders are, why the project exists, which actors and goals are in scope, and how the phases are scheduled and traced.

## Deliverable

An approved planning baseline consisting of the Stakeholder Analysis (SA-001), Business Case (BC-001), Use Case Diagram (UCD-001), the Traceability Matrix (TM-001), the Project Plan (PP-001) and the six gateway documents (MIL-001 to MIL-006), each reviewed against its QC checklist with an SQA Review Record where a checklist exists.

## Go / No-Go Criteria

| # | Criterion (objectively checkable) | Go | No-Go |
| --- | --- | --- | --- |
| 1 | SA-001 exists, every stakeholder has a stable `S<NN>` ID, and an owner and approving reviewer are named for every gateway | All present | Any gateway without an S-ID owner or reviewer |
| 2 | BC-001 contains all 15 required sections and states the in-scope and out-of-scope items, including the JSON result, JSONL history and retention requirements | Complete | Any required section missing |
| 3 | UCD-001 names every actor (at minimum the Calling system) and every actor has at least one use case; the viewer of marimo history is resolved (open issue OI-03) | Resolved | Actor for history viewing undecided |
| 4 | Each of SA-001, BC-001, UCD-001 and MIL-001 to MIL-006 has an RC record with verdict Go (or Go-with-conditions and all action items closed) | All verdicts Go | Any No-Go verdict or open action item |
| 5 | PP-001 lists all six gateways with owner and dependency order; target dates are either stated with a source or recorded as an accepted open issue | Consistent | Dates invented without a source, or gateway missing |
| 6 | TM-001 has a row for every existing artifact instance | Complete | Any instance missing |
| 7 | Open issues OI-01 to OI-11 in PP-001 each have an owner S-ID and a resolving gateway | Assigned | Any without an owner |

## Dependencies

| Depends on | Reason |
| --- | --- |
| None | First gateway of the project |

## Traceability

| Business Case objective / KPI / user story | Reference |
| --- | --- |
| Business goal: interactive, understandable analysis of booking timing, arrivals, holidays, cancellations, guest mix and estimated room revenue | BC-001 (planned, task 9); no KPI document is planned, see PP-001 Scope Coverage |

## Ownership

| Role | Stakeholder ID (SA) |
| --- | --- |
| Owner | TBD, pending SA-001 (open issue OI-02) |
| Approving reviewer | TBD, pending SA-001 (open issue OI-02) |

## Target Date

TBD. No project deadline or start date is supplied; recorded as open issue OI-01 in PP-001.

## Tasks

| # | Task | Summary | Needs its own Use Case/User Story? | Reference |
| --- | --- | --- | --- | --- |
| 1 | Review PP-001 project plan | The Project Plan PP-001 was drafted during this planning activity and schedules the six gateways. This task covers its review by the approving stakeholder against each gateway's Go/No-Go criteria, because no PP QC checklist exists. | No | PP-001 |
| 2 | Review MIL-001 gateway document | MIL-001 was drafted during planning; this task produces its SQA Review Record against QC-MIL-001 so the Go/No-Go criteria are confirmed objective and traceable. | No | MIL-001, QC-MIL-001 |
| 3 | Review MIL-002 gateway document | Produces the RC record for MIL-002 against QC-MIL-001 so the requirements gateway has checkable criteria before work starts. | No | MIL-002, QC-MIL-001 |
| 4 | Review MIL-003 gateway document | Produces the RC record for MIL-003 against QC-MIL-001 so the contracts and design gateway has checkable criteria. | No | MIL-003, QC-MIL-001 |
| 5 | Review MIL-004 gateway document | Produces the RC record for MIL-004 against QC-MIL-001 so the first coding gateway has checkable criteria and correct artifact dependencies. | No | MIL-004, QC-MIL-001 |
| 6 | Review MIL-005 gateway document | Produces the RC record for MIL-005 against QC-MIL-001 so the analyses coding gateway has checkable criteria and correct artifact dependencies. | No | MIL-005, QC-MIL-001 |
| 7 | Review MIL-006 gateway document | Produces the RC record for MIL-006 against QC-MIL-001 so the marimo UI and acceptance gateway has checkable criteria. | No | MIL-006, QC-MIL-001 |
| 8 | Write SA-001 Stakeholder Analysis | Identify the stakeholders (project owner, calling-system owner, reviewers, data owner) and assign stable S-IDs. Every other artifact needs these IDs for owners and reviewers, and none are known yet (OI-02). | No | SA-001 |
| 9 | Write BC-001 Business Case | Record the problem, objectives, in and out of scope, assumptions, constraints and risks for the booking-analysis app, including the JSON result, JSONL history and configurable retention. It is the objective that gateways and stories trace to. | No | BC-001 |
| 10 | Write UCD-001 Use Case Diagram | Define the system boundary, the Calling system actor, the viewer actor for marimo history (to be resolved), and the goals in scope. Story roles and use case names must match it. | No | UCD-001 |
| 11 | Write TM-001 Traceability Matrix | Create the matrix with one row per artifact instance so upstream and downstream links and review status are tracked from the start. | No | TM-001 |
| 12 | Review SA-001 | Produce the RC record for SA-001 against QC-SA-001; the reviewer must not be the author. | No | SA-001, QC-SA-001 |
| 13 | Review BC-001 | Produce the RC record for BC-001 against QC-BC-001 to confirm the scope and objectives before requirements start. | No | BC-001, QC-BC-001 |
| 14 | Review UCD-001 | Produce the RC record for UCD-001 against QC-UCD-001 so actors and goals are agreed before stories and use cases are written. | No | UCD-001, QC-UCD-001 |

---

[BC-001]: ../business-case.md
