# AI Prompt: Plan the Hotel Booking Analysis marimo Project

We are in **planning mode**. Create a practical, reviewable project plan for a marimo application that analyzes hotel booking data. Do not implement the application yet: make no source-code, test, configuration, dependency, or environment changes. The deliverable for this phase is the planning documentation and its task breakdown.

The application will be called by another system. That calling system is the actor and will supply a JSON file containing hotel booking records. After analysis, the application must return the analysis result to the caller as JSON and append the result to a local JSONL history file. Marimo must also be able to display prior results from that JSONL history. Retain only the most recent configured number of results; the default is 10. The retention setting must come from a configuration file. For local development and demonstration later, the example file is expected at `./data/example/nf_hotel_bookings.csv`; it may be added later. The production input is JSON, not the example CSV.

Inspect the repository and its existing project guidance, artifact catalog, registry, and planning conventions before proposing files. Follow the applicable repository guidance without repeating general coding rules in this prompt. Use the repository's project-planning and artifact conventions for gateways, tasks, user stories, use cases, and artifact documents. Do not duplicate an artifact format or invent a parallel planning structure.

## Planning outcome

Produce a phased plan organized as **gateways**, each with a concrete deliverable and objective Go/No-Go criteria. Each gateway must include its task breakdown.

**Create exactly one task for each artifact document or artifact instance judged necessary.** A task must produce one artifact; do not bundle several artifacts into one task. If one artifact document contains several related user stories, it is still one artifact and gets one task. After the required artifacts for a scope are completed and reviewed, create the coding tasks that implement that scope in a later gateway. Coding tasks must depend on and reference the relevant approved artifacts (such as user stories, use cases, data contracts, models, and architecture decisions). Do not schedule coding before its prerequisite artifacts. This remains planning only: define the coding tasks, but do not implement them now.

First decide which artifacts are actually needed for this project. Consider the existing artifact catalog and repository state; do not mechanically create every artifact type. For each selected artifact, state its purpose, why it is needed, the gateway where it will be delivered, and its dependencies. Include the project plan and gateway documents required by the repo's planning convention. Add user-story/use-case artifacts for real actor goals, and design/data/architecture artifacts only where they clarify a decision needed before implementation. Capture missing facts as assumptions or open issues instead of inventing them.

Do not sync milestones or issues to a remote Git host, commit, push, or open a pull request. The plan should be reviewable locally first.

## Business goal

Plan an interactive, understandable analysis of hotel booking timing, arrivals, holidays, cancellations, guest mix, and estimated room revenue. The eventual application should make data limitations visible and distinguish observed associations from causal claims. This planning request must result in requirements and a staged plan only, not the app itself.

## Actor and primary use case

**Actor:** Calling system.

**Primary use case:** Analyze hotel bookings.

The calling system supplies JSON booking records; the eventual app validates and prepares the data, presents analyses, and reports data quality issues. On completion, the result is returned to the caller as JSON and appended to a local JSONL history. The marimo interface can display results from that history. Retention is controlled by a configuration file and defaults to the latest 10 results. During local development only, the app may fall back to `./data/example/nf_hotel_bookings.csv` when no JSON input is supplied. The production input and result contracts have not yet been specified unless the repository contains them. Plan artifacts/tasks to define both contracts, the history format/location, and configuration behavior; do not silently assume schemas.

## Candidate user goals to assess and model

Choose concise, independent stories/use cases appropriate to the artifact conventions. The following are candidate goals, not a requirement to create a separate artifact for each bullet:

1. **Load and understand data:** supply JSON records; learn record count, date coverage, missing or invalid values, and duplicate booking IDs when available. Analyses with missing fields should be identified as unavailable rather than fabricated.
2. **Explore lead time:** understand booking windows overall and by cancellation status, arrival period, market segment, and customer type where fields exist. Compare supplied lead time with the date difference between booking and arrival when possible.
3. **Analyze Cambodian holidays:** use the Python `holidays` package for Cambodia (`KH`) for years present in the data. Separate booking-date behavior from arrival-date behavior; compare holiday dates and configurable windows (for example, 1, 3, or 7 days before/after) with suitable non-holiday periods. Consider weekday, season, year coverage, and sample size. Describe association, not causation. Do not invent holidays if package support is unavailable.
4. **Understand seasonality and booking pace:** distinguish bookings by booking date from arrivals by arrival date; summarize useful weekly/monthly patterns, cancellation rates, and prices where available; account for partial-year coverage.
5. **Investigate cancellations:** compare cancellation rates by lead-time bands, deposit type, market segment, customer type, arrival period, special requests, and booking changes where available. Show denominators/sample sizes; avoid causal or unsupported predictive claims.
6. **Estimate room value and stay patterns:** derive length of stay from weekend and weekday nights; where price and nights exist, estimate booking value as nightly price times total nights. Separate canceled bookings and clearly label the result as an estimate, not realized revenue, because payments, taxes, discounts, and adjustments are not supplied.
7. **Explore guest and booking mix:** inspect guest composition, country, meal, room type, repeat-guest status, parking, and special requests where available, and compare with length of stay, cancellation, or price when meaningful.

