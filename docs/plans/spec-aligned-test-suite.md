# ExecPlan: Spec-Aligned Test Suite Hardening

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. Maintain this document in accordance with `.agent/PLANS.md` and ground every addition in `docs/test_specs.md`.

## Purpose / Big Picture

Budgeting, ledger, and reporting behavior must remain trustworthy even as the product evolves. This plan delivers a full testing pyramid that proves every specification in `docs/test_specs.md`, prioritizing fast unit/property checks, then integration, then Cypress E2E, and finally performance. By the end, a contributor can run `scripts/run-tests` with coverage enabled and immediately know which domain regressed, while Domain 8 journeys and Domain 9 performance budgets are guarded by deterministic suites. The plan also prunes legacy tests that no longer correspond to a spec so maintenance effort stays focused on meaningful assertions.

## Progress

- [x] (2025-12-11 18:20Z) Captured baseline audit of existing suites and recorded plan scope.
- [x] (2025-12-11 22:00Z) Milestone 1 — Coverage instrumentation and deterministic fixtures.
- [x] (2025-12-12 16:45Z) Milestone 2 — Spec-complete unit and property coverage.
- [x] (2025-12-12 20:10Z) Domain 3 rollover fix — `scripts/run-tests --filter property` now passes with Spec 3.6 asserting `Available(M-1)` carryover after seeding month state.
- [ ] (2025-12-11 18:20Z) Milestone 3 — Spec-complete integration coverage.
- [ ] (2025-12-11 18:20Z) Milestone 4 — Spec-complete Cypress journeys and cleanup.
- [ ] (2025-12-11 18:20Z) Milestone 5 — Performance harness and thresholds.

## Surprises & Discoveries

- Observation: No project-level coverage tooling is configured; `pyproject.toml` contains no `pytest-cov` reference (confirmed via `rg -n "pytest-cov" pyproject.toml`). Evidence: ripgrep returned no matches on 2025-12-11, so coverage gates must be added.
- Observation: Hypothesis `settings` does not accept a `seed=` keyword; deterministic property runs required exporting `HYPOTHESIS_SEED` before registering our custom profile. Evidence: pytest import error reproduced on 2025-12-11 until the environment variable approach replaced the unsupported parameter.
- Surprise: `budget_category_monthly_state` does not roll last month's availability into new months, so Spec 3.6 fails without a rollover job. Evidence: `scripts/search-logs dojo-run-tests-YNkmHQ --property` captured the 2025-12-12 failure (`0 == 6850`), so the new property test is marked `xfail` until the rollover logic is implemented. Resolution (2025-12-12 20:10Z): added `_ensure_category_month_state` + seeding SQL and reran `scripts/run-tests --filter property` to confirm deterministic carryover.

## Decision Log

- Decision: Use `pytest-cov` plus a repo-level `.coveragerc` for Python suites and `@bahmutov/cypress-code-coverage` + `c8` for Cypress so frontend/backend coverage can be aggregated. Rationale: aligns with priority on fast feedback and allows `scripts/run-tests` to emit a single summary target. Date/Author: 2025-12-11 / Codex.
- Decision: Replace the legacy `tests/integration/test_payday_assignment.py` with spec-specific integration modules per domain, then retire the legacy file once all new suites are in place. Rationale: the existing test only covers Domain 3.1 superficially and overlaps fully with Cypress user story 01; focusing on domain-specific modules reduces duplication. Date/Author: 2025-12-11 / Codex.
- Decision: Consolidate Cypress coverage to the seven Domain 8 flows and retire UI-only allocation stories (`cypress/e2e/user-stories/07` and `09`–`11`, `17`–`19`) after their assertions are captured at unit or integration layers. Rationale: Domain 8 demands zero-flake journeys, and the extra 13 UI scripts increase runtime without mapping to current specs. Date/Author: 2025-12-11 / Codex.
- Decision: Introduce an autouse pytest fixture that monkeypatches `dojo.core.clock.now()` with a deterministic, monotonic UTC ticker so ledger operations and integration tests share reproducible timestamps. Rationale: ordering-sensitive SCD-2 assertions (e.g., `list_recent`) flake when `recorded_at` ties; the fixture enforces deterministic ordering. Date/Author: 2025-12-11 / Codex.
- Decision: Mark the Spec 3.6 property test as `xfail` until month rollover carries `last_month_available_minor` forward; this preserves suite stability while documenting the gap exposed by `scripts/search-logs dojo-run-tests-YNkmHQ --property`. Date/Author: 2025-12-12 / Codex.
- Decision: Seed category monthly state via `_ensure_category_month_state` + `seed_category_month_state.sql`, update DAO activity math to subtract deltas, and drop the Spec 3.6 `xfail`. Rationale: ensures `Available(M)` reflects carryover + allocations - activity with deterministic property coverage. Date/Author: 2025-12-12 / Codex.

