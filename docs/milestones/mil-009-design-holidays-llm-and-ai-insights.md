# Gateway 9: Design for Holidays, LLM Discovery and AI Insights

## Metadata
| Key | Value |
| --- | --- |
| ID | MIL-009 |
| CrossReference | [BC-001], [US-001] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-30 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-30 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |

---

## Purpose

Decide whether the contracts, architecture decisions and behavior and design artifacts for the new capabilities are settled before any code is written. Unlike MIL-007, which documented code that already existed, this gateway is a design made first: the sequence and class diagrams show the intended design, and the code in MIL-010 to MIL-012 is checked against them.

Every new use case gets the full set: a system sequence diagram, operation contracts, sequence diagrams and a design class diagram. Because those types are single documents (SSD-001, OC-001, SD-001, DCD-001), each new use case is added as a section of the existing document and the task revises that document.

**The question of how the app is called** (a command line with subcommands, or a FastAPI service) is decided here in ADR-0008, so that the design artifacts and the code follow one interface. The proposal is to keep the command line and add subcommands, and to plan FastAPI only as the conditional gateway MIL-012 if the calling-system owner needs HTTP.

## Deliverable

Revised DM-001; ADR-0008 (invocation interface), ADR-0009 (LLM provider discovery and connection), ADR-0010 (AI insight generation and guardrails), ADR-0011 (output contracts: holiday listing, provider listing, result 1.1 with insights) and ADR-0012 (configuration extension); SSD-001, OC-001, SD-001 and DCD-001 revised for UC-003, UC-004 and UC-005 (and UC-002's insight display); and a review record for each reviewed document.

## Go / No-Go Criteria

| # | Criterion (objectively checkable) | Go | No-Go |
| --- | --- | --- | --- |
| 1 | ADR-0008 compares the command line with subcommands and a FastAPI service against the calling-system owner's needs (long model calls, remote or other-language callers, concurrency, extra dependencies), states the decision, and says what happens to the exit codes of ADR-0005 | Decision stated and accepted by S02 | Undecided |
| 2 | ADR-0009 fixes how Ollama and LM Studio are found and queried (addresses, the endpoints used to list models, timeouts), how a model is chosen, and the behavior when neither is reachable | Fixed | Any of these open |
| 3 | ADR-0010 fixes what is sent to the model (aggregate findings only, no raw records), the required structure of the answer, the wording guardrails (hypotheses, sample sizes, no causal claims), the AI-generated label, and what happens on failure, timeout or an unsuitable answer | Fixed | Any of these open |
| 4 | ADR-0011 defines the JSON of the holiday listing, of the provider listing, and result schema version 1.1 with per-analysis insights, and states that a 1.0 result in the history stays readable | Defined | Any output undefined |
| 5 | ADR-0012 defines the new configuration keys with defaults and validation, and every option is off or safe by default | Defined | Any key without a default or validation |
| 6 | DM-001 covers every new concept used by the ADRs (for example Language Model Provider, Language Model, AI Insight, Executive Summary, Improvement Suggestion, Holiday Calendar Listing) with multiplicities | Covered | Any concept missing |
| 7 | Every main-scenario step and extension of UC-003, UC-004 and UC-005 maps to an SSD-001 message; every message has an OC-001 contract; every contract postcondition is realized by an SD-001 diagram; every class in DCD-001 for the new features is designed on the layers of ADR-0006 with no dependency against the direction | Complete | Any gap |
| 8 | An RC record exists for DM-001, SSD-001, OC-001, SD-001 and DCD-001 (revisions) with verdict Go (or Go-with-conditions and all action items closed); each ADR is approved by S04 | All Go | Any No-Go or open item |

## Dependencies

| Depends on | Reason |
| --- | --- |
| MIL-008 | The design realizes the approved stories and use cases |
| MIL-007 | SSD-001, OC-001, SD-001 and DCD-001 are the documents extended here |

## Traceability

| Business Case objective / KPI / user story | Reference |
| --- | --- |
| BC-001 objectives 8 to 10 | US-001.11 to US-001.14, UC-003, UC-004, UC-005 |

## Ownership

| Role | Stakeholder ID (SA) |
| --- | --- |
| Owner | S01 |
| Approving reviewer | S04 |

## Target Date

TBD, open issue OI-01 in PP-001.

## Tasks

| # | Task | Summary | Needs its own Use Case/User Story? | Reference |
| --- | --- | --- | --- | --- |
| 1 | Revise DM-001 for LLM providers and AI insights | Add the concepts behind the new stories: language model provider, language model, provider status, AI insight, executive summary, improvement suggestion and holiday calendar listing, with their associations. It keeps one vocabulary for the contracts and code. The same revision states how the as-built model differs from DM-001 (analysis kinds as strategies, the history as a file behind two ports, the result holding a copy of the input metadata, transient group statistics, retained results as JSON on the read side) and resolves OI-25. | No | DM-001 |
| 2 | Write ADR-0008 invocation interface | Decide whether the app is called through command-line subcommands or a FastAPI service, given the long model calls and a possibly remote caller. It resolves OI-17 and closes OI-04. | No | ADR-0008, UC-003, UC-004, UC-005 |
| 3 | Write ADR-0009 LLM provider discovery and connection | Decide how Ollama and LM Studio are found and queried, the endpoints and timeouts, and how a model is chosen. Discovery must be a quick, read-only check that never starts an analysis. | No | ADR-0009, UC-004 |
| 4 | Write ADR-0010 AI insight generation and guardrails | Decide what data reaches the model (aggregates only), the structured answer required, and the wording rules that keep suggestions as hypotheses tied to sample sizes. It also fixes behavior on failure, timeout and unsuitable answers. | No | ADR-0010, UC-005 |
| 5 | Write ADR-0011 output contracts and result 1.1 | Define the JSON of the holiday listing and the provider listing, and add per-analysis insights to the result as schema version 1.1 while keeping 1.0 results readable in the history. | No | ADR-0011, ADR-0002 |
| 6 | Write ADR-0012 configuration extension | Add the configuration keys for provider addresses, model choice, timeouts and the insight option, with defaults and validation, extending ADR-0004 without changing retention behavior. | No | ADR-0012, ADR-0004 |
| 7 | Revise SSD-001 for UC-003, UC-004 and UC-005 | Add the system sequence diagrams of the new use cases, including the no-provider and model-failure flows, and the insight display in UC-002. It is written before the code. | No | SSD-001, UC-003, UC-004, UC-005 |
| 8 | Revise OC-001 for the new operations | Add one contract per new system operation with preconditions, postconditions in domain-model terms and exceptions. | No | OC-001, SSD-001 |
| 9 | Revise SD-001 for the new operations | Add sequence diagrams that realize each new contract with the intended objects and ports, annotated with the patterns used. | No | SD-001, OC-001 |
| 10 | Revise DCD-001 for the new design | Add the designed classes, ports and adapters for the new features on the layers of ADR-0006, traced to the contracts and diagrams. Later code is checked against it. | No | DCD-001, SD-001, DM-001 |
| 11 | Review DM-001 (revision) | Produce the RC record for the revised domain model against QC-DM-001. | No | DM-001, QC-DM-001 |
| 12 | Review SSD-001 (revision) | Produce the RC record for the revised system sequence diagrams against QC-SSD-001. | No | SSD-001, QC-SSD-001 |
| 13 | Review OC-001 (revision) | Produce the RC record for the revised operation contracts against QC-OC-001. | No | OC-001, QC-OC-001 |
| 14 | Review SD-001 (revision) | Produce the RC record for the revised sequence diagrams against QC-SD-001. | No | SD-001, QC-SD-001 |
| 15 | Review DCD-001 (revision) | Produce the RC record for the revised design class diagram against QC-DCD-001. | No | DCD-001, QC-DCD-001 |

---

[BC-001]: ../business-case.md
[US-001]: ../user-stories.md
