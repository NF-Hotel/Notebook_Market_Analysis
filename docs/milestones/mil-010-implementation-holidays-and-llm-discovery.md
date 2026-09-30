# Gateway 10: Holiday Listing and LLM Discovery Implementation

## Metadata
| Key | Value |
| --- | --- |
| ID | MIL-010 |
| CrossReference | [BC-001], [US-001] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-30 | Proposed | Jens Tirsvad Nielsen | Team2 (S04) |

---

## Purpose

Decide whether the two standalone outputs work: the Calling system can ask for the Cambodian holidays as JSON and for the reachable language-model providers as JSON, each without running an analysis. **Coding starts here only after MIL-008 and MIL-009 are Go.** All code follows the project Python rules (type annotations, Clean Architecture layers, polars first, `Decimal` for money, fakes over mocks) and is written through the `python-developer` agent, and is checked against the design in DCD-001, SD-001 and OC-001.

The interface (command-line subcommands or HTTP routes) is the one ADR-0008 selects; the task titles below use "command" for either.

## Deliverable

Two new commands with tests: the holiday listing (UC-003) and the LLM provider listing (UC-004), the configuration extension (ADR-0012), the output schemas (ADR-0011), and updated run documentation.

## Go / No-Go Criteria

| # | Criterion (objectively checkable) | Go | No-Go |
| --- | --- | --- | --- |
| 1 | The test suite passes, import-linter reports no layer violation, mypy strict and ruff are clean, and the coverage report is produced by pytest | All clean | Any failure |
| 2 | The holiday listing returns JSON that validates against the ADR-0011 schema, comes from the `holidays` package for `KH`, and lists a year with no holiday data as unavailable instead of inventing dates | Verified by test | Invented or missing years |
| 3 | The holiday listing writes nothing to the history and runs no analysis | Verified by test | History or analysis touched |
| 4 | The provider listing reports Ollama and LM Studio each as reachable or not with a reason, and the models of each reachable one, validating against the ADR-0011 schema | Verified against fake servers | Any provider or field missing |
| 5 | An unreachable, slow or misbehaving provider gives a normal listing entry (not reachable, with reason) within the configured timeout, never a crash or a hang | Verified by test | Crash or hang |
| 6 | Configuration keys of ADR-0012 have their defaults and reject invalid values naming the key | Verified by test | Any key unchecked |
| 7 | The code matches DCD-001 for these features, and the differences are listed | Matches or listed | Unlisted difference |

## Dependencies

| Depends on | Reason |
| --- | --- |
| MIL-009 | Contracts, interface decision and design must be approved |
| MIL-008 | Stories and use cases define the behavior |

## Traceability

| Business Case objective / KPI / user story | Reference |
| --- | --- |
| BC-001 objectives 9 and 10 | US-001.11, US-001.12, UC-003, UC-004 |

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
| 1 | Extend configuration for providers and insights | Add the provider addresses, model choice, timeouts and insight option to the configuration loader with defaults and validation. Everything new is off or safe by default. | No | ADR-0012, ADR-0004 |
| 2 | Implement the holiday listing command | Add the use case and command that return the Cambodian holidays for the requested years as JSON, using the existing holiday calendar adapter, without running an analysis or touching the history. | Yes | UC-003, US-001.11, ADR-0011 |
| 3 | Implement LLM provider port and discovery adapters | Add the provider port and adapters for Ollama and LM Studio that list reachable models with a short timeout, using only the standard library or an already approved dependency. | No | ADR-0009, DCD-001 |
| 4 | Implement the provider listing command | Add the use case and command that return the status and models of each configured provider as JSON, with unreachable providers reported and not treated as errors. | Yes | UC-004, US-001.12, ADR-0011 |
| 5 | Add output schemas and contract tests | Add JSON Schemas for the holiday and provider listings and test every output against them, with fake HTTP servers for both providers and cases for timeout, refused connection and malformed answers. | No | ADR-0011, ADR-0009 |
| 6 | Update run documentation | Document the new commands, their output and the new configuration keys in the README and the example configuration, verifying every documented command by running it. | No | ADR-0008, ADR-0012 |

---

[BC-001]: ../business-case.md
[US-001]: ../user-stories.md
