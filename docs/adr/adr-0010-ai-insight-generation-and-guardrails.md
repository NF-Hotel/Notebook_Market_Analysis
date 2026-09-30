# ADR-0010: AI Insight Generation and Guardrails

## Metadata
| Key | Value |
| --- | --- |
| ID | ADR-0010 |
| CrossReference | [UC-005], [ADR-0007], [ADR-0009] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-30 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-30 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |

---

## Context

[UC-005] adds an optional executive summary and improvement suggestions per analysis, produced by a local language model and meant to help a market analyst look for ways to increase earnings. Three forces pull against each other:

- **Honesty of the findings.** [ADR-0007] bans causal wording and fixes association-only templates, and the business case bans forecasts. A model writes free text; it cannot be limited to templates, and it may state a cause, promise earnings or invent a number.
- **Privacy.** Only aggregate findings may leave the analysis (S03); raw booking records, booking identifiers and file paths must never reach a model (open issue OI-14 in [PP-001]).
- **Dependability.** A model can be absent, slow, or wrong. The analysis is deterministic and must stay valid and delivered whatever the model does (S02); insights are optional and off by default.

Open issues touched: OI-14 (what leaves the machine), OI-15 (language, English assumed, S05) and OI-19 (cached or regenerated, and how latency and cost are limited; regenerated assumed, S01).

Options for the answer: free prose (cannot be checked), or a fixed structure with a validator. Options for a rejected answer: repair it (hides the defect and may keep a wrong claim), retry until it passes (unbounded cost), or drop it and say why. Options for the tension with [ADR-0007]: force template wording on the model (not possible), or keep [ADR-0007] for findings, label the AI text clearly, and check it with rules that are as strict on words as [ADR-0007].

## Decision

Each available analysis gets at most one insight from one model request, built from that analysis's aggregate findings only, answered in a required JSON structure, and accepted only if a validator finds the wording, sample sizes and figures acceptable; otherwise the insight is unavailable with a reason and nothing else changes.

**What is sent.** The prompt for one analysis contains the fixed instruction text and one JSON block with: the analysis name, that analysis's `findings` exactly as in the result ([ADR-0002]), and the data-quality counts (record count, duplicate booking ID count, zero-price count, and missing and invalid counts per field). It never contains a raw booking record, a booking identifier, the input `reference`, `content_sha256`, any file name or path, the date of an individual booking, or the names of unknown input fields. Counts by period (a month or an ISO week) and the data coverage dates of the data-quality counts (earliest and latest booking and arrival date) are findings, not individual bookings, and are allowed. Group labels that come from the data (for example a country or market segment value) are included as JSON string values, cut to 60 characters, and the instruction tells the model to treat the block as data, not instructions. A scanner test builds the prompt of every analysis from fixtures that contain marker booking identifiers, file names and paths, and fails if any marker or any key of a raw record appears in any prompt (the check named in [PP-001], implemented in MIL-011). The scanner also enforces these rules: the prompt contains no booking identifier and no per-booking record (no object with a booking-level key such as a booking ID, a single booking date or an arrival date next to a price or guest count), and no group with fewer bookings than `min_group_size` ([ADR-0004]) is labelled by a single date, because such a group could identify one booking.

**How it is asked.** One request per available analysis, sequential, in English, regenerated on every run and never cached (OI-19 assumed). The instruction text is a fixed template with a `prompt_version` (first value `"1"`); any change to the template raises it, and it is stored once per run, in the result-level `insights` object ([ADR-0011]), not in each insight. The template states the required structure, asks for hypothesis wording, and lists the forbidden words. Model, provider, deadline and temperature come from [ADR-0009] and [ADR-0012]; the temperature is 0, which reduces but does not remove differences between runs.

**Required answer.** A JSON object (a single surrounding Markdown code fence is tolerated and removed) with:

