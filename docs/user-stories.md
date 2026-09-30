# User Story

## Metadata
| Key | Value |
| --- | --- |
| ID | US-001 |
| CrossReference | [UCD-001], [BC-001], [MIL-001], [MIL-002], [MIL-003], [MIL-004], [MIL-005], [MIL-006], [MIL-008], [UC-001], [UC-002], [UC-003], [UC-004], [UC-005] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-30 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-30 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-30 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |

---

## Purpose and Scope

Stories for the epic in [MIL-002]: analyze hotel bookings supplied as JSON by the Calling system, return and keep the result, and review prior results. Stories US-001.11 to US-001.15 (added in [MIL-008]) cover the holiday listing, the provider listing, the AI executive summary and improvement suggestions per analysis, and the Analyst's view of them. Roles match the actors in [UCD-001]. The Analyst is provisional (open issue OI-03 in [PP-001]). Field names below come from the example CSV and are not the production schema, which is decided in ADR-0001. Where a field is missing, the dependent analysis is reported as unavailable, never estimated. For the AI stories, the tension in [BC-001] applies: the suggestions aim to increase NF Hotel earnings, but they are hypotheses drawn from observed associations, never causes, forecasts or promised earnings. Assumptions recorded here: local models only (OI-14), English (OI-15), insights inside the result and history (OI-16), regenerated per run and not cached (OI-19), the holiday listing covers Cambodia only, for the years requested with the current year as default (OI-18), and the Analyst (S05) is the market analyst who reads the insights (OI-20); the open issues are in [PP-001].

## Story List

### US-001.01 — Load and understand data

**As a** Calling system, **I want** a data-quality summary of the booking records I supply, **so that** I know how far the analyses can be trusted.

**Acceptance Criteria**

- Given a JSON file of booking records, when the analysis runs, then the result reports the record count, the earliest and latest booking and arrival dates, and the count of missing and invalid values per field.
- Given records with the same booking ID, when the analysis runs, then the result reports the number of duplicate booking IDs.
- Given a field an analysis needs is absent from all records, when the analysis runs, then that analysis is marked unavailable with the missing field named, and no value is produced for it.

| Traces to | Size | INVEST exceptions |
| --- | --- | --- |
| [UC-001], [MIL-002] | fits one iteration | none |

### US-001.02 — Explore lead time

**As a** Calling system, **I want** a lead-time analysis, **so that** I understand how far ahead guests book.

**Acceptance Criteria**

- Given lead time is present, when the analysis runs, then the result shows the lead-time distribution overall and split by cancellation status, arrival period, market segment and customer type for the fields that exist.
- Given both booking date and arrival date are present, when the analysis runs, then the result compares the supplied lead time with the date difference and reports the count of records that differ.
- Given a group has too few records, when the analysis runs, then the group is flagged as a small sample with its count.

| Traces to | Size | INVEST exceptions |
| --- | --- | --- |
| [UC-001], [MIL-002] | fits one iteration | none |

### US-001.03 — Analyze Cambodian holidays

**As a** Calling system, **I want** booking and arrival behavior compared around Cambodian holidays, **so that** I can see whether activity is associated with holidays.

**Acceptance Criteria**

- Given bookings spanning some years, when the analysis runs, then Cambodian public holidays come from a maintained holiday calendar (the source is fixed in ADR-0007) for exactly the years present in the data.
- Given holiday dates, when the analysis runs, then booking-date behavior and arrival-date behavior are reported separately, each compared for the holiday itself and for configurable windows before and after it with non-holiday periods.
- Given the calendar has no data for a year, when the analysis runs, then that year is reported as unavailable and no holiday is invented.
- Given results are shown, then each comparison shows its counts, and the wording states an association and does not state a cause.

| Traces to | Size | INVEST exceptions |
| --- | --- | --- |
| [UC-001], [MIL-002] | fits one iteration | none |

### US-001.04 — Understand seasonality and booking pace

**As a** Calling system, **I want** seasonality and booking-pace summaries, **so that** I see when bookings are made and when guests arrive.

