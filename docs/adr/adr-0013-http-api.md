# ADR-0013: HTTP API

## Metadata
| Key | Value |
| --- | --- |
| ID | ADR-0013 |
| CrossReference | [UC-001], [UC-003], [UC-004], [UC-005], [ADR-0005], [ADR-0008] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-30 | Draft | Jens Tirsvad Nielsen | Team2 (S04) |

---

## Context

The amendment of [ADR-0008] of 2026-09-30 accepts an HTTP interface as a second driving adapter next to the command line and leaves these points to [MIL-012]: the routes and their arguments, the mapping of the outcomes of [ADR-0005] and of the listings to HTTP status codes (success is never returned when the history write or the delivery failed), the timeout of a long insight request, how the history lock and the model calls are shared safely inside one process, and how the service is bound and secured. The forces are that the command line and its exit codes stay unchanged, that a route must give the same JSON as the command with the same input, that a request must never make the service read a path or a setting the caller names, and that the service is new attack surface for booking data. The use cases take an input file path and write to a result sink ([ADR-0006]), and they must not change.

## Decision

**Entry and binding.** `python -m hotel_booking_analysis serve [--host 127.0.0.1] [--port 8000] [--config FILE]` starts the service with uvicorn. The default address is loopback only. `--config` is the configuration file of [ADR-0004] used for every request (its lookup rules, including `HOTEL_ANALYSIS_CONFIG`, are unchanged and are read at each request, as each command run reads it once). The ASGI application is created by `create_app(settings)` in `infrastructure/http_api.py`, the composition-root layer, which builds each use case through the same `bootstrap` functions as the command line. FastAPI, uvicorn and starlette are used only there; an import-linter contract forbids them in `domain`, `application`, `adapters` and `interface`.

**Routes.** Each route runs the use case of the command of the same name.

| Route | Use case | Arguments | Body of the answer |
| --- | --- | --- | --- |
| `POST /analyze` | [UC-001], with [UC-005] when `insights=true` | query `insights` (boolean, default `false`); request body: the JSON array of bookings of [ADR-0001], `Content-Type: application/json` | the result of [ADR-0002] and [ADR-0011] |
| `GET /holidays` | [UC-003] | query `years` (text, as `--years` of [ADR-0011]) | the holiday listing |
| `GET /llm-providers` | [UC-004] | none | the provider listing |
| `GET /health` | none | none | `{"status":"ok"}` |

The interactive OpenAPI pages (`/docs`, `/redoc`) and `/openapi.json` stay enabled. The OpenAPI document publishes the JSON Schemas of the repository as the response schemas (result 1.0 and 1.1, holiday listing, provider listing) in `components/schemas`, embedded without `$id` and `$schema` and with every `$ref` rewritten to a pointer into the document, because a resolver does not switch its base URI inside an embedded document; the 422 answers of the routes also allow the framework's `detail` body. The answers themselves are plain bytes, not Pydantic response models, so they stay identical to the command's output. Unknown routes and methods, a wrong `Content-Type` (415) and a malformed query value such as `insights=maybe` (framework 422 with a `detail` list) use the framework defaults.

**Same bytes.** A route runs the use case with a sink over an in-memory stream, so the answer body is the exact serialized line and one newline that the command writes to standard output, with media type `application/json`. The body of `POST /analyze` is the line that was appended to the history ([ADR-0005] rules 1 and 2 hold unchanged).

**The analysis body.** The use case reads a file, so the adapter writes the request bytes to a file named `request-body.json` inside a fresh temporary directory that exists only for the request, runs the existing input path (reader, validation of [ADR-0001], `content_sha256` of the body bytes), and deletes it. The application layer and its ports do not change. The server never reads a path named by the caller, and it takes no input path, configuration path or history path from a request. As [ADR-0002] keeps only a file name in `input.reference`, the result of a request body shows `input.source` `supplied` and `input.reference` `request-body.json`. The development fallback of [ADR-0001] can never apply, because an empty body is an invalid JSON input.

**Status codes.** One rule: the HTTP status follows the exit code of [ADR-0005] and [ADR-0008].

| Situation | Exit code of the command | Status | Body |
| --- | --- | --- | --- |
| Completed, including `completed_with_warnings`, unavailable insights, a listing with a year without calendar data or with no reachable provider | 0 | 200 | the document |
| Input or configuration error (invalid JSON, not an array, empty, a record not an object, unparsable or invalid configuration, invalid `years`, invalid `[llm]` value for the routes that use it) | 2 | 422 | the failed document (the same one the command prints; nothing stored) |
| History write or retention failure | 3 | 500 | error object, no `result_id` |
| The document could not be handed over (the in-memory stream failed): a completed result already saved, a failed result not stored, or a listing with nothing stored | 4 | 500 | error object; for `POST /analyze` with `result_id` |

422 is chosen over 400: the request is well formed HTTP and understood, its content cannot be processed, and 422 is what the framework already uses for a rejected argument; one status for all content errors is simpler for a caller than a split by cause, and the `error.code` of the failed document tells the causes apart. A configuration error is reported with 422 as well, because it is the same document as the command prints, although the caller did not cause it. The error object is `{"status":"error","error":{"code":"HISTORY_FAILED"|"DELIVERY_FAILED","message":"..."}}` plus `"result_id"` for a failed hand-over of an analysis, where [ADR-0005] has the command name it. Its `message` is the text the command writes to standard error. It has no `schema_version` and is not a result. The status is 200 only when the history write and the hand-over both completed. A retention failure leaves the appended result in the history, as in [ADR-0005]; the message says so, and the caller must treat 500 with `HISTORY_FAILED` as "the result may be stored but was not delivered".

