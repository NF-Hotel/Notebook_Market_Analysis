# ADR-0002: Result JSON Contract

## Metadata
| Key | Value |
| --- | --- |
| ID | ADR-0002 |
| CrossReference | [US-001], [UC-001], [DM-001], [ADR-0003], [ADR-0005] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |

---

## Context

The application returns each analysis to the Calling system as JSON and keeps the same result in a history that marimo reads. The result needs identification and versioning so the caller and the history can rely on it, and it must not expose raw bookings (open issues OI-06 and OI-09 in [PP-001]). Options for content: include raw records (large, exposes data); include only aggregate findings and metadata (small, stable).

## Decision

The result is one JSON object with these top-level fields, and contains aggregate findings only, never raw booking records:

| Field | Meaning |
| --- | --- |
| `schema_version` | `"MAJOR.MINOR"` string, starting at `"1.0"`; adding a field raises MINOR, removing or changing one raises MAJOR |
| `result_id` | UUID string, unique per run |
| `generated_at` | RFC 3339 UTC time when the result was completed |
| `status` | `completed`, `completed_with_warnings` (some analysis unavailable or some data invalid), or `failed` |
| `input` | `source` (`supplied` or `development_sample`), `reference` (file name only, no directory), `record_count`, `content_sha256` of the input bytes |
| `data_quality` | record count, earliest and latest booking and arrival dates, duplicate booking ID count, per-field missing and invalid counts, zero-price count, unknown field names |
| `analyses` | one entry per analysis: `lead_time`, `holidays`, `seasonality`, `cancellations`, `room_value`, `guest_mix`; each has `status` (`available` or `unavailable`), `reason` when unavailable, and `findings` |
| `notices` | list of `{code, message}` items, including data limitations and the estimate label |
| `error` | present only when `status` is `failed`: `{code, message}` |

Every group figure inside `findings` is an object with `group`, `numerator`, `denominator` and `small_sample` (boolean). Money is a decimal string, not a float. Ratios are given as numerator and denominator, not rounded values. The room-value entry always carries the notice code `ESTIMATE_NOT_REVENUE`. Findings text uses the association wording defined in [ADR-0007].

A machine-checkable JSON Schema for version 1.0 is a deliverable of the coding gateway and is derived from this table. Aggregation by country and agent is allowed; a raw record, a booking ID list and any person-level data are not. The sample data contains no guest names, so no personal data is expected; this is unconfirmed for the production feed.

The result returned to the caller and the history line are the same serialization ([ADR-0005]).

## Consequences

**Positive:**

- The caller gets a small, versioned, self-describing result.
- Rate figures can be recomputed and checked from counts.
- Additive changes do not break callers that ignore unknown fields.

**Negative:**

- A caller wanting raw records or a booking-level drill-down cannot get it without a new decision.
- Version negotiation with callers is not covered; callers must tolerate unknown fields within a MAJOR version.
- `content_sha256` requires reading the file bytes once more.

## Affected Artifacts

- [US-001] — stories 08 and 01 to 07 define what appears in `findings`.
- [UC-001] — step 5 and postconditions.
- [DM-001] — Analysis Result, Analysis and Group Statistic.
- [ADR-0003] — history lines use this format.
- [ADR-0005] — delivery of the same serialization.

---

[US-001]: ../user-stories.md
[UC-001]: ../use-cases/uc-001-analyze-hotel-bookings.md
[DM-001]: ../domain-model.md
[PP-001]: ../project-plan.md
[ADR-0003]: ./adr-0003-jsonl-history-and-retention.md
[ADR-0005]: ./adr-0005-delivery-and-failure-semantics.md
[ADR-0007]: ./adr-0007-analysis-methods.md
