# ADR-0009: LLM Provider Discovery and Connection

## Metadata
| Key | Value |
| --- | --- |
| ID | ADR-0009 |
| CrossReference | [UC-004], [UC-005], [ADR-0008] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-30 | Proposed | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-30 | Proposed | Jens Tirsvad Nielsen | Team2 (S04) |

---

## Context

[UC-004] lists the reachable language-model providers, Ollama and LM Studio, and [UC-005] needs one provider and one model to produce insights. The use cases leave open how a provider is found and queried, which timeouts apply, which model is chosen when a provider offers several, and whether models may run remotely (open issues OI-13 and OI-14 in [PP-001]). The forces are:

- Discovery must be a quick, read-only check that never starts an analysis and never sends booking data ([UC-004] business rules).
- One slow or absent provider must not block the answer or fail the request.
- Only aggregate findings go to a model ([ADR-0010]); even so, S03's interest is that nothing leaves the machine unless that is chosen deliberately.
- The project keeps its dependencies few ([ADR-0006]); the standard library can make plain HTTP calls.
- Both providers are used through their documented HTTP interfaces: Ollama's own interface and LM Studio's OpenAI-compatible interface.

Options for the HTTP client: a provider SDK or `requests`/`httpx` (new runtime dependencies, one more thing to keep current) or the standard library `urllib` (no dependency, enough for four fixed requests). Options for model choice: always require configuration (safe but forces setup before the first insight) or fall back to a fixed rule (works out of the box, may pick an unsuitable model).

## Decision

Ollama and LM Studio are queried over HTTP with the Python standard library (`urllib`); no dependency is added. Discovery is read-only, short and never starts an analysis, and only local providers are used unless configuration allows otherwise.

| | Ollama | LM Studio |
| --- | --- | --- |
| Configuration key ([ADR-0012]) | `llm.ollama_url` | `llm.lmstudio_url` |
| Default base URL | `http://localhost:11434` | `http://localhost:1234` |
| List models | `GET /api/tags`; the model names are `models[].name` | `GET /v1/models` (OpenAI-compatible); the model names are `data[].id` |
| Generate | `POST /api/chat` with `stream` false, the messages, `format` `json` and the temperature in `options`; the text is `message.content` | `POST /v1/chat/completions` with the messages and the temperature; the text is `choices[0].message.content` |

**Discovery** (used by `llm-providers` and by `analyze --insights` before any model call):

1. Both providers are checked, always in the order `ollama`, `lmstudio`, one after the other. Each check is one list request with the total deadline `llm.discovery_timeout_seconds` (default 2 s), so the whole check takes at most twice that time (see Deadlines below).
2. A provider is `reachable` when the list request answers with HTTP 200 and a body in the expected structure; its models are the names listed (possibly none).
3. A provider is `unreachable` with one reason code: `CONNECTION_REFUSED` (nothing is listening), `TIMEOUT` (no complete answer within the discovery deadline), `UNEXPECTED_ANSWER` (an HTTP error status or a body not in the expected structure) or `NETWORK_ERROR` (any other failure to connect, for example a name that does not resolve).
4. An unreachable provider is a normal entry in the listing; the request still succeeds ([UC-004]). Discovery sends no booking data, asks no model to generate text and writes nothing.

**Local only.** The base URL is parsed, and its host name (the part without port and, for `[::1]`, without the brackets) must be one of `localhost`, `127.0.0.1` or `::1`; the host is compared as text after parsing and is not resolved, and the scheme must be `http` or `https`. A text that does not parse to a scheme and a host name is invalid. A URL with any other host is rejected as a configuration error naming the key (for example `llm.ollama_url`) before any connection is made, unless `llm.allow_remote` is `true` (default `false`). This makes remote use a deliberate choice; it resolves the assumption of OI-14 as local only and leaves the decision to allow remote models, and to let aggregate findings leave the machine, to S03.

**Model choice** for insights, in this order:

1. If `llm.provider` and `llm.model` are both set, that provider must be reachable and list that model.
2. If only `llm.model` is set, the first reachable provider in the order `ollama`, `lmstudio` that lists it is used.
3. If only `llm.provider` is set, that provider is used, with the first model it lists.
4. If neither is set, the first reachable provider in the order `ollama`, `lmstudio` is used, with the first model it lists.

