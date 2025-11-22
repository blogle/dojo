# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Auditable ledger MVP: FastAPI monolith with DuckDB migrations, temporal transaction service, net worth API, and SPA wired to `/api/transactions` & `/api/net-worth/current`.
- Unit + property tests covering transaction invariants and net worth aggregation.
- Cypress-based e2e suite (config + docs) that drives the SPA transaction flow via `npx cypress run --e2e --browser <browser> [--headed]` from an activated dev shell.
- Account and budget management APIs plus SPA pages to create, edit, and deactivate accounts and categories with new Cypress coverage.
- Account classes/roles, SCD detail tables, and special categories plus a categorized-transfer API, Ready to Assign query/route, and tangibles valuation table that feed the net worth snapshot (ledger + positions + tangibles) along with unit tests for transfers, RTA, and net worth.
- SPA updates that drive the Assets & Liabilities page from the backend, show net worth and Ready to Assign stats, group cards by account class with role icons, surface an account detail modal, and convert the Add Account modal into a real POST flow with sensible defaults.
- Envelope-budgeting MVP: transactions form with mode/unit toggles, budgets section with allocation form + category modal, categorized transfer UX with toast feedback, backend category-state joins (with `month` query), README guidance, and new Cypress scenarios for the three flows.
- Transaction status tracking: DuckDB now stores pending/cleared states, the `/api/transactions` payloads include `status`, and the SPA ledger renders the true reconciliation state instead of inferring from dates.
- Dedicated allocations ledger: DuckDB now persists `budget_allocations` rows with from/to metadata, `/api/budget/allocations` exposes guard rails plus a month summary endpoint, and the SPA ships a standalone `#/allocations` page with summary chips, ledger table, and Cypress coverage.
- Dev/demo data loader: `python -m dojo.core.seed` executes `sql/seeds/*.sql`, and tests now rely on purpose-built fixtures under `tests/fixtures/`.
- Payday assignment Cypress spec with dedicated SQL fixture plus per-spec database reset to validate user-story-driven budgeting flows.
- Funded credit card spending flow now mirrors budgeted purchases into the matching payment envelope, adds a tailored SQL fixture, and ships a Cypress spec that verifies category balances, Ready-to-Assign integrity, and credit liability updates end to end.
- Credit accounts now auto-provision payment envelopes (grouped under "Credit Card Payments") and a migration backfills both the group and per-account envelopes so budgets consistently show the dedicated section at the top.
- Rolling with the Punches Cypress spec + SQL fixture validate Dining Out overspending, Groceries-to-Dining reallocations via the allocations ledger, Ready-to-Assign stability, and the cash impact on House Checking.

### Changed
- Reskinned frontend navigation into distinct Transactions, Accounts, and Budgets pages with header stats and consistent top bar layout.
- Repositioned the dashboard stats into a single no-wrap card row, right-justified the navigation links, and removed the redundant pre-content copy so the ledger cards sit immediately below the hero metrics.
- Rebuilt the Accounts view into an Assets & Liabilities workspace with grouped cards, navigation filters, stats, and a guided add-account modal for new holdings.
- Updated architecture domain docs for Assets & Liabilities, Budgeting & Transactions, Net Worth, and Overview to formalize cash-only Ready to Assign, off-budget Accessible Assets, ledger-driven loan balances, and the unified net worth formula (ledger + positions + tangibles).
- Simplified the SPA currency UX to dollars-only, exposed a month-to-date budgeted hero card backed by allocation totals, and added a budget-month summary chip so the ledger and Ready-to-Assign math stay reconciled at a glance.
- Rebuilt the Transactions UI with an inflow/outflow toggle, inline editable rows (no modal hops), and moved categorized transfers into their own page so single-leg ledger work stays focused.
- Transactions ledger rows now enter inline edit mode on click with separate inflow/outflow columns and the compact StatusToggle badge, removing the redundant actions column and the old “quick edit” buttons.
- Removed the hard-coded house accounts/categories from `0001_core.sql`; README now documents optional seed scripts so migrations stay production-safe by default.
- Promoted opening balance, available-to-budget, transfer, and balance-adjustment categories to first-class system envelopes so ledger posts stay valid, hidden from the budgets UI, and excluded from activity math while still contributing to Ready to Assign.

### Deprecated

### Removed

### Fixed
- Corrected the dashboard hero layout so the date, month-to-date spend, and net worth stay in a single card row and the page links pin to the top-right without stray pre-content text.

### Security
