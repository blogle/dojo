# ARCHITECTURE.md — Dojo System Architecture

> This is a **living document**. It must reflect the codebase as it exists today.
>
> **Audience:** maintainers and contributors who need to understand system structure, runtime flows, data boundaries, and non‑negotiable constraints.
>
> **Scope:** high-level architecture + invariants. Deeper notes live under `docs/architecture/`. Data model details live under `docs/data-model/`.

---

## 0. Status & Change Discipline

- **Last updated:** 2026-01-10
- **Updated by:** codex
- **Why it changed:**
  - Establish a root-level architecture map + Constitution aligned to the current FastAPI/DuckDB/Vite implementation.

**When to update this doc**
- Any change that affects **boundaries**, **public interfaces**, **shared infrastructure**, **persistence patterns**, **observability**, or **performance‑critical paths**.
- Any change that alters **core invariants** (ledger correctness, temporal semantics, money/returns rules).

---

## 1. System Overview

### 1.1 Purpose

Dojo is a self-hosted personal finance application for a household. It replaces spreadsheet-based budgeting with a ledger-first system that supports envelope budgeting, account reconciliation, net worth tracking, and investment tracking. The system prioritizes auditability (time-travel semantics for edits) and operational simplicity (a single backend process + a single DuckDB file).

### 1.2 Non-goals

- Multi-tenant SaaS hosting, billing, or org-level permissions.
- Automated bank ingestion / Plaid-style integrations (not part of the current runtime).
- Double-entry accounting with a general ledger chart-of-accounts.
- Distributed infrastructure (queues, multi-node DB, event bus) as a baseline requirement.

### 1.3 Users & Primary Workflows

- Capture and edit transactions (append-only SCD2 semantics).
- Allocate funds across envelope categories (“Ready to Assign” → categories; category → category).
- Manage accounts and categories (including credit-card payment reserve categories).
- Reconcile an account against a statement by committing a checkpoint.
- View current net worth snapshot (assets, liabilities, investments, tangibles).
- Track investment accounts (positions + uninvested cash) and optionally fetch market prices.

### 1.4 Runtime Topology (at a glance)

- **Browser SPA** (Vue/Vite build) served by the backend.
- **FastAPI monolith** created by `dojo.core.app:create_app`.
- **DuckDB** single-file store (default `data/ledger.duckdb`, configurable).
- **Optional in-process background tasks** for market data sync.

```mermaid
flowchart LR
  subgraph Browser
    SPA[SPA (Vue/Vite)]
  end

  subgraph Backend
    API[FastAPI app]
    Services[Domain services]
    DAO[DAO + SQL resources]
  end

  subgraph Storage
    DB[(DuckDB file)]
  end

  SPA -->|HTTP JSON| API
  API --> Services
  Services --> DAO
  DAO --> DB
```

---

## 2. Architecture Principles

### 2.1 Design Principles

- **Truth in data:** ledger correctness and auditability beat convenience.
- **Simple by design:** prefer a monolith and explicit interfaces over distributed complexity.
- **Derive, then cache:** derived tables exist for performance, but must be rebuildable from authoritative sources.
- **Explicit boundaries:** keep domain logic local; avoid hidden coupling (“teleportation”).

### 2.2 Layering & Dependency Rules

The dominant layering in request paths is:

`FastAPI router → domain service → DAO → SQL file → DuckDB`

Conventions enforced by review:

- Routers (`src/dojo/**/routers.py`) own HTTP concerns (status codes, query params, request/response schemas).
- Services (`src/dojo/**/services.py`, `src/dojo/**/service.py`) own validation and orchestration.
- DAOs (`src/dojo/**/dao.py`) own SQL execution and row mapping.
- SQL lives under `src/dojo/sql/**` and is loaded via `importlib.resources` helpers.

### 2.3 Change Safety

- **Migrations are required** for schema changes and are applied via `python -m dojo.core.migrate`.
- The migration runner validates **strict sequential numbering** (`0001_...`, `0002_...`, …) and records applied files in `schema_migrations`.
- After migrations, derived caches are rebuilt automatically (unless `DOJO_SKIP_CACHE_REBUILD=1`).
- Test-only HTTP endpoints exist but are gated behind `Settings.testing` and return 404 when disabled.

---

## 3. Constitution (Succinct Technical Requirements)

### 3.1 Global (Theory & Tradeoffs)

- G1 — Dojo SHOULD remain operable as a single-process monolith with a single DuckDB store.
- G2 — Auditability is a first-class requirement: business-row edits MUST preserve history.
- G3 — External integrations (e.g., market data fetch) MUST be best-effort and MUST NOT compromise ledger integrity.

### 3.2 System-wide (Repo Invariants)

