# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Auditable ledger MVP: FastAPI monolith with DuckDB migrations, temporal transaction service, net worth API, and SPA wired to `/api/transactions` & `/api/net-worth/current`.
- Unit + property tests covering transaction invariants and net worth aggregation.
- Cypress-based e2e suite (config + docs) that drives the SPA transaction flow via `direnv exec . npx cypress run --e2e --browser <browser> [--headed]`.

### Changed

### Deprecated

### Removed

### Fixed

### Security
