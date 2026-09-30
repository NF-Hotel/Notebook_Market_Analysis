# Operation Contracts

## Metadata
| Key | Value |
| --- | --- |
| ID | OC-001 |
| CrossReference | [SSD-001], [DM-001], [SD-001], [UC-003], [UC-004], [UC-005] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | TBD (S04 not yet named) |
| 2026-09-30 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-30 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-30 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-30 | Proposed | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-30 | Proposed | Jens Tirsvad Nielsen | Team2 (S04) |

---

One contract per system operation (message) of [SSD-001]: the built system has one for [UC-001] and three for [UC-002]; the Designed Additions at the end add one contract each for [UC-003] and [UC-004], and one change block each for `analyzeBookings` ([UC-005]) and `selectResult` (the insight display of [UC-002]), so the design has six contracts in all: the built four, of which two are changed, and two new ones (`getHolidayCalendar`, `getLlmProviders`). The built contracts describe the built system. Preconditions and postconditions use the concept names of [DM-001] (Booking Submission, Booking Record, Data Quality Summary, Analysis, Analysis Result, Result History, Retention Policy); they state what is true, not how it is achieved. Where the built behavior differs from an earlier decision, the difference is listed in the section **As-Built Deviations** at the end.

**Scope note (MIL-009, 2026-09-30).** Everything above the heading **Designed Additions (MIL-009, not yet built)** at the end of this document describes the built system and is unchanged. That last part is a design made before the code: the contracts of `getHolidayCalendar` and `getLlmProviders`, the Designed change to `analyzeBookings` (the insights) and the Designed change to `selectResult` (the insight display). They are implemented in MIL-010 and MIL-011.

The operation `analyzeBookings` is realized in the code by `AnalyzeBookings.run(input_path: Path | None, config_path: Path | None) -> AnalyzeOutcome` in `application/analyze_bookings.py`, called by `main(...) -> int` in `infrastructure/cli.py`, which maps the outcome status to the exit code (0, 2, 3, 4).

## UC-001 Analyze Hotel Bookings

### Contract: analyzeBookings

| Item | Value |
| --- | --- |
| Operation | `analyzeBookings(inputFile: Path \| None, configFile: Path \| None): (resultJson: str, exitCode: int)` where `exitCode` is 0, 2, 3 or 4 and `resultJson` is absent when `exitCode` is 3 or 4 |
| Traces to | UC-001 message 1 (`analyzeBookings`) in [SSD-001], all diagrams 1.1 to 1.5 |
| Domain Model concepts | Booking Submission, Booking Record, Data Quality Summary, Analysis (Lead Time Analysis, Holiday Analysis, Seasonality Analysis, Cancellation Analysis, Room Value Analysis, Guest Mix Analysis), Analysis Result, Result History, Retention Policy; associations supplies, is answered by, includes, contains, retains, is limited by ([DM-001]) |

**Preconditions**

- A Booking Submission source exists: either `inputFile` names a JSON file whose top level is a non-empty array of Booking Records, or `inputFile` is absent, the configured environment is `development` and the development sample file exists.
- At least one Booking Record of the submission holds a valid value in at least one field.
- The configuration is valid: when a configuration file exists it is valid TOML, `environment` is `production` or `development`, and the Retention Policy limit is an integer of at least 1; when no configuration file exists the defaults apply (environment `production`, Retention Policy limit 10, Result History at `output/analysis_history.jsonl`).
- The Result History location can be created and written, and its lock can be taken within the wait limit.
- Standard output of the process can be written.

**Postconditions**

Main success (exit code 0):

- A Booking Submission instance was created, with source set to `supplied` (or `development_sample` when the fallback was used) and reference set to the file name; it supplies its Booking Records.
- A Data Quality Summary instance was created with the record count, the date coverage, the duplicate booking ID count, and the missing and invalid values per field.
- One Analysis instance per kind of Analysis was created; each Analysis whose required fields are not usable has availability set to unavailable and unavailable reason set to the missing fields, and no values were estimated.
- An Analysis Result instance was created with a new result identifier, the format version, the generated time, and status set to `completed`, or to `completed_with_warnings` when an Analysis is unavailable, a Booking Record has an invalid value, or unknown configuration keys were ignored.
- The Analysis Result was associated with the Booking Submission (is answered by), with the Data Quality Summary (includes) and with its Analyses (contains); it holds no Booking Record.
- The Analysis Result was associated with the Result History (retains) as its newest retained result.
- The Result History no longer retains its oldest Analysis Results beyond the Retention Policy limit; results that were not beyond the limit and lines that are not valid results were not removed.
- The Calling system received the serialized Analysis Result on standard output, identical to the retained one, and the exit code 0.
- When the configuration file was missing, the Analysis Result carries the notice `CONFIG_FILE_NOT_FOUND`; when the fallback was used it carries the notice `DEVELOPMENT_SAMPLE_USED`.

