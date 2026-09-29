# Traceability Matrix

## Metadata
| Key | Value |
| --- | --- |
| ID | TM-001 |
| CrossReference | [BC-001] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | TBD (S04 not yet named) |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-29 | Proposed | Jens Tirsvad Nielsen | Team2 (S04) |

---

## Purpose

Tracks backward/forward links between artifact instances so that the Business Case's cross-artifact traceability success criterion is measurable. A row is added or updated whenever an artifact instance is created or reviewed.

## Traceability Table

| Artifact Instance | Type | Upstream (Backward Link) | Downstream (Forward Link) | Last Reviewed (RC-ID) |
| --- | --- | --- | --- | --- |
| [SA-001] | Stakeholder Analysis | - | [BC-001], [UCD-001] | [RC-001] |
| [BC-001] | Business Case | [SA-001] | [UCD-001], [PP-001] | [RC-002] |
| [UCD-001] | Use Case Diagram | [SA-001], [BC-001] | [US-001], [UC-001], [UC-002] | [RC-003] |
| [PP-001] | Project Plan | [BC-001] | [MIL-001] to [MIL-006] | - |
| [MIL-001] | Milestone / Gateway | [PP-001] | - | [RC-004] |
| [MIL-002] | Milestone / Gateway | [PP-001] | - | [RC-005] |
| [MIL-003] | Milestone / Gateway | [PP-001] | - | [RC-006] |
| [MIL-004] | Milestone / Gateway | [PP-001] | - | [RC-007] |
| [MIL-005] | Milestone / Gateway | [PP-001] | - | [RC-008] |
| [MIL-006] | Milestone / Gateway | [PP-001] | - | [RC-009] |
| [MIL-007] | Milestone / Gateway | [PP-001] | - | - |
| [US-001] | User Story | [UCD-001], [BC-001], [MIL-002] | [UC-001], [UC-002] | [RC-010] |
| [UC-001] | Use Case | [UCD-001], [US-001], [SA-001] | [DM-001] | [RC-011] |
| [UC-002] | Use Case | [UCD-001], [US-001], [SA-001] | [DM-001] | [RC-012] |
| [DM-001] | Domain Model | [UC-001], [UC-002], [UCD-001] | [ADR-0001], [ADR-0002], [ADR-0003], [ADR-0007] | [RC-013] |
| [ADR-0001] | Architecture Decision Record | [US-001], [UC-001] | - | - |
| [ADR-0002] | Architecture Decision Record | [US-001], [UC-001] | - | - |
| [ADR-0003] | Architecture Decision Record | [US-001], [UC-001] | - | - |
| [ADR-0004] | Architecture Decision Record | [US-001], [UC-001] | - | - |
| [ADR-0005] | Architecture Decision Record | [US-001], [UC-001] | - | - |
| [ADR-0006] | Architecture Decision Record | [US-001], [UC-001] | - | - |
| [ADR-0007] | Architecture Decision Record | [US-001], [UC-001] | - | - |

## Coverage Notes

- ADR instances have no QC checklist, so no RC record is possible for them (OI-07); they are approved by the S04 reviewer instead.
- `-` in Upstream means foundational, in Downstream means nothing is built on it yet, and in Last Reviewed means no `RC-*` record exists yet.
- RC-001 to RC-013 are AI-assisted draft reviews with verdict Go-with-conditions, awaiting confirmation by S04. ADR and PP have no QC checklist, so no RC record is possible for them.

---

[SA-001]: ./../stakeholder-analysis.md
[BC-001]: ./../business-case.md
[UCD-001]: ./../use-case-diagram.md
[PP-001]: ./../project-plan.md
[MIL-001]: ./../milestones/mil-001-inception-baseline.md
[MIL-002]: ./../milestones/mil-002-requirements-actor-goals.md
[MIL-003]: ./../milestones/mil-003-contracts-and-design.md
[MIL-004]: ./../milestones/mil-004-core-pipeline-implementation.md
[MIL-005]: ./../milestones/mil-005-analyses-implementation.md
[MIL-006]: ./../milestones/mil-006-marimo-ui-and-acceptance.md
[US-001]: ./../user-stories.md
[UC-001]: ./../use-cases/uc-001-analyze-hotel-bookings.md
[UC-002]: ./../use-cases/uc-002-review-analysis-history.md
[DM-001]: ./../domain-model.md
[ADR-0001]: ./../adr/adr-0001-input-json-contract.md
[ADR-0002]: ./../adr/adr-0002-result-json-contract.md
[ADR-0003]: ./../adr/adr-0003-jsonl-history-and-retention.md
[ADR-0004]: ./../adr/adr-0004-configuration-file.md
[ADR-0005]: ./../adr/adr-0005-delivery-and-failure-semantics.md
[ADR-0006]: ./../adr/adr-0006-architecture-and-invocation.md
[ADR-0007]: ./../adr/adr-0007-analysis-methods.md
[RC-001]: ./reviews/rc-001-stakeholder-analysis.md
[RC-002]: ./reviews/rc-002-business-case.md
[RC-003]: ./reviews/rc-003-use-case-diagram.md
[RC-004]: ./reviews/rc-004-mil-001.md
[RC-005]: ./reviews/rc-005-mil-002.md
[RC-006]: ./reviews/rc-006-mil-003.md
[RC-007]: ./reviews/rc-007-mil-004.md
[RC-008]: ./reviews/rc-008-mil-005.md
[RC-009]: ./reviews/rc-009-mil-006.md
[RC-010]: ./reviews/rc-010-user-stories.md
[RC-011]: ./reviews/rc-011-uc-001-analyze-hotel-bookings.md
[RC-012]: ./reviews/rc-012-uc-002-review-analysis-history.md
[RC-013]: ./reviews/rc-013-domain-model.md
[MIL-007]: ./../milestones/mil-007-behavior-and-design-artifacts.md
