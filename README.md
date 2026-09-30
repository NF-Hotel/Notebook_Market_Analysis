# Notebook Market Analysis: hotel booking analysis

A Python application that a calling system runs on a JSON file of hotel bookings. It validates the
records, runs six analyses (lead time, holidays, seasonality, cancellations, room value, guest
mix), returns one result as JSON on standard output and keeps the latest results in a JSONL
history. A read-only marimo notebook shows the data-quality summary, the six analyses and the
retained results.

## Project documentation

The project is planned and documented with the SQA and QC framework in `framework/`. Every
document lives under `docs/`:

| What | Where |
| --- | --- |
| Business case, stakeholders, use case diagram | `docs/business-case.md`, `docs/stakeholder-analysis.md`, `docs/use-case-diagram.md` |
| Project plan and the gateways (phases, tasks, Go/No-Go criteria) | `docs/project-plan.md`, `docs/milestones/` |
| User stories and use cases | `docs/user-stories.md`, `docs/use-cases/` |
| Domain model and architecture decisions (input, result, history, configuration, delivery, architecture, analysis methods) | `docs/domain-model.md`, `docs/adr/` |
| Behavior and design of every use case (as built) | `docs/ssd.md`, `docs/operation-contracts.md`, `docs/sequence-diagrams.md`, `docs/dcd.md` |
| Review records and traceability matrix | `docs/sqa/reviews/`, `docs/sqa/traceability-matrix.md` |
| Artifact registry (locations and next versions) | `docs/artifact-registry.md` |

Tasks are tracked as GitHub milestones (one per gateway) and issues; each pull request closes the
issues it completes.

## Repository layout

```
src/hotel_booking_analysis/
  domain/          entities, value objects and the analysis rules (no libraries)
  application/     use cases and ports
  adapters/        readers, polars-based analyzers, holiday calendar, serializer
  infrastructure/  JSONL history, command line entry, composition root
  interface/       marimo history notebook and its view models
tests/             mirrors src/
docs/              planning and design artifacts
data/example/      development sample (git-ignored except the folder)
```

Dependencies point inward (interface, infrastructure, adapters, application, domain), enforced by
import-linter.

## Status

| Gateway | Scope | State |
| --- | --- | --- |
| MIL-001 to MIL-003 | Baseline, requirements, contracts and design | Documents drafted and reviewed (review records are drafts pending the independent reviewer) |
| MIL-004 | Core pipeline: input, result, history, retention, command line | Implemented |
| MIL-005 | The six analyses | Implemented |
| MIL-006 | marimo notebook and acceptance | Implemented |
| MIL-007 | System sequence diagrams, operation contracts, sequence diagrams, design class diagram | Drafted as built, reviews pending |
| MIL-008, MIL-009 | Requirements and design for holidays, LLM discovery and AI insights | Approved |
| MIL-010 | `holidays` and `llm-providers` commands, `[llm]` configuration | Implemented |
| MIL-011 | AI insights (`analyze --insights`), result schema 1.1, insight view | Implemented |
| MIL-012 | HTTP service (`serve`), a second entry beside the command line | Implemented |

Not built yet: charts (the notebook shows tables), and real production input, whose schema is a
proposal until the calling-system owner confirms it (ADR-0001).

MIL-007 documents the built design for every use case: system sequence diagrams
(`docs/ssd.md`), operation contracts (`docs/operation-contracts.md`), sequence diagrams
(`docs/sequence-diagrams.md`) and the design class diagram (`docs/dcd.md`). They are drafts until
reviewed.

## Install

Requires Python 3.13 or newer.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

On Linux or macOS use `.venv/bin/python` instead of `.venv\Scripts\python.exe`.

## How a calling system invokes it

```powershell
.venv\Scripts\python.exe -m hotel_booking_analysis analyze --input bookings.json --config hotel_analysis.toml
```

- `--input` is a UTF-8 JSON file whose top level is an array of booking objects (ADR-0001).
- `--config` is optional; see Configuration below.
- Standard output holds the result JSON and nothing else (ADR-0002). The same bytes are appended to
  the history file before they are returned.
- Standard error holds log lines and, on a delivery failure, an error message.

Exit codes (ADR-0005):