## Outcomes & Retrospective

- (2025-12-11) Milestone 1 complete: `scripts/run-tests --skip-e2e --coverage` emits backend coverage (72.6% overall, 87%+ in DAOs) plus `coverage/coverage.xml`, `coverage/coverage.json`, and leaves Cypress lcov scaffolding ready for Milestone 4. Deterministic Hypothesis and clock fixtures removed flakes in `tests/unit/budgeting/test_transactions.py`.

## Context and Orientation

Tests live under `tests/` for Python and `cypress/` for E2E. Unit tests currently emphasize `dojo.budgeting.services.TransactionEntryService`, `BudgetCategoryAdminService`, and `dojo.core.net_worth.current_snapshot` (see `tests/unit/budgeting/*.py` and `tests/unit/core/*.py`). Property suites in `tests/property/` use Hypothesis and in-memory DuckDB fixtures from `dojo.testing.fixtures`. Integration testing is minimal: `tests/integration/test_payday_assignment.py` is the only API-level test and relies on FastAPI's `TestClient`. Cypress scripts under `cypress/e2e/user-stories` reset and seed the DB via SQL fixtures (e.g., `tests/fixtures/e2e_account_onboarding_ledger.sql`). `scripts/run-tests` orchestrates pytest and Cypress, but today it lacks coverage flags or deterministic seeding beyond fixture usage. The database invariants (SCD-2 tables, Ready-to-Assign cache, allocation ledger) are enforced through services inside `src/dojo/budgeting/`. Reconciliation logic, net worth APIs, and goal calculations reside under `src/dojo/core` and `src/dojo/budgeting`. A novice following this plan will edit files inside these modules, create new test modules adjacent to existing suites, and adjust `scripts/run-tests`, `pyproject.toml`, and Cypress config (`cypress.config.cjs`) to introduce coverage collection.

## Existing Coverage Audit

Domain 1 (Account Onboarding) currently has service-level checks for CRUD (`tests/unit/budgeting/test_admin_services.py`) and a Cypress flow (`cypress/e2e/user-stories/15-account-onboarding-ledger.cy.js`). There is no integration test verifying RTA/net-worth side effects per Spec 1.1–1.4, so these specs require new coverage. The Cypress test spans UI but cannot assert SQL invariants; once integration specs exist, we keep the Cypress flow solely as a UI sanity check.

Domain 2 (SCD-2 Ledger) is partially covered by unit tests in `tests/unit/budgeting/test_transactions.py` (edits, deletes, cross-account transfers) and property tests in `tests/property/budgeting/test_transactions_properties.py` (one-active-version, chronological chain). Missing pieces include reconciliation window integrity (Spec 2.4), cross-account edit balance validation (Spec 2.5) at API level, historical ripple/backdating (Spec 2.6), and reconciliation adjustment flows (Spec 2.8). No unit test captures Spec 2.3's concurrent edit protection, and there is no fuzz/state-machine coverage for Spec 2.7 yet (existing property tests verify chains but not `valid_to == valid_from` continuity under randomized operations for entire lifecycle). We must augment the property suites and add dedicated integration cases with fixtures representing reconciled accounts.

Domain 3 (Ready to Assign and Allocations) has several unit tests inside `tests/unit/budgeting/test_transactions.py` (guard rails, RTA updates) and property tests in `tests/property/budgeting/test_budgeting_properties.py` (reallocation conservation, cache correctness). Specs 3.2, 3.6, and 3.7 require stronger property coverage (global zero-sum, fundamental budget equation). Spec 3.4 (Category Rollover) is partially covered via `test_last_month_state_aggregates`, but no integration test asserts the month flip API or reports. There are redundant Cypress scripts (07, 09, 10, 11, 17, 18, 19) that exercise allocation UI details multiple times without mapping to Domain 8; these will be retired once unit/integration specs assert the same invariants.

Domain 4 (Spending Flows) lacks direct tests. The unit suite verifies generic transaction create/delete but never asserts the spec-specific envelopes (cash vs credit, split precision, refund behavior). Integration coverage is absent, so the entire domain must be implemented from scratch at the API layer, plus targeted unit tests for split rounding (Spec 4.6).

