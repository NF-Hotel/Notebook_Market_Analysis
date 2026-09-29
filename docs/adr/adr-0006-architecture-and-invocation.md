# ADR-0006: Architecture and Invocation

## Metadata
| Key | Value |
| --- | --- |
| ID | ADR-0006 |
| CrossReference | [US-001], [UC-001], [UC-002], [ADR-0005], [ADR-0007] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |

---

## Context

The application is "called by another system" (open issue OI-04 in [PP-001]), but how is not specified. The project rules require Clean Architecture (`domain`, `application`, `adapters`, `infrastructure`; dependencies pointing inward), polars rather than pandas, dataframes only in adapters and infrastructure, and `Decimal` for money. The marimo interface must show history results. None of `marimo`, `polars`, `holidays` or `pytest` is installed in `.venv` yet.

Options for invocation: a command-line program run as a process (simple, language-independent for the caller); a Python function call (only callers in the same Python process); an HTTP service (needs a running server, security and hosting decisions outside scope); the marimo app itself as the entry (interactive, not suitable for a machine caller).

## Decision

- **Invocation:** a command-line entry, `python -m hotel_booking_analysis analyze --input <file.json> [--config <file.toml>]`. The result JSON is written to standard output, and errors and progress to standard error. Exit codes follow [ADR-0005]. A caller that needs a different mechanism must raise it before coding starts. This is a proposal for the Calling-system owner (S02) to confirm.
- **Marimo:** a separate read-only notebook, `python -m marimo run` on `src/hotel_booking_analysis/interface/history_notebook.py`, that reads the history through the same history reader port as the CLI and never writes to it.
- **Layers** in package `hotel_booking_analysis` under `src/`:
  - `domain`: booking value objects, data-quality and result entities, analysis rules that need no libraries (lead-time bands, small-sample rule, association wording, estimate label). It imports nothing from other layers.
  - `application`: use cases (analyze bookings, list results, load a result) and ports as `Protocol` classes: booking reader, holiday calendar, analyzers, history repository, result serializer, clock. It imports only `domain`.
  - `adapters`: JSON and development-CSV readers, polars-based analyzers implementing the analyzer ports, holiday calendar over the `holidays` package, TOML configuration reader.
  - `infrastructure`: JSONL history repository with locking, command-line entry, marimo notebook, and the composition root.
  Import-linter contracts in `pyproject.toml` enforce the direction.
- **Dependencies to install at the start of the coding gateway:** runtime `polars`, `holidays`, `marimo`; development `pytest`, `import-linter`, `jsonschema`. Configuration uses the standard library `tomllib`. Python 3.13 as in `.venv`.
- **Tests:** mirror `src/`; ports are faked, file input and output use `tmp_path`.
- All Python under `src/` and `tests/` is written through the `python-developer` agent.

## Consequences

**Positive:**

- A process call works from any calling technology, and exit codes give a clear contract.
- The analysis core stays free of marimo and dataframe libraries in the domain and application layers.
- Marimo and the CLI share one history reader, so they cannot disagree on parsing.

**Negative:**

- A calling system that wants an HTTP or in-process interface needs a further decision and adapter.
- Keeping polars out of the application layer means analysis computation lives in adapters behind ports, splitting analysis logic between `domain` rules and adapter code.
- Starting a Python process per call has start-up cost.

## Affected Artifacts

- [US-001] — stories 08 to 10.
- [UC-001] — invocation of the main scenario.
- [UC-002] — marimo read-only notebook.
- [ADR-0005] — exit codes and delivery.
- [ADR-0007] — analyses implemented as adapters behind ports.

---

[US-001]: ../user-stories.md
[UC-001]: ../use-cases/uc-001-analyze-hotel-bookings.md
[UC-002]: ../use-cases/uc-002-review-analysis-history.md
[PP-001]: ../project-plan.md
[ADR-0005]: ./adr-0005-delivery-and-failure-semantics.md
[ADR-0007]: ./adr-0007-analysis-methods.md
