# Use Case: Get Available LLM Providers

## Metadata
| Key | Value |
| --- | --- |
| ID | UC-004 |
| CrossReference | [UCD-001], [US-001], [SA-001], [DM-001], [SSD-001] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-30 | Proposed | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-30 | Proposed | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-30 | Proposed | Jens Tirsvad Nielsen | Team2 (S04) |

---

**Format:** Casual

Scope: Hotel Booking Analysis (the system). Level: user-goal. Primary Actor: Calling system.

## Casual

The Calling system asks the application which language-model (LLM) providers it can reach, and gets the answer as JSON. The providers are Ollama and LM Studio. No booking records are supplied, no analysis runs and nothing is written to the history: this use case is independent of Analyze Hotel Bookings and Review Analysis History.

For each configured provider the system makes a quick, read-only check within a time limit. The addresses of the providers come from configuration; their defaults are fixed later in the design gateway (ADR-0009 and ADR-0012, planned). The answer lists every configured provider with its name and address, whether it is reachable, the reason when it is not (for example not running or timed out), and, for a reachable provider, the models it offers. A provider that is not reachable is a normal entry in the answer, not an error: the request still succeeds. Which model is chosen when a provider offers several is not part of this use case (open issue OI-13 in [PP-001], owner S01).

If the configuration is invalid, the system returns a failed answer that names the problem and does not guess. If the answer cannot be returned to the Calling system, the system reports the failure and does not report success; nothing was stored, so a retry has no side effect.

Preconditions: the application can be called by the Calling system; no booking file is needed; a configuration may exist, and defaults apply when it does not. Postconditions: the Calling system holds a JSON answer listing each configured provider as reachable or not with the reason, and the models of the reachable ones; no analysis ran, no model was asked to generate text, and the history is unchanged.

Business rules: the check only reads (it never sends booking data or starts a generation); it completes within a stated timeout so that one slow provider cannot block the answer; an unreachable provider never turns the request into a failure; the answer names only providers and models, never any booking data. Whether models may also run remotely is OI-14 (assumed local only, owner S03).

Open issues: the model acceptance rule (OI-13), local-only providers (OI-14), the timeout value and configuration defaults (design gateway, ADR-0009, ADR-0012).

---

[UCD-001]: ../use-case-diagram.md
[US-001]: ../user-stories.md
[SA-001]: ../stakeholder-analysis.md
[DM-001]: ../domain-model.md
[SSD-001]: ../ssd.md
[PP-001]: ../project-plan.md