**Acceptance Criteria**

- Given booking and arrival dates, when the analysis runs, then bookings are summarized by booking date and arrivals by arrival date, as separate series, by week and month.
- Given cancellation status and price are present, when the analysis runs, then cancellation rate and price are summarized per period with the record count.
- Given the data covers part of a year, when the analysis runs, then the result states which periods are incomplete.

| Traces to | Size | INVEST exceptions |
| --- | --- | --- |
| [UC-001], [MIL-002] | fits one iteration | none |

### US-001.05 — Investigate cancellations

**As a** Calling system, **I want** cancellation rates compared across booking attributes, **so that** I can see which groups cancel more often.

**Acceptance Criteria**

- Given cancellation status is present, when the analysis runs, then cancellation rates are reported by lead-time band, deposit type, market segment, customer type, arrival period, special requests and booking changes for the fields that exist.
- Given each rate, then its numerator, denominator and small-sample flag are shown.
- Given results are shown, then wording states associations only and makes no causal or predictive claim.

| Traces to | Size | INVEST exceptions |
| --- | --- | --- |
| [UC-001], [MIL-002] | fits one iteration | none |

### US-001.06 — Estimate room value and stay patterns

**As a** Calling system, **I want** length of stay and an estimated room value, **so that** I understand stay patterns and approximate booking value.

**Acceptance Criteria**

- Given weekend and weekday night counts, when the analysis runs, then length of stay is their sum.
- Given price per night and total nights, when the analysis runs, then estimated booking value is price per night times total nights, with cancelled bookings reported separately from the others.
- Given any value is shown, then it is labeled an estimate and not realized revenue, and the result states that payments, taxes, discounts and adjustments are not supplied.

| Traces to | Size | INVEST exceptions |
| --- | --- | --- |
| [UC-001], [MIL-002] | fits one iteration | none |

### US-001.07 — Explore guest and booking mix

**As a** Calling system, **I want** guest and booking composition summaries, **so that** I understand who books and how.

**Acceptance Criteria**

- Given the fields exist, when the analysis runs, then the result summarizes guest composition, country, meal, room type, repeat-guest status, parking and special requests.
- Given a mix is compared with length of stay, cancellation or price, then the comparison is shown only when each group meets the small-sample rule and includes the counts.
- Given a field is missing, then the related summary is marked unavailable.

| Traces to | Size | INVEST exceptions |
| --- | --- | --- |
| [UC-001], [MIL-002] | fits one iteration | none |

### US-001.08 — Receive the analysis result as JSON

**As a** Calling system, **I want** the completed analysis returned as JSON, **so that** I can process it automatically.

**Acceptance Criteria**

- Given a completed analysis, when it finishes, then a JSON result is returned with a schema version, a result identifier, the generated time, a status, input reference metadata and the findings.
- Given the result, then it contains no raw booking records.
- Given the result cannot be returned or the history cannot be written, then the outcome reports the failure and does not report success.

| Traces to | Size | INVEST exceptions |
| --- | --- | --- |
| [UC-001], [MIL-002] | fits one iteration | none |

### US-001.09 — Keep a bounded analysis history

**As a** Calling system, **I want** each result kept in a local history limited to the latest N results, **so that** past results stay available without unbounded growth.

**Acceptance Criteria**

- Given a completed analysis, when it finishes, then the same result that was returned is appended to the history as one JSON object on one line.
- Given a configuration file with a retention value, when results exceed it, then only the latest N results remain and nothing more is removed than required.
- Given no retention value is configured, then the limit is 10.
- Given an invalid retention value, then the run reports the configuration error instead of using a guess.
- Given a malformed line or an interrupted write, then the remaining results stay readable and the problem is reported.

| Traces to | Size | INVEST exceptions |
| --- | --- | --- |
| [UC-001], [MIL-002] | fits one iteration | none |

### US-001.10 — Review prior results in marimo

**As an** Analyst, **I want** to open marimo and select a retained result, **so that** I can review an earlier analysis and when it was produced.

