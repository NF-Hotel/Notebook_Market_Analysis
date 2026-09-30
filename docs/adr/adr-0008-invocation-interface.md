# ADR-0008: Invocation Interface

## Metadata
| Key | Value |
| --- | --- |
| ID | ADR-0008 |
| CrossReference | [UC-003], [UC-004], [UC-005] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-30 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-30 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |

---

## Context

The application has one entry, `python -m hotel_booking_analysis analyze`, decided in [ADR-0006] with the exit codes of [ADR-0005]. MIL-008 adds three capabilities: the holiday listing ([UC-003]), the provider listing ([UC-004]) and optional AI insights during an analysis ([UC-005]). The calling-system owner (S02) must say how these are called (open issues OI-04 and OI-17 in [PP-001]). Two options were compared against the needs of the calling system:

| Need | Command-line subcommands | FastAPI service |
| --- | --- | --- |
| Long calls: a model call may take a minute or more, and an analysis with insights makes up to six of them in sequence | A process runs as long as the caller waits; the caller sets its own process timeout; nothing else to configure | HTTP clients, proxies and gateways commonly time out first; needs a job-and-poll design or streaming, which is a further decision |
| Remote or non-Python callers | Any technology that can start a process and read standard output; a caller on another machine cannot call it without its own transport | Any HTTP client, on the network |
| Concurrency | Each call is its own process; two runs at once meet only at the history lock file ([ADR-0003]) | One server process handles many requests; the history lock and model calls then have to be shared safely inside it |
| Extra dependencies | None: `argparse` and the standard library, as built | FastAPI and an ASGI server (for example uvicorn), both new runtime dependencies |
| Operation and security | Nothing to run or protect; the caller's own permissions apply | A server to start, keep running, bind to an address and secure (authentication, exposure of booking analysis results) |
| State | Stateless per call; state is the configuration and the history file | Stateless per request in principle, but a long-lived process invites caching and shared state that no decision has approved |
| Start-up cost | One Python process start per call | Paid once |

Forces: the built code already has the entry, the exit-code contract and a layering (`application` use cases behind ports, `infrastructure` composition root, [ADR-0006]) in which a second driving adapter can call the same use cases. No requirement or stakeholder statement names HTTP, a remote caller or high concurrency. The open assumption is that the calling system runs on the same machine and starts processes (S02 to confirm).

## Decision

The application stays a command-line program with subcommands on the existing entry `python -m hotel_booking_analysis`; FastAPI is not added now. Every subcommand writes one JSON document to standard output and messages to standard error.

| Subcommand | Arguments | Use case | Output |
| --- | --- | --- | --- |
| `analyze` | `[--input <file.json>] [--config <file.toml>] [--insights]` | [UC-001], with [UC-005] when `--insights` is given | the analysis result ([ADR-0002], [ADR-0011]) |
| `holidays` | `[--years <2025 or 2024-2026 or 2024,2026>] [--config <file.toml>]` | [UC-003] | the holiday listing ([ADR-0011]) |
| `llm-providers` | `[--config <file.toml>]` | [UC-004] | the provider listing ([ADR-0011]) |

The rules of the `--years` value and the JSON of the two listings are in [ADR-0011]; the addresses, timeouts and model choice are in [ADR-0009]; the keys are in [ADR-0012]. `--insights` is the only way to ask for insights; without it no model is contacted ([UC-005]).

**Exit codes** extend [ADR-0005] and leave its table for `analyze` unchanged:

| Situation | Caller receives | History | Exit code |
| --- | --- | --- | --- |
| `analyze`, all outcomes of [ADR-0005] and its 2026-09-30 amendment | as in [ADR-0005] | as in [ADR-0005] | 0, 2, 3, 4 as in [ADR-0005] |
| `analyze --insights`, some or all insights unavailable, the analysis completed | the result on standard output, status `completed_with_warnings` ([ADR-0011]) | result appended | 0, the same as without insights |
| `holidays` or `llm-providers`, the listing was produced (including a year without calendar data, and no reachable provider) | the listing on standard output | not touched | 0 |
| `holidays` with an invalid `--years` value or a configuration file that does not parse; `llm-providers` with a configuration file that does not parse or an invalid `[llm]` value | a failed document with `error` on standard output (as for `analyze`) | not touched | 2 |
| `holidays` or `llm-providers`, the listing cannot be written to the caller | an error message on standard error; nothing was stored, so a retry has no side effect | not touched | 4 |

Exit code 3 is never used by `holidays` and `llm-providers`, because they never touch the history. Option errors that the argument parser itself rejects (an unknown option, a missing value) end with exit code 2 and a usage message on standard error and no JSON document; the `--years` value is passed to the application as text and checked there, so an invalid value gives the failed document. A failure of insights never changes the exit code of a completed analysis.

