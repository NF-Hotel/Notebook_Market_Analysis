# ADR-0011: Output Contracts and Result 1.1

## Metadata
| Key | Value |
| --- | --- |
| ID | ADR-0011 |
| CrossReference | [UC-003], [UC-004], [UC-005], [ADR-0002], [ADR-0010] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-30 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-30 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |

---

## Context

[ADR-0002] defines the result JSON, version 1.0, and says adding a field raises the MINOR part of `schema_version`. Three new outputs need a contract before code is written:

- the holiday listing of [UC-003];
- the provider listing of [UC-004];
- the AI insights of [UC-005], which the business case and [UC-002] keep inside the result and the history (open issue OI-16 in [PP-001], assumed, S02 to confirm).

Open issue OI-18 (which years the holiday listing takes, and whether only Cambodia) is settled here as an assumption for S02 to confirm. Forces: callers that ignore unknown fields must not break; results already in the history must stay readable; a result made without insights must not change at all; the machine-checkable schemas must be derivable from this text. Options for insights: a separate output linked by `result_id` (a second file to keep in step, and the history view would need both) or inside the result (one document, one history line, [ADR-0005]'s same-bytes rule intact). Options for versioning: always 1.1 (changes every result and every caller's expectation) or 1.1 only when insights were requested.

## Decision

The two listings are new documents with their own `kind`, and result schema version 1.1 adds insights to the result of [ADR-0002] as an additive MINOR change; version 1.1 is used only when insights were requested. A result in the history that was made under 1.0 stays valid and readable.

**Common rules of the listings.** Each listing is one JSON document, written as one compact line in UTF-8 that ends with a newline (the serialization style of the result). Field names are lowercase with underscores. Times are RFC 3339 UTC. The top-level fields are:

| Field | Meaning |
| --- | --- |
| `schema_version` | `"1.0"`, with the same MAJOR.MINOR rule as [ADR-0002] |
| `kind` | `holiday_calendar` or `llm_providers` |
| `status` | `completed`, or `failed` when the request was invalid |
| `generated_at` | when the document was produced |
| `notices` | list of `{code, message}`, as in the result |
| `error` | present only when `status` is `failed`: `{code, message}`; the codes are `INVALID_YEARS` (the `--years` value) and `CONFIGURATION_ERROR` ([ADR-0004], naming the key; for `holidays` only a file that does not parse, [ADR-0012]) |

A failed document has the `error` field and an empty `notices` list, has no `years` or `providers` field, and is never stored; it is delivered with exit code 2 ([ADR-0008]).

**Holiday listing** (`kind` `holiday_calendar`):

| Field | Meaning |
| --- | --- |
| `country` | always `"KH"` |
| `years` | one entry per requested year, ascending: `{year, status, holidays}` for `status` `available`, or `{year, status, reason}` for `status` `unavailable` |
| `years[].holidays` | list of `{date, name}` in date order; `date` is `YYYY-MM-DD`, `name` is the holiday's name as the calendar source gives it |
| `years[].reason` | `NO_CALENDAR_DATA`: the calendar returned no holiday for that year; nothing is invented |

A year is `available` when the calendar source returns at least one holiday for it. The notice `CALENDAR_SOURCE` names the source (the `holidays` package for `KH`, [ADR-0007]) and its installed version; when no year was requested the notice `DEFAULT_YEAR_USED` states the year used. The same years and the same calendar version give the same document, except `generated_at`.

**The `--years` value** (assumption for OI-18, S02 to confirm; Cambodia only, no country option):

- A single year: `2025`. A range: `2024-2026`, inclusive, first year not after the last. A comma list of single years: `2024,2026` (a range is not allowed inside a list).
- Omitted: the current year, taken from the clock port; the notice `DEFAULT_YEAR_USED` says which.
- A year is a whole number from 1900 to 2100. Duplicates are removed and the years are sorted.
- At most 30 years. More than 30, an empty value, a non-number, an out-of-range year, a reversed range or any other form gives a failed document with `INVALID_YEARS` and a message that names the problem.
- `holidays` reads the configuration file only to check that it parses as TOML, so that an unreadable file is reported the same way as in the other commands; it uses no key from it and does not validate the `[llm]` values, which only `llm-providers` and `analyze --insights` validate ([ADR-0012]).

**Provider listing** (`kind` `llm_providers`):

| Field | Meaning |
| --- | --- |
| `providers` | one or two entries (minimum 1, maximum 2), in the order `ollama`, `lmstudio`: `{provider, base_url, status, reason, models}` |
| `providers[].provider` | `ollama` or `lmstudio` |
| `providers[].base_url` | the configured base URL ([ADR-0012]) |
| `providers[].status` | `reachable` or `unreachable` ([ADR-0009]) |
| `providers[].reason` | `null` when reachable; else one of `CONNECTION_REFUSED`, `TIMEOUT`, `UNEXPECTED_ANSWER`, `NETWORK_ERROR` |
| `providers[].models` | list of `{name}`; empty when unreachable or when the provider lists none |

When no provider is reachable, `status` is still `completed` and the notice `NO_PROVIDER_REACHABLE` is added ([UC-004]). The document names only providers and models, never booking data.