**Exceptions**

| Condition (failing precondition) | Outcome |
| --- | --- |
| The configuration file cannot be read or parsed, `environment` is not `production` or `development`, or another configuration value (retention limit, history path, holiday windows, minimum group size) is invalid; error code `CONFIGURATION_ERROR` | A `failed` Analysis Result instance was created with the error, no Booking Submission, no Data Quality Summary and no Analysis; it was not associated with the Result History; the Calling system received it on standard output and exit code 2 |
| No `inputFile` and the environment is not `development`; error code `NO_INPUT` (see AD-1) | As above: `failed` Analysis Result, Result History unchanged, exit code 2 |
| `inputFile` does not exist (`INPUT_NOT_FOUND`), cannot be read (`INPUT_UNREADABLE`), is not valid JSON (`INPUT_INVALID_JSON`), has a top level that is not an array (`INPUT_NOT_ARRAY`), is an empty array (`INPUT_EMPTY`), or holds an item that is not an object (`INPUT_RECORD_NOT_OBJECT`); for the development sample, `INPUT_INVALID_CSV` or `INPUT_EMPTY` | As above: `failed` Analysis Result, Result History unchanged, exit code 2 |
| No Booking Record holds a valid value in any field (`NO_VALID_RECORDS`) | As above: `failed` Analysis Result, Result History unchanged, exit code 2 |
| The Result History cannot be extended: its directory cannot be created, its lock cannot be taken within the wait limit, or the append fails | The Analysis Result was not associated with the Result History and the Result History is unchanged; no result was delivered; the message on standard error says the history was not updated; exit code 3 |
| The Retention Policy could not be applied after the append (retention rewrite fails) | The Analysis Result stays associated with the Result History, which may retain more results than the limit; no result was delivered; the message on standard error says the result was appended but retention failed; exit code 3 |
| Standard output cannot be written for a completed Analysis Result | The Analysis Result stays associated with the Result History; the Calling system received no result; the message on standard error names the result identifier and says it was saved but not delivered; exit code 4 |
| Standard output cannot be written for a `failed` Analysis Result (see AD-2) | Nothing was stored; the Calling system received no result; the message on standard error names the result identifier, the error code and the delivery error; exit code 4 |

## UC-002 Review Analysis History

The three operations of [UC-002] read only. Each postcondition states that the Result History and every Analysis Result are unchanged, because "viewing never modifies or removes history entries" ([UC-002] business rules). The state that does change is the session state of the notebook (the current listing, the current selection and the current option), which is not a Domain Model concept and is named as such.

### Contract: listRetainedResults

| Item | Value |
| --- | --- |
| Operation | `listRetainedResults(): HistoryListing` where `HistoryListing` holds the list of retained Analysis Results newest first (each with result identifier, generated time, status, input source, record count, schema version), an optional empty message, an optional malformed-lines message and an optional error message. Realized by `load_history(working_directory: Path, environ: Mapping[str, str]) -> LoadedHistory` in `interface/history_source.py` and `build_history_view(readout: HistoryReadout) -> HistoryView` in `interface/history_view.py`. |
| Traces to | UC-002 message 1 (`listRetainedResults`) in [SSD-001], diagrams 2.1 to 2.4 |
| Domain Model concepts | Result History, Retention Policy, Analysis Result ([DM-001]) |

**Preconditions**

- The location of the Result History can be determined from the configuration (the configuration file in the working directory, or the file named by the environment variable `HOTEL_ANALYSIS_CONFIG`; the default location when no file exists).
- The Result History either does not exist yet, or holds lines of which the valid ones are Analysis Results retained under the Retention Policy.

**Postconditions**

