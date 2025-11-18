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

### Changed
- Reskinned frontend navigation into distinct Transactions, Accounts, and Budgets pages with header stats and consistent top bar layout.
- Repositioned the dashboard stats into a single no-wrap card row, right-justified the navigation links, and removed the redundant pre-content copy so the ledger cards sit immediately below the hero metrics.
- Rebuilt the Accounts view into an Assets & Liabilities workspace with grouped cards, navigation filters, stats, and a guided add-account modal for new holdings.

### Deprecated

### Removed

### Fixed
- Corrected the dashboard hero layout so the date, month-to-date spend, and net worth stay in a single card row and the page links pin to the top-right without stray pre-content text.

### Security