- S1 — Persisted monetary values MUST be stored as integer **minor units** (`*_minor` BIGINT). Floats MUST NOT be used for money.
- S2 — Multi-table write paths MUST be executed inside a single DB transaction (BEGIN/COMMIT) and MUST rollback on error.
- S3 — DuckDB connections MUST be short-lived and request-scoped (no long-lived globals). Connection acquisition is serialized (`dojo.core.db`).
- S4 — Current-state reads SHOULD filter `is_active = TRUE`; historical queries SHOULD use `recorded_at` / `valid_from` / `valid_to`.

### 3.3 Domain / Subsystem (Local Invariants)

- D1 — Transactions use `concept_id` to link versions; there MUST be at most one active version per concept (`transactions.is_active`).
- D2 — `budget_category_monthly_state` is a derived cache; write paths that affect envelopes MUST update it in the same transaction, and drift MUST be repairable via `scripts/rebuild-caches`.
- D3 — Reconciliation checkpoints (`account_reconciliations`) are append-only; worksheet queries use the latest checkpoint as the cutoff.

### 3.4 Module Conventions (Enforcement-by-review)

- M1 — Public HTTP surface is `/api/**`. On-wire contracts are Pydantic models under `src/dojo/**/schemas.py`.
- M2 — Test utilities MUST live under `src/dojo/testing/` and be guarded by `Settings.testing`.

---

## 4. System Context

### 4.1 External Dependencies

- **Yahoo Finance** via `yfinance` for daily OHLC market data (`src/dojo/investments/market_client.py`).
  - Requires outbound network access.
  - Treated as best-effort input (missing prices are tolerated).

### 4.2 Trust Boundaries & Security

- There is currently **no authentication/authorization layer** in the API.
- Treat the Browser ⇄ API boundary as untrusted input; deploy behind a trusted network, reverse proxy, or VPN.
- Test-only endpoints are blocked unless `dojo_testing=true` (see `src/dojo/core/app.py`).

---

## 5. Component Model

### 5.1 Component Inventory (Cities)

- **`core`** (`src/dojo/core/`)
  - App factory (`app.py`), config (`config.py`), DB connection dependency (`db.py`), migrations (`migrate.py`), seeds (`seed.py`), cache rebuild (`cache_rebuild.py`), net worth (`net_worth.py`), reconciliation (`reconciliation.py`).
- **`budgeting`** (`src/dojo/budgeting/`)
  - Accounts, categories, transactions, allocations; SCD2 write logic and envelope invariants.
- **`investments`** (`src/dojo/investments/`)
  - Portfolio state, reconcile flows, securities/market prices, and market sync job.
- **`frontend`** (`src/dojo/frontend/`)
  - Vue/Vite SPA source under `vite/`; packaged static assets under `static/`. Backend serves `static/dist` when built.
- **`sql`** (`src/dojo/sql/`)
  - Migrations (`migrations/`), dev seeds (`seeds/`), and query fragments grouped by domain.
- **`testing`** (`src/dojo/testing/`)
  - Test-only routes/services to reset and seed the DB for deterministic test runs.
- **`forecasting` / `optimization` / `backtesting`** (`src/dojo/{forecasting,optimization,backtesting}/`)
  - Present as packages, but not currently exposed via the FastAPI router set.

### 5.2 Interfaces & Contracts (Highways)

- **Backend entry point:** `uvicorn dojo.core.app:create_app --factory --reload`
- **HTTP API namespace:** mounted under `/api` (routers included in `src/dojo/core/app.py`).
- **Health checks:** `GET /healthz` and `GET /api/health`.
- **Operator scripts:** `scripts/run-tests`, `scripts/rebuild-caches`, `scripts/run-migrations-check`.

### 5.3 Shared Infrastructure (Rivers/Lakes)

- **DuckDB file**: default `data/ledger.duckdb` (`dojo_db_path` / `DOJO_DB_PATH`).
- **Connection discipline**: request-scoped connections and serialized acquisition (`src/dojo/core/db.py`).
- **Derived caches**: rebuilt from ledger (`src/dojo/core/cache_rebuild.py`).

---

## 6. Runtime Flows

### 6.1 Transaction Create / Update (Ledger Write)

- SPA sends `POST /api/transactions` (create) or `PUT /api/transactions/{concept_id}` (correction).
- Router (`src/dojo/budgeting/routers.py`) acquires a request-scoped DuckDB connection via `connection_dep`.
- Service (`src/dojo/budgeting/services.py:TransactionEntryService`) runs a DAO transaction:
  - Retires the prior active version when updating (`close_active_transaction`).
  - Inserts a new `transactions` row (new `transaction_version_id`, same `concept_id`).
  - Updates `accounts.current_balance_minor` and (when applicable) budget monthly caches.

### 6.2 Budget Allocation (Envelope Move)

- SPA sends `POST /api/budget/allocations` (or `PUT/DELETE` by `concept_id`).
- Service records allocations in `budget_allocations` (SCD2) and adjusts `budget_category_monthly_state` atomically.