- The Result History and its Analysis Results are unchanged (no instance was created, associated or removed).
- The session's current listing was set to the valid retained Analysis Results of the Result History, ordered by generated time, newest first.
- When the Result History has no valid Analysis Result, the session's current listing is empty and the empty message states that there are no saved results yet.
- When the Result History holds lines that are not valid results, the session's malformed count was set to their number and a message states how many lines were skipped; the readable results are listed.

**Exceptions**

| Condition (failing precondition) | Outcome |
| --- | --- |
| The Result History does not exist or is empty (nothing retained yet) | Empty listing and the message that there are no saved results yet (diagram 2.2); not an error |
| The configuration file is invalid, so the location of the Result History cannot be determined | Empty listing, the configuration error message and the no-saved-results message; the location is not shown (diagram 2.3) |
| The Result History exists but cannot be read | Empty listing, the read error message naming the file and the no-saved-results message (diagram 2.3) |
| The Result History holds lines that are not valid results | Readable results listed and the count message shown (diagram 2.4); no lines were removed |

### Contract: selectResult

| Item | Value |
| --- | --- |
| Operation | `selectResult(resultLabel: str): SelectedResultView` where `SelectedResultView` holds the Data Quality Summary view, the limitation notes, the default views of the Analyses and an optional schema-version notice. Realized by the picker cell of `interface/history_notebook.py` and `version_notice(result: Result) -> str \| None` in `interface/history_view.py`. |
| Traces to | UC-002 message 2 (`selectResult`) in [SSD-001], diagrams 2.1 and 2.5 |
| Domain Model concepts | Analysis Result, Data Quality Summary, Analysis, Group Statistic, Result History ([DM-001]) |

**Preconditions**

- The current listing holds at least one retained Analysis Result.
- `resultLabel` is the label of exactly one entry of the current listing (the picker offers only these labels).

**Postconditions**

- The Result History and its Analysis Results are unchanged.
- The session's current selection was set to the Analysis Result named by `resultLabel`.
- The Data Quality Summary of the selected Analysis Result is shown with its record count, date coverage, duplicate booking IDs, and missing and invalid values.
- Each Analysis of the selected Analysis Result is shown with its counts (Group Statistic numerator and denominator, small-sample flag) and limitation notes; an Analysis with availability unavailable is shown as unavailable with its unavailable reason; room value figures are labeled as estimates.
- When the schema version of the selected Analysis Result does not have the supported major version, a notice names that version and the session shows only the parts that can be read.

**Exceptions**

| Condition (failing precondition) | Outcome |
| --- | --- |
| The current listing is empty | No picker is offered and no selection is set; nothing is shown beyond the listing messages |
| The selected Analysis Result has a schema version that is missing or of another major version (see diagram 2.5) | The readable parts are shown with the version notice; the selection is set; not a failure |
| An Analysis is missing or unreadable inside the selected Analysis Result | That Analysis is shown as unavailable; the other views are shown |

### Contract: chooseViewOption

| Item | Value |
| --- | --- |
| Operation | `chooseViewOption(analysis: str, option: str): AnalysisView` where `analysis` is one of `lead_time`, `seasonality`, `holidays`, `cancellations`, `guest_mix` and `AnalysisView` is that Analysis with its limitation notes for the chosen option. Realized by the option dropdown cells of `interface/history_notebook.py`, for example `holiday_window` for holidays and the render functions of `interface/marimo_render.py`. |
| Traces to | UC-002 message 3 (`chooseViewOption`) in [SSD-001], diagram 2.1 |
| Domain Model concepts | Analysis (Lead Time Analysis, Seasonality Analysis, Holiday Analysis, Cancellation Analysis, Guest Mix Analysis), Group Statistic, Holiday Window, Analysis Result ([DM-001]) |

**Preconditions**

- The session's current selection holds an Analysis Result.
- The Analysis named by `analysis` is available in that Analysis Result and offers a list of options, and `option` is one value of that list.

**Postconditions**

- The Result History and the selected Analysis Result are unchanged.
- The session's current option for the Analysis named by `analysis` was set to `option`.
- The view of that Analysis is shown for `option` (for example the Group Statistics of the Holiday Window of the chosen size) together with its limitation notes; no other Analysis view and no selection changed.

**Exceptions**

