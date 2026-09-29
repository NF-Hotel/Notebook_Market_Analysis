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