**Acceptance Criteria**

- Given a history with results, when marimo opens, then all retained results are listed with their generated time and one can be selected.
- Given a result is selected, then its data-quality summary and each available analysis are shown with counts and limitation notes, and estimates are labeled.
- Given the history is empty or contains a malformed line, then marimo shows a clear message and the readable results.

| Traces to | Size | INVEST exceptions |
| --- | --- | --- |
| [UC-002], [MIL-002] | fits one iteration | none |

### US-001.11 — List the Cambodian holidays

**As a** Calling system, **I want** the Cambodian holidays of the years I name as JSON without an analysis being run, **so that** I can use the holiday dates on their own.

**Acceptance Criteria**

- Given I request the holidays for one or more years, when the request is handled, then the JSON answer contains for each requested year the Cambodian (`KH`) holidays, each with its date and name, and no other country.
- Given I name no year, when the request is handled, then the current year is used and the answer states which year that was (assumption, OI-18).
- Given the holiday calendar has no data for a requested year, when the request is handled, then that year is listed as unavailable with the reason and no holiday is invented for it.
- Given the request is handled, then no analysis runs, no booking records are needed, and the history is unchanged (its content is the same before and after).
- Given a year that is not valid, when the request is handled, then the outcome is a failure that names the problem, and it does not report success.

| Traces to | Size | INVEST exceptions |
| --- | --- | --- |
| [UC-003], [MIL-008] | fits one iteration | none |

### US-001.12 — List the reachable LLM providers

**As a** Calling system, **I want** to know which language-model providers the app can reach and which models they offer, as JSON without an analysis being run, **so that** I can tell whether AI insights can be produced before I ask for them.

**Acceptance Criteria**

- Given Ollama and LM Studio are configured, when the request is handled, then the JSON answer has one entry for each of them.
- Given a provider is reachable, when the request is handled, then its entry says it is reachable and lists the models it offers.
- Given a provider is not reachable (not running, timed out or refusing), when the request is handled, then its entry says it is not reachable with the reason, the other providers are still reported, and the request itself succeeds.
- Given a provider does not answer, when the request is handled, then the answer is returned within the configured timeout per provider.
- Given the request is handled, then no analysis runs, no model is asked to generate text, no booking data is sent anywhere, and the history is unchanged.

| Traces to | Size | INVEST exceptions |
| --- | --- | --- |
| [UC-004], [MIL-008] | fits one iteration | none |

### US-001.13 — Receive one executive summary per analysis

**As a** Calling system, **I want** each analysis to come with an AI-generated executive summary when I ask for insights, **so that** a market analyst can grasp each analysis at a glance.

**Acceptance Criteria**

- Given insights are requested and a provider is reachable, when the analysis completes, then each available analysis in the result has exactly one executive summary.
- Given a summary, then it is labeled AI-generated and names the model and the provider that produced it.
- Given a summary, then it is built only from aggregate findings: no raw booking record and no booking identifier appears in any prompt or in the summary.
- Given a summary, then none of the words "caused", "because", "due to", "effect of", "leads to" or "drives" (the list in [ADR-0007]) appears in it, and it makes no forecast and no promise of earnings.
- Given insights are not requested (the default), then no model is contacted and the result is the same as without this story.
- Given no provider is reachable, when insights are requested, then no summary is produced, the result says insights were unavailable with the reason, and the analysis result stays valid and is returned and saved.
- Given the model fails or does not answer within the time limit, or its answer is rejected as unsuitable, when insights are requested, then that analysis has no summary and is marked unavailable with the reason, the other analyses are not affected, and the analysis result stays valid.
- Given an analysis is itself unavailable, then it has no summary and no text is invented for it.

| Traces to | Size | INVEST exceptions |
| --- | --- | --- |
| [UC-005], [UC-002], [MIL-008] | fits one iteration | none |

### US-001.14 — Receive improvement suggestions per analysis