| Condition (failing precondition) | Outcome |
| --- | --- |
| No Analysis Result is selected | No option list is offered and nothing is shown |
| The Analysis is unavailable in the selected Analysis Result or offers no options | No option list is offered for it; the view shows the unavailable reason or the single default view |

## As-Built Deviations

Update 2026-09-30: UC-001 now states AD-1 and OD-1; AD-2 is amended in ADR-0005 and AD-3 in ADR-0003. The contracts are unchanged.

The differences of [SSD-001] (AD-1 to AD-5) apply to these contracts; the ones that change a contract are repeated here. Each was raised as an open issue in the project plan (OI-21 to OI-27) through the MIL-007 review; AD-1 and OD-1 are resolved in UC-001, AD-2 in ADR-0005, AD-3 in ADR-0003, and OD-2 is resolved by the DM-001 revision of MIL-009 task 1 (OI-25): the Analysis Result holds a copy of the input description and the association was removed.

| ID | Earlier decision | As built | Effect on the contracts |
| --- | --- | --- | --- |
| AD-1 | [UC-001] extension 1a.2: no input outside development stops "without a result". | A `failed` Analysis Result with `NO_INPUT` is delivered, exit code 2 ([ADR-0005]). | Exception rows of `analyzeBookings` deliver a `failed` result. |
| AD-2 | [ADR-0005]: exit code 4 leaves the result saved. | For a `failed` result that cannot be delivered, exit code 4 and nothing is stored. | Last exception row of `analyzeBookings`. |
| AD-3 | [ADR-0003]: "latest" means later in the file. | The notebook orders the list by generated time. | Postcondition of `listRetainedResults`. |
| OD-1 | [UC-001] has an extension for a history that cannot be written (6a) but none for a failure of retention (step 7) or for a lock that cannot be taken. | Retention failure and lock timeout end the run with exit code 3 ([ADR-0003], [ADR-0005]); after a retention failure the appended result stays. | Two exception rows of `analyzeBookings` have no use case extension. |
| OD-2 | [DM-001] associates an Analysis Result with the Booking Submission it answers ("is answered by"). | As built the result holds a copy of the input metadata (`ResultInput`: source, reference, record count, content hash) and no link to a Booking Submission object; the postconditions of `analyzeBookings` that name this association are satisfied by that copy (SD-7, DD-5). | Postconditions of `analyzeBookings` that create the association. |

## Designed Additions (MIL-009, not yet built)

Design made before the code (gateway MIL-009, task 8). The contracts above describe the built system and stay true. This part adds the contracts of the system operations that [SSD-001] designs for [UC-003], [UC-004] and [UC-005] and the revised return of `selectResult` for [UC-002]; they are implemented in MIL-010 and MIL-011 and are marked `Designed` in every heading. They use the concept names of the revised [DM-001] (Language Model Provider, Provider Status, Language Model, AI Insight, Executive Summary, Improvement Suggestion, Holiday Calendar Listing, Holiday Calendar Year, Holiday, LLM Provider Listing, Notice) besides the built ones. The reason codes are those of [ADR-0009], [ADR-0010] and [ADR-0011].

One contract per operation, traced to its SSD messages:

| SSD-001 message | Contract in this document | Where |
| --- | --- | --- |
| UC-003 message 1 (`getHolidayCalendar`) | `getHolidayCalendar` | new contract below (Designed) |
| UC-004 message 1 (`getLlmProviders`) | `getLlmProviders` | new contract below (Designed) |
| UC-005 message 1 (`analyzeBookings` with `insights`, the extension of UC-001 message 1) | `analyzeBookings` | the built contract above plus the Designed change block below; UC-005 message 1 is the same operation with one more argument, so there is one contract, not two |
| UC-002 message 2 (`selectResult`, revised return) | `selectResult` | the built contract above plus the Designed change block below |

The operations are realized in the code by the planned use cases `ListHolidays.run(years: str | None, config_path: Path | None) -> ListingOutcome` and `ListLlmProviders.run(config_path: Path | None) -> ListingOutcome` in `application`, called by the new subcommands `holidays` and `llm-providers` of `main(...) -> int` in `infrastructure/cli.py`, and by `AnalyzeBookings.run(input_path, config_path, insights)` with the planned `GenerateInsights` (see [DCD-001] Designed Additions).