The command line is the only driving adapter now. Because the use cases sit behind ports in the `application` layer, an HTTP adapter can be added as a second driving adapter over the same use cases without changing them. It would be built only as the conditional gateway MIL-012, and only if S02 states that HTTP is needed; otherwise MIL-012 is closed as not needed.

## Consequences

**Positive:**

- No new dependency, no server to run or secure, and one contract (JSON on standard output, exit codes) for all three operations.
- The long model calls are not constrained by an HTTP timeout; the caller chooses how long to wait.
- The existing entry, tests and exit-code contract keep working; `analyze` without `--insights` is unchanged.
- The layering keeps the HTTP option open at the cost of one adapter, so this decision is reversible.

**Negative:**

- A caller on another machine, or one that cannot start processes, cannot call the application; it would need MIL-012.
- The worst-case duration of `analyze --insights` is long: six analyses in sequence at the generation deadline of [ADR-0012] (120 s each, a total limit per request, [ADR-0009]) is 12 minutes plus discovery (up to 4 s), so the caller must set a process timeout to match.
- Each call pays a Python process start, and concurrent callers meet only at the history lock ([ADR-0003]).
- The decision depends on S02's answer to OI-17; if S02 needs HTTP, ADR-0005's behavior for HTTP (which it notes would need revisiting) must be decided in MIL-012.

## Affected Artifacts

- [UC-003] — invoked by `holidays`.
- [UC-004] — invoked by `llm-providers`.
- [UC-005] — requested by `analyze --insights`; failure never changes the exit code.
- [ADR-0005] — its exit codes are extended to the two listing commands; the table for `analyze` is unchanged.
- [ADR-0006] — its invocation decision gains two subcommands and the `--insights` option; the layering is reused.
- [ADR-0009] — the discovery behind `llm-providers` and `--insights`.
- [ADR-0011] — the JSON written to standard output.
- [ADR-0012] — the configuration read by every subcommand through `--config`; the `[llm]` values are validated only by `llm-providers` and `analyze --insights`.
- [PP-001] — resolves OI-17 and closes OI-04 once S02 accepts; MIL-012 stays conditional.

## Amendment 2026-09-30 (MIL-012, open issues OI-04 and OI-17)

The calling-system owner (S02) accepts an HTTP interface, as stated by the project owner (S01) on 2026-09-30. The decision above is amended in one point: **a FastAPI service is added as a second driving adapter, and the command line stays.** Nothing else in the decision changes.

- **Both interfaces stay.** `analyze`, `holidays` and `llm-providers` on `python -m hotel_booking_analysis` are unchanged, with the same JSON and exit codes. The service calls the same three use cases through the composition root, so a route gives the same JSON as the command with the same input, and the analysis route returns the result that was appended to the history. The domain and application layers do not change; the service is an adapter in the outer layers ([ADR-0006]).
- **Conditions of the gateway.** MIL-012 is no longer closed as not needed. It is built after MIL-010 and MIL-011 and its criterion 0 is met by this amendment.
- **New dependencies.** FastAPI and an ASGI server (for example uvicorn) are added, and only those. They are listed in the pull request of MIL-012 and used only in the outer layers.
- **Left to MIL-012.** The routes and their arguments, the mapping of the outcomes of [ADR-0005] and the listings to HTTP status codes (success is never returned when the history write or the delivery failed), the timeout of a long insight request, how the history lock and the model calls are shared safely inside one process, and how the service is bound and secured. The negative consequences listed above (long calls, concurrency, a server to run and protect, exposure of booking analysis results) become design points of MIL-012 and are decided and documented there, in an amendment of this ADR or a new ADR.
- **The 12-minute worst case** of `analyze --insights` still applies to the command line. The service must not block the listings while an insight request runs and must state a timeout for it (criterion 5 of MIL-012).

The design of the service is decided in [ADR-0013]. This amendment needs the written confirmation of S02 (open issue OI-17) and the acceptance of S04.

---

[UC-003]: ../use-cases/uc-003-get-holiday-calendar.md
[UC-004]: ../use-cases/uc-004-get-available-llm-providers.md
[UC-005]: ../use-cases/uc-005-get-ai-insights-for-analyses.md
[PP-001]: ../project-plan.md
[ADR-0002]: ./adr-0002-result-json-contract.md
[ADR-0003]: ./adr-0003-jsonl-history-and-retention.md
[ADR-0005]: ./adr-0005-delivery-and-failure-semantics.md
[ADR-0006]: ./adr-0006-architecture-and-invocation.md
[ADR-0009]: ./adr-0009-llm-provider-discovery-and-connection.md
[ADR-0011]: ./adr-0011-output-contracts-and-result-1-1.md
[ADR-0012]: ./adr-0012-configuration-extension.md
[ADR-0013]: ./adr-0013-http-api.md
[UC-001]: ../use-cases/uc-001-analyze-hotel-bookings.md
