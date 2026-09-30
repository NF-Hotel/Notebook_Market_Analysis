# SQA Review Record: UCD-001 (revision)

## Metadata
| Key | Value |
| --- | --- |
| ID | RC-020 |
| CrossReference | [UCD-001], [QC-UCD-001] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-30 | Proposed | Claude Code (AI-assisted draft) | Team2 (S04) |

---

## Artifact Under Review

- Instance reviewed: [UCD-001]
- Checklist used: [QC-UCD-001]

This record is a draft review made by an independent AI reviewer agent that did not write the document, then applied by the author. The reviewer of record is S04, who has not yet confirmed it, so the verdict is conditional. Defects found were fixed on 2026-09-30 and are noted in the criteria they affected.

## Checklist Results

| # | Criterion | Status | Evidence/Notes |
| --- | --- | --- | --- |
| 1 | Actors are defined with correct UML stereotypes (e.g. `<<System>>`, `<<Actor>>`) | Pass | Actors and the system carry their stereotypes; the language-model providers are external services and are deliberately not drawn, with the reason given. |
| 2 | System boundary is clearly drawn and labeled | Pass | The boundary is labeled and described in Purpose and Scope. |
| 3 | Include/extend relationships are used correctly per UML 2.5.1, not as generic "uses" arrows | Pass | UC-005 extends UC-001, drawn from the extension to the base, with the extension point (after step 4) and the condition in the relationships table. Found in review: UC-001 did not declare the extension point. Fixed: UC-001 now declares 'insights requested' and cites UC-005. |
| 4 | Every actor participates in at least one use case (no orphan actors) | Pass | Both actors have use cases (Calling system: UC-001, UC-003, UC-004, UC-005; Analyst: UC-002). |
| 5 | Diagram is traceable to a documented stakeholder need | Pass | Actor rows cite S-IDs and the objectives 8 to 10 map to the new use cases. |
| 6 | Use case names are verb phrases describing actor goals, not internal system operations | Pass | All five names are verb phrases and match the use case titles. |
| 7 | Diagram is free of implementation detail (e.g. UI widgets, database tables) | Pass | No screens or tables. Found in review: a 'None' placeholder row in the relationships table. Fixed: replaced by a sentence. |
| 8 | Actor and use case naming is consistent with corresponding Use Case and User Story documents | Pass | Titles and actor names match UC-001 to UC-005 and US-001. Found in review: a stale sentence said the use cases were still to be written. Fixed. |

## Overall Verdict

Go-with-conditions — all eight criteria pass after three fixes; the verdict stays conditional until S04 confirms. Mermaid renderers may drop angle-bracket stereotypes from labels; not verified.

## Action Items

| Action | Owner | Due |
| --- | --- | --- |
| Check the diagram renders the stereotypes in the viewer that is used | S01 | TBD (OI-01) |
| S04 confirms or amends this review | S04 | TBD (OI-01) |

---

[UCD-001]: ../../use-case-diagram.md
[QC-UCD-001]: ../../../framework/qc/qc-use-case-diagram.md