## UC-003 Get Holiday Calendar (Designed)

### Contract: getHolidayCalendar (Designed)

| Item | Value |
| --- | --- |
| Operation | `getHolidayCalendar(years: str \| None, configFile: Path \| None): (holidayListingJson: str, exitCode: int)` where `exitCode` is 0, 2 or 4 and `holidayListingJson` is a holiday listing (exit code 0), a failed listing (exit code 2), or absent (exit code 4) |
| Traces to | UC-003 message 1 (`getHolidayCalendar`) in [SSD-001], diagrams 3.1 to 3.4 |
| Domain Model concepts | Holiday Calendar Listing, Holiday Calendar Year, Holiday, Notice; associations covers, lists, carries ([DM-001]). Analysis Result, Analysis and Result History are named only to state that they are unchanged |

**Preconditions**

- `years` is absent, or is a single year (`2025`), a range of years (`2024-2026`, the first year not after the last) or a comma list of single years (`2024,2026`), with every year a whole number from 1900 to 2100 and at most 30 different years ([ADR-0011]).
- The configuration is valid: when a configuration file exists it is valid TOML; when none exists the defaults apply. `holidays` uses no configuration value and validates only that the file parses as TOML; the `[llm]` values are validated only by `llm-providers` and `analyze --insights` ([ADR-0011], [ADR-0012]).
- The Cambodian holiday calendar source (the `holidays` package for `KH`) can be read. A year that the source does not support is not a failure of this precondition; see the exceptions.
- Standard output of the process can be written.

**Postconditions**

Main success (exit code 0):

- A Holiday Calendar Listing instance was created with country `KH` and the generated time.
- A Holiday Calendar Year instance was created for each requested year, ascending and without duplicates, and associated with the Holiday Calendar Listing (covers); the requested years are the years selected by `years`, or the current year when `years` is absent.
- Each Holiday Calendar Year for which the calendar source supplies at least one Holiday has availability set to available and is associated (lists) with exactly the Holiday instances of that year, in date order, each with its date and name.
- Each other Holiday Calendar Year has availability set to unavailable and unavailable reason set to `NO_CALENDAR_DATA`, and lists no Holiday; no Holiday was created that the calendar source does not supply.
- The Holiday Calendar Listing carries the notice `CALENDAR_SOURCE` naming the calendar source and its version, and, when `years` was absent, the notice `DEFAULT_YEAR_USED` naming the year used.
- No Booking Submission, Booking Record, Data Quality Summary, Analysis, Analysis Result or AI Insight instance was created, no analysis ran, and the Result History is unchanged; the Holiday Calendar Listing was not associated with the Result History.
- The Calling system received the serialized Holiday Calendar Listing on standard output and the exit code 0.

**Exceptions**

| Condition (failing precondition) | Outcome |
| --- | --- |
| `years` is empty, not a number, outside 1900 to 2100, a reversed range, a range inside a list, or names more than 30 years; error code `INVALID_YEARS` | No Holiday Calendar Listing was created; the Calling system received a failed listing (status failed, the error code and a message that names the problem, no years) on standard output and exit code 2; the Result History is unchanged |
| The configuration file cannot be read or parsed; error code `CONFIGURATION_ERROR` (the `[llm]` values are not validated by this operation) | As above: failed listing, exit code 2 |
| The calendar source returns no Holiday for a requested year, including a year it does not support (the `holidays` package returns no holidays for an unsupported year instead of failing) | Not a failure: that Holiday Calendar Year is unavailable with `NO_CALENDAR_DATA` and lists no Holiday (diagram 3.2); the other years are unaffected; exit code 0 |
| Standard output cannot be written | Nothing was stored; the Calling system received no document; the message on standard error names the delivery error; exit code 4; a retry has no side effect |

## UC-004 Get Available LLM Providers (Designed)

### Contract: getLlmProviders (Designed)

| Item | Value |
| --- | --- |
| Operation | `getLlmProviders(configFile: Path \| None): (providerListingJson: str, exitCode: int)` where `exitCode` is 0, 2 or 4 and `providerListingJson` is a provider listing (exit code 0), a failed listing (exit code 2), or absent (exit code 4) |
| Traces to | UC-004 message 1 (`getLlmProviders`) in [SSD-001], diagrams 4.1 to 4.4 |
| Domain Model concepts | LLM Provider Listing, Language Model Provider, Provider Status, Language Model, Notice; associations covers, reports, is offered by, carries ([DM-001]). The listing is an answer to a request and is not stored |

