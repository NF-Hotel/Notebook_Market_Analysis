# Use Case: Review Analysis History

## Metadata
| Key | Value |
| --- | --- |
| ID | UC-002 |
| CrossReference | [UCD-001], [US-001], [SA-001] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-29 | Proposed | Jens Tirsvad Nielsen | Team2 (S04) |

---

**Format:** Casual

Scope: Hotel Booking Analysis (the system). Level: user-goal. Primary Actor: Analyst (provisional; confirmation of this actor is open issue OI-03).

## Casual

The Analyst opens the marimo interface to look at earlier analyses. The system reads the local JSONL history and lists the retained results, each with the time it was produced, newest first. The Analyst selects one, and the system shows its data-quality summary and each available analysis with counts and limitation notes. Analyses that were unavailable when the result was produced are shown as unavailable with the reason, and the room-value figures are labeled as estimates, not realized revenue. Findings are shown as associations, not causes.

If the history file is missing or empty, the system says there are no saved results yet. If a line in the history is malformed, the system shows the readable results and reports how many lines could not be read, without stopping. If a result was produced under an older result-schema version, the system shows what it can and states the version it could not fully display.

Preconditions: at least one analysis has been run, otherwise the empty message applies. Postcondition: the Analyst has seen the selected result; nothing in the history is changed by viewing it.

Business rules: viewing never modifies or removes history entries (only the retention step of a new analysis does). The list shows only results still retained under the configured limit.

---

[UCD-001]: ../use-case-diagram.md
[US-001]: ../user-stories.md
[SA-001]: ../stakeholder-analysis.md
