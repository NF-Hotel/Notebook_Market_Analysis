# Gateway 12: HTTP API with FastAPI (Conditional)

## Metadata
| Key | Value |
| --- | --- |
| ID | MIL-012 |
| CrossReference | [BC-001], [US-001] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-30 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |

---

## Purpose

**This gateway is conditional.** It is built only if ADR-0008 (MIL-009) selects an HTTP interface, which would happen if the calling-system owner (S02) needs a long-running service, remote or non-process callers, or concurrent requests, for example because AI insights make a call last a minute or more. If ADR-0008 keeps the command line, this gateway is closed as not needed and no work is done.

If built, a FastAPI service is added as a second entry point over the same use cases. The domain and application layers do not change; the API is an adapter in the outer layers, as ADR-0006 already allows.

## Deliverable

A FastAPI application with routes for the analysis (with the optional insights), the holiday listing and the provider listing, an outcome-to-status-code mapping, an OpenAPI description that matches the ADR-0011 schemas, tests, and run documentation.

## Go / No-Go Criteria

| # | Criterion (objectively checkable) | Go | No-Go |
| --- | --- | --- | --- |
| 0 | ADR-0008 selects an HTTP interface and S02 has accepted it; otherwise the gateway is closed as not needed | Selected: met by the amendment of ADR-0008 of 2026-09-30 | Not selected: close without work |
| 1 | The test suite passes, import-linter reports no layer violation (the API imports use cases only through the composition root), mypy strict and ruff are clean, and the coverage report is produced by pytest | All clean | Any failure |
| 2 | Every route returns the same JSON as the command with the same input, and the analysis route returns the result that was appended to the history | Verified by test | Any difference |
| 3 | The outcomes of ADR-0005 map to documented HTTP status codes, and success is never returned when the history write or delivery failed | Verified by test | Success on failure |
| 4 | The generated OpenAPI description validates and its response schemas agree with the ADR-0011 result and listing schemas | Verified by test | Any disagreement |
| 5 | A long insight request does not block the holiday and provider listings and has a documented timeout | Verified by test | Blocked or unbounded |
| 6 | The new dependencies (FastAPI and an ASGI server) are the only additions and are listed in the pull request | Listed | Unlisted dependency |

## Dependencies

| Depends on | Reason |
| --- | --- |
| MIL-009 | ADR-0008 must select HTTP |
| MIL-011 | The analysis route exposes the insight option |
| MIL-010 | The listing routes expose the two standalone outputs |

## Traceability

| Business Case objective / KPI / user story | Reference |
| --- | --- |
| BC-001 objectives 8 to 10 (interface for the calling system) | UC-001, UC-003, UC-004, UC-005, ADR-0008 |

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
| 1 | Add the FastAPI and ASGI server dependencies (conditional) | Add FastAPI and an ASGI server to the project dependencies only if ADR-0008 selects HTTP. Nothing else changes in the environment. | No | ADR-0008, ADR-0006 |
| 2 | Implement the API entry point over the use cases (conditional) | Add routes for the analysis, the holiday listing and the provider listing as an adapter in the outer layers that calls the same use cases through the composition root. | No | ADR-0008, DCD-001 |
| 3 | Map outcomes to HTTP status codes (conditional) | Translate the four outcomes of ADR-0005 and the listing results to documented status codes, so that success is returned only when the history write and the delivery succeeded. | No | ADR-0005, ADR-0008 |
| 4 | Add OpenAPI and contract tests (conditional) | Test every route against the ADR-0011 schemas and the OpenAPI description, and against the command line's output for the same input. | No | ADR-0011 |
| 5 | Add the API end-to-end test (conditional) | Run the service, call the analysis route with and without insights against a fake model, and check the response, the history line and the marimo view agree. | No | UC-001, UC-005, ADR-0005 |
| 6 | Update run documentation for the API (conditional) | Document how to start the service, the routes and status codes, and the timeouts, verifying each documented command by running it. | No | ADR-0008 | 

---

[BC-001]: ../business-case.md
[US-001]: ../user-stories.md