Domain 5 (Transfers, Contributions, Payments) has limited unit coverage for transfers in `tests/unit/budgeting/test_transactions.py`, but the assertions stop at account balances and do not ensure RTA neutrality, category impact, or asset isolation per specs 5.1–5.6. No integration-level verification ensures both legs are stored, nor do we have Cypress coverage tied to Domain 5 flows (user story 04 touches accessible assets but must be updated to align precisely with Spec 5.2/5.3). This domain needs new integration tests plus some property invariants (e.g., ensuring paired transfer entries remain balanced).

Domain 6 (Month Boundary) is partially touched by unit tests, yet there is no API/integration test to assert the month-flip endpoint and zero-sum behavior during rollover. The existing Cypress story 14 exercises monthly summary cards but does not explicitly check the spec validations, so both integration and E2E coverage must be enhanced.

Domain 7 (Net Worth) has unit and property coverage for aggregation (`tests/unit/core/test_net_worth.py`, `tests/property/core/test_net_worth_properties.py`). However, Spec 7.1 demands API integration verifying account-class breakdowns, Spec 7.2 needs lifecycle tests for inactive accounts, and Spec 7.3 calls for a property test that asserts the equation while toggling tracking/on-budget roles and account activation. None of these exist today.

Domain 8 (UI Journeys) is partially satisfied by `cypress/e2e/user-stories/01`–`06`, `12`, `15`, and `16`, which align roughly with Specs 8.1, 8.2, 8.6, and 8.7. Specs 8.3–8.5 are not explicitly covered; user stories 12 and 14 touch on investment transfers and monthly summaries but need to be refactored to follow the new scenario scripts. To keep Cypress fast and deterministic, we will collapse the suite into exactly seven spec-aligned specs and retire the nine user stories that duplicate Domain 3 behavior.

Domain 9 (Performance) has no tests. We must build a reproducible DuckDB dataset generator (10k+ transactions) and benchmark ready-to-assign and net-worth queries against the stated latency targets.

Domain 10 (Budget Goals) currently only verifies goal CRUD (`tests/unit/budgeting/test_goals.py`) and metadata persistence. Specs 10.1–10.5 (target calculations, skipped months, recurring intervals) have zero coverage, so we must add deterministic unit tests around the goal calculation utilities and a small integration test for skipped-month catch-up logic.

## Milestones

### Milestone 1 — Coverage Instrumentation and Deterministic Fixtures

Outcome: `scripts/run-tests` accepts `--coverage`, installs/configures `pytest-cov`, produces `coverage.xml`, and collects Cypress coverage via `@bahmutov/cypress-code-coverage`. Hypothesis stateful tests receive seeded RNG per run via a `HYPOTHESIS_SEED` environment helper, and a shared clock helper (wrapping `dojo.core.clock`) ensures fixed timestamps for month-boundary tests and monotonic `recorded_at` ordering. Acceptance: running `scripts/run-tests --skip-e2e --coverage` records ≥60% backend coverage baseline and stores artifacts under `coverage/`.

### Milestone 2 — Spec-Complete Unit & Property Coverage

Outcome: Each Domain 2, 3, 5, 7, and 10 unit/property spec is encoded in targeted modules:
- `tests/unit/budgeting/test_transactions_scd2.py` for Specs 2.1–2.3, 2.6, 2.8.
- `tests/property/budgeting/test_allocations_properties.py` for Specs 3.2, 3.6, 3.7.
- `tests/unit/budgeting/test_spending_precision.py` for Spec 4.6.
- `tests/unit/budgeting/test_goals_calculations.py` for Specs 10.1–10.5.
- Property tests for Spec 2.7 and 7.3 expanded in existing modules.
Acceptance: `scripts/run-tests --filter unit` and `--filter property` both pass with coverage on, and failing the new tests before code changes can be demonstrated via selective rollbacks.

### Milestone 3 — Spec-Complete Integration Coverage

Outcome: Create `tests/integration/domainX` modules that call FastAPI endpoints using `TestClient` or `httpx.AsyncClient` with in-memory DuckDB and fixtures that mirror each spec's initial condition. Each Domain 1–7 & 10.3 spec has at least one integration test verifying API responses and DB state. Legacy `tests/integration/test_payday_assignment.py` is removed once these modules exist. Acceptance: `scripts/run-tests --skip-property --skip-e2e --coverage` passes and reports ≥80% backend coverage for touched modules.

