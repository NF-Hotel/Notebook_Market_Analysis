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
| 2026-09-29 | Proposed | Jens Tirsvad Nielsen | TBD (S04 not yet named) |

---

## Purpose

Tracks backward/forward links between artifact instances so that the Business Case's cross-artifact traceability success criterion is measurable. A row is added or updated whenever an artifact instance is created or reviewed.

## Traceability Table

| Artifact Instance | Type | Upstream (Backward Link) | Downstream (Forward Link) | Last Reviewed (RC-ID) |
| --- | --- | --- | --- | --- |
| [SA-001] | Stakeholder Analysis | - | [BC-001], [UCD-001] | - |
| [BC-001] | Business Case | [SA-001] | [UCD-001], [PP-001] | - |
| [UCD-001] | Use Case Diagram | [SA-001], [BC-001] | [US-001], [UC-001], [UC-002] | - |
| [PP-001] | Project Plan | [BC-001] | [MIL-001] to [MIL-006] | - |
| [MIL-001] | Milestone / Gateway | [PP-001] | - | - |
| [MIL-002] | Milestone / Gateway | [PP-001] | - | - |
| [MIL-003] | Milestone / Gateway | [PP-001] | - | - |
| [MIL-004] | Milestone / Gateway | [PP-001] | - | - |
| [MIL-005] | Milestone / Gateway | [PP-001] | - | - |
| [MIL-006] | Milestone / Gateway | [PP-001] | - | - |
| [US-001] | User Story | [UCD-001], [BC-001], [MIL-002] | [UC-001], [UC-002] | - |
| [UC-001] | Use Case | [UCD-001], [US-001], [SA-001] | - | - |
| [UC-002] | Use Case | [UCD-001], [US-001], [SA-001] | - | - |

## Coverage Notes

- No type beyond those listed has an instance yet: DM and ADR are planned in MIL-003.
- `-` in Upstream means foundational, in Downstream means nothing is built on it yet, and in Last Reviewed means no `RC-*` record exists yet.
- No review record has been issued because no independent reviewer (S04) has been named.

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
