# Use Case: Get AI Insights for Analyses

## Metadata
| Key | Value |
| --- | --- |
| ID | UC-005 |
| CrossReference | [UCD-001], [US-001], [SA-001], [DM-001], [SSD-001], [UC-001], [UC-002], [UC-004] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-30 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-30 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-30 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |

---

**Format:** Fully Dressed

## Fully Dressed

- **Scope:** Hotel Booking Analysis (the system)
- **Level:** user-goal
- **Primary Actor:** Calling system
- **Stakeholders and Interests:**
  - S01 — the insights help a market analyst look for ways to increase NF Hotel earnings, without contradicting the ban on causal and predictive claims
  - S02 — insights are optional, never break or delay the analysis result, and are part of a dependable, versioned result
  - S03 — only aggregate findings leave the analysis; raw booking records and booking identifiers are never sent to a model
  - S05 — each insight is clearly marked AI-generated, states the sample sizes it rests on, and is readable in the history view ([UC-002]); the Analyst (S05) is the reader the wording is written for (open issue OI-20)
- **Preconditions:**
  - The use case Analyze Hotel Bookings ([UC-001]) is running and has completed step 4, so at least the findings of the analyses exist.
  - The Calling system has asked for insights; insights are off by default.
  - A configuration may exist; if it does not, defaults apply.
- **Postconditions (success guarantee):**
  - Each available analysis in the result carries an executive summary and improvement suggestions, each labeled AI-generated with the model and provider that produced it.
  - Every suggestion is worded as a hypothesis and names the sample sizes it rests on; none states a cause or promises earnings.
  - No raw booking record and no booking identifier was sent to any model.
  - The result stays valid and complete, with or without insights; an analysis without an insight states why.

**Extension:** this use case is an `<<extend>>` of [UC-001], attached at the extension point "insights requested", after step 4 (analyses run) and before step 5 (result assembled). It runs only when the Calling system asks for it; [UC-001] is complete without it.

### Main Success Scenario

1. The system finds, at the extension point of [UC-001] (after step 4), that the Calling system asked for insights together with its request.
2. The system selects a reachable language-model provider and a model from the configured ones.
3. For each analysis that is available, the system prepares its aggregate findings (counts, rates, denominators and sample-size flags only).
4. The system sends the aggregate findings of that analysis to the selected model and asks for a structured executive summary and improvement suggestions.
5. The system receives the structured answer.
6. The system checks the answer against the guardrails: hypothesis wording, the sample sizes the analysis reports, no causal claims, no promised earnings.
7. The system labels the insight AI-generated, with the model and provider, and attaches it to that analysis in the result.
8. The system repeats steps 3 to 7 for every available analysis, then returns control to [UC-001], which assembles the result at its step 5.

The Analyst sees the saved insights later through [UC-002].

Insights are not requested by default. When they are not requested this use case does not start: no model is contacted and [UC-001] completes as before.

### Extensions (Alternative / Exception Flows)

- 2a. No configured provider is reachable, or the reachable provider offers no usable model (none, or not the configured one):
  1. The system does not contact any model, records in the result that insights were unavailable with the reason "no reachable provider" (or "no model" when a provider is reachable but offers no usable model), and [UC-001] continues; the analysis result stays valid (see [UC-004] for how reachability is reported to the Calling system).
- 3a. An analysis is unavailable (a required field was missing, [UC-001] step 4a, or the calendar had no data for every year, step 4b; an analysis that is unavailable only for some years, such as the holidays of one year, still counts as available and its insight states the years left out):
  1. The system produces no insight for it and marks the insight not applicable because the analysis is unavailable; nothing is invented.
- 4a. The model fails, or does not answer within the time limit:
  1. The system marks the insight for that analysis unavailable with the reason (failure or timeout), does not retry without limit, and continues with the next analysis; the analysis result stays valid.
- 5a. The answer is empty or not in the expected structure:
  1. The system treats it as an unsuitable answer and continues at 6a.
- 6a. The answer fails the guardrails (states a cause, promises earnings, omits sample sizes, or is not worded as a hypothesis):
  1. The system rejects that answer, does not include its text in the result, marks the insight for that analysis unavailable with the reason "rejected", and continues; the analysis result stays valid.
- 7a. Some analyses have insights and others do not:
  1. The result contains the insights that passed and marks each of the others unavailable with its reason; the insights present are not affected by the missing ones.
- 8a. The result, with or without insights, cannot be saved or returned:
  1. The failure is handled as in [UC-001] (steps 6a and 8a); insights never turn a failed delivery into a success.

### Special Requirements / Business Rules

| Step | Rule |
| --- | --- |
| 1 | Insights are optional and off by default; the Calling system opts in. |
| 2 | Only local models on the same machine are used (assumption, OI-14, owner S03); the provider and model come from configuration, and the default model choice is OI-13 (S01). |
| 3, 4 | Only aggregate findings are sent. Raw booking records and booking identifiers are never sent, and no prompt contains them. |
| 4, 5 | The answer is requested in English (assumption, OI-15, owner S05) and in a fixed structure: an executive summary and improvement suggestions. |
| 6 | Suggestions are hypotheses drawn from observed associations. Each names the sample sizes it rests on, and small-sample flags are carried over. No causal claim, no forecast, no promised earnings; the forbidden wording of [ADR-0007] ("caused", "because", "due to", "effect of", "leads to", "drives") never appears. |
| 7 | Every insight is labeled AI-generated with its model and provider. The analysis itself stays deterministic; insight text may differ between runs. |
| 8 | Insights are generated again for each run and not cached (assumption, OI-19, owner S01); the time limit and the cost of model calls are bounded by configuration. |
| 8 | Insights are kept inside the result and therefore in the history (assumption, OI-16, owner S02), so the Analyst can review them later. |
| 2a, 4a, 6a | A failed, slow or rejected insight never fails the run, never removes another analysis, and never delays delivery beyond the configured limits. |

### Open Issues

- Local models only (OI-14, S03), English (OI-15, S05), placement of insights in the result and history (OI-16, S02), caching (OI-19, S01), acceptable models and the default choice (OI-13, S01) are assumptions here and are resolved or deferred in the MIL-008 and MIL-009 gateways.
- The Analyst as reader, and whether the Calling system also consumes the suggestions (OI-20, S01).
- The exact answer structure, the guardrail validator and the failure codes are decided in the design gateway (ADR-0010 and ADR-0011, planned).

---

[UCD-001]: ../use-case-diagram.md
[US-001]: ../user-stories.md
[SA-001]: ../stakeholder-analysis.md
[DM-001]: ../domain-model.md
[SSD-001]: ../ssd.md
[UC-001]: ./uc-001-analyze-hotel-bookings.md
[UC-002]: ./uc-002-review-analysis-history.md
[UC-004]: ./uc-004-get-available-llm-providers.md
[ADR-0007]: ../adr/adr-0007-analysis-methods.md
