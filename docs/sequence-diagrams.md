# Sequence Diagrams

## Metadata
| Key | Value |
| --- | --- |
| ID | SD-001 |
| CrossReference | [OC-001], [DCD-001] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | TBD (S04 not yet named) |
| 2026-09-30 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-30 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |

---

This document shows how the **built** objects of `src/hotel_booking_analysis` collaborate to realize the postconditions of the four operation contracts of [OC-001] (gateway MIL-007, sequence caveat: the documents describe the system as built and were checked against the code). Each block names the contract it realizes, gives one Mermaid `sequenceDiagram`, annotates the GRASP and GoF patterns, lists which message satisfies which postcondition, and checks that no object is a god object. Object and method names are the real names in the code; the class structure is in [DCD-001].

The operation `analyzeBookings` has one block for the object construction (1.0) and one block per scenario of [SSD-001] diagrams 1.1 to 1.5 (1.1 to 1.5 below); the three operations of [UC-002] have one block each (2.1 to 2.3).

| Block | Realizes (contract in [OC-001]) | Scenario |
| --- | --- | --- |
| 1.0 | `analyzeBookings` (lifecycle: the System instance is created) | Object graph built by the composition root |
| 1.1 | `analyzeBookings` | Main success, steps 1 to 5: configuration, load, validate, analyze, assemble |
| 1.2 | `analyzeBookings` | Main success, steps 6 to 8: serialize, append, retention, deliver, exit code 0 |
| 1.3 | `analyzeBookings` | Input or configuration error: `failed` result, exit code 2 (or 4, AD-2) |
| 1.4 | `analyzeBookings` | History write or retention failure: exit code 3 |
| 1.5 | `analyzeBookings` | Delivery failure of a completed result: exit code 4 |
| 2.1 | `listRetainedResults` | Notebook reads the history and lists the results |
| 2.2 | `selectResult` | Analyst selects a result, older-schema notice, default views |
| 2.3 | `chooseViewOption` | Analyst chooses a view option, one view re-renders |

**Notation.** Solid line with filled arrowhead (`->>`) is a synchronous call; dashed line with filled arrowhead (`-->>`) is the return; a dashed line with a cross (`--x`) is an exception that ends the call; `create participant` marks the message that constructs an object, and `destroy` marks the end of a transient object. All calls are synchronous: the analysis run is a single-threaded call chain in one process and the marimo cells are run one after the other by the notebook runtime, so no asynchronous (open arrow) message occurs. Activation bars show the call nesting. Messages are numbered per diagram. A participant labelled `module` is a module of functions (Pure Fabrication) rather than a class. Layer names under a participant are the packages of `src/hotel_booking_analysis`.

## Sequence 1.0: analyzeBookings, object construction

**Realizes:** `analyzeBookings` in [OC-001] (the SSD-001 lifecycle note "created when the process starts (the composition root wires the adapters)"; a prerequisite of blocks 1.1 to 1.5).

### Diagram

```mermaid
sequenceDiagram
    participant PM as "__main__<br/>module"
    participant CLI as ":cli<br/>module, infrastructure"
    participant BS as ":bootstrap<br/>module, composition root"
    PM->>+CLI: 1: main(argv, sys.stdout.buffer, sys.stderr, Path.cwd(), os.environ)
    CLI->>CLI: 2: build_parser().parse_args(argv)
    CLI->>CLI: 3: _attach_stderr(stderr)
    CLI->>+BS: 4: build_analyze_bookings(stdout, working_directory, environ, lock_wait_seconds)
    create participant CL as ":TomlConfigurationLoader<br/>adapters"
    BS->>CL: 5: create(working_directory, environ)
    create participant RJ as ":JsonBookingReader<br/>adapters"
    BS->>RJ: 6: create()
    create participant RC as ":DevelopmentCsvReader<br/>adapters"
    BS->>RC: 7: create()
    create participant BL as ":BookingLoader<br/>application"
    BS->>BL: 8: create(supplied_reader, development_reader, development_sample_path)
    create participant SER as ":JsonResultSerializer<br/>adapters"
    BS->>SER: 9: create()
    create participant HW as ":JsonlHistoryWriter<br/>infrastructure"
    BS->>HW: 10: create(lock_wait_seconds, base_directory=working_directory)
    create participant HR as ":JsonlHistoryReader<br/>infrastructure"
    BS->>HR: 11: create(working_directory)
    create participant SNK as ":StreamResultSink<br/>infrastructure"
    BS->>SNK: 12: create(stdout)
    create participant CK as ":SystemClock<br/>infrastructure"
    BS->>CK: 13: create()
    create participant ID as ":UuidGenerator<br/>infrastructure"
    BS->>ID: 14: create()
    BS->>+BS: 15: build_analyzers()
    create participant HC as ":KhmerHolidayCalendar<br/>adapters"
    BS->>HC: 16: create()
    create participant AZ as ":Analyzer x 6<br/>adapters"
    BS->>AZ: 17: create LeadTimeAnalyzer(), HolidayAnalyzer(calendar), SeasonalityAnalyzer(), CancellationAnalyzer(), RoomValueAnalyzer(), GuestMixAnalyzer()
    BS-->>-BS: 18: analyzers (tuple of six)
    create participant UC as ":AnalyzeBookings<br/>application"
    BS->>UC: 19: create(configuration_loader, booking_loader, serializer, history_writer, history_reader, sink, clock, ids, analyzers)
    BS-->>-CLI: 20: use_case
    CLI->>+UC: 21: run(arguments.input, arguments.config)
    Note over CLI,UC: run continues in blocks 1.1 and 1.2, or 1.3 to 1.5 on failure
    UC-->>-CLI: 22: outcome
    CLI-->>-PM: 23: exit code from _EXIT_CODES[outcome.status]
```

### Pattern Annotations

| Pattern (GRASP / GoF) | Applied to | Rationale |
| --- | --- | --- |
| Factory (creation in one place, GoF Factory Method style function) and Pure Fabrication (GRASP) | `bootstrap.build_analyze_bookings`, `bootstrap.build_analyzers` | The wiring of concrete adapters is a technical concern with no domain counterpart, so it is put in one module of the outermost non-notebook layer; the use case never names a concrete class. |
| Dependency Injection (constructor injection) and Protected Variations (GRASP) | `AnalyzeBookings` (message 19), `BookingLoader` (message 8), `HolidayAnalyzer` (message 17) | Collaborators are passed as `Protocol` ports, so an adapter can be replaced (tests use fakes) without changing the use case. |
| Adapter (GoF) | `TomlConfigurationLoader`, `JsonBookingReader`, `DevelopmentCsvReader`, `JsonResultSerializer`, `JsonlHistoryWriter`, `JsonlHistoryReader`, `StreamResultSink`, `SystemClock`, `UuidGenerator`, `KhmerHolidayCalendar` | Each adapts a file format, stream, clock or library to one port of `application/ports.py`. |
| Strategy (GoF) | `AZ` (the six analyzers, message 17) | The analyzers are interchangeable implementations of the `Analyzer` port; the use case receives them as a tuple and applies each by its `name`. |
| Controller (GRASP), command-line entry | `cli.main` | Receives the system event from the process boundary, delegates the work to the use case and translates the outcome to the exit code. |

### Postcondition Coverage

This block has no postcondition of its own; it realizes the lifecycle note of [SSD-001] (one operating-system process per call, adapters wired when the process starts) and the precondition "Standard output of the process can be written" (message 12 passes the stream to the sink).

| Postcondition (from contract) | Satisfied by message |
| --- | --- |
| Not applicable: construction only. It supplies the objects (messages 5 to 19) that realize every postcondition in blocks 1.1 to 1.5 | 5 to 19, and 21 to 23 for the hand-over to and the return from `run` |

### Responsibility Check

`cli.main` sends 5 of the 23 messages and `bootstrap` sends 16 (13 of them creations); neither computes anything of the analysis. `AnalyzeBookings` receives one message (`run`) in this block. Creation is separated from use (low coupling), so no object receives all messages.

