# Gateway 3: Contracts and Design Decisions

## Metadata
| Key | Value |
| --- | --- |
| ID | MIL-003 |
| CrossReference | [BC-001] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-29 | Proposed | Jens Tirsvad Nielsen | TBD (S-ID pending SA-001) |
| 2026-09-29 | Proposed | Jens Tirsvad Nielsen | TBD (S04 not yet named) |

---

## Purpose

Decide whether the data contracts, domain vocabulary and architecture decisions are settled well enough to code. Nothing about the production JSON input, the JSON result, the JSONL history or the configuration file is specified in the repository, so each is decided here rather than assumed.

## Deliverable

A Domain Model (DM-001) and seven Architecture Decision Records (ADR-0001 to ADR-0007) covering the input contract, result contract, history and retention, configuration, delivery semantics, architecture and invocation, and analysis methods, all with status Accepted, plus a review record for DM-001.

## Go / No-Go Criteria

| # | Criterion (objectively checkable) | Go | No-Go |
| --- | --- | --- | --- |
| 1 | ADR-0001 lists every input field as required or optional per analysis, with type, date format and timezone rule, and states what happens to a missing optional field | Listed for all fields in US-001 | Any field or analysis unspecified |
| 2 | ADR-0002 defines the result envelope: schema version, result ID, generated time, status, input metadata, data-quality summary, findings per analysis, and an unavailable-analysis marker; it states that raw booking records are excluded | Defined | Any element missing |
| 3 | ADR-0003 defines history path, JSONL line format, creation and read behavior, handling of malformed lines and interrupted writes, and when retention is applied without deleting more than required | Defined | Any behavior undecided |
| 4 | ADR-0004 defines the configuration file format, location, the retention key with default 10, and validation and error behavior for invalid values | Defined | Any behavior undecided |
| 5 | ADR-0005 states that the caller's result and the history record are the same serialized result and defines behavior when either delivery or history write fails, never reporting success on failure | Defined | Ambiguous failure behavior |
| 6 | ADR-0006 fixes layering (domain, application, adapters, infrastructure), the marimo boundary, the invocation mechanism from the caller, and the dependency list to be installed | Decided | Invocation mechanism undecided (OI-04) |
| 7 | ADR-0007 defines lead-time bands, holiday windows and comparison baselines, minimum sample-size rule, estimate labeling and association-only wording | Defined | Any analysis without a definition |
| 8 | DM-001 covers every concept used by the ADRs and stories, with multiplicities; RC record for DM-001 has verdict Go | Go | Any No-Go verdict |
| 9 | Each ADR names its affected artifacts and is approved by an S-ID reviewer, since no QC-ADR checklist exists (OI-07) | Approved | Not approved |

## Dependencies

| Depends on | Reason |
| --- | --- |
| MIL-002 | Decisions and the domain model derive from the approved stories and use cases |

## Traceability

| Business Case objective / KPI / user story | Reference |
| --- | --- |
| Result delivery, history and retention objectives (BC-001) | US-001.08, US-001.09, US-001.10, UC-001, UC-002 |
| Analysis objectives (BC-001) | US-001.01 to US-001.07 |

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
| 1 | Write DM-001 Domain Model | Model the concepts behind the stories: booking, data-quality finding, analysis result, holiday window, result history and retention policy. It gives the ADRs and code one shared vocabulary and keeps domain types free of framework details. | No | DM-001, UC-001, UC-002 |
| 2 | Write ADR-0001 input JSON contract | Decide the production JSON shape, field names, types, date formats and required versus optional fields per analysis, using the example CSV columns only as context. Also decide the local-development CSV fallback. Without this decision validation cannot be written. | No | ADR-0001, US-001.01 |
| 3 | Write ADR-0002 result JSON contract | Decide the result envelope, identification and versioning fields, status values and findings structure returned to the caller. A fixed contract lets callers and the history rely on one format. | No | ADR-0002, US-001.08 |
| 4 | Write ADR-0003 JSONL history format and retention | Decide the history file location, the one-object-per-line format, creation, reading, malformed-line and interrupted-write handling, and when retention trims to the latest N results. Retention must not delete more than required. | No | ADR-0003, US-001.09, US-001.10 |
| 5 | Write ADR-0004 configuration file | Decide the configuration format and location, the retention setting with default 10 when omitted, and how invalid values are reported. The retention limit must come from configuration, not code. | No | ADR-0004, US-001.09 |
| 6 | Write ADR-0005 delivery and failure semantics | Decide that the returned JSON and the history record are the same completed result and what happens when returning or writing fails, including ordering of the two steps. Success must never be claimed when delivery did not happen. | No | ADR-0005, UC-001 |
| 7 | Write ADR-0006 architecture and invocation | Decide layering per the clean-architecture rules, how marimo sits at the edge, how the calling system invokes the app and receives the JSON, and which dependencies are approved (marimo, polars, holidays). Resolves open issue OI-04. | No | ADR-0006, UC-001, UC-002 |
| 8 | Write ADR-0007 analysis methods | Decide lead-time bands, holiday window sizes and comparison baselines using the `holidays` package for KH, sample-size flags, partial-year handling, and estimate and association wording. This makes the analyses reproducible and honest about limits. | No | ADR-0007, US-001.02 to US-001.07 |
| 9 | Review DM-001 | Produce the RC record for DM-001 against QC-DM-001. | No | DM-001, QC-DM-001 |

---

[BC-001]: ../business-case.md
