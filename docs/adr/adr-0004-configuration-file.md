# ADR-0004: Configuration File

## Metadata
| Key | Value |
| --- | --- |
| ID | ADR-0004 |
| CrossReference | [US-001], [UC-001], [ADR-0001], [ADR-0003], [ADR-0007] |
| DomainLanguages | IT Professional English |

## Version History
| Date | Status | Author | Reviewer |
| --- | --- | --- | --- |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |
| 2026-09-29 | Approved | Jens Tirsvad Nielsen | Team2 (S04) |

---

## Context

Retention must come from a configuration file and default to 10 when omitted. The format, location and validation are not specified. Other behavior that needs a setting has appeared in the other decisions: the history path ([ADR-0003]), the development fallback ([ADR-0001]), the holiday windows and the small-sample threshold ([ADR-0007]). Options for format: JSON (no comments), TOML (comments, standard library reader in the Python version in use), YAML (extra dependency), environment variables (poor for structured values).

## Decision

The configuration is a TOML file named `hotel_analysis.toml`, read from the working directory unless another path is given by the `--config` option or the `HOTEL_ANALYSIS_CONFIG` environment variable (the option wins). TOML is read with the Python standard library.

```toml
environment = "production"          # "production" (default) or "development"

[history]
retention = 10                      # latest results kept; default 10
path = "output/analysis_history.jsonl"

[analysis]
holiday_windows_days = [1, 3, 7]    # days before and after a holiday
min_group_size = 30                 # groups smaller than this are flagged
```

Rules:

- Every key is optional. An omitted key takes the default shown; an omitted `history.retention` therefore gives 10.
- If the file does not exist, all defaults apply and the result carries a notice that no configuration file was found.
- `history.retention` must be an integer of at least 1. Zero, negative numbers, decimals, strings and booleans are invalid.
- `holiday_windows_days` must be a non-empty list of distinct integers of at least 1. `min_group_size` must be an integer of at least 1. `environment` must be one of the two values.
- If the file cannot be parsed or a value is invalid, the run fails before any analysis with an input error naming the key; the history is not touched and no default is guessed.
- Unknown keys are ignored and listed in a notice.
- Configuration is read once at the start of each run; the marimo interface reads it when it opens.

## Consequences

**Positive:**

- Retention and the other tunable behavior are changed without code changes.
- Invalid values fail loudly, so a typo cannot silently delete history.
- No new dependency is needed to read the file.

**Negative:**

- Callers must ship or generate a TOML file if defaults do not suit them.
- A missing file is tolerated, so a misplaced file is only caught by the notice.

## Affected Artifacts

- [US-001] — story 09 acceptance criteria on retention.
- [UC-001] — extensions 7a and 7b.
- [ADR-0001] — the `environment` setting.
- [ADR-0003] — `history.path` and `history.retention`.
- [ADR-0007] — `holiday_windows_days` and `min_group_size`.

---

[US-001]: ../user-stories.md
[UC-001]: ../use-cases/uc-001-analyze-hotel-bookings.md
[ADR-0001]: ./adr-0001-input-json-contract.md
[ADR-0003]: ./adr-0003-jsonl-history-and-retention.md
[ADR-0007]: ./adr-0007-analysis-methods.md