## Sequence 1.1: analyzeBookings, assemble the Analysis Result (steps 1 to 5)

**Realizes:** `analyzeBookings` in [OC-001], main success postconditions on the Booking Submission, the Data Quality Summary, the Analyses and the Analysis Result (UC-001 steps 1 to 5), and the notice postcondition.

### Diagram

```mermaid
sequenceDiagram
    participant CLI as ":cli<br/>module, infrastructure"
    participant UC as ":AnalyzeBookings<br/>application"
    participant CL as ":TomlConfigurationLoader<br/>adapters"
    participant BL as ":BookingLoader<br/>application"
    participant RD as ":BookingReader<br/>JsonBookingReader or DevelopmentCsvReader"
    participant VB as ":validate_bookings<br/>module, application"
    participant ID as ":UuidGenerator<br/>infrastructure"
    participant CK as ":SystemClock<br/>infrastructure"
    participant BR as ":build_result<br/>module, application"
    participant RA as ":run_analyses<br/>module, application"
    participant AZ as ":Analyzer<br/>one of six, adapters"
    participant HC as ":KhmerHolidayCalendar<br/>adapters"
    CLI->>+UC: 1: run(input_path, config_path)
    UC->>+CL: 2: load(config_path)
    CL->>CL: 3: resolve_path(config_path)
    alt configuration file not found (extension 7a)
        CL->>CL: 4: notice CONFIG_FILE_NOT_FOUND, defaults apply
    else configuration file found and valid
        CL->>CL: 5: _parse(path), build_configuration(data), _unknown_keys(data)
    end
    create participant AC as ":AppConfiguration<br/>application"
    CL->>AC: 6: create(environment, history_path, retention, holiday_windows_days, min_group_size)
    CL-->>-UC: 7: LoadedConfiguration(configuration, notices)
    UC->>+BL: 8: load(input_path, configuration.environment)
    alt input_path is given (supplied)
        BL->>BL: 9: use supplied_reader, InputSource.SUPPLIED
    else input_path absent and environment is development (extension 1a)
        BL->>BL: 10: use development_reader, development_sample_path, InputSource.DEVELOPMENT_SAMPLE
    end
    BL->>+RD: 11: read(location)
    RD->>RD: 12: read_input_bytes(location), decode, parse_record(raw) per item
    create participant SUB as ":BookingSubmission<br/>domain"
    RD->>SUB: 13: create(source, reference=file name, content_sha256, records, unknown_fields)
    RD-->>-BL: 14: submission
    BL-->>-UC: 15: submission
    UC->>+VB: 16: validate_bookings(submission)
    VB->>VB: 17: usable_fields(records), assess_availability(records)
    create participant QS as ":DataQualitySummary<br/>domain"
    VB->>QS: 18: create via summarize(records, unknown_fields)
    create participant VAL as ":ValidatedBookings<br/>application"
    VB->>VAL: 19: create(submission, summary, availability, usable_fields)
    VB-->>-UC: 20: validated
    UC->>+ID: 21: new_id()
    ID-->>-UC: 22: result_id
    UC->>+CK: 23: now()
    CK-->>-UC: 24: generated_at
    UC->>+BR: 25: build_result(validated, loaded.notices, result_id, generated_at, configuration, analyzers)
    BR->>+RA: 26: run_analyses(validated, configuration, analyzers)
    loop for each AnalysisAvailability of validated.availability (six, one per AnalysisName)
        alt availability.is_available is false (required fields not usable)
            create participant AN as ":Analysis<br/>domain"
            RA->>AN: 27: create(name, UNAVAILABLE, reason=missing fields) via _unavailable(availability)
        else an Analyzer is registered for availability.analysis
            RA->>+AZ: 28: analyze(validated, configuration)
            opt the analysis is HOLIDAYS
                AZ->>+HC: 29: holidays_in_year(year) for each distinct year
                HC-->>-AZ: 30: tuple of Holiday, empty when the year is unknown (that part is marked unavailable)
            end
            AZ->>VAL: 31: records_for(field_names)
            AZ->>AN: 32: create(name, availability, reason, findings)
            AZ-->>-RA: 33: Analysis
        else no Analyzer registered (placeholder)
            RA->>AN: 34: create(name, availability, findings=PLACEHOLDER_FINDINGS) and notice ANALYSIS_NOT_IMPLEMENTED
        end
    end
    RA-->>-BR: 35: (analyses, analysis_notices)
    BR->>BR: 36: _source_notices(submission.source), _estimate_notice(), _status(validated, analyses, notices)
    create participant AR as ":AnalysisResult<br/>domain"
    BR->>AR: 37: create(result_id, generated_at, status, input=ResultInput(...), data_quality, analyses, notices)
    BR-->>-UC: 38: result
    Note over UC: run continues with _store_and_deliver in block 1.2
    UC-->>-CLI: 39: (see block 1.2 for the outcome)
```

### Pattern Annotations

| Pattern (GRASP / GoF) | Applied to | Rationale |
| --- | --- | --- |
| Controller (GRASP), use-case controller | `AnalyzeBookings.run` (messages 1 to 39) | Receives the system event `analyzeBookings` and delegates each step to a specialist; it holds no analysis rule itself. |
| Strategy (GoF) | `AZ`, the `Analyzer` port (messages 28 to 33) | `run_analyses` selects the analyzer by `AnalysisName` and calls the same `analyze` operation; each of the six analyses is a separate class, so a new analysis is added without changing `run_analyses`. |
| Adapter (GoF) | `CL` (`TomlConfigurationLoader`), `RD` (`JsonBookingReader`, `DevelopmentCsvReader`), `HC` (`KhmerHolidayCalendar`) | They turn a TOML file, a JSON or CSV file and the `holidays` package into the `ConfigurationLoader`, `BookingReader` and `HolidayCalendar` ports. |
| Information Expert (GRASP) | `BookingLoader.load` (messages 8 to 10), `ValidatedBookings.records_for` (message 31), `summarize` (message 18), `_status` (message 36) | The class or function that holds the data decides: the loader knows the fallback rule, the validated bookings know which records hold valid values, the summary function sees all records, and the status depends on the analyses, the summary and the notices that `build_result` holds. |
| Creator (GRASP) | `RD` creates `BookingSubmission`; `validate_bookings` creates `DataQualitySummary` and `ValidatedBookings`; `build_result` creates `AnalysisResult`; analyzers and `run_analyses` create `Analysis` | The creating object contains, aggregates or has the initializing data of the created object. |
| Pure Fabrication (GRASP) | `validate_bookings`, `build_result`, `run_analyses` (modules of functions) | They are use-case steps with no counterpart in the Domain Model; keeping them out of `AnalyzeBookings` keeps it small and keeps the steps testable alone. |
| Value Object | `AppConfiguration`, `LoadedConfiguration`, `BookingSubmission`, `DataQualitySummary`, `ValidatedBookings`, `Analysis`, `AnalysisResult` | All are frozen dataclasses: the result is assembled once and never changed. |

### Postcondition Coverage

