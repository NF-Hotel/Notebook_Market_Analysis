# ADR-0003: JSONL History and Retention

## Metadata
| Key | Value |
| --- | --- |
| ID | ADR-0003 |
| CrossReference | [US-001], [UC-001], [UC-002], [DM-001], [ADR-0002], [ADR-0004], [ADR-0005] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |

---

## Context

Each completed result is appended to a local JSONL history that marimo reads, and only the latest N results are kept (open issue OI-10 in [PP-001]). The repository already ignores `output/*`, which suggests generated output belongs there. Questions to settle: where the file lives, the line format, how a partial or malformed line is handled, what counts as one retained result, when retention runs, and what happens with concurrent callers. Retention must never delete more than required.

## Decision

- **Location:** `output/analysis_history.jsonl` relative to the working directory, changeable with the `history.path` setting in [ADR-0004]. Missing directory and file are created on first append.
- **Line format:** one result per line, the compact UTF-8 JSON of the [ADR-0002] result, ended by `\n`, with no newline inside the JSON.
- **What is stored:** only results with status `completed` or `completed_with_warnings`. A `failed` result is returned to the caller but not stored. One valid line is one retained result.
- **Append:** the whole line is written with a single write in append mode, flushed and synced to disk. If the file exists and does not end with `\n` (an interrupted earlier write), a `\n` is written first so the partial line stays isolated.
- **Read:** lines are read in file order; a line that is not valid JSON or does not carry the required envelope fields is skipped and counted as malformed. Reading never changes the file. Marimo and the analysis run both report the malformed-line count.
- **Order:** "latest" means later in the file, not later by `generated_at`.
- **Retention:** applied immediately after a successful append. If the number of valid results exceeds N, the oldest valid results beyond N are removed and nothing else is: malformed lines are kept, never deleted by retention. The file is rewritten to a temporary file in the same directory and then atomically replaced. If retention fails, the newly appended result stays, and the failure is reported as a history failure ([ADR-0005]).
- **Concurrency:** a writer takes an exclusive lock by creating `<history file>.lock` and waits up to 10 seconds; failing to get it is a history write failure. Readers do not lock and tolerate a file being replaced. Stale lock files older than 60 seconds are treated as abandoned and replaced.

## Consequences

**Positive:**

- The history stays readable after crashes, and retention removes exactly the surplus.
- Marimo needs only a read-only, tolerant reader.
- Concurrent callers cannot interleave lines.

**Negative:**

- Rewriting the whole file at retention time is O(N); acceptable for small N such as the default 10.
- Kept malformed lines can accumulate and need manual cleanup.
- The lock file approach is simple but not proof against every crash; the stale-lock rule covers the common case.

## Affected Artifacts

- [US-001] — stories 09 and 10.
- [UC-001] — steps 6 and 7, extensions 6a and 7a.
- [UC-002] — reading and listing results.
- [DM-001] — Result History and Retention Policy.
- [ADR-0002] — line content.
- [ADR-0004] — path and retention settings.
- [ADR-0005] — failure behavior.

---

[US-001]: ../user-stories.md
[UC-001]: ../use-cases/uc-001-analyze-hotel-bookings.md
[UC-002]: ../use-cases/uc-002-review-analysis-history.md
[DM-001]: ../domain-model.md
[PP-001]: ../project-plan.md
[ADR-0002]: ./adr-0002-result-json-contract.md
[ADR-0004]: ./adr-0004-configuration-file.md
[ADR-0005]: ./adr-0005-delivery-and-failure-semantics.md
