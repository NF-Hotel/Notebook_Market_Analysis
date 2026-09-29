# Artifact Registry

This project's artifact state. Types, short names and `CrossReference
Candidates` come from the framework catalog
(`framework/registry/artifact-catalog.md`); this file only records where
each document lives in *this* project and the next version to use.

| Short Name | Artifact Type | Primary File | Next Available Version |
| --- | --- | --- | --- |
| BC | Business Case | docs/business-case.md | 002 |
| SA | Stakeholder Analysis | docs/stakeholder-analysis.md | 002 |
| PP | Project Plan | docs/project-plan.md | 002 |
| MIL | Milestone / Gateway | docs/milestones/*.md | 007 |
| UCD | Use Case Diagram | docs/use-case-diagram.md | 002 |
| US | User Story | docs/user-stories.md | 002 |
| UC | Use Case (Brief/Casual/Fully Dressed) | docs/use-cases/*.md | 003 |
| DM | Domain Model | docs/domain-model.md | 002 |
| ADR | Architecture Decision Record | docs/adr/adr-NNNN-*.md | 0008 |
| RC | SQA Review Record | docs/sqa/reviews/rc-*.md | 010 |
| TM | Traceability Matrix | docs/sqa/traceability-matrix.md | 002 |

## Notes

- "Next Available Version" is the zero-padded version to use the *next* time
  a new document of that type is created. Increment it only when a brand-new
  document is created, not when an existing document's `## Version History`
  gets a row.
- `ADR` uses 4 digits (`0001`); `RC` is sequential across all artifact types.
- Only `PP` and `MIL` documents exist so far (planning phase). All other rows
  are planned artifacts whose tasks are listed in the `MIL-*` documents.
