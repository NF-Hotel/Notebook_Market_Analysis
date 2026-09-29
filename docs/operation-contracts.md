# Operation Contracts

## Metadata
| Key | Value |
| --- | --- |
| ID | OC-001 |
| CrossReference | [SSD-001], [DM-001] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-29 | Proposed | Jens Tirsvad Nielsen | Team2 (S04) |

---

One contract per system operation (message) of [SSD-001]: one for [UC-001] and three for [UC-002]. The contracts describe the built system. Preconditions and postconditions use the concept names of [DM-001] (Booking Submission, Booking Record, Data Quality Summary, Analysis, Analysis Result, Result History, Retention Policy); they state what is true, not how it is achieved. Where the built behavior differs from an earlier decision, the difference is listed in the section **As-Built Deviations** at the end.

The operation `analyzeBookings` is realized in the code by `AnalyzeBookings.run(input_path: Path | None, config_path: Path | None) -> AnalyzeOutcome` in `application/analyze_bookings.py`, called by `main(...) -> int` in `infrastructure/cli.py`, which maps the outcome status to the exit code (0, 2, 3, 4).

## UC-001 Analyze Hotel Bookings

### Contract: analyzeBookings

| Item | Value |
| --- | --- |
| Operation | `analyzeBookings(inputFile: Path \| None, configFile: Path \| None): (resultJson: str, exitCode: int)` where `exitCode` is 0, 2, 3 or 4 and `resultJson` is absent when `exitCode` is 3 |
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

The differences of [SSD-001] (AD-1 to AD-5) apply to these contracts; the ones that change a contract are repeated here. Each is to be raised as an open issue or a new task through the MIL-007 review.

| ID | Earlier decision | As built | Effect on the contracts |
| --- | --- | --- | --- |
| AD-1 | [UC-001] extension 1a.2: no input outside development stops "without a result". | A `failed` Analysis Result with `NO_INPUT` is delivered, exit code 2 ([ADR-0005]). | Exception rows of `analyzeBookings` deliver a `failed` result. |
| AD-2 | [ADR-0005]: exit code 4 leaves the result saved. | For a `failed` result that cannot be delivered, exit code 4 and nothing is stored. | Last exception row of `analyzeBookings`. |
| AD-3 | [ADR-0003]: "latest" means later in the file. | The notebook orders the list by generated time. | Postcondition of `listRetainedResults`. |
| OD-1 | [UC-001] has an extension for a history that cannot be written (6a) but none for a failure of retention (step 7) or for a lock that cannot be taken. | Retention failure and lock timeout end the run with exit code 3 ([ADR-0003], [ADR-0005]); after a retention failure the appended result stays. | Two exception rows of `analyzeBookings` have no use case extension. |

---

[SSD-001]: ./ssd.md
[DM-001]: ./domain-model.md
[UC-001]: ./use-cases/uc-001-analyze-hotel-bookings.md
[UC-002]: ./use-cases/uc-002-review-analysis-history.md
[ADR-0003]: ./adr/adr-0003-jsonl-history-and-retention.md
[ADR-0005]: ./adr/adr-0005-delivery-and-failure-semantics.md
