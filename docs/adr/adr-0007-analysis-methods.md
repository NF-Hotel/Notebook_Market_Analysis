# ADR-0007: Analysis Methods

## Metadata
| Key | Value |
| --- | --- |
| ID | ADR-0007 |
| CrossReference | [US-001], [UC-001], [DM-001], [ADR-0001], [ADR-0002], [ADR-0004] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |

---

## Context

The stories ask for analyses that are honest about their limits: associations not causes, denominators everywhere, holiday effects handled carefully, and room value labeled an estimate. Without fixed definitions two implementations would give different numbers. The data may cover partial years (the sample's bookings run from 2021-03-08 to 2025-12-29, arrivals from 2022-01-01 to 2025-12-31), so period coverage matters. The values below are proposed defaults for S01 and S03 to confirm; bands and thresholds are not derived from a business rule.

## Decision

**Common rules**

- Every rate is reported as numerator and denominator ([ADR-0002]). A group with fewer records than `min_group_size` (default 30, [ADR-0004]) is flagged `small_sample` and still shown. Comparisons across groups are made only among groups that are not flagged.
- Records with a missing or invalid value in a field are left out of the analyses that need it and counted ([ADR-0001]).
- Wording is drawn from a fixed set of templates that describe an observed association ("was higher in", "was associated with", "was observed"). The words "caused", "because", "due to", "effect of", "leads to" and "drives" never appear in findings; a test checks this.
- Arrival period means calendar month and quarter. No seasons (dry, rainy) are defined, because none are supplied.

**Lead time**

- Bands in days: 0 to 7, 8 to 30, 31 to 90, 91 to 180, 181 and more.
- The distribution (count and median) is given overall and split by cancellation status, arrival month, market segment and customer type.
- Comparison with dates: difference = arrival date minus booking date in days; the count and share of records where it differs from `lead_time` are reported.

**Cambodian holidays**

- Holidays come from `holidays.country_holidays("KH", years=...)` for the years present in the relevant date field. If the package returns no holidays for a year, that year is reported unavailable with no substitute.
- Booking-date behavior and arrival-date behavior are analyzed separately.
- Each calendar day within the data's date span is classified as: a holiday; within the configured window before a holiday; within the window after; or baseline (not a holiday and outside the largest window of every holiday). A day near two holidays takes the closest; a tie or a holiday itself takes the holiday class.
- For each window size in `holiday_windows_days` (default 1, 3 and 7) and each of the before and after sides, the result gives the mean number of bookings per day (booking side) or arrivals per day (arrival side), and the cancellation share of arrivals, alongside the baseline on the same weekday, with the number of days in each group as denominator.
- Groups of fewer than `min_group_size` days are flagged. The year span is stated so partial coverage is visible.

**Seasonality and booking pace**

- Bookings are counted by booking date and arrivals by arrival date as separate monthly and ISO-week series, each with cancellation share and mean `price_per_night` where the fields exist.
- A period is `partial` if the series' first or last observed date does not cover it fully; a year with fewer than 12 months present is listed as incomplete.

**Cancellations**

- Cancellation rate (numerator and denominator) by: lead-time band, deposit type, market segment, customer type, arrival month, special requests (0, 1, 2, 3 or more) and booking changes (0, 1, 2 or more). No modeling and no prediction.

**Room value and stay**

- Length of stay = weekend nights + week nights. Stay buckets: 1, 2, 3, 4 to 7, 8 or more nights; records with 0 nights are left out of value and counted.
- Estimated value = `price_per_night` × length of stay, computed with exact decimals, reported as total, mean and count for cancelled and for not-cancelled bookings separately, and never combined into one figure. Records with price 0 are included and counted separately.
- The input carries no currency, so figures are labeled "in the price units of the input", and every value carries the notice `ESTIMATE_NOT_REVENUE`: an estimate, not realized revenue, since payments, taxes, discounts and adjustments are not supplied.

**Guest and booking mix**

- Total guests = adults + children + babies. Distributions are given for total guests, country, meal, assigned room type, repeat-guest status, parking spaces and special requests.
- Comparison with length of stay, cancellation share or mean price is given only for groups that are not small samples.

## Consequences

**Positive:**

- The analyses are reproducible and testable against hand-computed fixtures.
- Limits (small samples, partial periods, unavailable years) are visible in every result.
- Association-only wording is enforced by a test.

**Negative:**

- Bands, the sample threshold and the holiday day-classification are choices that stakeholders may want to change.
- The holiday baseline uses a simple day classification and is not adjusted for other factors; it cannot support causal claims.
- The unknown currency limits value figures to relative comparison.

## Affected Artifacts

- [US-001] — stories 02 to 07.
- [UC-001] — step 4 and its business rules.
- [DM-001] — Analysis kinds and Group Statistic.
- [ADR-0001] — required fields.
- [ADR-0002] — how findings are reported.
- [ADR-0004] — configurable windows and sample threshold.

---

[US-001]: ../user-stories.md
[UC-001]: ../use-cases/uc-001-analyze-hotel-bookings.md
[DM-001]: ../domain-model.md
[ADR-0001]: ./adr-0001-input-json-contract.md
[ADR-0002]: ./adr-0002-result-json-contract.md
[ADR-0004]: ./adr-0004-configuration-file.md