### Milestone 4 — Cypress Journeys and Cleanup

Outcome: Replace `cypress/e2e/user-stories` with `cypress/e2e/specs/` containing seven files (`08.1`–`08.7` naming). Each script seeds DB via dedicated fixtures, freezes time via backend API or stubbed clock, and asserts spec validations end-to-end. Retire redundant stories 07 and 09–11, 17–19 once Domain 3 invariants exist in lower layers. Acceptance: `scripts/run-tests --filter e2e` runs only seven specs with green runs in two consecutive executions, and analytics show no network retries/timeouts.

### Milestone 5 — Performance Harness

Outcome: Add `tests/perf/` (or `scripts/run-tests --filter perf`) that seeds ≥10k transactions using `tests/fixtures/high_volume.sql`, runs `python -m dojo.budgeting.services ReadyToAssignService` queries, and asserts wall-clock thresholds (<200 ms for RTA, <100 ms for net worth). Integrate with CI optional job. Acceptance: `scripts/run-tests --filter perf` prints timing summary and fails when thresholds exceeded.

## Plan of Work

1. Add `pytest-cov` and `coverage[toml]` to `pyproject.toml`, create `.coveragerc` excluding generated fixtures, and update `scripts/run-tests` to accept `--coverage` (defaults to off). Update `cypress.config.cjs` and `src/dojo/frontend/vite` entry to include `@bahmutov/cypress-code-coverage` plugin plus Babel instrumentation, writing combined reports to `coverage/lcov.info`. Document usage in `scripts/README.md`.
2. Create deterministic fixtures: extend `tests/fixtures/for_unit_testing.sql` to include reconciled accounts and month boundary data. Add a helper in `tests/conftest.py` to freeze `dojo.core.clock.now()` via monkeypatch, ensuring reproducible `recorded_at` fields in integration tests. Update property fixtures to call `hypothesis.settings(seed=...)` and set `Phase.reuse` off for stability.
3. For Domain 2 unit/property coverage, split the monolithic `tests/unit/budgeting/test_transactions.py` into domain-specific modules (keep file for general tests, add `test_transactions_scd2.py` for specs). Write targeted tests for correction flows (2.1), voids (2.2), concurrent edit guard (2.3) by simulating `TransactionEntryService.create` from concurrent tasks using `threading` + connection clones, backdated insert ripple (2.6), and reconciliation adjustments (2.8). Extend Hypothesis tests to fuzz entire lifecycle (2.7) ensuring `valid_to` continuity and single active rows even during randomly interleaved deletes/edits.
4. For Domain 3 properties, create `tests/property/budgeting/test_ready_to_assign_properties.py` verifying zero-sum allocations, fundamental budget equation, and global cash/envelope conservation using generated sequences of inflows, allocations, category-to-category moves, and spending. Use in-memory snapshots to confirm invariants across months. Expand unit tests for guard rails (Spec 3.3) by asserting API error payload shape using `TestClient` to ensure stable error JSON.
5. Domain 4 & 5 integration tests: add modules under `tests/integration/domain4_spending.py` and `domain5_transfers.py`. Use FastAPI `client` fixture to post transactions/transfers per spec, then query `/api/budget/categories`, `/api/accounts`, and net worth endpoints to confirm RTA neutrality, category changes, and net worth effects. Cover split precision via service-level tests verifying integer minor units and rounding distribution.
6. Domain 6 integration: script month flip by calling the scheduler or a management endpoint (if nonexistent, use services). Validate category rollover and RTA invariants while asserting API responses for reports. Domain 7 integration: call `/api/net-worth/current` and new `GET /api/net-worth/history?as_of=` endpoints to ensure inactive accounts excluded and tracking accounts included per spec.
7. Domain 10 unit/integration: implement calculation helpers (if absent) exposed from `dojo.budgeting.services.GoalCalculator`. Write tests covering monthly target math, existing balance adjustments, skipped month catch-up, recurring targets, and interval goals per spec. For Spec 10.3 integration, simulate month skip via fixtures and assert API output statuses.
8. Refactor Cypress suite: create `cypress/e2e/specs/08.1-onboard-paycheck-allocate.cy.ts` etc. Each spec-specific file should import shared page objects, use `cy.task("freezeTime", ...)` to lock the server clock (add supporting task in `cypress.config.cjs` hooking into backend). Ensure intercepts watch API endpoints defined in specs. Remove redundant user-story scripts after ensuring coverage is captured elsewhere, and update `cypress/support/e2e.js` to register coverage plugin.
9. Establish performance harness: add `tests/perf/high_volume.py` building a DuckDB file using `tests/fixtures/high_volume.sql` or Python generator, run core queries, measure durations via `time.perf_counter`, and assert thresholds. Extend `scripts/run-tests` to accept `--filter perf` and document usage.
10. Update documentation: add `docs/rules/cypress.md` or existing doc to describe deterministic seeding/time control, update `README.md` with coverage usage, and mention new plan in `docs/plans/ci-release-pipeline.md` if necessary.