| Code | Meaning | Standard output |
| --- | --- | --- |
| 0 | Analysis completed, saved to the history and returned | the result |
| 2 | Input or configuration error | a result with `status` `failed` and an `error` |
| 3 | History write or retention failure | nothing; message on standard error |
| 4 | Saved to the history but could not be written to the caller | nothing; message on standard error names the `result_id` |

The result contract is defined in `docs/adr/adr-0002-result-json-contract.md`; the history and
retention in `docs/adr/adr-0003-jsonl-history-and-retention.md`.

## AI insights (optional)

```powershell
.venv\Scripts\python.exe -m hotel_booking_analysis analyze --input bookings.json --insights
```

`--insights` asks a local language model (Ollama or LM Studio) for an executive summary and up to
five improvement suggestions per analysis, aimed at a market analyst who looks for ways to raise
NF Hotel earnings (UC-005, ADR-0010). Without `--insights` (the default) no provider is contacted
and the result is exactly the result of version 1.0.

- **What the model sees:** only the aggregate findings of one analysis and the data-quality counts.
  Never a booking record, a booking identifier, the input file name or its hash.
- **Which model:** `llm.provider` and `llm.model` if set; otherwise the first reachable provider in
  the order `ollama`, `lmstudio`, with the first model it lists (ADR-0009). Check what is reachable
  with `llm-providers`. The first listed model may be unsuitable (for example an embedding model);
  set `llm.model` to choose one.
- **Result 1.1:** with `--insights` a completed result has `schema_version` `"1.1"`, a top-level
  `insights` (`requested`, `provider`, `model`, `prompt_version`) and an `insight` in every entry of
  `analyses` with `status` `available`, `unavailable` or `not_applicable`, and the label
  `AI-generated` when available. The JSON Schema is
  `src/hotel_booking_analysis/adapters/schemas/analysis_result_1_1.schema.json`. The returned JSON
  and the history line are the same bytes, and the history viewer shows the insights.
- **Guardrails:** an answer is rejected and its text dropped when its structure is wrong, when it
  uses causal words ("because", "leads to" and so on), promises or forecasts earnings, names a
  percentage or amount that is not in the findings, names a sample size that is not in the
  findings, lacks the words "small sample" for a small group, or lacks hypothesis wording ("may",
  "could" and so on). That insight is then `unavailable` with the reason `BAD_STRUCTURE` or
  `GUARDRAIL_REJECTED`. Small models are often rejected: in a trial run with `gemma4:e2b`
  on the development sample, five of six insights were rejected and one timed out. Rejecting is
  intended (ADR-0010); a larger model, or `llm.model` set to a better one, gives more accepted
  insights.
- **Failures never fail the run:** `NO_PROVIDER`, `NO_MODEL`, `TIMEOUT` and `MODEL_ERROR` also make
  an insight `unavailable`. The analyses stay unchanged, the result `status` becomes
  `completed_with_warnings` with the notice `INSIGHTS_UNAVAILABLE`, and the exit code stays 0.
- **Limits:** one request per available analysis, in order, no retry, each within
  `llm.generation_timeout_seconds` (default 120 s), so a run can take up to 6 x 120 s plus the
  discovery time. Set the process timeout of the calling system to match. The text is regenerated on
  every run and differs between runs.
- **AI text is a hypothesis, not a forecast.** The checks look at form, words and figures, not at
  truth. A wrong sentence can pass them, so read each suggestion next to its sample size and the
  analysis it belongs to. The notebook shows the sample size with every suggestion.
- `[llm]` values are validated when `--insights` is given; an invalid value gives exit code 2 and
  names the key.

## HTTP service (optional)

```powershell
.venv\Scripts\python.exe -m hotel_booking_analysis serve --port 8000 --config hotel_analysis.toml
```

A FastAPI service that calls the same use cases as the command line (ADR-0008 amendment, ADR-0013).
The command line is unchanged and stays the reference. Every route returns exactly the JSON the
command with the same input writes, and `POST /analyze` returns the line that was appended to the
history.

| Route | Same as | Notes |
| --- | --- | --- |
| `POST /analyze?insights=false` | `analyze [--insights]` | body: the JSON array of bookings (ADR-0001), header `Content-Type: application/json` |
| `GET /holidays?years=2024-2026` | `holidays` | `years` as for `--years`; omitted means the current year |
| `GET /llm-providers` | `llm-providers` | |
| `GET /health` | | `{"status":"ok"}` |

