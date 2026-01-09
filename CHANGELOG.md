# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Account Onboarding Wizard: New multi-step modal for creating accounts with detailed configuration (APY, credit limits, etc.) aligned with architecture specs.
- Backend schemas and migrations to support detailed account properties (interest rates, terms, institution names).
- Account detail pages: dedicated per-account pages with charts, filtered ledgers/holdings, and URL-driven integrity actions (reconcile, verify holdings, valuation).
- Account reconciliation: worksheet view + checkpoint commits from Accounts page.
- Cache rebuild utility (`scripts/rebuild-caches`) for recomputing current balances and budgeting state.

### Changed
- Budget category availability now carries forward across months.
- Budget allocations UI refactored into `AllocationModal` + `AllocationTable`; the budgets page now focuses on orchestration.
- `scripts/run-tests` supports `--coverage` and merges pytest + Cypress coverage when enabled.
- UI polish: refined border thickness and table spacing.

### Fixed
- Budget/transaction date handling: fixed missing `todayISO` import and timezone formatting drift.
- Cypress e2e stability: pin backend date via `x-test-date`, stub `Date` in specs (without freezing timers), and anchor fixtures to explicit months.
- Cypress code coverage is now optional, so `scripts/run-tests` no longer fails when the plugin is missing.

### Testing
- Expanded unit/property coverage for budgeting invariants (goals, spending precision, SCD2 transactions).
- Expanded and renamed integration coverage (account onboarding, month boundaries, net worth snapshots, transfers, reconciliation).

### Docs
- Added `docs/test_specs.md`, `docs/architecture/reconciliation.md`, and plans for reconciliation + spec-aligned tests; refreshed rules and data-model docs.

### Removed
- Removed stale test-spec documentation.

## [v0.1.2] - 2025-12-11

### Added
- **Vue 3 / Vite Frontend**: Complete migration of the frontend to Vue 3 SFCs and Vite, offering improved performance and developer experience.
- **Deletion Support**: Ability to delete allocations and transactions, implemented with SCD2 safety (soft deletes) and updated UI controls.
- Python integration test suite (`tests/integration`) for verifying core API logic independently of the frontend.
- Collapsible budget groups with stable table layout and bulk category assignment from the group modal.
- Controllable system clock for budgeting flows to facilitate time-travel testing.
- Added a title to the transactions page for improved user experience.
- Enabled reordering of budget categories directly on the budgets page.
- New development scripts (`prefetch-npm-deps`, `update-frontend-deps`, `search-logs`) for enhanced developer workflow.

### Changed
- Refined UI aesthetics: updated color palette to cohesive earth tones, standardized sentence case for labels, removed redundant help text, and improved delete button styling for consistency.
- Validated and updated Cypress E2E tests to reflect the completed Vue frontend migration and new features.
- Default recurring budget due dates to the start of the next month.
- Documented Kubernetes consumption patterns and extracted release-note tooling into a reusable CLI.
- Removed legacy SPA code and dependencies following the Vue migration.
- Streamlined allocation deletion by removing the confirmation dialog to align with transaction deletion UX.

### Fixed
- Transaction status toggles: restored visual states and ensured status updates are correctly handled via API.
- Allocation dropdowns now mirror budget table order, show system categories first, and hide group placeholders from selection.
- Hardened DuckDB migrations against DDL serialization races and centralized backup logic for Kubernetes deploys.
- CI reliability: addressed issues with frontend asset injection, `npmDepsHash` updates, and Cypress/frontend build paths in `flake.nix`.
- Cypress stability: enforced Anti-Flake network rules, stabilized specs, and refreshed testing documentation.
- Resolved runtime errors on the `TransactionsPage` and removed visible migration markers from the UI.
- Fixed linter errors and configured Biome for consistent code style enforcement.

### Breaking
- None.

## [v0.1.1] - 2025-12-01

