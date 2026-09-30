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
| 2026-09-30 | Proposed | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-30 | Proposed | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-30 | Proposed | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-30 | Proposed | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-30 | Proposed | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-30 | Proposed | Jens Tirsvad Nielsen | Team2 (S04) |

---

## Purpose

Tracks backward/forward links between artifact instances so that the Business Case's cross-artifact traceability success criterion is measurable. A row is added or updated whenever an artifact instance is created or reviewed.

## Traceability Table

| Artifact Instance | Type | Upstream (Backward Link) | Downstream (Forward Link) | Last Reviewed (RC-ID) |
| --- | --- | --- | --- | --- |
| [SA-001] | Stakeholder Analysis | - | [BC-001], [UCD-001] | [RC-001] |
| [BC-001] | Business Case | [SA-001] | [UCD-001], [PP-001] | [RC-002], [RC-019] |
| [UCD-001] | Use Case Diagram | [SA-001], [BC-001] | [US-001], [UC-001], [UC-002] | [RC-003], [RC-020] |
| [PP-001] | Project Plan | [BC-001] | [MIL-001] to [MIL-006] | - |
| [MIL-001] | Milestone / Gateway | [PP-001] | - | [RC-004] |
| [MIL-002] | Milestone / Gateway | [PP-001] | - | [RC-005] |
| [MIL-003] | Milestone / Gateway | [PP-001] | - | [RC-006] |
| [MIL-004] | Milestone / Gateway | [PP-001] | - | [RC-007] |
| [MIL-005] | Milestone / Gateway | [PP-001] | - | [RC-008] |
| [MIL-006] | Milestone / Gateway | [PP-001] | - | [RC-009] |
| [MIL-007] | Milestone / Gateway | [PP-001] | - | - |
| [MIL-008] | Milestone / Gateway | [PP-001] | - | - |
| [MIL-009] | Milestone / Gateway | [PP-001] | - | - |
| [MIL-010] | Milestone / Gateway | [PP-001] | - | - |
| [MIL-011] | Milestone / Gateway | [PP-001] | - | - |
| [MIL-012] | Milestone / Gateway | [PP-001] | - | - |
| [US-001] | User Story | [UCD-001], [BC-001], [MIL-002] | [UC-001], [UC-002] | [RC-010], [RC-021] |
| [UC-001] | Use Case | [UCD-001], [US-001], [SA-001] | [DM-001], [SSD-001] | [RC-011], [RC-018] |
| [UC-002] | Use Case | [UCD-001], [US-001], [SA-001] | [DM-001], [SSD-001] | [RC-012], [RC-025] |
| [UC-003] | Use Case | [UCD-001], [US-001], [SA-001] | - | [RC-022] |
| [UC-004] | Use Case | [UCD-001], [US-001], [SA-001] | - | [RC-023] |
| [UC-005] | Use Case | [UCD-001], [US-001], [SA-001], [UC-001] | - | [RC-024] |
| [DM-001] | Domain Model | [UC-001], [UC-002], [UCD-001] | [ADR-0001], [ADR-0002], [ADR-0003], [ADR-0007], [SSD-001], [DCD-001] | [RC-013], [RC-026] |
| [ADR-0001] | Architecture Decision Record | [US-001], [UC-001] | - | - |
| [ADR-0002] | Architecture Decision Record | [US-001], [UC-001] | - | - |
| [ADR-0003] | Architecture Decision Record | [US-001], [UC-001] | - | - |
| [ADR-0004] | Architecture Decision Record | [US-001], [UC-001] | - | - |
| [ADR-0005] | Architecture Decision Record | [US-001], [UC-001] | - | - |
| [ADR-0006] | Architecture Decision Record | [US-001], [UC-001] | - | - |
| [ADR-0007] | Architecture Decision Record | [US-001], [UC-001] | - | - |
| [ADR-0008] | Architecture Decision Record | [UC-003], [UC-004], [UC-005] | - | - |
| [ADR-0009] | Architecture Decision Record | [UC-004], [UC-005], [ADR-0008] | - | - |
| [ADR-0010] | Architecture Decision Record | [UC-005], [ADR-0007], [ADR-0009] | - | - |
| [ADR-0011] | Architecture Decision Record | [UC-003], [UC-004], [UC-005], [ADR-0002], [ADR-0010] | - | - |
| [ADR-0012] | Architecture Decision Record | [ADR-0004], [ADR-0009] | - | - |
| [SSD-001] | System Sequence Diagram | [UC-001], [UC-002], [DM-001] | [OC-001] | [RC-014], [RC-027] |
| [OC-001] | Operation Contract | [SSD-001], [DM-001] | [SD-001] | [RC-015], [RC-028] |
| [SD-001] | Sequence Diagram | [OC-001] | [DCD-001] | [RC-016], [RC-029] |
| [DCD-001] | Design Class Diagram | [SD-001], [DM-001] | - | [RC-017], [RC-030] |

