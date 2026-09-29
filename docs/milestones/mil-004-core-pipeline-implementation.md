# Gateway 4: Core Pipeline Implementation

## Metadata
| Key | Value |
| --- | --- |
| ID | MIL-004 |
| CrossReference | [BC-001] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-29 | Proposed | Jens Tirsvad Nielsen | TBD (S-ID pending SA-001) |
| 2026-09-29 | Proposed | Jens Tirsvad Nielsen | TBD (S04 not yet named) |

---

## Purpose

Decide whether the core pipeline (input, validation, result, history, retention, configuration and delivery) works end to end before any individual analysis is added. **Coding starts here only after MIL-001, MIL-002 and MIL-003 are Go.** All code follows the project Python rules (type annotations, `src/<package>/{domain,application,adapters,infrastructure}` layout, polars first, `Decimal` for money, fakes over mocks) and is written through the `python-developer` agent.

## Deliverable

A working core in `src/` and `tests/` that loads a JSON booking file (or the development CSV fallback), validates it, produces a contract-conformant result with a data-quality summary, returns it as JSON, appends it to the JSONL history and enforces the configured retention, with passing tests and import-linter contracts.

## Go / No-Go Criteria

| # | Criterion (objectively checkable) | Go | No-Go |
| --- | --- | --- | --- |
| 1 | The test suite passes and import-linter reports no layer violation | 0 failures, 0 violations | Any failure or violation |
| 2 | A sample JSON input produces a result that validates against the ADR-0002 schema | Valid | Invalid |
| 3 | The returned JSON and the appended history line are identical for the same run | Identical | Any difference |
| 4 | With retention set to N, the history holds exactly the latest N results after N+3 runs, and with no setting holds 10 | Verified by test | Different count |
| 5 | A malformed history line, an interrupted write, an invalid configuration value and a failed history write each behave as ADR-0003, ADR-0004 and ADR-0005 specify | All tests pass | Any untested or wrong |
| 6 | Missing optional fields mark dependent analyses unavailable without fabricated values | Verified by test | Fabricated value |
| 7 | Every task's code cites the ADR, story or use case it implements | Cited | Any uncited |

## Dependencies

| Depends on | Reason |
| --- | --- |
| MIL-003 | Contracts, domain model and architecture decisions must be Accepted |
| MIL-002 | Stories US-001.01, US-001.08 and US-001.09 and use case UC-001 define behavior |

## Traceability

| Business Case objective / KPI / user story | Reference |
| --- | --- |
| Data understanding, JSON delivery and bounded history objectives (BC-001) | US-001.01, US-001.08, US-001.09; UC-001 |

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
| 1 | Scaffold package, dependencies and import-linter | Create the package layout, `pyproject.toml`, install the dependencies approved in ADR-0006 into `.venv` and add import-linter contracts. This is the first environment change and is allowed only once the coding gateway is authorized. | No | ADR-0006 |
| 2 | Implement domain entities and value objects | Code the frozen dataclasses for booking, data-quality finding, analysis result and retention policy from the domain model, with no framework or dataframe types. | No | DM-001 |
| 3 | Implement configuration loader | Read the configuration file, default retention to 10 when omitted, and reject invalid values as ADR-0004 specifies. Retention must come from configuration only. | Yes | ADR-0004, US-001.09 |
| 4 | Implement JSON input reader and dev CSV fallback | Read the caller's JSON file per the input contract, and fall back to `./data/example/nf_hotel_bookings.csv` (semicolon-delimited) only in development when no JSON is supplied. | Yes | ADR-0001, US-001.01, UC-001 |
| 5 | Implement validation and data-quality summary | Report record count, date coverage, missing or invalid values and duplicate booking IDs, and mark analyses whose required fields are missing as unavailable. Parsing rules for dates follow the input contract. | Yes | ADR-0001, ADR-0007, US-001.01 |
| 6 | Implement result builder and JSON serialization | Assemble the result envelope with version, ID, generated time, status and input metadata, without raw booking records, and serialize it to JSON. | Yes | ADR-0002, US-001.08 |
| 7 | Implement JSONL history repository | Append one result per line, create the file when missing, skip and report malformed lines on read, and survive an interrupted write as ADR-0003 specifies. | Yes | ADR-0003, US-001.09, US-001.10 |
| 8 | Implement retention enforcement | Trim the history to the latest N results at the time ADR-0003 fixes, deleting no more than required. | Yes | ADR-0003, ADR-0004, US-001.09 |
| 9 | Implement analyze-bookings use case and entry point | Orchestrate read, validate, analyze, return and append in the order ADR-0005 defines, expose the invocation mechanism from ADR-0006, and never report success when delivery or the history write failed. | Yes | UC-001, ADR-0005, ADR-0006, US-001.08 |
| 10 | Add core contract and integration tests | Test the schema validity, return and history consistency, retention counts, malformed lines, interrupted writes and failure behavior with `tmp_path` and port fakes. | No | ADR-0002, ADR-0003, ADR-0005 |

---

[BC-001]: ../business-case.md
