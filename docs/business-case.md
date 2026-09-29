# Business Case

## Metadata
| Key | Value |
| --- | --- |
| ID | BC-001 |
| CrossReference | [SA-001], [UCD-001] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | TBD (S04 not yet named) |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | TBD (S04 not yet named) |

---

## Executive Summary

Hotel booking records are hard to interpret without a consistent, honest analysis of timing, arrivals, holidays, cancellations, guest mix and room value. This project builds a marimo application that a calling system invokes with a JSON file of booking records. The application validates the data, runs the analyses, returns the result to the caller as JSON, appends it to a local JSONL history with a configurable retention limit, and lets marimo display prior results. The application must show its data limitations and describe associations, never causes. The recommendation is to proceed, in gateways that complete and review the requirement, contract and design artifacts before any code is written.

## Methodological and Standards Foundation

Artifacts follow the use-case-driven sequence of Larman's *Applying UML and Patterns* (business case, actors and goals, user stories and use cases, domain model, then design decisions). Quality is reviewed against the ISO/IEC 25010:2023 characteristics through the framework's QC checklists. Code is later structured with Clean Architecture.

## Problem Statement

- Booking timing, holiday effects, cancellations and room value are not analyzed in one repeatable, documented way.
- Analyses of small or partial-year data can suggest causes that the data cannot support.
- Data quality problems (missing fields, invalid dates, duplicate booking IDs) are easy to miss.
- A calling system needs a machine-readable result, and people need to see earlier results, but no result history or retention rule exists.

## Business Opportunity

A single application makes the analyses repeatable, makes data limits visible, hands a stable JSON result to the calling system and keeps a bounded, viewable history, so decisions about booking and pricing rest on documented evidence.

## Objectives

1. Report data quality (record count, date coverage, missing or invalid values, duplicate booking IDs) and identify analyses that are unavailable because fields are missing.
2. Provide the lead-time, Cambodian-holiday, seasonality and booking-pace, and cancellation analyses, each showing denominators and describing associations only.
3. Provide the room-value estimate (labeled an estimate, not realized revenue), stay patterns, and the guest and booking mix analysis.
4. Return each completed analysis to the calling system as JSON.
5. Append each result as one JSON object per line to a local JSONL history and keep only the latest N results, where N comes from a configuration file and defaults to 10.
6. Display prior results from the history in marimo, with a way to select among them and see when each was produced.
7. Deliver through gateways in which requirement, contract and design artifacts are completed and reviewed before the code that depends on them.

## Scope

### In Scope

- JSON input from the calling system, validation and data preparation, and a data-quality report.
- The analyses in objectives 2 and 3, using the Python `holidays` package for Cambodia (`KH`).
- The JSON result, the JSONL history, the retention setting and configuration file, and the marimo display of saved results.
- A development-only fallback to `./data/example/nf_hotel_bookings.csv` when no JSON is supplied.
- Input, result, history and configuration contracts, decided in Architecture Decision Records.

### Out of Scope

- Causal inference or predictive modeling of cancellations, prices or holiday effects.
- Realized revenue, payments, taxes, discounts and adjustments.
- A production CSV input path.
- Storing raw booking records in results or history unless a documented need arises.
- Authentication, multi-user access control and remote hosting of the marimo interface.
- Synchronization of bookings from any hotel system.

## Expected Benefits

### Tangible Benefits

- Repeatable analyses that return the same result for the same input.
- A stable, versioned JSON result that a calling system can consume.
- A bounded history file whose size is controlled by configuration.
- Data problems reported with counts rather than silently ignored.

### Intangible Benefits

- Greater trust in findings because limits and sample sizes are visible.
- A shared vocabulary for booking analysis across the artifacts.
- A documented decision trail for every contract and architecture choice.

## Strategic Alignment

The project supports evidence-based decisions about hotel bookings, and its documentation-first approach keeps the application reviewable and maintainable. No organization-level strategy document is supplied, so no further alignment is claimed.

## Success Criteria

| # | Criterion | Target | Objective |
| --- | --- | --- | --- |
| 1 | Analyses with missing required fields are reported as unavailable, with no fabricated values | 100% of such analyses | 1 |
| 2 | Reported rates and comparisons show their denominator | 100% of reported rates | 2 |
| 3 | The JSON returned to the caller and the appended history line are identical for one run | 100% of runs in the acceptance test | 4, 5 |
| 4 | After more runs than N, the history holds exactly the latest N results, and 10 when no value is configured | Exactly N (or 10) | 5 |
| 5 | Every saved result in the history is selectable in marimo with its generated time | 100% of retained results | 6 |
| 6 | Every code task cites an approved artifact it implements | 100% of coding tasks | 7 |

No baseline exists because there is no earlier process to measure.

## Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Production JSON schema is not supplied | Validation cannot be finalized | Decide it with the calling-system owner (S02) in ADR-0001 before coding |
| Small or partial-year data | Holiday and seasonal findings mislead | Sample-size flags and association-only wording (ADR-0007) |
| Concurrent callers corrupt the history file | Lost or malformed results | Decide locking and atomic append in ADR-0003 |
| Failure while returning or saving a result | Caller believes a result was delivered | Define failure behavior in ADR-0005 and never report success on failure |
| Booking data exposed through results | Data protection concern | Exclude raw records from results; assess sensitivity in ADR-0002 |
| One person acting as author and reviewer | Weak review independence | Name an independent reviewer (S04) before review records are issued |

## Assumptions

- The production input is JSON; the example CSV is development context only and is not a production schema.
- The calling system is the primary actor; a human analyst may view history in marimo (open issue OI-03 in [PP-001]).
- The `holidays` package supports `KH` for the years present in the data; this is unverified.
- Price per night is a single nightly figure, and total nights are weekend plus week nights.

## Constraints

- No project start date or deadline is known.
- Retention must be read from a configuration file and default to 10 when omitted.
- Coding may start only after the requirement, contract and design gateways are Go.
- Python code follows the repository rules: type annotations, Clean Architecture layers, polars before pandas, `Decimal` for money.

## Cost–Benefit Assessment

Qualitative, because no cost, budget or benefit figures are supplied.

| Costs | Benefits |
| --- | --- |
| Effort to write and review the artifacts and code across six gateways | Repeatable, documented analyses with visible limits |
| Review time from an independent reviewer (S04) | Stable result contract for the calling system |
| Maintenance of the history and configuration behavior | Bounded, viewable history of past analyses |

## Stakeholders

| ID | Role in this project |
| --- | --- |
| [S01] | Approves scope and gateway decisions |
| [S02] | Confirms the input and result contracts |
| [S03] | Confirms data use and data-quality rules |
| [S04] | Reviews artifacts before gateway decisions |
| [S05] | Confirms the history display meets the need (provisional) |

Stakeholder details are in [SA-001].

## Recommendation

Proceed. The goal is clear and bounded, and the gateway approach lets each contract and design decision be reviewed before code exists.

---

[SA-001]: ./stakeholder-analysis.md
[PP-001]: ./project-plan.md
[S01]: ./stakeholder-analysis.md
[S02]: ./stakeholder-analysis.md
[S03]: ./stakeholder-analysis.md
[S04]: ./stakeholder-analysis.md
[S05]: ./stakeholder-analysis.md
[UCD-001]: ./use-case-diagram.md
