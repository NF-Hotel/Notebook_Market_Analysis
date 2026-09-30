# Use Case: Review Analysis History

## Metadata
| Key | Value |
| --- | --- |
| ID | UC-002 |
| CrossReference | [UCD-001], [US-001], [SA-001], [DM-001], [SSD-001], [UC-005] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | TBD (S04 not yet named) |
| 2026-09-30 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |

---

**Format:** Casual

Scope: Hotel Booking Analysis (the system). Level: user-goal. Primary Actor: Analyst (provisional; confirmation of this actor is open issue OI-03).

## Casual

The Analyst opens the marimo interface to look at earlier analyses. The system reads the local JSONL history and lists the retained results, each with the time it was produced, newest first. The Analyst selects one, and the system shows its data-quality summary and each available analysis with counts and limitation notes. Analyses that were unavailable when the result was produced are shown as unavailable with the reason, and the room-value figures are labeled as estimates, not realized revenue. Findings are shown as associations, not causes.

When the result was produced with AI insights ([UC-005]), the system also shows, for each analysis, its executive summary and its improvement suggestions. Each is clearly marked AI-generated and shows the model and provider that produced it, and each suggestion shows the sample sizes it rests on and is worded as a hypothesis, not as a cause or a promise of earnings. The Analyst (provisional; open issue OI-20 confirms this reading of the request) can therefore review the ideas next to the findings they come from. If the result was saved without insights (they were not requested), the system says so and shows the findings as before. If an insight is marked unavailable for an analysis (no reachable provider, model failure or timeout, an answer that was rejected, or the analysis itself unavailable), the system shows it as unavailable with the reason and shows no text for it.

If the history file is missing or empty, the system says there are no saved results yet. If a line in the history is malformed, the system shows the readable results and reports how many lines could not be read, without stopping. If a result was produced under an older result-schema version, the system shows what it can and states the version it could not fully display.

Preconditions: at least one analysis has been run, otherwise the empty message applies. Postcondition: the Analyst has seen the selected result; nothing in the history is changed by viewing it.

Business rules: AI-generated text is always labeled as such with model and provider and is never shown as a finding, forecast or cause; an older result without insight fields is shown without error. Viewing never modifies or removes history entries (only the retention step of a new analysis does). The list shows only results still retained under the configured limit.

---

[UCD-001]: ../use-case-diagram.md
[US-001]: ../user-stories.md
[SA-001]: ../stakeholder-analysis.md
[DM-001]: ../domain-model.md
[SSD-001]: ../ssd.md
[UC-005]: ./uc-005-get-ai-insights-for-analyses.md
