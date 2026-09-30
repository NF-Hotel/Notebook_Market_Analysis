# ADR-0012: Configuration Extension

## Metadata
| Key | Value |
| --- | --- |
| ID | ADR-0012 |
| CrossReference | [UC-004], [UC-005], [ADR-0004], [ADR-0009] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-30 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-30 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |

---

## Context

[ADR-0004] fixes the configuration file `hotel_analysis.toml`, its lookup (`--config`, then `HOTEL_ANALYSIS_CONFIG`, then the working directory), that every key is optional with a default, and that an invalid value fails the run naming the key. The new capabilities need settings: the addresses of the two providers, a discovery timeout and a generation timeout, an optional provider and model, a local-only switch and the model temperature ([ADR-0009], [ADR-0010]). The forces are that everything must be safe or off by default (insights only with `--insights`, local providers only), that a typo must fail loudly as before, and that the retention behavior and the existing keys must not change. Options: add keys to the existing tables (the `analysis` table is about the analyses, not the model) or a new `[llm]` table (one place, unknown keys still detected per table).

## Decision

A new table `[llm]` extends the configuration file of [ADR-0004]; the existing keys, the lookup, the "every key is optional" rule, the ignoring of unknown keys with a notice, and the retention behavior are unchanged.

```toml
[llm]
ollama_url = "http://localhost:11434"     # base URL of Ollama
lmstudio_url = "http://localhost:1234"    # base URL of LM Studio
discovery_timeout_seconds = 2             # total time limit per provider, listing models
generation_timeout_seconds = 120          # total time limit per analysis, one model request
provider = ""                             # "" = automatic; or "ollama" or "lmstudio"
model = ""                                # "" = automatic; or a model name
allow_remote = false                      # true allows a non-loopback base URL
temperature = 0                           # 0.0 to 1.0
```

| Key | Default | Validation (an invalid value fails the command that uses the key, before any work and naming the key, and guesses nothing) |
| --- | --- | --- |
| `llm.ollama_url` | `http://localhost:11434` | non-empty string; scheme `http` or `https`; a host; loopback host (`localhost`, `127.0.0.1`, `::1`) unless `llm.allow_remote` is true ([ADR-0009]) |
| `llm.lmstudio_url` | `http://localhost:1234` | the same rules |
| `llm.discovery_timeout_seconds` | 2 | a number (integer or decimal) greater than 0; a boolean or string is invalid |
| `llm.generation_timeout_seconds` | 120 | a number greater than 0 |
| `llm.provider` | `""` (automatic) | one of `""`, `ollama`, `lmstudio` |
| `llm.model` | `""` (automatic) | a string; `""` means automatic; leading and trailing blanks are invalid |
| `llm.allow_remote` | `false` | a boolean; a string or number is invalid |
| `llm.temperature` | 0 | a number from 0.0 to 1.0 inclusive |

Rules:

- **Off or safe by default.** No key turns insights on: insights run only when the caller passes `--insights` ([ADR-0008]). With no `[llm]` table, both providers use the local defaults, discovery takes at most 4 s in total, and remote hosts are rejected.
- **Where the keys are used.** The `llm-providers` command and `analyze --insights` read all `[llm]` keys; `analyze` without `--insights` and `holidays` use none of them and check only that the file parses as TOML (and that `llm`, when present, is a table), so a bad `[llm]` value stops only the two commands that use it. The values in the table below are therefore validated by `llm-providers` and `analyze --insights` only; the keys of the other tables are validated as in [ADR-0004].
- **`llm.model` with an explicit `llm.provider`** is checked at run time against the provider's list ([ADR-0009]), not when the file is read, because reading the file must not contact a provider.
- **The two timeouts are total limits.** Each is a wall-clock deadline for the whole request, from connecting to the last byte of the answer, and not a per-operation limit ([ADR-0009]).
- **Unknown keys** in `[llm]` are ignored and listed in the existing notice `CONFIG_UNKNOWN_KEYS`, as `llm.<key>`; an unknown table is listed as before. `llm` must be a table.
- **Retention** (`history.retention`, `history.path`) and the analysis keys ([ADR-0007]) behave exactly as in [ADR-0004]; insights are part of the stored result and count as one result toward retention ([ADR-0003]).
- The file is read once at the start of each run, as before.

## Consequences

**Positive:**

- All new behavior is configurable in one table and is safe with an empty or missing file.
- Invalid values fail before any provider is contacted, with the key named, as for every other key, and only in the commands that use them.
- Existing files and callers are unaffected: nothing existing changes meaning, and unknown-key detection works for the new table.
- The local-only rule cannot be relaxed by accident; it needs one explicit key.

**Negative:**

- Eight more keys to document and test; a wrong `llm.model` is found only at run time, as `NO_MODEL`.
- A bad `[llm]` value is not noticed by `analyze` without `--insights` or by `holidays`; it shows only when `llm-providers` or `analyze --insights` runs. That keeps an unrelated command from stopping over a section it does not use.
- Values such as 2 s and 120 s are defaults chosen without measurement; slow hardware needs a larger `llm.generation_timeout_seconds`.
- Strings and booleans are rejected for numbers, so a value such as `"120"` fails instead of being converted.

## Affected Artifacts

- [ADR-0004] — extended with the `[llm]` table; its other rules are unchanged.
- [ADR-0009] — the addresses, timeouts, provider, model and remote switch it decides.
- [ADR-0010] — `llm.temperature` and `llm.generation_timeout_seconds`; `analysis.min_group_size` is used by its validator.
- [ADR-0008] — every subcommand accepts `--config`.
- [UC-004] — the timeout and defaults it leaves open.
- [UC-005] — the time limit and cost bound on model calls.
- [PP-001] — open issue OI-19 (limits on latency and cost are the two timeouts and the one request per analysis; confirmation by S01 pending).

---

[UC-004]: ../use-cases/uc-004-get-available-llm-providers.md
[UC-005]: ../use-cases/uc-005-get-ai-insights-for-analyses.md
[ADR-0004]: ./adr-0004-configuration-file.md
[ADR-0009]: ./adr-0009-llm-provider-discovery-and-connection.md
[PP-001]: ../project-plan.md
[ADR-0003]: ./adr-0003-jsonl-history-and-retention.md
[ADR-0007]: ./adr-0007-analysis-methods.md
[ADR-0008]: ./adr-0008-invocation-interface.md
[ADR-0010]: ./adr-0010-ai-insight-generation-and-guardrails.md