## Concrete Steps

1. Run `rg -n "pytest-cov" pyproject.toml` to verify dependency absence (already done) and then add it; after editing, run `poetry lock` or `uv pip compile` per repo tooling (here: update `uv.lock` via `uv pip compile` if needed). Validate by running `scripts/run-tests --skip-e2e --coverage` to ensure coverage report creation.
2. Use `scripts/run-tests --filter unit:budgeting` repeatedly while adding new unit/property tests; rely on `pytest -k` locally if needed but record canonical command in plan.
3. For integration suites, run `scripts/run-tests --skip-property --skip-e2e` to keep runtime manageable until Cypress is ready. After migrating Cypress scripts, run `scripts/run-tests --filter e2e` twice to confirm stability.
4. For performance harness, run `scripts/run-tests --filter perf` and capture timings; store the baseline in `docs/test_specs.md` appendices or a new `docs/plans/perf-benchmarks.md` entry.

## Validation and Acceptance

- Each milestone closes only when `scripts/run-tests` (with relevant skips) passes twice consecutively and coverage thresholds (60% after Milestone 1, 80% backend after Milestone 3) are satisfied.
- Unit/property additions must fail on pre-change code: intentionally revert the new assertions temporarily to confirm they detect regressions (record evidence via log excerpts in this plan's `Surprises` section).
- Integration tests must inspect both API responses and direct DB state (via DuckDB queries) to ensure ledger and category tables match specs.
- Cypress specs must assert UI plus server values (e.g., intercept `/api/budget/ready-to-assign` responses) and run without retry loops.
- Performance harness must log actual timings and fail if budgets are exceeded, ensuring CI enforces latency.

## Idempotence and Recovery

In-memory DuckDB fixtures and Cypress DB resets already provide clean states. Ensure new fixtures are idempotent by truncating tables before inserts. Property tests should cap `max_examples` to avoid long runs yet remain reproducible due to seeds. If `scripts/run-tests --coverage` fails mid-run, rerun with the same command; coverage data in `coverage/` should be deleted before reruns via `rm -rf coverage/` (documented in README). Cypress tasks that freeze time must always unfreeze in `afterEach` to avoid leakage.

## Artifacts and Notes

- Store combined coverage reports under `coverage/coverage.json` (Python) and `coverage/lcov.info` (Cypress). Publish summary percentages in CI logs.
- Keep new fixtures in `tests/fixtures/` (e.g., `high_volume_performance.sql`) with comments describing usage.
- Record major discoveries (e.g., uncovered race conditions) in this plan under `Surprises & Discoveries` with log snippets for future readers.

## Interfaces and Dependencies

- Python services: `dojo.budgeting.services.TransactionEntryService`, `BudgetCategoryAdminService`, `AccountAdminService`, `GoalCalculator` (to be created if missing), `dojo.core.net_worth.current_snapshot`, reconciliation helpers in `dojo.budgeting.services.ReconciliationService` (or implement). Integration tests will hit FastAPI routes defined in `src/dojo/budgeting/routers.py` and `src/dojo/core/routers.py`.
- Testing libs: `pytest`, `pytest-cov`, `hypothesis`, `duckdb`, `fastapi.testclient`. Property tests depend on `hypothesis.strategies` and must import new helper fixtures for deterministic seeds.
- Cypress: `cypress`, `@bahmutov/cypress-code-coverage`, page objects under `cypress/support/pages/*.js`. Add TypeScript support if desired when renaming files, ensuring Vite build instrumentation via Babel plugin.
- Performance harness: standard library `time` for benchmarking plus `duckdb` CLI to load fixtures quickly.

By following this ExecPlan, a contributor unfamiliar with Dojo can implement, validate, and maintain a spec-complete, coverage-aware test pyramid without ambiguity.