| Postcondition (from contract) | Satisfied by message |
| --- | --- |
| A Booking Submission instance was created, source `supplied` (or `development_sample`), reference the file name, supplies its Booking Records | 9 or 10 select the reader and source; 11 and 12 read the records; 13 creates the `BookingSubmission` with source, reference and records |
| A Data Quality Summary instance was created with the record count, date coverage, duplicate booking ID count, and missing and invalid values per field | 17 and 18: `summarize(records, unknown_fields)` creates `DataQualitySummary`; 19 attaches it to `ValidatedBookings` |
| One Analysis instance per kind was created; an Analysis whose required fields are not usable is unavailable with the missing fields as reason, and no values were estimated | 26 to 35: the loop creates one `Analysis` per `AnalysisAvailability` (27 unavailable with reason, 32 analyzed, 34 placeholder); 31 lets an analyzer use only records with valid values, and no message fills a missing value |
| An Analysis Result instance was created with a new result identifier, the format version, the generated time and status `completed` or `completed_with_warnings` | 21 and 22 (new identifier), 23 and 24 (generated time), 36 (`_status`: warnings when an Analysis is unavailable, a value is invalid or unknown configuration keys were ignored), 37 (creation; `schema_version` takes its default `SCHEMA_VERSION`) |
| The Analysis Result was associated with the Booking Submission (is answered by), the Data Quality Summary (includes) and its Analyses (contains); it holds no Booking Record | 37: the arguments are `ResultInput` (source, reference, record count and content hash of the submission, no records), the `DataQualitySummary` and the tuple of `Analysis`; the submission's records are not passed |
| When the configuration file was missing the result carries `CONFIG_FILE_NOT_FOUND`; when the fallback was used it carries `DEVELOPMENT_SAMPLE_USED` | 4 (notice in `LoadedConfiguration`, message 7), 10 and 36 (`_source_notices` adds `DEVELOPMENT_SAMPLE_USED`), 37 (notices stored in the result) |

The postconditions on the Result History, the Retention Policy and the delivery are realized in block 1.2.

### Responsibility Check

`AnalyzeBookings` sends 7 of the 39 messages (six calls to the configuration loader, the loader, the validator, the identifier generator, the clock and `build_result`, and the final return) and does no parsing, counting or statistics. `build_result` and `run_analyses` split the assembly from the analysis, the six analyzers hold the analysis computation (cohesion by analysis), `BookingLoader` holds the source rule, and the domain functions hold the counting rules. No participant sends more than 7 messages (the controller 7, the configuration loader 5), so the controller is not a god object.

## Sequence 1.2: analyzeBookings, store and deliver (steps 6 to 8)

**Realizes:** `analyzeBookings` in [OC-001], main success postconditions on the Result History (retains), the Retention Policy and the delivery to the Calling system (UC-001 steps 6 to 8), exit code 0.

### Diagram

```mermaid
sequenceDiagram
    actor C as Calling system
    participant CLI as ":cli<br/>module, infrastructure"
    participant UC as ":AnalyzeBookings<br/>application"
    participant SER as ":JsonResultSerializer<br/>adapters"
    participant HW as ":JsonlHistoryWriter<br/>infrastructure"
    participant RET as ":jsonl_retention<br/>module, infrastructure"
    participant SNK as ":StreamResultSink<br/>infrastructure"
    participant HR as ":JsonlHistoryReader<br/>infrastructure"
    Note over CLI,UC: continues run() of block 1.1 with the AnalysisResult result
    activate CLI
    activate UC
    UC->>UC: 1: _store_and_deliver(result, configuration)
    UC->>+SER: 2: serialize(result)
    SER->>SER: 3: result_to_document(result), json.dumps compact, ASCII, Decimal as string
    SER-->>-UC: 4: line (one JSON line)
    UC->>+HW: 5: append(configuration.history_path, line, configuration.retention)
    HW->>HW: 6: _payload(line), single line and status in STORED_STATUSES
    HW->>HW: 7: location.parent.mkdir(parents=True, exist_ok=True)
    create participant FL as ":FileLock<br/>infrastructure"
    HW->>FL: 8: create(lock_path_for(location), lock_wait_seconds, lock_stale_after_seconds)
    HW->>+FL: 9: __enter__() acquires the lock file exclusively
    FL-->>-HW: 10: lock held
    HW->>HW: 11: _append(location, payload), open ab, write, flush, fsync
    HW->>+RET: 12: enforce_retention(location, retention.limit, replace)
    RET->>RET: 13: _lines_to_remove(lines, limit), _rewrite(path, kept, replace) only when results are beyond the limit
    RET-->>-HW: 14: number of removed results
    destroy FL
    HW->>FL: 15: __exit__() releases the lock file
    HW-->>-UC: 16: None
    UC->>+SNK: 17: write(line)
    SNK->>C: 18: standard output receives line and newline, then flush
    SNK-->>-UC: 19: None
    UC->>+HR: 20: read(configuration.history_path)
    HR-->>-UC: 21: HistoryReadout, malformed_line_count
    create participant OUT as ":AnalyzeOutcome<br/>application"
    UC->>OUT: 22: create(SUCCEEDED, result_id, serialized=line, malformed_history_lines)
    UC-->>CLI: 23: outcome
    deactivate UC
    CLI->>CLI: 24: _report(outcome), warning when malformed lines are counted, info "completed, saved and delivered"
    CLI-->>C: 25: exit code 0 from _EXIT_CODES[SUCCEEDED]
    deactivate CLI
```

### Pattern Annotations

| Pattern (GRASP / GoF) | Applied to | Rationale |
| --- | --- | --- |
| Controller (GRASP) | `AnalyzeBookings._store_and_deliver` | Orders the steps serialize, append, deliver and only then reports success, so success is reported after both the history write and the hand-over. |
| Adapter (GoF) | `SER`, `HW`, `SNK`, `HR` | Adapt JSON text, the JSONL file with locking and standard output to the ports `ResultSerializer`, `HistoryWriter`, `ResultSink` and `HistoryReader`. |
| Repository-like port (split into writer and reader) | `HistoryWriter`, `HistoryReader` and their JSONL adapters | The application depends on the port, not on the file format; the read side is a separate class because the run writes and the notebook only reads. |
| Information Expert (GRASP) | `enforce_retention` (messages 12 to 14), `JsonlHistoryWriter._payload` (message 6) | The retention function sees the lines of the file and decides which valid results are beyond the limit; the writer knows the stored format (one line, stored status). |
| Scoped resource (context manager) with transient object | `FileLock` (messages 8 to 15) | The lock file of [ADR-0003] exists only for the append and the retention rewrite and is released when the `with` block ends; it is destroyed after `__exit__`. |
| Pure Fabrication (GRASP) | `enforce_retention`, `jsonl_format` helpers | Technical file handling without a domain counterpart, kept out of the writer class. |

### Postcondition Coverage

| Postcondition (from contract) | Satisfied by message |
| --- | --- |
| The Analysis Result was associated with the Result History (retains) as its newest retained result | 2 to 4 create the one serialized line; 6 to 11: `append` adds the line at the end of the file under the lock (`_append`), so it is the newest by file position |
| The Result History no longer retains its oldest Analysis Results beyond the Retention Policy limit; results not beyond the limit and lines that are not valid results were not removed | 12 to 14: `enforce_retention` removes only the oldest valid results beyond `retention.limit` and keeps malformed and blank lines in place |
| The Calling system received the serialized Analysis Result on standard output, identical to the retained one, and the exit code 0 | 4, 5 and 17: the same `line` is written to the history and to the sink; 18 delivers it on standard output; 25 returns exit code 0 |
| (Closing the run) the outcome is `SUCCEEDED` only after the append and the delivery both completed | 16 and 19 precede 22, which creates `AnalyzeOutcome(SUCCEEDED, ...)` |

The postcondition of a warning about malformed history lines (AD-5 of [SSD-001]) is message 20 to 24 and is not a postcondition of the contract.

### Responsibility Check

`AnalyzeBookings` sends 7 of the 25 messages here (one self call, five calls and the return) and delegates serialization, storage, locking, retention, delivery and the malformed-line count to different collaborators. `JsonlHistoryWriter` receives one operation (`append`) and delegates the lock to `FileLock` and the retention to `enforce_retention`. No participant receives all messages.

## Sequence 1.3: analyzeBookings, input or configuration error

**Realizes:** `analyzeBookings` in [OC-001], the exceptions "configuration cannot be read or a value is invalid" (`CONFIGURATION_ERROR`), "no `inputFile` outside development" (`NO_INPUT`), "`inputFile` cannot be used" (`INPUT_NOT_FOUND`, `INPUT_UNREADABLE`, `INPUT_INVALID_JSON`, `INPUT_NOT_ARRAY`, `INPUT_EMPTY`, `INPUT_RECORD_NOT_OBJECT`, `INPUT_INVALID_CSV`), "no valid record" (`NO_VALID_RECORDS`), and the last exception row (a `failed` result that cannot be delivered, AD-2).

