# Use Case: Get Holiday Calendar

## Metadata
| Key | Value |
| --- | --- |
| ID | UC-003 |
| CrossReference | [UCD-001], [US-001], [SA-001], [DM-001], [SSD-001] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-30 | Proposed | Jens Tirsvad Nielsen | Team2 (S04) |

---

**Format:** Casual

Scope: Hotel Booking Analysis (the system). Level: user-goal. Primary Actor: Calling system.

## Casual

The Calling system asks the application for the Cambodian (`KH`) public holidays, and gets them back as JSON. No booking records are supplied, no analysis runs and nothing is written to the history: this use case is independent of Analyze Hotel Bookings and Review Analysis History.

The Calling system names the years it wants. The system takes the holidays from the maintained holiday calendar source (the source is fixed later in [ADR-0007] and the design gateway) and returns, for each requested year, the list of holidays with their date and name. Assumption (open issue OI-18 in [PP-001], owner S02): the years returned are the years requested, and when no year is requested the current year is used; whether a range is also accepted, and whether countries other than Cambodia are ever offered, is open, and this use case covers Cambodia only.

If the calendar has no data for a requested year, that year appears in the answer marked unavailable with the reason, and no holiday is invented for it. If a request names something that is not a valid year, the system returns a failed answer that names the problem, and no holidays are returned for it. If the answer cannot be returned to the Calling system, the system reports the failure and does not report success; nothing was stored, so a retry has no side effect.

Preconditions: the application can be called by the Calling system; no booking file is needed. Postconditions: the Calling system holds a JSON answer with, per requested year, either its holidays (date and name) or an unavailable marker with the reason; no analysis ran and the history is unchanged.

Business rules: the answer contains only holidays that the calendar source supplies, never estimated or invented ones. The same years and calendar version give the same answer. The listing is a plain list of dates and names; it makes no statement about bookings.

Open issues: the parameters of the listing (years, range, country) are OI-18; the calendar source and its version reporting are decided in [ADR-0007] and the design gateway.

---

[UCD-001]: ../use-case-diagram.md
[US-001]: ../user-stories.md
[SA-001]: ../stakeholder-analysis.md
[DM-001]: ../domain-model.md
[SSD-001]: ../ssd.md
[PP-001]: ../project-plan.md
[ADR-0007]: ../adr/adr-0007-analysis-methods.md