## Coverage Notes

- ADR instances have no QC checklist, so no RC record is possible for them (OI-07); they are approved by the S04 reviewer instead.
- `-` in Upstream means foundational, in Downstream means nothing is built on it yet, and in Last Reviewed means no `RC-*` record exists yet.
- RC-001 to RC-030 are AI-assisted draft reviews with verdict Go-with-conditions, awaiting confirmation by S04. ADR and PP have no QC checklist, so no RC record is possible for them.

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
[SSD-001]: ./../ssd.md
[OC-001]: ./../operation-contracts.md
[SD-001]: ./../sequence-diagrams.md
[DCD-001]: ./../dcd.md
[RC-014]: ./reviews/rc-014-ssd.md
[RC-015]: ./reviews/rc-015-operation-contracts.md
[RC-016]: ./reviews/rc-016-sequence-diagrams.md
[RC-017]: ./reviews/rc-017-dcd.md
[MIL-008]: ./../milestones/mil-008-requirements-holidays-llm-and-ai-insights.md
[MIL-009]: ./../milestones/mil-009-design-holidays-llm-and-ai-insights.md
[MIL-010]: ./../milestones/mil-010-implementation-holidays-and-llm-discovery.md
[MIL-011]: ./../milestones/mil-011-implementation-ai-insights.md
[MIL-012]: ./../milestones/mil-012-conditional-http-api-fastapi.md
[RC-018]: ./reviews/rc-018-uc-001-revision.md
[UC-003]: ./../use-cases/uc-003-get-holiday-calendar.md
[UC-004]: ./../use-cases/uc-004-get-available-llm-providers.md
[UC-005]: ./../use-cases/uc-005-get-ai-insights-for-analyses.md
[RC-019]: ./reviews/rc-019-business-case-revision.md
[RC-020]: ./reviews/rc-020-use-case-diagram-revision.md
[RC-021]: ./reviews/rc-021-user-stories-revision.md
[RC-022]: ./reviews/rc-022-uc-003.md
[RC-023]: ./reviews/rc-023-uc-004.md
[RC-024]: ./reviews/rc-024-uc-005.md
[RC-025]: ./reviews/rc-025-uc-002-revision.md
[ADR-0008]: ./../adr/adr-0008-invocation-interface.md
[ADR-0009]: ./../adr/adr-0009-llm-provider-discovery-and-connection.md
[ADR-0010]: ./../adr/adr-0010-ai-insight-generation-and-guardrails.md
[ADR-0011]: ./../adr/adr-0011-output-contracts-and-result-1-1.md
[ADR-0012]: ./../adr/adr-0012-configuration-extension.md
[RC-026]: ./reviews/rc-026-domain-model-mil-009.md
[RC-027]: ./reviews/rc-027-ssd-mil-009.md
[RC-028]: ./reviews/rc-028-operation-contracts-mil-009.md
[RC-029]: ./reviews/rc-029-sequence-diagrams-mil-009.md
[RC-030]: ./reviews/rc-030-dcd-mil-009.md