### Diagram

```mermaid
sequenceDiagram
    actor C as Calling system
    participant CLI as ":cli<br/>module, infrastructure"
    participant UC as ":AnalyzeBookings<br/>application"
    participant CL as ":TomlConfigurationLoader<br/>adapters"
    participant BL as ":BookingLoader<br/>application"
    participant RD as ":BookingReader<br/>adapters"
    participant VB as ":validate_bookings<br/>module, application"
    participant ID as ":UuidGenerator<br/>infrastructure"
    participant CK as ":SystemClock<br/>infrastructure"
    participant BR as ":build_result<br/>module, application"
    participant SER as ":JsonResultSerializer<br/>adapters"
    participant SNK as ":StreamResultSink<br/>infrastructure"
    CLI->>+UC: 1: run(input_path, config_path)
    UC->>+CL: 2: load(config_path)
    alt file cannot be parsed or a value is invalid (CONFIGURATION_ERROR)
        CL--xUC: 3: raise ConfigurationError(message, key)
        UC->>UC: 4: error = ConfigurationError, notices = ()
    else configuration valid
        CL-->>UC: 5: LoadedConfiguration
    end
    deactivate CL
    opt the configuration was valid
        UC->>+BL: 6: load(input_path, environment)
        alt no input_path and environment is not development (NO_INPUT)
            BL--xUC: 7: raise InputError NO_INPUT
            UC->>UC: 8: error = NO_INPUT, notices = loaded.notices
        else the input file cannot be used (INPUT_NOT_FOUND and the other INPUT codes)
            BL->>+RD: 9: read(location)
            RD--xBL: 10: raise InputError(code, message)
            deactivate RD
            BL--xUC: 11: propagate InputError
            UC->>UC: 12: error = INPUT code, notices = loaded.notices
        else the input was read
            BL-->>UC: 13: submission
        end
        deactivate BL
        opt the submission was read
            UC->>+VB: 14: validate_bookings(submission)
            VB--xUC: 15: raise InputError NO_VALID_RECORDS, no record holds a valid value
            deactivate VB
            UC->>UC: 16: error = NO_VALID_RECORDS, notices = loaded.notices
        end
    end
    UC->>UC: 17: _deliver_failure(error, notices)
    UC->>+ID: 18: new_id()
    ID-->>-UC: 19: result_id
    UC->>+CK: 20: now()
    CK-->>-UC: 21: generated_at
    UC->>+BR: 22: build_failed_result(error, notices, result_id, generated_at)
    create participant AR as ":AnalysisResult<br/>domain"
    BR->>AR: 23: create(status=FAILED, input=None, data_quality=None, notices, error=ResultError(code, message))
    BR-->>-UC: 24: failed result
    UC->>+SER: 25: serialize(result)
    SER-->>-UC: 26: line
    UC->>+SNK: 27: write(line)
    alt standard output accepts the line
        SNK->>C: 28: failed result JSON on standard output
        SNK-->>UC: 29: None
        UC->>UC: 30: status = INPUT_FAILED, message = error.message
    else standard output cannot be written (AD-2)
        SNK--xUC: 31: raise ResultDeliveryError
        UC->>UC: 32: status = DELIVERY_FAILED, message names result id, error code and delivery error, not stored
    end
    deactivate SNK
    create participant OUT as ":AnalyzeOutcome<br/>application"
    UC->>OUT: 33: create(status, result_id, serialized, message)
    UC-->>-CLI: 34: outcome
    CLI->>CLI: 35: _report(outcome), error message on standard error
    CLI-->>C: 36: exit code 2 for INPUT_FAILED, exit code 4 for DELIVERY_FAILED
```

### Pattern Annotations

| Pattern (GRASP / GoF) | Applied to | Rationale |
| --- | --- | --- |
| Controller (GRASP) with exception translation | `AnalyzeBookings.run`, `_deliver_failure` | Domain exceptions (`InputError`, `ConfigurationError`, `ResultDeliveryError`) are caught at one place and turned into a `failed` `AnalysisResult` and an `AnalyzeOutcome` status; no exception reaches the command line. |
| Information Expert (GRASP) | `BookingLoader.load` (message 7), `validate_bookings` (message 15), `TomlConfigurationLoader` (message 3) | Each raises the error for the rule it owns: the fallback rule, the no-valid-record rule, the configuration rules. |
| Creator (GRASP) | `build_failed_result` creates the failed `AnalysisResult` (message 23) | It has the error, notices, identifier and time that initialize the result. |
| Adapter (GoF) | `CL`, `RD`, `SER`, `SNK` | Same adapters as in block 1.1 and 1.2; the file, format and stream problems appear as domain errors, not as library exceptions. |
| Value Object | `AnalyzeOutcome`, failed `AnalysisResult` | Frozen dataclasses; the outcome carries the status that `cli` maps to the exit code. |

### Postcondition Coverage

| Postcondition (from contract, exception row) | Satisfied by message |
| --- | --- |
| Configuration error: a `failed` Analysis Result with the error, no Booking Submission, no Data Quality Summary and no Analysis; not associated with the Result History; delivered on standard output; exit code 2 | 3, 4 (error), 17 to 24 (failed result built with `input=None`, `data_quality=None` and no analyses, message 23), 28 (delivered), 36 (exit code 2). No message reaches `JsonlHistoryWriter`, so the Result History is unchanged |
| `NO_INPUT`: as above | 7, 8, then 17 to 36 as above |
| Input file cannot be used (`INPUT_*`): as above | 9 to 12, then 17 to 36 as above |
| `NO_VALID_RECORDS`: as above | 13 to 16, then 17 to 36 as above |
| A `failed` result that cannot be written to standard output (AD-2): nothing stored, no result delivered, standard error names the result identifier, the error code and the delivery error; exit code 4 | 27, 31, 32, 33 to 36: the branch creates `AnalyzeOutcome(DELIVERY_FAILED, ...)` whose message contains those parts; the failed result was never sent to the history writer |

### Responsibility Check

`AnalyzeBookings` sends 17 of the 36 messages, of which 7 are self messages that only record the error or the status; the other calls go to seven collaborators. The error rules stay in the collaborators that own them (loader, reader, validator, configuration loader), the failed result is built by `build_failed_result`, serialization and delivery are delegated, and the exit code is chosen by `cli`. No participant receives all messages.

## Sequence 1.4: analyzeBookings, history write or retention failure

**Realizes:** `analyzeBookings` in [OC-001], the exceptions "the Result History cannot be extended" (directory, lock timeout, append) and "the Retention Policy could not be applied after the append", exit code 3.

### Diagram