```powershell
curl.exe -X POST "http://127.0.0.1:8000/analyze" -H "Content-Type: application/json" --data-binary "@bookings.json"
curl.exe "http://127.0.0.1:8000/holidays?years=2026"
curl.exe "http://127.0.0.1:8000/llm-providers"
```

The interactive API description is at `/docs` and `/redoc`, and the OpenAPI document at
`/openapi.json`; its response schemas are the JSON Schemas of the repository.

Status codes follow the exit codes of the command (ADR-0005, ADR-0013):

| Status | Meaning | Body |
| --- | --- | --- |
| 200 | Completed (also `completed_with_warnings`, unavailable years, unreachable providers) | the document |
| 422 | Input or configuration error, invalid `years`, invalid `[llm]` value | the failed document the command prints; nothing stored |
| 500 | History write or retention failure, or the answer could not be built | `{"status":"error","error":{"code":"HISTORY_FAILED" or "DELIVERY_FAILED",...}}`; with `result_id` for `/analyze` when a result was saved |
| 415 | `Content-Type` is not `application/json` | framework default |

- **Bind and security:** the service listens on `127.0.0.1` by default and has no authentication, no
  TLS, no rate limit and no limit on the size of a request body. `serve` warns when the host is not
  local. Put it behind a gateway before exposing it. The request body is never read from a
  client-named path; `input.reference` of the result is `request-body.json`.
- **Timeouts:** the service has no cutoff. A request with `insights=true` lasts as long as the
  bound of ADR-0009 and ADR-0012: up to 2 x `llm.discovery_timeout_seconds` plus 6 x
  `llm.generation_timeout_seconds`, 12 minutes and 4 seconds with the defaults. Set the timeout of
  the HTTP client, and of any proxy in front, to match. There is no job-and-poll design.
- **Concurrency:** routes run in the framework's thread pool (40 threads), so a long insight request
  does not block the listings; the history lock file serializes the appends.
- Stop the service with Ctrl+C. The exit status after a signal depends on the platform.

## Holiday listing

```powershell
.venv\Scripts\python.exe -m hotel_booking_analysis holidays --years 2024-2026
```

Returns the Cambodian (`KH`) public holidays as JSON without running an analysis or touching the
history (UC-003, ADR-0008, ADR-0011). The data comes from the `holidays` package; the notice
`CALENDAR_SOURCE` names its version.

- `--years` is one year (`2025`), an inclusive range (`2024-2026`) or a comma list (`2024,2026`).
  Years are 1900 to 2100, at most 30. Omitted means the current year (notice `DEFAULT_YEAR_USED`).
- A year the calendar has no data for is listed as `unavailable` with the reason
  `NO_CALENDAR_DATA`; no holiday is invented.
- `--config` is optional; the file is only checked to be valid TOML.
- Exit codes: 0 listing produced, 2 invalid `--years` or unreadable configuration (a `failed`
  document with `error` on standard output), 4 the listing could not be written to the caller.

The output shape is `src/hotel_booking_analysis/adapters/schemas/holiday_calendar_1_0.schema.json`.

## LLM provider listing

```powershell
.venv\Scripts\python.exe -m hotel_booking_analysis llm-providers --config hotel_analysis.toml
```

Lists whether Ollama and LM Studio are reachable and which models each offers, as JSON (UC-004,
ADR-0009, ADR-0011). It only reads: no model is asked to generate text, no booking data is sent,
and the history is not touched.

- `providers` always holds `ollama` then `lmstudio`, each with `base_url`, `status`
  (`reachable` or `unreachable`), `reason` and `models`.
- The reason of an unreachable provider is `CONNECTION_REFUSED`, `TIMEOUT`, `UNEXPECTED_ANSWER` or
  `NETWORK_ERROR`. An unreachable provider is a normal entry, not an error; when none is
  reachable the notice `NO_PROVIDER_REACHABLE` is added and the exit code is still 0.
- Each provider is checked within `llm.discovery_timeout_seconds` (a total limit, default 2 s).
  On Windows a connection to a port where nothing listens can take about 2 s to be refused, so a
  stopped provider may show `TIMEOUT` instead of `CONNECTION_REFUSED`; raise the timeout to see
  the refusal.