**Preconditions**

- The configuration is valid: when a configuration file exists it is valid TOML and every value is valid, that is the two provider addresses have the scheme `http` or `https` and a parsed host name that is a loopback host (`localhost`, `127.0.0.1`, `::1`) unless `llm.allow_remote` is true, the timeouts are numbers greater than 0, and the other `[llm]` values are valid ([ADR-0009], [ADR-0012]); when none exists the defaults apply (Ollama at `http://localhost:11434`, LM Studio at `http://localhost:1234`, discovery timeout 2 seconds).
- Standard output of the process can be written.
- No provider needs to be running: reachability is what the operation reports, not a precondition.

**Postconditions**

Main success (exit code 0):

- One LLM Provider Listing instance was created with the generated time and associated (covers, reports) with the Language Model Provider and Provider Status instances below.
- One Language Model Provider instance was created for each of the two supported providers, `ollama` then `lmstudio`, each with its name and its configured address.
- Each Language Model Provider was associated (reports) with one Provider Status instance. A provider that answered the check within the discovery deadline has reachable set to true, and each model it lists is a Language Model instance associated with it (is offered by); a provider that listed none is reachable with no Language Model. A provider that did not answer has reachable set to false and reason set to one of `CONNECTION_REFUSED`, `TIMEOUT`, `UNEXPECTED_ANSWER` or `NETWORK_ERROR`, and has no Language Model.
- When no Provider Status is reachable the provider listing carries the notice `NO_PROVIDER_REACHABLE`; the operation still succeeds.
- No model was asked to generate text, no Booking Record or other booking data was sent to any provider, and no Booking Submission, Analysis, Analysis Result or AI Insight instance was created; the Result History is unchanged and the provider listing was not associated with it.
- The Calling system received the serialized provider listing on standard output, naming only providers and models, and the exit code 0.

**Exceptions**

| Condition (failing precondition) | Outcome |
| --- | --- |
| The configuration file cannot be read or parsed, or a value is invalid, including a provider address whose host is not a loopback host while `llm.allow_remote` is false; error code `CONFIGURATION_ERROR` naming the key (for example `llm.ollama_url`) | No provider was contacted and no instance was created; the Calling system received a failed listing (status failed, the error, no providers) on standard output and exit code 2; the Result History is unchanged |
| A provider is not running, does not answer completely within the discovery deadline, answers with an error status or an unexpected body, or cannot be connected to | Not a failure: its Provider Status is unreachable with the reason (diagrams 4.1 and 4.2); the other provider is still checked; exit code 0 |
| Standard output cannot be written | Nothing was stored; the Calling system received no document; the message on standard error names the delivery error; exit code 4 |

## UC-005 Get AI Insights for Analyses (Designed)

UC-005 message 1 is UC-001 message 1 with the argument `insights`; the contract is `analyzeBookings` of [UC-001] above. The block below is the Designed change to that contract: it does not alter a word of the built contract and it is valid only when `insights` is true, except the first postcondition which fixes the default.

### Designed change to the contract: analyzeBookings (Designed, MIL-011)

| Item | Value |
| --- | --- |
| Operation | `analyzeBookings(inputFile: Path \| None, configFile: Path \| None, insights: bool = false): (resultJson: str, exitCode: int)` with `exitCode` 0, 2, 3 or 4 as above |
| Traces to | UC-005 message 1 (the extension of UC-001 message 1) in [SSD-001], diagrams 5.1 to 5.5; the built diagrams 1.1 to 1.5 keep applying |
| Domain Model concepts (added) | AI Insight, Executive Summary, Improvement Suggestion, Language Model, Language Model Provider, Provider Status; associations has, contains, is produced by, is offered by, reports ([DM-001]) |

**Added preconditions** (all of the built preconditions still apply)

- When `insights` is true, the `[llm]` configuration values are valid (the same rules as for `getLlmProviders`); when `insights` is false they are neither validated nor used ([ADR-0012]).
- A language model provider need not be reachable: the absence of one is an exception with a defined outcome, not a failed precondition of the operation.