### Added
- Auditable ledger MVP: FastAPI monolith with DuckDB migrations, temporal transaction service, net worth API, and SPA wired to `/api/transactions` and `/api/net-worth/current`.
- Unit and property tests for transaction invariants and net worth aggregation plus a Cypress e2e suite driven via `npx cypress run --e2e --browser <browser> [--headed]`.
- Account and budget management APIs with SPA create/edit/deactivate flows and Cypress coverage.
- Account classes/roles, SCD detail tables, special categories, categorized-transfer API, Ready to Assign route, tangibles valuation table, and corresponding unit tests feeding the net worth snapshot.
- SPA Assets & Liabilities experience with backend-driven stats, account-class grouping and icons, account detail modal, and an Add Account POST flow with defaults.
- Envelope-budgeting MVP: transactions form with mode/unit toggles, allocation form and category modal, categorized transfer UX with toasts, backend category-state joins (`month` query), README guidance, and Cypress scenarios.
- Transaction status tracking that persists pending/cleared states, returns `status` in `/api/transactions`, and renders reconciliation state in the ledger.
- Dedicated allocations ledger persisted in DuckDB, `/api/budget/allocations` guard rails and month summary, and a `#/allocations` SPA page with summary chips, ledger table, and Cypress coverage.
- Dev/demo data loader (`python -m dojo.core.seed`) for `sql/seeds/*.sql` plus test fixtures under `tests/fixtures/`.
- End-to-end specs with fixtures for payday assignment, funded credit card spending, credit payment envelope backfill, Rolling with the Punches reallocations, categorized investment transfers, and manual transaction lifecycle; added monthly summary, account onboarding, and credit transaction correction workflows (Stories 14–16).
- Deployment pipeline and infrastructure: Nix-built layered Docker image (`:edge`), Kustomize manifests with `Recreate` strategy, GitHub Actions CI/registry publish, and a `/healthz` endpoint for Kubernetes probes.

### Changed
- Renamed the canonical test wrapper to `scripts/run-tests`, fixed timing, added filtering, and enabled parallel suite execution; refreshed agent/docs guidance.
- Updated SQL guidance to keep SQL within `src/dojo/sql/`; enforced sqlfluff compliance with dollar params and explicit joins; added broader Ruff checks, actionlint, and Rust 120-character limit.
- Rebuilt CI/release automation with GitHub Actions for GHCR images and tag-based releases, aligned deploy image tagging, and hardened DuckDB migrations with preflight init and docs.
- Normalized budgeting schema limits, pagination guardrails, net worth rounding, and API host/port constants to favor statics.
- Documented DAO-backed layering, refreshed architecture/frontend docs and diagrams, and reskinned navigation into Transactions, Accounts, and Budgets pages with consistent headers.
- Refined budgeting UX: dollars-only display, month-to-date budgeted hero card, budget-month summary chip, inflow/outflow toggle, inline editable ledger rows with status badges, and separate categorized transfer page.
- Rebuilt Accounts view into an Assets & Liabilities workspace with grouped cards, navigation filters, stats, and guided add-account modal; repositioned dashboard stats into a compact card row.
- Transaction editing now reverses prior ledger effects before reapplying changes to keep envelopes and Ready to Assign accurate; system envelopes (opening balance, available-to-budget, transfer, balance-adjustment) are first-class and hidden from budgets.
- Removed hard-coded house accounts/categories from migrations; seeds documented as optional.

### Fixed
- Account administration backfills per-class detail tables; categorized transfers now reduce liabilities correctly; ledger refreshes immediately after opening balance posts.
- Transaction edits use `BudgetingDAO.transaction()` for rollback safety; TestingDAO mediates fixture SQL; DuckDB results wrapped in typed helpers to replace magic-number accessors.
- Corrected dashboard hero layout and navigation positioning.
- Fixed Ready-to-Assign races, complex allocation updates (including overspent reductions), and monthly state refresh on allocation edits; migration runner uses named parameters.
- Ready-to-Assign and ledger stability validated via expanded e2e specs; targeted lint/test runner fixes keep py-sql checks and run-tests filters accurate.

### Breaking
- None.

