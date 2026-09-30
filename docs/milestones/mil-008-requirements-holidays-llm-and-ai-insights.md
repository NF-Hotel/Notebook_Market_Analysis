# Gateway 8: Requirements for Holidays, LLM Discovery and AI Insights

## Metadata
| Key | Value |
| --- | --- |
| ID | MIL-008 |
| CrossReference | [BC-001], [US-001] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-30 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |

---

## Purpose

Decide whether the three new capabilities are specified well enough to design. When the app is called, the Calling system may (1) ask for the Cambodian holidays as JSON without running an analysis, (2) ask which language-model providers the app can reach (Ollama and LM Studio) as JSON without running an analysis, and (3) ask for an AI-written executive summary and improvement suggestions for each analysis, aimed at a market analyst who wants to increase NF Hotel earnings.

The business case (BC-001), the use case diagram (UCD-001) and the user stories (US-001) already exist and are revised here; the three new use cases get their own documents. Because the new features touch the Analyst's view, UC-002 is revised too. All actor goals here need the full behavior and design set (SSD, OC, SD, DCD), which is planned in MIL-009 before any code.

**Tension to resolve in the requirements:** BC-001 rules out causal and predictive claims, while advice to "increase earnings" invites them. The stories must therefore require the suggestions to be labeled hypotheses grounded in the observed associations and their sample sizes, never promises or causes.

## Deliverable

Revised BC-001 (objectives 8 to 10, scope, risks, assumptions), revised UCD-001 (new use cases and an `<<extend>>` relationship), revised US-001 (stories US-001.11 to US-001.14), new use cases UC-003, UC-004 and UC-005, revised UC-002, and a review record for each.

## Go / No-Go Criteria

| # | Criterion (objectively checkable) | Go | No-Go |
| --- | --- | --- | --- |
| 1 | BC-001 states objectives 8 (AI executive summary and improvement suggestions per analysis), 9 (holiday listing without an analysis) and 10 (reachable LLM providers without an analysis) and lists the risks of AI text (wrong or invented statements, causal wording, data exposure) each with a mitigation | Present | Any objective or risk missing |
| 2 | UCD-001 shows UC-003 and UC-004 for the Calling system, UC-005 as an `<<extend>>` of UC-001 with its justification, and the Analyst extended to see insights in UC-002 | Shown | Any use case or relationship missing |
| 3 | Every new story has Given/When/Then criteria: US-001.11 (holiday listing: years, country, no analysis run, JSON), US-001.12 (provider listing: Ollama and LM Studio, reachable or not, models, no analysis run, JSON), US-001.13 (one executive summary per analysis), US-001.14 (improvement suggestions per analysis, stated as hypotheses with the sample sizes they rest on) | 4 of 4 | Any story without criteria |
| 4 | The stories state what happens when no provider is reachable, when the model fails or times out, and that the analysis result stays valid without insights | Stated | Silent on failure |
| 5 | UC-003, UC-004 and UC-005 name the primary actor, preconditions, postconditions, main scenario and extensions; UC-005 is Fully Dressed | Present | Any missing |
| 6 | Open issues OI-13 to OI-20 in PP-001 are each resolved or deferred with an owner S-ID | Assigned | Any without an owner |
| 7 | RC records exist for every artifact revised or written here with verdict Go (or Go-with-conditions and all action items closed) | All Go | Any No-Go or open item |

## Dependencies

| Depends on | Reason |
| --- | --- |
| MIL-007 | SSD-001, OC-001, SD-001 and DCD-001 exist and are extended, not restarted, in MIL-009 |
| MIL-006 | The running application and the history viewer that the new use cases extend |

## Traceability

| Business Case objective / KPI / user story | Reference |
| --- | --- |
| BC-001 objectives 8 to 10 (new, added by task 1) | US-001.11 to US-001.14, UC-003, UC-004, UC-005 |

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
| 1 | Revise BC-001 for AI insights and standalone outputs | Add objectives 8 to 10, extend scope and out of scope (local models only if OI-14 says so), and add the risks of AI text with mitigations. It keeps the earlier objectives and the ban on causal claims, and explains how improvement suggestions stay hypotheses. | No | BC-001 |
| 2 | Revise UCD-001 with the new use cases | Add Get Holiday Calendar and Get Available LLM Providers for the Calling system and Get AI Insights for Analyses as an extend of Analyze Hotel Bookings. Include the Analyst's use of insights through the history view. | No | UCD-001 |
| 3 | Revise US-001 with stories US-001.11 to US-001.14 | Add the holiday listing, provider listing, executive summary and improvement suggestion stories with testable criteria and the failure behavior. The suggestion story must require hypothesis wording and sample sizes. | No | US-001 |
| 4 | Write UC-003 Get Holiday Calendar | Use case for asking the app for the Cambodian holidays as JSON without running an analysis. It states which years are returned and what happens for a year the calendar does not cover. | Yes | UC-003, US-001.11 |
| 5 | Write UC-004 Get Available LLM Providers | Use case for asking which of Ollama and LM Studio the app can reach, and which models each offers, as JSON without running an analysis. Unreachable providers are reported, not treated as an error. | Yes | UC-004, US-001.12 |
| 6 | Write UC-005 Get AI Insights for Analyses | Fully dressed use case, an extension of Analyze Hotel Bookings, in which each analysis receives an executive summary and improvement suggestions for a market analyst. Extensions cover no reachable provider, model failure or timeout, and an unsuitable answer. | Yes | UC-005, US-001.13, US-001.14 |
| 7 | Revise UC-002 to show AI insights | Add the display of the summary and suggestions, clearly marked as AI-generated, to Review Analysis History, and the case of results saved without insights. | No | UC-002 |
| 8 | Review BC-001 (revision) | Produce the RC record for the revised business case against QC-BC-001. | No | BC-001, QC-BC-001 |
| 9 | Review UCD-001 (revision) | Produce the RC record for the revised use case diagram against QC-UCD-001, including the new extend relationship. | No | UCD-001, QC-UCD-001 |
| 10 | Review US-001 (revision) | Produce the RC record for the revised stories against QC-US-001, checking that the new stories meet the INVEST criteria. | No | US-001, QC-US-001 |
| 11 | Review UC-003 | Produce the RC record for UC-003 against QC-UC-001. | No | UC-003, QC-UC-001 |
| 12 | Review UC-004 | Produce the RC record for UC-004 against QC-UC-001. | No | UC-004, QC-UC-001 |
| 13 | Review UC-005 | Produce the RC record for UC-005 against QC-UC-001. | No | UC-005, QC-UC-001 |
| 14 | Review UC-002 (revision) | Produce the RC record for the revised UC-002 against QC-UC-001. | No | UC-002, QC-UC-001 |

---

[BC-001]: ../business-case.md
[US-001]: ../user-stories.md