**Added postconditions**

Insights not requested (`insights` false, the default): every postcondition above holds unchanged; no AI Insight instance was created, no provider was contacted, and the Analysis Result has format version 1.0 and is identical in content and shape to a result made before this change.

Insights requested (`insights` true) and the Analysis Result completed (exit code 0, or 3 or 4 as above):

- One AI Insight instance was created for each Analysis of the Analysis Result and associated with it (has); the Analysis instances and their findings are identical to those of a run without insights.
- An AI Insight has exactly one status. It is available when the answer of the language model passed the checks of [ADR-0010]; unavailable with a reason (`NO_PROVIDER`, `NO_MODEL`, `TIMEOUT`, `MODEL_ERROR`, `BAD_STRUCTURE` or `GUARDRAIL_REJECTED`) when it could not be produced or the answer was rejected; not applicable when its Analysis is unavailable.
- An available AI Insight has its label set to AI-generated, its generated time set, an Executive Summary instance associated with it (contains) and one to five Improvement Suggestion instances associated with it (contains), and is associated with the Language Model that produced it (is produced by; the Analysis Result keeps the provider name and the model name as text).
- Each Improvement Suggestion has text worded as a hypothesis, evidence, and a sample size that is a whole number of at least 1 which appears in the findings of the Analysis; no Executive Summary or Improvement Suggestion contains a causal word of [ADR-0007], a promise or forecast of earnings, or a percentage or amount that is not in the findings; a suggestion whose sample size is below the minimum group size says that it rests on a small sample.
- An AI Insight that is unavailable or not applicable has no label, no Executive Summary and no Improvement Suggestion, and no text of a failed or rejected answer was kept anywhere. An unavailable AI Insight after an attempt (`TIMEOUT`, `MODEL_ERROR`, `BAD_STRUCTURE`, `GUARDRAIL_REJECTED`) keeps the provider name and model name that were tried ([ADR-0011]); with `NO_PROVIDER` or `NO_MODEL` it has the provider and model that were selected, or none, and a not applicable one has neither.
- No Booking Record, no booking identifier, no input reference or fingerprint, no file name or path, and no date of an individual booking was sent to any language model; only the findings of the Analysis and the data-quality counts were.
- The Analysis Result has format version 1.1 and holds insights information (requested true, the provider and the model selected or absent when none was selected, and the prompt version).
- When an AI Insight of an available Analysis is unavailable, the Analysis Result has status `completed_with_warnings` and carries the notice `INSIGHTS_UNAVAILABLE` giving the number of such insights; it is still associated with the Result History (retains) and delivered like any completed result, and the exit code is unchanged.

**Added exceptions**

| Condition (failing or unmet condition) | Outcome |
| --- | --- |
| No provider of the two is reachable, or the provider named by `llm.provider` is not reachable | No provider was asked to generate text; every available Analysis has an AI Insight unavailable with reason `NO_PROVIDER`; the result is delivered as above; exit code 0 (diagram 5.2) |
| A provider is reachable but the configured or automatic model is not offered (it lists no model, or does not list the model named by `llm.model`) | As above with reason `NO_MODEL` |
| The language model does not finish its answer within the total deadline `llm.generation_timeout_seconds` ([ADR-0009]) | The AI Insight of that Analysis is unavailable with reason `TIMEOUT`; no retry; the next Analysis is still tried (diagram 5.3) |
| The connection is refused, or the provider answers with an error status or a body that cannot be used | The AI Insight of that Analysis is unavailable with reason `MODEL_ERROR`; no retry |
| The answer is empty, is not JSON, lacks a required key, has a wrong type or exceeds a limit of [ADR-0010] | The AI Insight of that Analysis is unavailable with reason `BAD_STRUCTURE`; the text is dropped (diagram 5.4) |
| The answer fails a guardrail (causal word, promise of earnings, invented figure, sample size not in the findings, small sample not stated, no hypothesis wording) | The AI Insight of that Analysis is unavailable with reason `GUARDRAIL_REJECTED`; the text is dropped |
| An Analysis is unavailable | Not a failure: its AI Insight is not applicable; no request was made |
| An `[llm]` configuration value is invalid and `insights` is true | As the built exception for a configuration error: a `failed` Analysis Result with `CONFIGURATION_ERROR` and format version 1.0 without insights, Result History unchanged, exit code 2; no provider was contacted |
| The Result History cannot be extended, retention fails, or standard output cannot be written | As the built exception rows (exit codes 3 and 4); the insights are part of the retained Analysis Result |

