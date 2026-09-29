# Stakeholder Analysis

## Metadata
| Key | Value |
| --- | --- |
| ID | SA-001 |
| CrossReference | [BC-001] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |

---

## Purpose

Identify who influences or is affected by the hotel-booking analysis application, so that every later artifact can name owners, reviewers and actors by stable ID. The analysis follows the Power/Interest grid; concerns are mapped to FURPS+.

All five stakeholders are named: S01 is the project owner and author, S02 to S05 were named after the first draft. Each named person still has to confirm their entry (open issue OI-02 in [PP-001]). S01's role and S04's organization are assumptions to be confirmed.

## Stakeholder Summary Table

| ID | Name | Role/Title | Organization | Power Level | Interest Level | Quadrant | Primary Concern (Business Language) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S01 | Jens Tirsvad Nielsen | Project owner and author (assumed from repository authorship) | NF Hotel project | HIGH | HIGH | Manage Closely | The app gives a clear, honest analysis of booking behavior and is built in a controlled, reviewable way |
| S02 | Valdemar | Calling-system owner | Owner of the system that calls the app | HIGH | HIGH | Manage Closely | The app accepts the JSON the caller sends and returns a dependable, versioned JSON result |
| S03 | Team2 | Booking-data owner | NF Hotel | LOW | HIGH | Keep Informed | Booking data is used correctly, and data problems and limits are reported instead of hidden |
| S04 | Team2 | Independent reviewer (not the author) | To be confirmed | HIGH | LOW | Keep Satisfied | Artifacts are reviewed against the quality checklists before each Go/No-Go decision |
| S05 | PO | Analyst who reviews saved results in marimo (provisional, open issue OI-03) | NF Hotel | LOW | HIGH | Keep Informed | Prior analyses are easy to find, and each shows when it was produced and what its limits are |

## Power/Interest Classification Rationale

- **Manage Closely (S01, S02):** S01 approves scope and decisions. S02 decides what the input and result contracts must look like, so a wrong assumption about the caller invalidates design work.
- **Keep Satisfied (S04):** the reviewer's Go/No-Go verdict controls whether a gateway passes, but their day-to-day interest in the app is limited to review material.
- **Keep Informed (S03, S05):** they do not decide scope, but they judge whether the data handling and the displayed results are trustworthy and usable.

## Primary Concerns and FURPS+ Mapping

| ID | Concern | FURPS+ attribute |
| --- | --- | --- |
| S01 | Complete analyses; visible limitations; controlled delivery | Functionality, Supportability |
| S02 | Stable JSON input and result contracts; clear failure behavior | Interface (+), Reliability |
| S03 | Correct treatment of booking data; missing or invalid values shown | Functionality, Design constraints (+) |
| S04 | Reviewable artifacts with objective criteria | Supportability |
| S05 | Retained results selectable, timestamped and understandable | Usability |

## Communication Requirements

| ID | Channel | Frequency | Deliverable | Phase / Milestone |
| --- | --- | --- | --- | --- |
| S01 | Pull request review | Once per gateway | Gateway documents and artifacts | MIL-001 to MIL-006 |
| S02 | Comment on the pull request or issue for the contract decisions in the project's GitHub repository (proposed; S02 to confirm) | At contract decisions | Input and result contract decisions for confirmation | MIL-003 |
| S03 | Comment on the pull request or issue for the stories and decisions in the project's GitHub repository (proposed; S03 to confirm) | At data-quality rules | Data-quality rules and example findings | MIL-002, MIL-003 |
| S04 | Review record (RC) | Once per reviewed artifact | Completed review records | MIL-001 to MIL-003 |
| S05 | Live walkthrough of the marimo notebook, with feedback recorded as a GitHub issue (proposed; S05 to confirm) | At UI acceptance | marimo demonstration | MIL-006 |

## Conflicting Interests and Mitigations

| Conflict | Stakeholders | Mitigation |
| --- | --- | --- |
| The caller wants a fast, fixed result contract while analyses may need to grow | S02, S01 | Version the result envelope in ADR-0002 so fields can be added without breaking the caller |
| Full raw records help the analyst, but results should stay small and avoid exposing booking data | S05, S03 | Exclude raw records from results by default; add fields only through a documented need |
| One person may be author and reviewer, which weakens review independence | S01, S04 | S04 (Team2) is a different person from S01; review records are issued as drafts until S04 confirms them, and S04's organization is still to be confirmed |

## Traceability Analysis

### Business Goal Alignment

| Stakeholder | Concern | Business Case objective |
| --- | --- | --- |
| S01 | Complete analyses; controlled delivery | [BC-001] objectives 1 to 3 and 7 |
| S02 | Stable contracts; failure behavior | [BC-001] objectives 4 and 5 |
| S03 | Data quality visible | [BC-001] objective 1 |
| S04 | Reviewable artifacts | [BC-001] objective 7 |
| S05 | Saved results displayed in marimo | [BC-001] objective 6 |

## Sign-Off

Not signed. All five stakeholders are now named (S02 Valdemar, S03 and S04 Team2, S05 PO). Pending: confirmation by each named person that their entry and their proposed communication channel are correct, and S01's confirmation of their own role.

---

[PP-001]: ./project-plan.md
[BC-001]: ./business-case.md
[BC-001]: ./business-case.md