- Only local addresses (`localhost`, `127.0.0.1`, `::1`) are accepted unless `llm.allow_remote`
  is `true`.
- Exit codes: 0 listing produced, 2 unreadable configuration or an invalid `[llm]` value (a
  `failed` document naming the key), 4 the listing could not be written to the caller.

The output shape is `src/hotel_booking_analysis/adapters/schemas/llm_providers_1_0.schema.json`.

## Configuration

`hotel_analysis.toml` in the working directory, or the file named by `--config` or by the
`HOTEL_ANALYSIS_CONFIG` environment variable (ADR-0004). A missing file means defaults. Copy
`hotel_analysis.toml.example`, which lists every key with its default:

| Key | Default | Meaning |
| --- | --- | --- |
| `environment` | `"production"` | `"production"` or `"development"`; only `"development"` allows the CSV fallback |
| `history.retention` | `10` | number of results the history keeps |
| `history.path` | `output/analysis_history.jsonl` | history file, relative to the working directory |
| `analysis.holiday_windows_days` | `[1, 3, 7]` | window sizes in days around holidays |
| `analysis.min_group_size` | `30` | groups below this are flagged as small samples |
| `llm.ollama_url` | `http://localhost:11434` | base URL of Ollama |
| `llm.lmstudio_url` | `http://localhost:1234` | base URL of LM Studio |
| `llm.discovery_timeout_seconds` | `2` | total time limit per provider when listing models (number above 0) |
| `llm.generation_timeout_seconds` | `120` | total time limit per model request (number above 0; used by `analyze --insights`) |
| `llm.provider` | `""` | `""` (automatic), `"ollama"` or `"lmstudio"` |
| `llm.model` | `""` | `""` (automatic) or a model name |
| `llm.allow_remote` | `false` | `true` allows a base URL that is not on this machine |
| `llm.temperature` | `0` | model temperature, 0.0 to 1.0 |

The `[llm]` values are validated only by `llm-providers` and `analyze --insights`; an
invalid value names its key and gives exit code 2 there, and is ignored by `analyze` and
`holidays` (ADR-0012).

## History notebook

Start it from the working directory that holds `output/` (and `hotel_analysis.toml`, if used):

```powershell
.venv\Scripts\python.exe -m marimo run src/hotel_booking_analysis/interface/history_notebook.py
```

`marimo run` serves it in the browser; with the console script on the path,
`marimo run src/hotel_booking_analysis/interface/history_notebook.py` is the same command. The
notebook only reads the history. Pick a retained result (newest first, with its generated time) to
see its data quality and the six analyses, each with a limitations notice. Use the selectors above
each analysis to change the split, series, granularity, holiday window size or attribute. An empty
or partly unreadable history shows a message instead of failing.

## Development fallback (example CSV)

When the configuration says `environment = "development"` and no `--input` is given, the app reads
`data/example/nf_hotel_bookings.csv` (semicolon-delimited, `dd-mm-yyyy`) from the working directory
and the result states `"source": "development_sample"`. Run it from the repository root:

```powershell
.venv\Scripts\python.exe -m hotel_booking_analysis analyze --config hotel_analysis.toml
```

In any other environment, or when `--input` is given, the CSV is never used; no input in
production exits with code 2.

## Reading the results

- Findings describe associations in the supplied records. They are not causes, and other factors
  are not adjusted for.
- Every figure is shown with the number of records it rests on; groups below `min_group_size` are
  flagged as small samples and are not compared.
- Room value is an estimate (price per night times total nights), not realized revenue.

## Checks

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\lint-imports.exe
.venv\Scripts\python.exe -m mypy src tests
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
```

`pytest` also prints a coverage report (line and branch, with the missing lines per file) and
writes an HTML report to `htmlcov/index.html`; both come from `pytest-cov`, configured in
`pyproject.toml` under `[tool.pytest.ini_options]` and `[tool.coverage]`. No minimum coverage is
enforced yet. The command line run by the subprocess tests is measured too. The marimo notebook
cells are executed by marimo and their lines are not attributed (`history_notebook.py` and part of
`marimo_render.py` read low); the view models behind them are tested directly.
