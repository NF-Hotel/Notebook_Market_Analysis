# SQA Review Record: DM-001

## Metadata
| Key | Value |
| --- | --- |
| ID | RC-013 |
| CrossReference | [DM-001], [QC-DM-001] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-29 | Approved | Claude Code (AI-assisted draft) | Team2 (S04) |

---

## Artifact Under Review

- Instance reviewed: [DM-001]
- Checklist used: [QC-DM-001]

This record is an AI-assisted draft review. The author of the artifact is S01; the reviewer of record is S04, who has not yet confirmed it, so the verdict below is conditional. DM-001 was marked Approved before this review; because the review changed the document, a new Proposed row was added to its version history.

## Checklist Results

| # | Criterion | Status | Evidence/Notes |
| --- | --- | --- | --- |
| 1 | Uses ubiquitous/business language throughout; no technical or implementation jargon (e.g. no "table", "class", "pointer") | Pass | Found during review: attributes 'schema version' was technical. Fixed: renamed 'format version'. Other names (booking, holiday window, retention policy) are business terms; class-style names appear only as Mermaid diagram identifiers. |
| 2 | Multiplicities on associations are correct and complete (e.g. `1..*`, `0..1`) | Pass | Found during review: the retains association gave the History end as 1, but a failed result is never retained and retention removes old results. Fixed: History end is 0..1. All other associations have both ends. |
| 3 | No operation/method signatures shown — attributes and associations only | Pass | The diagram lists attributes only; no operations. |
| 4 | Associations are named with an unambiguous reading direction | Pass | Each association has a name and reading direction in the table, for example 'submission is answered by result'. |
| 5 | Generalization/specialization used correctly, reflecting true "is-a" relationships, not misused for code reuse | Pass | Six analysis kinds are specializations of Analysis; each is a true is-a. No inheritance for reuse. |
| 6 | Every concept traces to a noun phrase found in the use cases or glossary | Pass | Found during review: Holiday Window cited a UC-001 phrase that does not exist. Fixed: it now cites US-001.03. Every other concept cites a UC-001 or UC-002 phrase, and the glossary-style ones (Group Statistic) cite UC-001 rule wording. |
| 7 | Attributes are simple domain data (no foreign-key-like references or object pointers modeled as attributes) | Pass | Attributes are plain data (dates, counts, names). No identifiers referring to other concepts; those are associations. |

## Overall Verdict

Go-with-conditions — all seven criteria pass after three fixes made during the review (technical attribute name, one wrong multiplicity, one wrong source citation). The verdict stays conditional until S04 confirms this review and the corrected model.

## Action Items

| Action | Owner | Due |
| --- | --- | --- |
| S04 confirms or amends this review and the corrected DM-001 | S04 | TBD (OI-01) |
| Check that ADR-0002, ADR-0003 and ADR-0007 still agree with the corrected multiplicity and the term 'format version' | S01 | TBD (OI-01) |

---

[DM-001]: ../../domain-model.md
[QC-DM-001]: ../../../framework/qc/qc-domain-model.md