```mermaid
sequenceDiagram
    actor C as Calling system
    participant CLI as ":cli<br/>module, infrastructure"
    participant UC as ":AnalyzeBookings<br/>application"
    participant SER as ":JsonResultSerializer<br/>adapters"
    participant HW as ":JsonlHistoryWriter<br/>infrastructure"
    participant RET as ":jsonl_retention<br/>module, infrastructure"
    Note over CLI,UC: continues run() of block 1.1 with the AnalysisResult result
    activate CLI
    activate UC
    UC->>UC: 1: _store_and_deliver(result, configuration)
    UC->>+SER: 2: serialize(result)
    SER-->>-UC: 3: line
    UC->>+HW: 4: append(configuration.history_path, line, configuration.retention)
    HW->>HW: 5: _payload(line)
    alt the history directory cannot be created
        HW->>HW: 6: mkdir raises OSError, raise HistoryWriteError
        HW--xUC: 7: HistoryWriteError, the history directory cannot be created
    else the directory exists or was created
        create participant FL as ":FileLock<br/>infrastructure"
        HW->>FL: 8: create(lock_path_for(location), lock_wait_seconds, lock_stale_after_seconds)
        HW->>FL: 9: __enter__() acquire
        alt the lock cannot be taken (wait limit exceeded or lock file not creatable)
            FL--xHW: 10: raise HistoryWriteError
            HW--xUC: 11: HistoryWriteError, the lock could not be taken
        else the lock is held
            FL-->>HW: 12: lock held
            activate FL
            alt the append fails
                HW->>HW: 13: _append raises HistoryWriteError from OSError
            else the append succeeds and the retention rewrite fails
                HW->>+RET: 14: enforce_retention(location, retention.limit, replace)
                RET->>RET: 15: _rewrite fails, temporary file removed, history file untouched
                RET--xHW: 16: raise HistoryRetentionError
                deactivate RET
            end
            deactivate FL
            destroy FL
            HW->>FL: 17: __exit__() releases the lock file
            HW--xUC: 18: HistoryWriteError or HistoryRetentionError
        end
    end
    deactivate HW
    UC->>UC: 19: _history_failure(result, error)
    alt error is HistoryRetentionError
        UC->>UC: 20: message "appended to the history but retention failed", result stays in the history
    else error is HistoryWriteError
        UC->>UC: 21: message "The history was not updated", history unchanged
    end
    create participant OUT as ":AnalyzeOutcome<br/>application"
    UC->>OUT: 22: create(HISTORY_FAILED, result_id, message + "No result was delivered.")
    UC-->>CLI: 23: outcome, serialized is None
    deactivate UC
    CLI->>CLI: 24: _report(outcome), error message on standard error
    CLI-->>C: 25: exit code 3, nothing on standard output
    deactivate CLI
```

### Pattern Annotations

| Pattern (GRASP / GoF) | Applied to | Rationale |
| --- | --- | --- |
| Controller (GRASP) with exception translation | `AnalyzeBookings._history_failure` | Maps `HistoryWriteError` and `HistoryRetentionError` to one outcome status and chooses the message that states whether the result was appended. |
| Information Expert (GRASP) | `JsonlHistoryWriter.append`, `enforce_retention`, `FileLock.acquire` | The writer knows the storage steps, the retention function knows the file lines, the lock knows the wait limit; each raises the specific `HistoryError` subclass. |
| Scoped resource with transient object | `FileLock` (messages 8 to 17) | Released when the `with` block ends even on failure; destroyed after release. In the lock timeout branch the lock was never held and is dropped without release. |
| Adapter (GoF) | `HW` | Turns file-system errors (`OSError`) into the domain errors of the `HistoryWriter` port. |
| Exception hierarchy | `HistoryError`, `HistoryWriteError`, `HistoryRetentionError` | The subclass tells the controller whether the append happened, so the message and the state of the Result History are exact. |

### Postcondition Coverage

| Postcondition (from contract, exception row) | Satisfied by message |
| --- | --- |
| The Result History cannot be extended (directory, lock, append): the Analysis Result was not associated with the Result History, the Result History is unchanged, no result was delivered, standard error says the history was not updated, exit code 3 | 6 and 7 (directory), 10 and 11 (lock timeout), 13 and 18 (append failure); 19, 21 (message "The history was not updated"), 22 and 23 (outcome without `serialized`); 25 (exit code 3). No message reaches `StreamResultSink`, so nothing is delivered |
| The Retention Policy could not be applied after the append: the Analysis Result stays associated with the Result History, which may retain more results than the limit; no result was delivered; standard error says the result was appended but retention failed; exit code 3 | 14 to 16 (the append of the first branch did not fail, retention fails, and the append is not undone), 18, 19, 20 (message "appended to the history but retention failed"), 22, 23, 25 (exit code 3) |

### Responsibility Check

`AnalyzeBookings` sends 8 of the 25 messages (4 of them self messages that choose the failure message) and `JsonlHistoryWriter` sends 10 (mostly the failure exits). The error semantics are split by owner: the writer and lock raise, the controller translates, `cli` reports. No participant receives all messages.

## Sequence 1.5: analyzeBookings, delivery failure of a completed result

**Realizes:** `analyzeBookings` in [OC-001], the exception "standard output cannot be written for a completed Analysis Result", exit code 4. (The delivery failure of a `failed` result is the last branch of block 1.3.)

### Diagram

```mermaid
sequenceDiagram
    actor C as Calling system
    participant CLI as ":cli<br/>module, infrastructure"
    participant UC as ":AnalyzeBookings<br/>application"
    participant HW as ":JsonlHistoryWriter<br/>infrastructure"
    participant SNK as ":StreamResultSink<br/>infrastructure"
    participant HR as ":JsonlHistoryReader<br/>infrastructure"
    Note over CLI,UC: continues run() of block 1.1, the result was serialized as line
    activate CLI
    activate UC
    UC->>UC: 1: _store_and_deliver(result, configuration)
    UC->>+HW: 2: append(configuration.history_path, line, configuration.retention)
    HW-->>-UC: 3: None, the result is now retained (block 1.2 messages 6 to 16)
    UC->>+SNK: 4: write(line)
    SNK->>SNK: 5: stream.write(line bytes + newline), flush raises OSError or ValueError
    SNK--xUC: 6: raise ResultDeliveryError(str(error))
    deactivate SNK
    UC->>+HR: 7: read(configuration.history_path)
    HR-->>-UC: 8: HistoryReadout, malformed_line_count
    create participant OUT as ":AnalyzeOutcome<br/>application"
    UC->>OUT: 9: create(DELIVERY_FAILED, result_id, line, message "was saved to the history but could not be written to standard output")
    UC-->>CLI: 10: outcome
    deactivate UC
    CLI->>CLI: 11: _report(outcome), error message with the result identifier on standard error
    CLI-->>C: 12: exit code 4, nothing on standard output
    deactivate CLI
```

### Pattern Annotations

| Pattern (GRASP / GoF) | Applied to | Rationale |
| --- | --- | --- |
| Controller (GRASP) | `AnalyzeBookings._store_and_deliver` | The order append then deliver makes "saved but not delivered" a distinct, reportable outcome, so a retry by the Calling system can be reasoned about. |
| Adapter (GoF) | `StreamResultSink` | Turns `OSError` and `ValueError` of a binary stream into the domain error `ResultDeliveryError` of the `ResultSink` port. |
| Value Object | `AnalyzeOutcome` | Carries status, result identifier, the serialized line and the message to `cli`. |

### Postcondition Coverage

| Postcondition (from contract, exception row) | Satisfied by message |
| --- | --- |
| The Analysis Result stays associated with the Result History | 2 and 3: the append completed before the delivery was tried and nothing removes it |
| The Calling system received no result | 5 and 6: the write fails; 12 shows nothing on standard output |
| The message on standard error names the result identifier and says it was saved but not delivered; exit code 4 | 9 (message text with the result identifier), 11 (reported on standard error), 12 (exit code 4) |

### Responsibility Check

`AnalyzeBookings` sends 6 of the 12 messages (a self call, three calls, the creation of the outcome and the return), because the diagram shows only the delegation of the last steps; the sink, the writer and the reader each handle one concern and `cli` maps the outcome. No participant receives all messages.

## Sequence 2.1: listRetainedResults

**Realizes:** `listRetainedResults` in [OC-001] (`load_history` in `interface/history_source.py` and `build_history_view` in `interface/history_view.py`), including the exceptions "history does not exist or is empty", "configuration invalid", "history cannot be read" and "malformed lines".

### Diagram