**As a** Calling system, **I want** each analysis to come with AI-generated improvement suggestions stated as hypotheses, **so that** a market analyst has ideas to test for increasing NF Hotel earnings without mistaking them for facts.

**Acceptance Criteria**

- Given insights are requested and a provider is reachable, when the analysis completes, then each available analysis in the result has improvement suggestions, each labeled AI-generated with the model and provider.
- Given a suggestion, then it is worded as a hypothesis to test (for example "could be tested"), names the observed association it rests on and the sample sizes (counts) behind it, and carries over a small-sample flag from the analysis.
- Given a suggestion, then it does not state a cause, does not forecast or promise earnings (any figure it quotes comes from the findings), and none of the words "caused", "because", "due to", "effect of", "leads to" or "drives" appears in it.
- Given an answer contains a suggestion without a sample size, a causal statement or a promised earning, when the answer is checked, then that answer is rejected and none of its text appears in the result.
- Given only aggregate findings are used, then no raw booking record and no booking identifier appears in any prompt.
- Given no provider is reachable, or the model fails, times out or gives an unsuitable answer, when insights are requested, then the affected analyses have no suggestions and state the reason, and the analysis result stays valid, returned and saved.

| Traces to | Size | INVEST exceptions |
| --- | --- | --- |
| [UC-005], [UC-002], [MIL-008] | fits one iteration | none |

### US-001.15 — See saved AI insights in the history view

**As an** Analyst, **I want** to see the AI executive summary and the improvement suggestions of a saved result, marked as AI-generated, **so that** I can judge them against the analysis they belong to and act on them as hypotheses.

**Acceptance Criteria**

- Given the Analyst opens a saved result that has insights, when the result is shown, then each analysis shows its executive summary and its improvement suggestions marked AI-generated with the model and provider that produced them, and each suggestion shows the sample sizes it rests on and its hypothesis wording.
- Given a result was saved without insights, when it is shown, then it is shown without them and says so, and no error appears.
- Given an insight was marked unavailable, when the result is shown, then the insight is shown with its reason.

| Traces to | Size | INVEST exceptions |
| --- | --- | --- |
| [UC-002], [MIL-008] | fits one iteration | none |

## INVEST Check

Independent, Negotiable, Valuable, Estimable, Small and Testable hold for all fifteen stories. Note: stories US-001.02 to US-001.07 share the result contract and the small-sample rule (ADR-0002, ADR-0007), so they are independent in behavior but not in schema; the dependency is recorded in [MIL-003] and does not block estimation. Stories US-001.13 and US-001.14 rest on the same insight generation but are separable, because the summary and the suggestions are separate outputs, each testable on its own by the label, sample-size and forbidden-word checks in its criteria; US-001.11 and US-001.12 are independent of the analysis and of each other; US-001.15 is the Analyst's view of what US-001.13 and US-001.14 produce and is separate because it belongs to another actor.

---

[UCD-001]: ./use-case-diagram.md
[BC-001]: ./business-case.md
[UC-001]: ./use-cases/uc-001-analyze-hotel-bookings.md
[UC-002]: ./use-cases/uc-002-review-analysis-history.md
[UC-003]: ./use-cases/uc-003-get-holiday-calendar.md
[UC-004]: ./use-cases/uc-004-get-available-llm-providers.md
[UC-005]: ./use-cases/uc-005-get-ai-insights-for-analyses.md
[ADR-0007]: ./adr/adr-0007-analysis-methods.md
[MIL-008]: ./milestones/mil-008-requirements-holidays-llm-and-ai-insights.md
[MIL-002]: ./milestones/mil-002-requirements-actor-goals.md
[MIL-003]: ./milestones/mil-003-contracts-and-design.md
[PP-001]: ./project-plan.md
[MIL-001]: ./milestones/mil-001-inception-baseline.md
[MIL-004]: ./milestones/mil-004-core-pipeline-implementation.md
[MIL-005]: ./milestones/mil-005-analyses-implementation.md
[MIL-006]: ./milestones/mil-006-marimo-ui-and-acceptance.md
