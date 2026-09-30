# Gateway 11: AI Insights Implementation

## Metadata
| Key | Value |
| --- | --- |
| ID | MIL-011 |
| CrossReference | [BC-001], [US-001] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-30 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |

---

## Purpose

Decide whether the AI insights are useful, safe and honest: for each analysis the app asks a reachable language model for an executive summary and for improvement suggestions aimed at a market analyst who wants to increase NF Hotel earnings, and puts them in the result. **Coding starts here only after MIL-008 and MIL-009 are Go**, and after MIL-010 has delivered the provider adapters and configuration. Code follows the project Python rules and is checked against DCD-001, SD-001 and OC-001.

The guardrails matter more than the text: the model receives only aggregate findings (never raw bookings), its suggestions are worded as hypotheses that name the sample sizes they rest on, they are marked AI-generated, and a failed or unsuitable answer leaves the analysis itself unchanged.

## Deliverable

Optional AI insights in the analyze flow: a model client for Ollama and LM Studio, prompt builders for the six analyses, an insight generator, a guardrail validator, result schema 1.1 with insights, a tolerant history reader for 1.0 and 1.1 results, the insight view in marimo, and tests with a fake model including an end-to-end acceptance test.

## Go / No-Go Criteria

| # | Criterion (objectively checkable) | Go | No-Go |
| --- | --- | --- | --- |
| 1 | The test suite passes, import-linter reports no layer violation, mypy strict and ruff are clean, and the coverage report is produced by pytest | All clean | Any failure |
| 2 | With the insight option off (the default) the result is identical to before and no provider is contacted | Verified by test | Any change or contact |
| 3 | With a fake model, each of the six analyses receives an executive summary and improvement suggestions in the result, in the ADR-0011 result 1.1 schema, and the result still validates | Six of six | Any analysis without insights |
| 4 | The prompt sent to the model contains no raw booking record and no booking identifier; a test scans every prompt built from the sample data | None found | Any raw data in a prompt |
| 5 | Every suggestion carries the sample size it rests on and hypothesis wording, and the guardrail validator rejects answers with causal wording, promised outcomes or missing sample sizes, marking that insight unavailable with a reason | Verified by test | Any unsuitable answer accepted |
| 6 | Every insight is labeled AI-generated with the model and provider that produced it | Present in JSON and in marimo | Any unlabeled insight |
| 7 | An unreachable provider, a timeout, a malformed answer and a rejected answer each leave the analysis and the rest of the result intact, report the reason, and never fail the run | Verified by test | Analysis lost or run failed |
| 8 | The returned JSON and the history line remain the same serialized result (ADR-0005), and a history containing both 1.0 and 1.1 results is listed and displayed by marimo | Verified by test | Different or unreadable |
| 9 | The code matches DCD-001 for these features, and the differences are listed | Matches or listed | Unlisted difference |

## Dependencies

| Depends on | Reason |
| --- | --- |
| MIL-010 | Provider adapters, configuration and output schemas are used here |
| MIL-009 | The guardrails, contracts and design are decided there |
| MIL-005 | The analysis findings that the insights summarize |

## Traceability

| Business Case objective / KPI / user story | Reference |
| --- | --- |
| BC-001 objective 8 | US-001.13, US-001.14, UC-005, UC-002 (revised) |

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
| 1 | Implement the model client for Ollama and LM Studio | Add the port and the two adapters that send a prompt and read the answer, with timeouts and clear errors. It reuses the discovery adapters and needs no analysis to run. | No | ADR-0009, DCD-001 |
| 2 | Implement prompt builders for the six analyses | Build for each analysis a prompt from its aggregate findings only, with the required answer structure and the guardrail instructions. Raw records and booking identifiers must never appear. | No | ADR-0010 |
| 3 | Implement the insight generator | For each analysis ask the model for an executive summary and improvement suggestions for a market analyst aiming to raise NF Hotel earnings, and collect them per analysis. | Yes | UC-005, US-001.13, US-001.14 |
| 4 | Implement the insight guardrail validator | Check every answer for causal wording, promised outcomes, missing sample sizes and unsupported figures, and mark rejected insights unavailable with a reason. It is what keeps the suggestions as hypotheses. | No | ADR-0010, ADR-0007 |
| 5 | Add result schema 1.1 and a tolerant history reader | Add the per-analysis insights to the result contract, keep 1.0 results readable in the history, and update the JSON Schema and its tests. | No | ADR-0011, ADR-0003 |
| 6 | Wire the optional insights into the analyze flow | Add the option to the analyze command and use case so that insights are generated only when asked, and so that any failure leaves the analysis and the run intact. | Yes | UC-005, ADR-0008, ADR-0010 |
| 7 | Implement the insight view in marimo | Show each analysis's summary and suggestions, labeled AI-generated with the model and provider and with their sample sizes, and show results saved without insights. | Yes | UC-002 (revised), US-001.13, US-001.14 |
| 8 | Add tests with a fake model | Test the generator, prompts, validator, schema and history compatibility with a deterministic fake model, including prompt scans for raw data and every failure case. | No | ADR-0010, ADR-0011 |
| 9 | Add the end-to-end acceptance test | Run the command with the insight option against a fake model server and check that the returned JSON, the history line and the marimo view show the same insights. | No | UC-005, UC-002, ADR-0005 |
| 10 | Update run documentation for the AI insights | Document the insight option, its configuration, the guardrails and the limits (AI text is a hypothesis, not a forecast) in the README, verifying each documented command. | No | ADR-0008, ADR-0010, ADR-0012 |

---

[BC-001]: ../business-case.md
[US-001]: ../user-stories.md