```mermaid
sequenceDiagram
    actor A as Analyst
    participant MR as ":marimo runtime<br/>runs the cells"
    participant NB as ":history_notebook<br/>module, interface, reading cell"
    participant HS as ":history_source<br/>module, interface"
    participant HV as ":history_view<br/>module, interface"
    A->>MR: 1: opens the notebook (python -m marimo run history_notebook.py)
    MR->>+NB: 2: runs the reading cell
    NB->>+HS: 3: load_history(Path.cwd(), os.environ)
    create participant CL as ":TomlConfigurationLoader<br/>adapters"
    HS->>CL: 4: create(working_directory, environ)
    HS->>+CL: 5: load(None)
    alt the configuration file is invalid (ConfigurationError)
        CL--xHS: 6: raise ConfigurationError
        HS->>HS: 7: readout = HistoryReadout((), 0), location = None, error = error.message
    else the configuration is valid
        CL-->>HS: 8: LoadedConfiguration, location = history_path
    end
    deactivate CL
    opt the configuration was valid
        create participant JR as ":JsonlHistoryReader<br/>infrastructure"
        HS->>JR: 9: create(working_directory)
        HS->>+JR: 10: read(location)
        alt the history file does not exist
            JR-->>HS: 11: HistoryReadout((), 0)
        else the history file exists but cannot be read (OSError)
            JR--xHS: 12: raise HistoryReadError
            HS->>HS: 13: readout = HistoryReadout((), 0), error = str(error)
        else the history file is readable
            loop for each non-blank line of the file
                JR->>JR: 14: parse_valid_result(line), a valid result is kept, otherwise malformed is counted
            end
            JR-->>HS: 15: HistoryReadout(results in file order, malformed_line_count)
        end
        deactivate JR
        destroy JR
        HS->>JR: 16: reader is discarded when load_history returns
    end
    destroy CL
    HS->>CL: 17: loader is discarded when load_history returns
    create participant LH as ":LoadedHistory<br/>interface"
    HS->>LH: 18: create(readout, location, error)
    HS-->>-NB: 19: loaded
    NB->>+HV: 20: build_history_view(loaded.readout)
    HV->>HV: 21: sorted(range(n), key=_generated_key, reverse=True), newest first by generated time
    loop for each result in the sorted order
        create participant ROW as ":HistoryRow<br/>interface"
        HV->>ROW: 22: create(result_id, generated_at, status, source, record_count, schema_version, fully_supported)
    end
    HV->>HV: 23: malformed_message(readout.malformed_line_count)
    alt no valid result
        HV->>HV: 24: empty_message = NO_RESULTS_MESSAGE
    end
    create participant VW as ":HistoryView<br/>interface"
    HV->>VW: 25: create(rows, empty_message, malformed_message, results)
    HV-->>-NB: 26: history
    NB->>NB: 27: messages = loaded.error, history.empty_message, history.malformed_message (those that are set)
    NB-->>-MR: 28: cell output history (the session's current listing) and callouts
    MR-->>A: 29: history file location, messages, and the table of retained results
```

### Pattern Annotations

| Pattern (GRASP / GoF) | Applied to | Rationale |
| --- | --- | --- |
| Pure Fabrication (GRASP) | `history_source.load_history`, `history_view.build_history_view` | Module functions with no domain counterpart: the first is a read-only access facade that turns failures into a message, the second a pure function from `HistoryReadout` to view model. Neither touches marimo. |
| Facade (GoF) | `load_history` | Hides the configuration loader and the history reader behind one call that never raises for a configuration or read failure. |
| Adapter (GoF) | `CL`, `JR` | Concrete adapters reached directly (AD-4 of [SSD-001], deviation SD-1 below): the notebook does not go through the `HistoryReader` port. |
| Information Expert (GRASP) | `JsonlHistoryReader.read` (messages 14 and 15), `HistoryRow.label`, `history_view._generated_key` | The reader knows the line format and counts malformed lines; the view module knows how to order rows and to word the messages. |
| Creator (GRASP) | `load_history` creates `LoadedHistory`; `build_history_view` creates `HistoryRow` and `HistoryView` | They hold the data that initializes the created objects. |
| Value Object | `LoadedHistory`, `HistoryView`, `HistoryRow` | Frozen dataclasses; the listing is built once per session. |
| Transient objects | `CL` and `JR` (messages 16 and 17) | Created inside `load_history` and dropped when it returns. |

### Postcondition Coverage

| Postcondition (from contract) | Satisfied by message |
| --- | --- |
| The Result History and its Analysis Results are unchanged (no instance created, associated or removed) | 10 to 15: `JsonlHistoryReader.read` only reads (`read_bytes`) and never writes; no message in the diagram reaches `JsonlHistoryWriter` or `FileLock` |
| The session's current listing was set to the valid retained Analysis Results, newest first by generated time | 20 to 26 (`build_history_view` sorts and creates `HistoryView`), 28 (the cell output `history` is the session's current listing) |
| When the Result History has no valid Analysis Result the listing is empty and the empty message states that there are no saved results yet | 11 (missing file gives an empty readout), 24 (`empty_message = NO_RESULTS_MESSAGE`), 27 and 29 (shown). Also the exception rows: invalid configuration 6 and 7, unreadable history 12 and 13, both then 24 and 27 |
| When the Result History holds lines that are not valid results, the malformed count was set and a message states how many were skipped; the readable results are listed | 14 and 15 (count in the readout), 23 (`malformed_message`), 27 and 29 (shown); the results are listed by 22 and 25 and no line is removed |

### Responsibility Check

The notebook cell sends 4 of the 29 messages (two calls, the assembly of the messages and its return) and contains no parsing or sorting; `load_history` sends 10. Reading is in `JsonlHistoryReader`, configuration in `TomlConfigurationLoader`, ordering and messages in `history_view`. No participant receives all messages.

## Sequence 2.2: selectResult

**Realizes:** `selectResult` in [OC-001] (the picker cell and the dependent cells of `interface/history_notebook.py`, `version_notice` in `interface/history_view.py`), including the older-schema notice and the unavailable Analysis exceptions.

### Diagram

```mermaid
sequenceDiagram
    actor A as Analyst
    participant MR as ":marimo runtime<br/>runs the cells"
    participant NB as ":history_notebook<br/>module, interface, cells"
    participant HV as ":HistoryView<br/>interface"
    participant HN as ":history_view<br/>module, interface"
    participant QV as ":quality_view<br/>module, interface"
    participant BV as ":view builder<br/>lead_time_view, seasonality_view, holiday_view, cancellation_view, room_value_view, guest_mix_view"
    participant LM as ":limitations<br/>module, interface"
    participant RN as ":marimo_render<br/>module, interface"
    A->>MR: 1: chooses an entry of the picker (default is the first label)
    MR->>+NB: 2: runs the selection cell with history and picker
    NB->>+HV: 3: labels()
    loop for each (position, row) of rows
        HV->>HV: 4: row.label(position)
    end
    HV-->>-NB: 5: labels
    NB->>NB: 6: selected = history.results[labels.index(picker.value)]
    NB->>+HN: 7: version_notice(selected)
    HN->>HN: 8: is_fully_supported(selected), major_version(schema_version)
    alt schema_version is missing or its major version is not 1
        HN-->>NB: 9: notice text naming the version, only readable parts are shown
        NB->>NB: 10: mo.callout(mo.md(notice), kind="warn") (marimo is called directly by the cell)
    else the schema version is supported
        HN-->>NB: 11: None
    end
    deactivate HN
    NB-->>-MR: 12: selected (the session's current selection)
    MR->>+NB: 13: runs the quality and limitations cell with selected
    NB->>+QV: 14: build_quality_view(selected)
    create participant DQV as ":DataQualityView<br/>interface"
    QV->>DQV: 15: create(record_count, booking_dates, arrival_dates, fields, unavailable_analyses, notices)
    QV-->>-NB: 16: data quality view
    NB->>+LM: 17: build_limitations(selected)
    LM-->>-NB: 18: LimitationsNotice
    NB->>+RN: 19: render_quality(view), render_limitations(notice)
    RN-->>-NB: 20: mo.Html
    NB-->>-MR: 21: Data Quality Summary and general limitation notes shown
    loop for each of the six analysis cells (lead time, seasonality, holidays, cancellations, room value, guest mix)
        MR->>+NB: 22: runs the analysis cell with selected and the option value
        NB->>+BV: 23: build_xxx_view(selected)
        BV->>BV: 24: analysis_findings(selected, name), unavailable_reason(entry)
        create participant AV as ":XxxView<br/>view model of one Analysis"
        BV->>AV: 25: create(message, findings of the Analysis or the unavailable reason, counts, small-sample flags)
        BV-->>-NB: 26: view
        NB->>+RN: 27: render_xxx(view, default option)
        RN-->>-NB: 28: mo.Html, unavailable view shows its reason, room value shows the estimate label
        NB->>+LM: 29: build_limitations(selected, analysis name), render_limitations(notice)
        LM-->>-NB: 30: notes on small samples, partial periods, unavailable parts, association and estimate
        NB-->>-MR: 31: view and limitation notes
    end
    MR-->>A: 32: the Data Quality Summary and the analysis views with limitation notes
```