## UC-002 Review Analysis History: insights (Designed)

### Designed change to the contract: selectResult (Designed, MIL-011)

| Item | Value |
| --- | --- |
| Operation | `selectResult(resultLabel: str): SelectedResultView` as above, where `SelectedResultView` additionally holds, per Analysis, an insight view (a state, the reason or the texts) |
| Traces to | UC-002 message 2 (`selectResult`, revised return) in [SSD-001], diagrams 2.6 to 2.8 (and 2.1, 2.5 as built) |
| Domain Model concepts (added) | AI Insight, Executive Summary, Improvement Suggestion ([DM-001]) |

**Added preconditions**

- None beyond the built ones. A selected Analysis Result of schema version 1.0, or without insights, is a normal case.

**Added postconditions**

- The Result History and every Analysis Result are unchanged; no provider was contacted and no text was generated.
- When the selected Analysis Result holds insights, each Analysis is shown with its AI Insight: an available one with its Executive Summary and its Improvement Suggestions, each marked with the AI-generated label and the provider and model that produced it, each suggestion with its evidence and sample size; an unavailable one with its reason and no text; a not applicable one as not applicable.
- The text of an AI Insight is shown as plain text and is shown apart from the findings of the Analysis, never as a finding.
- When the selected Analysis Result holds no insights (it was made without `--insights`, or under schema version 1.0), the view states that the result was saved without insights and shows the findings as before; no error is shown.

**Added exceptions**

| Condition (failing precondition) | Outcome |
| --- | --- |
| The selected Analysis Result has no insights (schema version 1.0 or a run without insights) | The statement that it was saved without insights; not a failure (diagram 2.7) |
| The insight part of one Analysis is missing or unreadable inside an Analysis Result that holds insights | That Analysis is shown without an insight and with the statement that its insight could not be read; the other views and insights are shown |
| The schema version has an unsupported major version | As the built exception: the readable parts, including any insight that can be read, with the version notice |

## Coverage of the Designed Contracts

Every designed message of [SSD-001] has a contract and every diagram of [SSD-001] is named by a contract.

| Contract | SSD messages | SSD diagrams | Realized in [SD-001] by |
| --- | --- | --- | --- |
| `getHolidayCalendar` | UC-003 message 1 | 3.1, 3.2, 3.3, 3.4 | blocks 3.0, 3.1, 3.2 |
| `getLlmProviders` | UC-004 message 1 | 4.1, 4.2, 4.3, 4.4 | blocks 4.0, 4.1, 4.2 |
| `analyzeBookings` (Designed change) | UC-005 message 1 | 5.1, 5.2, 5.3, 5.4, 5.5 | blocks 5.0, 5.1, 5.2 |
| `selectResult` (Designed change) | UC-002 message 2 (revised return) | 2.6, 2.7, 2.8 | block 2.4 |

---

[SSD-001]: ./ssd.md
[DM-001]: ./domain-model.md
[UC-001]: ./use-cases/uc-001-analyze-hotel-bookings.md
[UC-002]: ./use-cases/uc-002-review-analysis-history.md
[UC-003]: ./use-cases/uc-003-get-holiday-calendar.md
[UC-004]: ./use-cases/uc-004-get-available-llm-providers.md
[UC-005]: ./use-cases/uc-005-get-ai-insights-for-analyses.md
[ADR-0003]: ./adr/adr-0003-jsonl-history-and-retention.md
[ADR-0005]: ./adr/adr-0005-delivery-and-failure-semantics.md
[SD-001]: ./sequence-diagrams.md
[DCD-001]: ./dcd.md
[ADR-0007]: ./adr/adr-0007-analysis-methods.md
[ADR-0009]: ./adr/adr-0009-llm-provider-discovery-and-connection.md
[ADR-0010]: ./adr/adr-0010-ai-insight-generation-and-guardrails.md
[ADR-0011]: ./adr/adr-0011-output-contracts-and-result-1-1.md
[ADR-0012]: ./adr/adr-0012-configuration-extension.md