**Result schema version 1.1.** Rule for `schema_version`: it is `"1.1"` if and only if the run asked for insights (`--insights`) and the result `status` is `completed` or `completed_with_warnings`; in every other case, including a failed result (which stays `"1.0"`) and every run without `--insights`, it is `"1.0"` and the result is identical in content and shape to the result of [ADR-0002]. Everything in [ADR-0002] is unchanged; 1.1 adds only:

- a top-level `insights`: `{requested, provider, model, prompt_version}`. `requested` is always `true` in a 1.1 result; `provider` and `model` are the selected ones or `null` when none could be selected ([ADR-0009]); `prompt_version` is the version of the prompt template ([ADR-0010]).
- in each entry of `analyses`, an `insight`:

| Field | Meaning |
| --- | --- |
| `status` | `available`, `unavailable` or `not_applicable` ([ADR-0010]) |
| `reason` | `null` when `available` or `not_applicable`; else `NO_PROVIDER`, `NO_MODEL`, `TIMEOUT`, `MODEL_ERROR`, `BAD_STRUCTURE` or `GUARDRAIL_REJECTED` |
| `label` | `"AI-generated"` when `available`, else `null` |
| `provider`, `model` | the provider and model that produced it, or were tried; `null` when none was selected or the insight is `not_applicable` |
| `generated_at` | when the accepted answer was received; `null` unless `available` |
| `executive_summary` | the accepted text, or `null` |
| `improvement_suggestions` | list of `{suggestion, evidence, sample_size}`; empty unless `available` |

Rules: an analysis that is `unavailable` has `insight.status` `not_applicable`. Text of a rejected or failed answer is never stored. When any available analysis has an `unavailable` insight the result `status` is `completed_with_warnings` and a notice `INSIGHTS_UNAVAILABLE` says how many; the result is still stored and delivered as a completed result ([ADR-0005]). All new fields are additive, so a caller that ignores unknown fields reads a 1.1 result as 1.0 ([ADR-0002]).

**Older results stay readable.** A 1.0 result in the history is not rewritten, and the history, retention and the history reader work unchanged ([ADR-0003]); mixed 1.0 and 1.1 lines are normal. A reader treats a missing `insight` as "saved without insights" ([UC-002]) and shows no error. The history viewer decides full support by the MAJOR part (as built), so 1.1 is fully supported and shows the insights; a MAJOR version it does not know is shown as far as it can be read, with the version stated ([UC-002]).

**JSON Schemas** are deliverables of the coding gateways, derived from this text and kept with the existing 1.0 result schema: the holiday listing 1.0 and the provider listing 1.0 (MIL-010), the result 1.1 (MIL-011). Tests validate produced documents against them.

## Consequences

**Positive:**

- Callers get three small, versioned, self-describing documents with fixed reason codes.
- A run without `--insights` is byte-for-byte what it was, so nothing that exists is disturbed.
- Insights live in the one result and the one history line, so the viewer, retention and the same-bytes delivery of [ADR-0005] need no change.
- Old results stay readable and mixed histories work without migration.

**Negative:**

- A caller must tolerate two version values, and the version says whether insights were asked for, not whether the caller's code understands them.
- A stored 1.1 result can contain model text that changes on every run, so two results of the same data differ; the analysis part stays deterministic.
- A failed result carries no insights or version 1.1 even if insights were requested; the caller learns that only from the error.
- Insights make each result larger (up to six summaries and thirty suggestions).
- The `years` rules (range 1900 to 2100, at most 30) are assumptions until S02 confirms OI-18; the calendar source may support fewer years, which then appear as `NO_CALENDAR_DATA`.

## Affected Artifacts

- [UC-003] — the holiday listing document and the `--years` rules.
- [UC-004] — the provider listing document.
- [UC-005] — the insight in each analysis and the top-level `insights`.
- [ADR-0002] — extended, not superseded: version 1.1 adds fields as a MINOR change; version 1.0 is unchanged. An amendment section in [ADR-0002] records that `completed_with_warnings` also covers unavailable insights.
- [ADR-0003] — 1.0 and 1.1 lines coexist in the history; retention is unchanged.
- [ADR-0005] — a completed result with unavailable insights is delivered as usual.
- [ADR-0008] — the listings are what the subcommands write to standard output.
- [ADR-0009] — the provider reasons.
- [ADR-0010] — the insight statuses, reasons and label.
- [UC-002] — the history view shows the insights and states the version it cannot fully display.
- [PP-001] — resolves OI-16 (insights inside the result, S02 to confirm) and OI-18 (years rules, S02 to confirm).

---

[UC-003]: ../use-cases/uc-003-get-holiday-calendar.md
[UC-004]: ../use-cases/uc-004-get-available-llm-providers.md
[UC-005]: ../use-cases/uc-005-get-ai-insights-for-analyses.md
[ADR-0002]: ./adr-0002-result-json-contract.md
[ADR-0010]: ./adr-0010-ai-insight-generation-and-guardrails.md
[PP-001]: ../project-plan.md
[UC-002]: ../use-cases/uc-002-review-analysis-history.md
[ADR-0003]: ./adr-0003-jsonl-history-and-retention.md
[ADR-0004]: ./adr-0004-configuration-file.md
[ADR-0005]: ./adr-0005-delivery-and-failure-semantics.md
[ADR-0007]: ./adr-0007-analysis-methods.md
[ADR-0008]: ./adr-0008-invocation-interface.md
[ADR-0009]: ./adr-0009-llm-provider-discovery-and-connection.md
[ADR-0012]: ./adr-0012-configuration-extension.md
