# ADR-0005: Delivery and Failure Semantics

## Metadata
| Key | Value |
| --- | --- |
| ID | ADR-0005 |
| CrossReference | [US-001], [UC-001], [ADR-0002], [ADR-0003], [ADR-0006] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-30 | Proposed | Jens Tirsvad Nielsen | Team2 (S04) |

---

## Context

A run has two outputs that can fail independently: appending the result to the history, and returning it to the Calling system. The requirement is that they carry the same result and that success is never claimed when delivery did not happen. The order of the steps decides what state the system is left in when one fails.

Options: return first then save (the caller may hold a result that was never kept); save first then return (a saved result may not have reached the caller); treat both as one transaction (not possible across a file and a caller).

## Decision

1. The result is built once and serialized once. The identical bytes are used for the history line and for the value returned to the caller ([ADR-0002], [ADR-0003]).
2. The history is written first, including retention. Then the result is returned.
3. Outcomes and process exit codes:

| Situation | Caller receives | History | Exit code |
| --- | --- | --- | --- |
| Success | the result on standard output | result appended, retention applied | 0 |
| Input or configuration error | a `failed` result with `error` on standard output | unchanged | 2 |
| History write or retention failure | an error message on standard error and no result | may be unchanged, or hold the appended result if only retention failed | 3 |
| Result cannot be written to the caller | an error message on standard error naming the `result_id` | the result stays saved | 4 |

4. Success is reported only after both the history write and the return have completed. In cases 3 and 4 the message states which step failed and never says the analysis was delivered.
5. A result saved but not delivered (exit code 4) is not removed from the history: it is a valid completed analysis, is visible in marimo, and the caller can re-run. Duplicate saves from re-runs are expected and count toward retention.
6. A caller that cannot tolerate an orphaned history entry must treat exit code 4 as "saved, not delivered".

## Consequences

**Positive:**

- The durable record is written before the caller is told anything, so a delivered result is always also stored.
- Exit codes give the caller a simple, testable contract.
- No success message can be produced without both steps done.

**Negative:**

- A delivery failure leaves a history entry the caller never saw.
- A caller that retries after exit code 4 creates a second, similar result.
- The behavior depends on the invocation mechanism in [ADR-0006]; a different mechanism (such as HTTP) would need this ADR revisited.

## Affected Artifacts

- [US-001] — story 08 (failure behavior) and story 09.
- [UC-001] — steps 6 to 8, extensions 6a and 8a.
- [ADR-0002] — the serialized result.
- [ADR-0003] — history write and retention failures.
- [ADR-0006] — invocation and exit codes.

## Amendment 2026-09-30 (MIL-007 task 10, open issue OI-22)

The outcome table does not cover a failed result that cannot be written to the caller. As built, when the failed result of an input or configuration error cannot be delivered, the run ends with exit code 4 and nothing was stored, because a failed result is never stored ([ADR-0003]). The error message names the result identifier and says it was not stored.

Exit code 4 therefore has two meanings that the caller tells apart by the message on the diagnostic output: a completed result saved but not delivered, or a failed result neither stored nor delivered. Everything else in this decision is unchanged. This amendment is proposed and needs acceptance by S02 (the caller-facing behavior) and S04.

---

[US-001]: ../user-stories.md
[UC-001]: ../use-cases/uc-001-analyze-hotel-bookings.md
[ADR-0002]: ./adr-0002-result-json-contract.md
[ADR-0003]: ./adr-0003-jsonl-history-and-retention.md
[ADR-0006]: ./adr-0006-architecture-and-invocation.md