### Pattern Annotations

| Pattern (GRASP / GoF) | Applied to | Rationale |
| --- | --- | --- |
| Pure Fabrication (GRASP) | `version_notice`, `build_quality_view`, `build_xxx_view`, `build_limitations`, `render_xxx` (modules of functions) | View-model builders are pure functions from the stored result to display data; renderers are the only place that use marimo. |
| Model-View separation (view model) | `DataQualityView`, `LeadTimeView` and the other view models versus `marimo_render` | The view models hold what is shown, the renderer shows it; the builders can be tested without marimo. |
| Information Expert (GRASP) | `HistoryView.labels` and `HistoryRow.label` (messages 3 and 4), `figures.analysis_findings` (message 24) | The view holds the rows and knows the labels; the findings accessor knows the shape of a stored Analysis and is tolerant of missing parts. |
| Observer (reactive dependency, implemented by marimo) | `MR` re-runs the cells that depend on `selected` (messages 13 and 22) | Changing the picker re-runs exactly the dependent cells; the code only declares the dependency. Not written by the project. |
| Tolerant Reader | `json_access.as_mapping`, `as_list`, `as_int`, `as_text` used by the builders | A result from another schema version or with a missing part yields neutral values, so the view shows the readable parts (older-schema postcondition). |
| Value Object | all `*View`, `LimitationsNotice` | Frozen dataclasses built per selection. |

### Postcondition Coverage

| Postcondition (from contract) | Satisfied by message |
| --- | --- |
| The Result History and its Analysis Results are unchanged | No message reaches a writer or a lock: the cells only read `history.results` (3 to 6) and pure builders (23 to 26) |
| The session's current selection was set to the Analysis Result named by `resultLabel` | 3 to 6 (label to position to result), 12 (the cell output `selected`) |
| The Data Quality Summary of the selected Analysis Result is shown with record count, date coverage, duplicate booking IDs, missing and invalid values | 14 to 16 (`build_quality_view`), 19 and 20 (`render_quality`), 21 |
| Each Analysis is shown with its counts and limitation notes; an unavailable Analysis is shown as unavailable with its reason; room value figures are labelled as estimates | 22 to 31 (loop over the six Analyses): 24 and 25 produce the view with the counts or with the unavailable reason, 28 renders it with the estimate label for room value, 29 and 30 add the limitation notes |
| When the schema version does not have the supported major version a notice names that version and only the readable parts are shown | 7 to 10 (`version_notice`, callout); 24 and 25 build the views tolerantly from whatever parts exist |

### Responsibility Check

The notebook cells send 13 of the 32 messages (40 percent, the most of any participant) but hold no logic beyond wiring: label lookup, calling a builder, calling a renderer, and one return per cell. Each builder is responsible for one Analysis (high cohesion) and the renderer is separate from the view model (low coupling). No participant receives all messages.

## Sequence 2.3: chooseViewOption

**Realizes:** `chooseViewOption` in [OC-001] (the option dropdown cells of `interface/history_notebook.py` and the render functions of `interface/marimo_render.py`). The diagram shows the holidays window size; the other four Analyses with options follow the same shape (alternatives in the diagram).

### Diagram

```mermaid
sequenceDiagram
    actor A as Analyst
    participant MR as ":marimo runtime<br/>runs the cells"
    participant NB as ":history_notebook<br/>module, interface, option cells"
    participant BV as ":view builder<br/>build_xxx_view"
    participant AV as ":XxxView<br/>view model of one Analysis"
    participant RN as ":marimo_render<br/>module, interface"
    participant LM as ":limitations<br/>module, interface"
    MR->>+NB: 1: runs the option cell for the Analysis with selected
    NB->>+BV: 2: build_xxx_view(selected)
    create participant HVW as ":HolidayView<br/>interface"
    BV->>HVW: 3: create(message, note, calendar, windows_days, sections)
    participant HSC as ":HolidaySection<br/>interface, one per side (booking date, arrival date)"
    BV-->>-NB: 4: view
    alt the Analysis is holidays
        NB->>+HVW: 5: window_options()
        HVW-->>-NB: 6: dict of window size labels to days
    else lead time or cancellations
        NB->>AV: 7: split_options()
    else seasonality
        NB->>AV: 8: series_options() and granularity_options()
    else guest mix
        NB->>AV: 9: attribute_options()
    end
    opt the option list is not empty (room value and unavailable Analyses offer none)
        create participant UI2 as ":dropdown<br/>the option dropdown"
        NB->>UI2: 10: create(options, value=first option, label)
        NB-->>MR: 11: the dropdown is shown, its value is the current option
    end
    NB-->>-MR: 12: cell output, the dropdown
    A->>UI2: 13: chooses an option value
    UI2-->>MR: 14: value changed
    MR->>+NB: 15: re-runs only the cells that depend on the dropdown, with holiday_window.value
    NB->>+BV: 16: build_holiday_view(selected)
    BV-->>-NB: 17: HolidayView
    NB->>+RN: 18: render_holidays(view, window)
    RN->>+HSC: 19: comparison_table(window), weekday_table(window), statements(window), coverage_lines()
    HSC-->>-RN: 20: rows and statements for the window
    RN-->>-NB: 21: mo.Html
    NB->>+LM: 22: build_limitations(selected, "holidays"), render_limitations(notice)
    LM-->>-NB: 23: limitation notes
    NB-->>-MR: 24: the chosen view with limitation notes
    MR-->>A: 25: the view of that Analysis for the chosen option
```

### Pattern Annotations

| Pattern (GRASP / GoF) | Applied to | Rationale |
| --- | --- | --- |
| Observer (reactive dependency, implemented by marimo) | `MR` and the dropdown (messages 14 and 15) | Only the cells that depend on the dropdown value are re-run, so no other Analysis view and no selection changes (postcondition). Not written by the project. |
| Information Expert (GRASP) | `HolidayView.window_options`, `LeadTimeView.split_options`, `SeasonalityView.series_options`, `GuestMixView.attribute_options` (messages 5 to 9) | Each view model knows which options its findings support, so the notebook never inspects the JSON. |
| Pure Fabrication (GRASP) | `render_holidays`, `build_limitations` | Rendering and limitation wording are functions, separate from the view model and the runtime. |
| Value Object | `HolidayView` and the other view models | The view is rebuilt from the unchanged selection; nothing is mutated. |

### Postcondition Coverage

| Postcondition (from contract) | Satisfied by message |
| --- | --- |
| The Result History and the selected Analysis Result are unchanged | Messages 15 to 24 only read `selected` and build new view objects; no writer is reached |
| The session's current option for the Analysis was set to `option` | 13 and 14 (the dropdown value is the session state), 15 (`holiday_window.value` passed to the dependent cell) |
| The view of that Analysis is shown for `option` with its limitation notes; no other Analysis view and no selection changed | 16 to 24: `render_holidays(view, window)` renders the Group Statistics of the chosen window (19 and 20), 22 and 23 add the limitation notes; 15 re-runs only the dependent cells |
| Exception: no Analysis Result is selected, or the Analysis is unavailable or offers no options: no option list is offered and the view shows the reason or the single default view | 10 is inside `opt`: it is skipped when the option list is empty, so no dropdown is created and 18 renders the default view or the unavailable reason |