Reason codes: `NO_PROVIDER` means no provider can be reached (none is reachable, or the provider named by `llm.provider` is unreachable). `NO_MODEL` means a provider is reachable but the configured or automatic model is not offered (it lists no model, or does not list the configured `llm.model`). In both cases no model is contacted, the analysis is unaffected, and the reason is reported for every available analysis ([ADR-0010], [ADR-0011]). The default rule has no size or quality test, because the project has no acceptance rule for models (OI-13 stays partly open: the fixed order is the assumption, and S01 may add a rule later); the first listed model may be one that cannot follow the required answer structure, in which case the guardrails of [ADR-0010] reject its answers.

**Generation** is one request per available analysis, sequential, each with the total deadline `llm.generation_timeout_seconds` (default 120 s) and the temperature `llm.temperature` (default 0). A request is not retried. A refused connection, an HTTP error, an unusable body or an exception during generation gives `MODEL_ERROR`; exceeding the deadline gives `TIMEOUT`.

**Deadlines.** The timeout of `urllib` applies to each socket operation (connect, one read), not to the whole request, so a slow provider that keeps sending a few bytes would never trip it. The adapter therefore takes the start time, sets the socket timeout to the time that remains, reads the answer in chunks and checks the deadline before each read; when the deadline has passed it stops and reports `TIMEOUT`. The deadline covers connecting, sending and reading the whole answer, so the maximum durations stated elsewhere (2 s per provider, 120 s per analysis) are total limits, plus a small overhead. A name lookup is not covered by the socket timeout; with the loopback hosts allowed by default it takes no measurable time, and with `llm.allow_remote` a slow name lookup can add to the deadline. Text that the model returns is untrusted data ([ADR-0010]).

## Consequences

**Positive:**

- Discovery is quick, bounded and safe: two short read-only requests, no booking data, and an absent provider is information, not an error.
- No new dependency; the same code path serves the listing and the choice made for insights, so they cannot disagree.
- Insights work with no configuration when a local provider is running, and stay off until `--insights` is given.
- Remote models cannot be used by accident: the default rejects a non-loopback address.

**Negative:**

- The default model choice is arbitrary (the first listed model); it may be unsuitable (for example an embedding model), so users who care set `llm.model`. OI-13 is only partly resolved.
- `urllib` has no retries, connection pooling or streaming; that is acceptable for four request kinds but would have to be revisited for streamed answers.
- A local provider that is slow to start may be reported unreachable within the 2 s discovery deadline, and a large model on modest hardware may exceed 120 s and give `TIMEOUT`.
- The chunked read and the deadline check are code the project writes itself; the contract tests of the coding gateway must cover a provider that answers slowly in small pieces.
- Both providers' interfaces are external and can change; the `UNEXPECTED_ANSWER` reason and the contract tests of the coding gateway are the safety net.
- With `llm.allow_remote` true, aggregate findings leave the machine; only S03 can accept that, and this ADR does not.

## Affected Artifacts

- [UC-004] — the checks, reasons and timeout that the use case leaves to the design gateway.
- [UC-005] — steps 2 and 4 (selecting a provider and model, calling it) and extensions 2a and 4a.
- [ADR-0008] — the `llm-providers` subcommand and `--insights` use this discovery.
- [ADR-0010] — the reasons `NO_PROVIDER`, `NO_MODEL`, `TIMEOUT` and `MODEL_ERROR`, and the untrusted model text.
- [ADR-0011] — the JSON of the provider listing.
- [ADR-0012] — the keys `llm.ollama_url`, `llm.lmstudio_url`, `llm.discovery_timeout_seconds`, `llm.generation_timeout_seconds`, `llm.provider`, `llm.model`, `llm.allow_remote` and `llm.temperature`.
- [PP-001] — OI-13 (partly resolved) and OI-14 (proposed as local only, S03 to confirm).

---

[UC-004]: ../use-cases/uc-004-get-available-llm-providers.md
[UC-005]: ../use-cases/uc-005-get-ai-insights-for-analyses.md
[ADR-0008]: ./adr-0008-invocation-interface.md
[PP-001]: ../project-plan.md
[ADR-0006]: ./adr-0006-architecture-and-invocation.md
[ADR-0010]: ./adr-0010-ai-insight-generation-and-guardrails.md
[ADR-0011]: ./adr-0011-output-contracts-and-result-1-1.md
[ADR-0012]: ./adr-0012-configuration-extension.md