- `executive_summary`: a non-empty string of at most 600 characters.
- `improvement_suggestions`: a list of 1 to 5 items, each an object with `suggestion` (non-empty string, at most 400 characters), `evidence` (non-empty string, at most 400 characters) and `sample_size` (an integer of at least 1).

Other keys are dropped and never stored.

**Validator.** The whole answer is rejected, and none of its text is kept, when any rule fails:

| # | Rule | Reason code |
| --- | --- | --- |
| 1 | Not valid JSON, a required key missing, a wrong type, an empty text, a text over its limit, or a suggestion count outside 1 to 5 | `BAD_STRUCTURE` |
| 2 | Any word of the forbidden causal list of [ADR-0007] ("caused", "because", "due to", "effect of", "leads to", "drives") in the summary, a suggestion or its evidence, using the same definition (`FORBIDDEN_WORDS` in `domain/wording`), compared ignoring case | `GUARDRAIL_REJECTED` |
| 3 | A promise or forecast of earnings: "will increase", "will grow", "will raise", "will boost", "guarantee", "ensure", "certainly", "definitely", "forecast", "predict", including their inflections, ignoring case | `GUARDRAIL_REJECTED` |
| 4 | A percentage or a currency amount (a number with `%` or the word percent, or with a currency symbol or code) that does not appear in the findings sent for that analysis; an invented figure is rejected even when it looks harmless | `GUARDRAIL_REJECTED` |
| 5 | A suggestion whose `sample_size` is not a sample size present in the findings sent. The sample sizes are exactly the values of the fields named `numerator`, `denominator` and `records_used`, and a day count present in the findings (a field whose name ends in `_days`); the record count of the data-quality counts also counts. Medians, means, rates and other computed figures are not sample sizes | `GUARDRAIL_REJECTED` |
| 6 | A suggestion with a `sample_size` below the configured `min_group_size` ([ADR-0004]) whose `evidence` does not contain the words "small sample" | `GUARDRAIL_REJECTED` |
| 7 | A suggestion without hypothesis wording: none of the words "may", "might", "could", "suggests", "consider testing" in its `suggestion` | `GUARDRAIL_REJECTED` |

The validator is deterministic code in the `domain` layer that needs no model; the word lists and limits are constants that a test pins.

**Label.** Every insight that is available carries the label `AI-generated`, the provider, the model and the generation time ([ADR-0011]). The `prompt_version` is not part of the per-insight label: it is one value for the run, in the result-level `insights` object ([ADR-0011]). The analysis's own findings never contain AI text.

**An analysis available for only some years.** Its findings already list the years that were left out (for example a year with no data), and the prompt includes that list, because the prompt carries the findings exactly as they are. The insight must not claim more than the findings do (no statement about a year listed as left out); the validator cannot check this, so the instruction text says so and it stays part of the residual risk. Such an analysis is `available`, so it gets an insight; only an analysis that is `unavailable` as a whole is `not_applicable`.

**Failure semantics.** Each analysis's insight ends in exactly one state:

| Status | Reason code | When |
| --- | --- | --- |
| `available` | none | the answer passed the validator |
| `unavailable` | `NO_PROVIDER` | no provider can be reached ([ADR-0009]); no model was contacted |
| `unavailable` | `NO_MODEL` | a provider is reachable but the configured or automatic model is not offered ([ADR-0009]); no model was contacted |
| `unavailable` | `TIMEOUT` | no complete answer within the total deadline `llm.generation_timeout_seconds` ([ADR-0009]); not retried |
| `unavailable` | `MODEL_ERROR` | a refused connection, an error status or an unusable response during generation; not retried |
| `unavailable` | `BAD_STRUCTURE` | rule 1 of the validator |
| `unavailable` | `GUARDRAIL_REJECTED` | rules 2 to 7 of the validator |
| `not_applicable` | none | the analysis itself is unavailable; no request is made and nothing is invented |