### Responsibility Check

The notebook cells send 12 of the 25 messages, all wiring calls and returns; option knowledge is in the view models, rendering in `marimo_render`, wording in `limitations`, and re-running in the marimo runtime. No participant receives all messages.

## OC-001 Coverage Matrix

Every postcondition and exception of every contract of [OC-001] is realized by at least one block.

| Contract | Postcondition or exception (short name) | Realized by block |
| --- | --- | --- |
| `analyzeBookings` | Booking Submission created (source, reference) | 1.1 |
| `analyzeBookings` | Data Quality Summary created | 1.1 |
| `analyzeBookings` | One Analysis per kind, unavailable with reason, nothing estimated | 1.1 |
| `analyzeBookings` | Analysis Result created (identifier, version, time, status) | 1.1 |
| `analyzeBookings` | Result associated with submission, summary, analyses; no Booking Record | 1.1 |
| `analyzeBookings` | Result retained as newest in the Result History | 1.2 |
| `analyzeBookings` | Retention applied, only the oldest valid results removed | 1.2 |
| `analyzeBookings` | Serialized result on standard output identical to the retained one, exit code 0 | 1.2 |
| `analyzeBookings` | Notices `CONFIG_FILE_NOT_FOUND` and `DEVELOPMENT_SAMPLE_USED` | 1.1 |
| `analyzeBookings` | Exception: configuration error | 1.3 |
| `analyzeBookings` | Exception: `NO_INPUT` | 1.3 |
| `analyzeBookings` | Exception: input file cannot be used | 1.3 |
| `analyzeBookings` | Exception: `NO_VALID_RECORDS` | 1.3 |
| `analyzeBookings` | Exception: history cannot be extended (directory, lock, append) | 1.4 |
| `analyzeBookings` | Exception: retention fails after the append | 1.4 |
| `analyzeBookings` | Exception: completed result cannot be delivered | 1.5 |
| `analyzeBookings` | Exception: `failed` result cannot be delivered (AD-2) | 1.3 |
| `listRetainedResults` | Result History unchanged | 2.1 |
| `listRetainedResults` | Current listing set, newest first by generated time | 2.1 |
| `listRetainedResults` | Empty listing with the no-saved-results message | 2.1 |
| `listRetainedResults` | Malformed count and message, readable results listed | 2.1 |
| `listRetainedResults` | Exceptions: missing or empty history, invalid configuration, unreadable history, malformed lines | 2.1 |
| `selectResult` | Result History unchanged | 2.2 |
| `selectResult` | Current selection set | 2.2 |
| `selectResult` | Data Quality Summary shown | 2.2 |
| `selectResult` | Each Analysis shown with counts and notes, unavailable with reason, room value as estimate | 2.2 |
| `selectResult` | Older or unsupported schema version notice | 2.2 |
| `selectResult` | Exceptions: empty listing, unsupported schema version, unreadable Analysis | 2.2 (empty listing: no picker cell input, no message sent; unreadable Analysis: messages 24 and 25) |
| `chooseViewOption` | Result History and selected result unchanged | 2.3 |
| `chooseViewOption` | Current option set | 2.3 |
| `chooseViewOption` | View shown for the option with limitation notes, nothing else changes | 2.3 |
| `chooseViewOption` | Exceptions: no selection, unavailable Analysis or no options | 2.3 |

## As-Built Deviations

Differences between the built collaboration and earlier decisions ([ADR-0001] to [ADR-0007], [DM-001]) or [SSD-001] and [OC-001], continuing the numbering of the earlier documents (AD-1 to AD-5, OD-1). They are recorded here and are not corrected in the diagrams; each was raised as an open issue in the project plan (OI-21 to OI-27) through the MIL-007 review (Go/No-Go criterion 6), and the last column gives its status.

| ID | Earlier decision | As built (shown in) | Proposed follow-up |
| --- | --- | --- | --- |
| SD-1 | [ADR-0006]: the notebook reads the history "through the same history reader port as the CLI", and the application layer holds "list results" and "load a result" use cases (same as AD-4). | The notebook cell calls `history_source.load_history`, which creates `TomlConfigurationLoader` and `JsonlHistoryReader` directly; no application use case and no `HistoryReader` port variable is involved (block 2.1, messages 3 to 10). | Open issue OI-24: resolved by the amendment of ADR-0006 (MIL-007 task 12); acceptance pending. |
| SD-2 | [ADR-0006] lists the marimo notebook and the composition root in the infrastructure layer. | The composition root is `infrastructure/bootstrap.py` (block 1.0), but the notebook is in its own outermost `interface` layer (block 2.1). | Open issue OI-24: resolved by the amendment of ADR-0006, which records the fifth layer; acceptance pending. |
| SD-3 | [UC-001] steps 2 to 8 and [ADR-0005] outcome table do not mention re-reading the history after a successful append. | `AnalyzeBookings._malformed_lines` reads the history a second time through `HistoryReader.read` after the append (block 1.2 messages 20 and 21, block 1.5 messages 7 and 8), only to count malformed lines for a warning (same as AD-5). | Open issue OI-27: resolved, the history check after a run is kept on purpose and stated in UC-001 (MIL-007 tasks 9 and 13). |
| SD-4 | [DM-001] shows six kinds of Analysis (Lead Time Analysis to Guest Mix Analysis) as subclasses of Analysis, created as instances of their own kind. | One `Analysis` class is created for every kind (name in `AnalysisName`); the six kinds are six `Analyzer` strategies in `adapters` that create `Analysis` instances (block 1.1 messages 27 to 34). The generalization is not a class hierarchy. | Open issue OI-25: resolved by the DM-001 revision of MIL-009 task 1 (analysis kinds are analyzers); pending. |
| SD-5 | [ADR-0002] and [ADR-0007] define the six analyses; no decision covers a registered analysis without an analyzer. | `run_analyses` creates a placeholder `Analysis` with the notice `ANALYSIS_NOT_IMPLEMENTED` when no analyzer is registered (block 1.1 messages 34). With the six analyzers of `build_analyzers` this branch is not reached in production. | Open issue OI-26: resolved by the amendment of ADR-0006 (the placeholder analysis is kept as an extension point). |
| SD-6 | [OC-001] postconditions speak of Analysis Result instances retained by the Result History. | The Result History retains one JSON line per result and the read side never rebuilds `AnalysisResult` objects: `HistoryReadout.results` holds parsed JSON mappings and the notebook builds view models from them (block 2.1 messages 14 and 15, block 2.2 message 24). | Open issue OI-25: resolved by the DM-001 revision of MIL-009 task 1 (the retained result is a JSON document); pending. |
| SD-7 | [DM-001] association "Analysis Result is answered by Booking Submission". | The result does not point to the submission: `build_result` copies its source, reference, record count and content hash into `ResultInput` (block 1.1 message 37), so no submission object survives. | Open issue OI-25: resolved by the DM-001 revision of MIL-009 task 1 (a copy of the input metadata); pending. |

---

[OC-001]: ./operation-contracts.md
[SSD-001]: ./ssd.md
[DCD-001]: ./dcd.md
[DM-001]: ./domain-model.md
[UC-001]: ./use-cases/uc-001-analyze-hotel-bookings.md
[UC-002]: ./use-cases/uc-002-review-analysis-history.md
[ADR-0001]: ./adr/adr-0001-input-json-contract.md
[ADR-0002]: ./adr/adr-0002-result-json-contract.md
[ADR-0003]: ./adr/adr-0003-jsonl-history-and-retention.md
[ADR-0005]: ./adr/adr-0005-delivery-and-failure-semantics.md
[ADR-0006]: ./adr/adr-0006-architecture-and-invocation.md
[ADR-0007]: ./adr/adr-0007-analysis-methods.md