**What a hand-over failure means over HTTP.** The response is built in memory, so `DELIVERY_FAILED` is rare. A connection that breaks while the server sends a 200 cannot be seen by the use case: the history already holds the result, and the caller, who got no answer, follows [ADR-0005] rule 6 (saved, possibly not delivered; a retry makes a second result).

**Concurrency.** The routes are plain functions, which FastAPI runs in its thread pool (40 threads by default), so a long `POST /analyze?insights=true` does not block `GET /holidays`, `GET /llm-providers` or `GET /health`; a 41st concurrent request waits for a free thread. Each request builds its own use case, clock, stream and provider adapters; the service keeps no state except its settings, so it is stateless per request except the history file. The lock file of [ADR-0003] is created with an exclusive create per append and an object per append, so it is exclusive between threads of one process as it is between processes (tested); a request that cannot get the lock in 10 seconds ends as a history failure (500). Model calls are not shared or queued: each insight request makes its own sequence of calls.

**Timeout.** There is no cutoff in the service. A request lasts as long as the bound of [ADR-0009] and [ADR-0012]: discovery (up to 2 × `llm.discovery_timeout_seconds`) plus 6 × `llm.generation_timeout_seconds`, 12 minutes and 4 seconds with the defaults. `POST /analyze` without `insights` and the listings are short. A caller must set its HTTP client timeout (and that of any proxy or gateway in front) to at least this bound plus a margin for an insight request, or use `insights=false`; a client that hangs up early does not stop the run, and the result is still stored.

**Security.** The service has no authentication, no TLS, no rate limit and no limit on the size of a request body. The default bind is loopback, and `serve` logs a warning when the host is not `127.0.0.1`, `localhost` or `::1`. Anyone who can reach the port can submit bookings, append to the history (retention applies), read the provider listing and start model calls that cost time. It must be exposed only behind a gateway that adds authentication, transport security and limits. The request never chooses a file, and the booking data leaves the process only to the configured providers when `insights=true` ([ADR-0009] local-only rule unchanged).

**Dependencies.** `fastapi` and `uvicorn` are runtime dependencies and `httpx` is a development dependency (the test client), and nothing else is added. The `serve` process exits with the code of uvicorn: 0 after a clean stop where the platform allows it, non-zero if it cannot start (for example, the port is in use); the exit codes of [ADR-0005] apply to the commands that return a document.

## Consequences

**Positive:**

- The same three use cases serve both interfaces with the same JSON and the same outcomes; the domain, application and adapter layers are untouched.
- One documented mapping, with success never returned after a failed history write or hand-over.
- The service is safe by default (loopback, no client-chosen path) and does not block a listing behind a long insight request.

**Negative:**

- A server to run and protect; without a gateway, anything that can reach the port can use it. Request size is unbounded.
- The caller must configure long timeouts for an insight request (over 12 minutes with the defaults); there is no job-and-poll design, so a proxy with a shorter limit makes `insights=true` unusable.
- The body is copied to a temporary file per request, and every request builds its adapters again; the cost is small next to an analysis, and it keeps the use cases unchanged.
- A configuration error is a 422 although the caller did not cause it.
- 40 concurrent requests occupy the thread pool; more wait.
- The exit status of `serve` after a signal is platform specific.

## Affected Artifacts

- [ADR-0008] — the amendment of 2026-09-30 is completed by this decision.
- [ADR-0005] — its outcomes are mapped to HTTP status codes; its exit codes are unchanged.
- [ADR-0003] — the lock file is used from several threads of one process.
- [ADR-0006] — a second driving adapter in the composition-root layer; layers unchanged.
- [ADR-0009] and [ADR-0012] — the timeout bound of an insight request.
- [ADR-0011] — the JSON returned by the routes.
- [MIL-012] — tasks 1 to 3.

---

[UC-001]: ../use-cases/uc-001-analyze-hotel-bookings.md
[UC-003]: ../use-cases/uc-003-get-holiday-calendar.md
[UC-004]: ../use-cases/uc-004-get-available-llm-providers.md
[UC-005]: ../use-cases/uc-005-get-ai-insights-for-analyses.md
[ADR-0001]: ./adr-0001-input-json-contract.md
[ADR-0002]: ./adr-0002-result-json-contract.md
[ADR-0003]: ./adr-0003-jsonl-history-and-retention.md
[ADR-0004]: ./adr-0004-configuration-file.md
[ADR-0005]: ./adr-0005-delivery-and-failure-semantics.md
[ADR-0006]: ./adr-0006-architecture-and-invocation.md
[ADR-0008]: ./adr-0008-invocation-interface.md
[ADR-0009]: ./adr-0009-llm-provider-discovery-and-connection.md
[ADR-0011]: ./adr-0011-output-contracts-and-result-1-1.md
[ADR-0012]: ./adr-0012-configuration-extension.md
[MIL-012]: ../milestones/mil-012-conditional-http-api-fastapi.md