A failure of one insight does not affect another analysis's insight (the next analysis is still tried after a timeout). A failure never changes an analysis, never makes the run fail, never changes the exit code ([ADR-0008]) and never delays delivery beyond the configured deadlines. A completed analysis whose available analyses have unavailable insights is reported with the result status `completed_with_warnings` ([ADR-0011]); it is still stored and returned like any completed result ([ADR-0005]).

**Relation to [ADR-0007].** [ADR-0007] stays unchanged and governs the findings: fixed association templates, checked by its own test. AI text is not built from templates and is kept apart from the findings as a labeled insight; the causal-word ban is extended to it through the same word list, so the two rules cannot drift.

**The model's text is untrusted data.** It is stored and shown as plain text, never interpreted as markup, code or instructions, never used to choose an action, and never fed back into another prompt. A model cannot call tools through this application.

**Residual risk.** A model may write a plausible but wrong sentence that passes every check: for example a suggestion that misreads which group is larger, that pairs a true sample size with an unrelated claim, or that uses wording the lists do not name. The validator checks form, words and figures, not truth. The mitigations are the label `AI-generated`, the sample size shown with every suggestion, the hypothesis wording, and the fact that the analysis and its counts stay next to the text so the analyst can judge it ([UC-002]). S01 and S05 must accept this residual risk; insights are off unless the caller asks for them.

## Consequences

**Positive:**

- Only aggregate findings leave the analysis, and a test can prove it for every prompt.
- The failure behavior is complete and bounded: six failure reasons and one not-applicable state, each a defined state, none touching the analysis.
- The validator is deterministic and testable without a model; wrong-form answers never reach the caller or the history.
- Every insight is traceable to provider and model, and the run to its prompt version, and each suggestion shows the sample size behind it.

**Negative:**

- The validator will reject some good answers (a legitimate "will" wording, a percentage the model computed from counts), so small models may often yield `GUARDRAIL_REJECTED`; rejecting is safer than repairing.
- Residual risk remains as stated: correctness of meaning is not checked.
- Data-derived group labels can carry text from the input into a prompt (prompt injection); the length limit, the data framing and the output validator reduce, not remove, the effect, and the aggregate labels are not scanned for instructions.
- Regenerating on every run means insight text differs between runs and cost and time recur (up to six requests per run); results cannot be compared textually.
- Word lists are English only (OI-15) and need review if the language changes.

## Affected Artifacts

- [UC-005] — steps 3 to 7 and extensions 2a to 7a; the rules in its business-rules table.
- [ADR-0007] — the forbidden-word list is reused and extended to AI text; findings templates unchanged.
- [ADR-0002] — the findings sent to the model are the findings of the result; no raw records.
- [ADR-0004] — `min_group_size` is used by validator rule 6.
- [ADR-0005] — a completed result with unavailable insights is stored and delivered as usual.
- [ADR-0008] — insight failure never changes the exit code.
- [ADR-0009] — the reasons `NO_PROVIDER`, `NO_MODEL`, `TIMEOUT` and `MODEL_ERROR` come from selecting and calling a model.
- [ADR-0011] — the JSON of the insight, its label and the result status.
- [UC-002] — the history view shows the label, model, provider, sample sizes and reasons.
- [PP-001] — OI-14, OI-15 and OI-19 (assumptions stated, confirmations pending) and the AI risks in the Plan Risks table.

---

[UC-005]: ../use-cases/uc-005-get-ai-insights-for-analyses.md
[ADR-0007]: ./adr-0007-analysis-methods.md
[ADR-0009]: ./adr-0009-llm-provider-discovery-and-connection.md
[PP-001]: ../project-plan.md
[UC-002]: ../use-cases/uc-002-review-analysis-history.md
[ADR-0002]: ./adr-0002-result-json-contract.md
[ADR-0004]: ./adr-0004-configuration-file.md
[ADR-0005]: ./adr-0005-delivery-and-failure-semantics.md
[ADR-0008]: ./adr-0008-invocation-interface.md
[ADR-0011]: ./adr-0011-output-contracts-and-result-1-1.md
[ADR-0012]: ./adr-0012-configuration-extension.md