### 6.3 Market Update Job (Best-effort)

- `POST /api/jobs/market-update` schedules an in-process background task.
- Task opens its own DuckDB connection and upserts rows into `market_prices`.
- Failures surface in logs; ledger correctness does not depend on market prices.

### 6.4 Failure Modes & Recovery

- **Derived cache drift**: run `scripts/rebuild-caches` (replays ledger + allocations into cache tables).
- **Schema drift**: run `scripts/run-migrations-check` or `python -m dojo.core.migrate`.
- **Concurrent access issues**: avoid multiple processes pointing at the same DuckDB file; the code serializes connection acquisition but does not support multi-process writers.

---

## 7. Data Architecture

### 7.1 Data Model Overview

- Data model documentation: `docs/data-model/overview.md`
- Source-of-truth schema: migration files under `src/dojo/sql/migrations/`.

### 7.2 Ledger & Money Representation

- Monetary values are stored as integer minor units (BIGINT columns with `*_minor` naming).
- Decimal values exist for presentation (e.g., net worth response) but are derived from minor units (`src/dojo/core/net_worth.py`).

### 7.3 Temporal Modeling (Time Travel / SCD2)

- SCD2 tables use `concept_id`, `recorded_at`, `valid_from`, `valid_to`, `is_active`.
- Current-state queries filter `is_active = TRUE`.
- Correction flows retire old rows (set `is_active = FALSE`, advance `valid_to`) and insert new rows.

### 7.4 Migrations, Seeds, Fixtures

- **Migrations**: `src/dojo/sql/migrations/*.sql`, applied by `python -m dojo.core.migrate`.
  - Automatic cache rebuild unless `DOJO_SKIP_CACHE_REBUILD=1`.
- **Dev/demo seeds**: `src/dojo/sql/seeds/*.sql`, applied by `python -m dojo.core.seed`.
- **Test fixtures**: `tests/fixtures/*.sql`, applied via `POST /api/testing/seed_db` when `dojo_testing=true`.

---

## 10. Frontend Architecture

### 10.1 SPA Structure

- Vue/Vite source: `src/dojo/frontend/vite/src/`.
- Static packaged assets: `src/dojo/frontend/static/`.
- Serving behavior: the backend mounts `/static` to `static/`, and mounts `/` to `static/dist` when present (fallback to `static/`).

### 10.2 UI/UX Constraints

- See: `docs/rules/style_guide.md`
- See: `docs/rules/frontend.md`

---

## 11. Testing Strategy

### 11.1 Pyramid

- **Unit tests**: `tests/unit/**`
- **Property tests**: `tests/property/**`
- **Integration tests**: `tests/integration/**`
- **E2E (Cypress)**: `cypress/e2e/**`

### 11.2 Determinism & Reproducibility

- E2E tests reset and seed the DB between scenarios using testing routes (`src/dojo/testing/routers.py`).
- Prefer running the full suite via `scripts/run-tests` to keep orchestration consistent.

---

## 13. “Map” Snapshot (Concise Structural Summary)

This section is intentionally compact. It should answer: “What are the main subsystems, what do they own, and how do they connect?”

### 13.1 Subsystems & Ownership

- **Budgeting city** owns envelope rules, transactions, allocations, and category monthly cache.
- **Investments city** owns securities, market prices, SCD2 positions, and portfolio state views.
- **Core city** owns the app lifecycle (settings, DB access, migrations, cache rebuild) plus net worth + reconciliation read models.
- **Frontend city** owns SPA rendering and API consumption.

### 13.2 Key Dependencies

- Frontend → `/api/**` JSON contracts.
- Budgeting/Investments/Core → DuckDB via request-scoped connection dependency.
- Investments → Yahoo Finance (yfinance) for market prices.

### 13.3 Public Entry Points

- API factory: `dojo.core.app:create_app`
- Migration CLI: `python -m dojo.core.migrate`
- Seed CLI: `python -m dojo.core.seed`
- Test runner: `scripts/run-tests`

### 13.4 Change Impact Guide

- If you change **schema**: update `src/dojo/sql/migrations/**` and ensure cache rebuild still works.
- If you change **ledger write logic**: update budgeting services/DAOs and add/adjust tests (unit/property + e2e if user-visible).
- If you change **frontend routes/data shapes**: update SPA + corresponding `/api` schema models.

---

## 14. Glossary

- **Minor units**: integer representation of money (e.g., cents).
- **SCD2**: slowly changing dimension type 2; append-only history with `is_active` and validity windows.
- **Concept ID**: stable UUID that groups versions of the same logical transaction or position.
- **Ready to Assign (RTA)**: unallocated funds available to distribute across budget categories for a given month.

---

## 15. References

- `AGENTS.md`
- `README.md`
- `docs/architecture/`
- `docs/data-model/`
- `docs/rules/`
