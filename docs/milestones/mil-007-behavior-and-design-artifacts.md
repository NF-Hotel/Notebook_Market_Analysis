# Gateway 7: Behavior and Design Artifacts

## Metadata
| Key | Value |
| --- | --- |
| ID | MIL-007 |
| CrossReference | [BC-001], [US-001] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-29 | Proposed | Jens Tirsvad Nielsen | Team2 (S04) |

---

## Purpose

Decide whether the behavior and design of every use case is documented well enough to review, maintain and extend the application. Every use case ([UC-001] Analyze Hotel Bookings and [UC-002] Review Analysis History) gets a System Sequence Diagram, Operation Contracts, Sequence Diagrams and a Design Class Diagram.

**Sequence caveat:** the plan scheduled these design artifacts before the code, but the core pipeline, the analyses and the marimo notebook (MIL-004 to MIL-006) were built first. The artifacts are therefore written **as built**: they describe the implemented design and are checked against `src/`, and any place where the code and an earlier decision (ADR-0001 to ADR-0007) differ is recorded, not hidden. If the review finds a design flaw, the fix is a new coding task, not a silent edit of the diagram.

## Deliverable

Four artifact documents, each with one section per use case, plus a review record for each: the System Sequence Diagram document (SSD-001), the Operation Contracts document (OC-001), the Sequence Diagram document (SD-001) and the Design Class Diagram document (DCD-001), all traceable to UC-001, UC-002 and DM-001 and consistent with the code.

## Go / No-Go Criteria

| # | Criterion (objectively checkable) | Go | No-Go |
| --- | --- | --- | --- |
| 1 | Every main-success-scenario step of UC-001 and the scenario of UC-002 maps to at least one SSD message, or the deviation is justified in SSD-001 | 100% of steps mapped | Any step unmapped without justification |
| 2 | Every SSD message has exactly one operation contract in OC-001 with signature, preconditions, postconditions in domain-model terms, and the exceptions from the use case extensions | One contract per message | Any message without a contract, or a contract for no message |
| 3 | Every postcondition in OC-001 is realized by a sequence diagram in SD-001, and each diagram names the contract it realizes | All postconditions covered | Any postcondition unrealized |
| 4 | Every class, port and method in DCD-001 exists in `src/` under the same name and layer, and every class in the domain layer of `src/` appears in DCD-001 | Names and layers match | Any mismatch not listed as a documented deviation |
| 5 | DCD-001 layers agree with the import-linter contracts in `pyproject.toml`, with no dependency drawn against the direction | Consistent | Any dependency against the direction |
| 6 | Every difference between the built code and ADR-0001 to ADR-0007 that the artifacts reveal is listed in the artifact concerned and raised as an open issue or a new task | All listed | Any difference unlisted |
| 7 | An RC record exists for each of SSD-001, OC-001, SD-001 and DCD-001 with verdict Go (or Go-with-conditions and all action items closed) | All Go | Any No-Go verdict or open action item |
| 8 | TM-001 has rows for the four documents linking them to UC-001, UC-002 and DM-001 | Present | Missing |

## Dependencies

| Depends on | Reason |
| --- | --- |
| MIL-003 | DM-001 and the ADRs are the intended design the artifacts are compared with |
| MIL-006 | The code that the artifacts describe as built exists and passes its tests |

## Traceability

| Business Case objective / KPI / user story | Reference |
| --- | --- |
| BC-001 objectives 1 to 6 (realization of the analysis, delivery, history and display goals) and objective 7 (reviewed artifacts) | UC-001, UC-002, US-001.01 to US-001.10 |

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
| 1 | Write SSD-001 System Sequence Diagrams | One document with a system sequence diagram per use case: the Calling system and `:System` for UC-001 (main scenario, with the failure flows stated separately), and the Analyst and `:System` for UC-002. Message names become the operation contract names, so they must follow the use case steps. | No | SSD-001, UC-001, UC-002 |
| 2 | Write OC-001 Operation Contracts | One document with a contract for each system operation shown in SSD-001, such as analyzing a booking submission, listing retained results and selecting a result. Preconditions and postconditions use domain-model terms and the extensions of the use cases give the exceptions. | No | OC-001, SSD-001, DM-001 |
| 3 | Write SD-001 Sequence Diagrams | One document that shows how the built objects (use case, ports, adapters, history, notebook view models) realize each contract's postconditions, with control patterns annotated. It is drawn from the code as built and compared with ADR-0006. | No | SD-001, OC-001 |
| 4 | Write DCD-001 Design Class Diagram | One document with the class diagrams of the built application per layer (domain, application, adapters, infrastructure, interface): classes, ports, attributes, signatures, relationships and multiplicities. It must match `src/` and the import-linter contracts, and lists deviations from DM-001 and the ADRs. | No | DCD-001, SD-001, DM-001 |
| 5 | Review SSD-001 | Produce the RC record for SSD-001 against QC-SSD-001, including the check that it matches the use case steps. | No | SSD-001, QC-SSD-001 |
| 6 | Review OC-001 | Produce the RC record for OC-001 against QC-OC-001, including the one-contract-per-message check. | No | OC-001, QC-OC-001 |
| 7 | Review SD-001 | Produce the RC record for SD-001 against QC-SD-001, including the check that every postcondition is realized. | No | SD-001, QC-SD-001 |
| 8 | Review DCD-001 | Produce the RC record for DCD-001 against QC-DCD-001, including the check against `src/` and the import-linter contracts. | No | DCD-001, QC-DCD-001 |

---

[BC-001]: ../business-case.md
[US-001]: ../user-stories.md
[UC-001]: ../use-cases/uc-001-analyze-hotel-bookings.md
[UC-002]: ../use-cases/uc-002-review-analysis-history.md