## Development data context

The example CSV is semicolon-delimited and currently includes: `booking_id`, `hotel`, `is_canceled`, `lead_time`, `arrival_date_week_number`, `booking_date`, `arrival_date`, `arrival_date_day_of_month`, `stays_in_weekend_nights`, `stays_in_week_nights`, `adults`, `children`, `babies`, `meal`, `country`, `market_segment`, `is_repeated_guest`, `previous_cancellations`, `assigned_room_type`, `booking_changes`, `deposit_type`, `agent`, `customer_type`, `required_car_parking_spaces`, `total_of_special_requests`, and `price_per_night`.

Treat this only as sample-data context, not as a guaranteed production JSON schema. The plan should identify required versus optional fields for the analyses and include data-quality, date-parsing, and input-format considerations where relevant. Also cover output JSON schema, JSONL history, history retention configuration, and displaying saved results in marimo.

## Result delivery, history, and configuration requirements

Plan the end-to-end behavior and its artifacts/tasks for these requirements:

- Return each completed market analysis to the calling system as a JSON result. Define the result envelope and versioning/identification fields in a data contract artifact if one is needed. Include analysis status, input/reference metadata, generated time, and findings as justified by the analysis; avoid embedding raw booking records unless a documented need requires them.
- Append each result as one JSON object per line to a local JSONL history file. Define where the file lives, how it is created/read, and how malformed lines or interrupted writes are handled.
- Let the marimo app load and display results from the JSONL history, including a way to select among retained results and show when each analysis was produced.
- Keep only the latest N results, where N is loaded from a configuration file and defaults to 10 when omitted. Plan the configuration format/location, validation for invalid values, and when retention is applied. Retention must not delete more than required to enforce the configured limit.
- Make the JSON result returned to the caller and the local history record consistent representations of the same completed result. Decide and document behavior if returning to the caller or writing history fails; do not claim delivery succeeded when it did not.

## Expected planning work

- Review the repository to determine which planning artifacts already exist and which are missing. Avoid overwriting or duplicating existing artifacts.
- Define gateways in a sensible order: complete and review the required artifacts for a scope before its dependent coding gateway begins. Include dependencies, target dates only where supported by known constraints, concrete deliverables, and measurable Go/No-Go criteria. If dates, owners, stakeholders, business constraints, or approval roles are unavailable, record them as open issues; do not invent identities or dates.
- Create/plan the Project Plan and one gateway document per phase, following repository conventions. Each gateway document must hold that gateway's task list.
- Model actor goals as user stories and/or use cases using the repository's artifact types. Ensure every such artifact has its own task in the gateway that delivers it.
- Add an explicit task for every other artifact document selected as necessary (for example, data contract, domain/data model, architecture decision, or analysis/KPI definitions). Keep this list selective and justify each artifact.
- For every task, give a short title and a one-to-three-sentence summary that explains the work and why it matters. Mark whether it needs its own user story/use case according to the repository's planning rules; technical artifact-writing tasks generally do not represent an actor goal. Add coding tasks only in a later gateway, after their prerequisite artifacts are completed; each coding task must name the artifacts/stories it implements and have a concrete, reviewable software deliverable.
- Keep cross-references, IDs, versioning, links, and artifact registry updates consistent with the repo's artifact workflow. If scaffolding is needed, use the repo's documented artifact process; do not write ad hoc documents that bypass it. Consider separate data-contract artifacts for input and output/history only if the repository conventions and scope warrant them; each selected artifact must have its own task.
- Check task coverage: every planned artifact is represented by exactly one task; every task's artifact deliverable is clear; every user story traces to a use case or gateway as appropriate; every gateway has a decision-ready deliverable and criteria.
- State explicitly that the current activity creates/revises planning artifacts and defines future coding tasks only. No marimo app, Python modules, tests, dependency installation, or `.venv` changes are made until the required artifacts are completed and the coding gateway is authorized to start.

## Planning completion report

When planning is complete, summarize:

- Gateways and their purpose/deliverables.
- The artifacts selected, why they are needed, and the gateway/task that will produce each one.
- Any assumptions, unresolved decisions, risks, or missing stakeholder/date information.
- Confirmation that no application code or environment changes were made.
- The next review decision needed before implementation begins.
