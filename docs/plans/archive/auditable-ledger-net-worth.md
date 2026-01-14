# Auditable Ledger and Net Worth MVP

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be maintained as work proceeds. Maintain this plan in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

This roadmap delivers the first vertical slice of Dojo: a FastAPI monolith with a DuckDB-backed ledger that records transactions under the Atomic Transaction Mandate, keeps every edit via a temporal Transactions table, and immediately pushes balances into Accounts and BudgetCategories. A companion endpoint computes instantaneous net worth by summing the active balances, and a minimal SPA lets a household submit a transaction and see the updated net worth without refreshing. Successful delivery proves the write path, the temporal model, and the main KPI loop end to end, using the domain-oriented layout described in `docs/architecture/overview.md` (`core`, `budgeting`, etc.) so contributors can reason about features by business area rather than technical layers.

## Progress

- [x] (2025-11-10T22:11Z) Captured MVP scope and authored this initial ExecPlan skeleton.
- [x] (2025-11-11T07:15Z) Established backend scaffolding (package layout, FastAPI factory, settings, migration runner) and automated schema bootstrapping with DuckDB.
- [x] (2025-11-11T08:02Z) Implemented DuckDB schema, migration runner, and transaction entry service with temporal invariants plus unit/property coverage.
- [x] (2025-11-11T14:05Z) Exposed the net worth API, shipped the spreadsheet-style SPA, refreshed docs/changelog, and added comprehensive pytest coverage.
- [x] (2025-11-11T17:30Z) Replaced the deferred Playwright plan with a Cypress-based e2e suite runnable via `npx cypress run --e2e --browser <browser> [--headed]`, closing the automation gap.

## Surprises & Discoveries

- Observation: Repository currently ships only documentation and configuration; there is no existing FastAPI or DuckDB code to extend. Evidence: `rg --files` (2025-11-10) lists docs, licenses, and locks only, so this plan must define directory layout, modules, and SQL from scratch.
- Observation: The plan to write a lightweight migration runner is a pragmatic choice for the MVP but carries the risk of future maintenance overhead. This is an acceptable trade-off to accelerate initial delivery. A `TODO.md` entry has been created to evaluate robust, off-the-shelf tools post-MVP.
- Observation (2025-11-11): Installing Playwright browsers inside the sandbox failed because the packaged driver attempted to run dynamically linked executables outside the Nix sandbox. We mitigated this by adopting the Nix-provided Cypress Electron runner, which requires no external downloads and now drives the SPA end-to-end.

## Decision Log

- Decision: Deliver Phase 1 (ledger write path) and Phase 2 (net worth + SPA) inside one FastAPI monolith served from `src/dojo/core/app.py`, with the SPA as static assets instead of a separate frontend repo. Rationale: keeps the MVP auditable and deployable via a single process while honoring the DuckDB single-process guidance and the simple domain layout from `docs/architecture/overview.md`. Date/Author: 2025-11-10 / Codex.
- Decision: The FastAPI application factory (`create_app`) will serve as the designated `build_container` (per `AGENTS.md`). It will instantiate application-scoped services and attach them to `app.state` for access via dependencies, aligning framework patterns with our architectural rules. This pattern has been codified in `docs/rules/python.md`. Date/Author: 2025-11-10 / Codex.
- Decision: Adopt Cypress (packaged via the flake) for browser automation instead of Playwright so e2e tests remain runnable inside the sandbox without custom browser installations. Date/Author: 2025-11-11 / Codex & user.

## Outcomes & Retrospective

To be filled in when the MVP loop is verified (transaction insert updates balances, `/api/net-worth/current` reflects it, SPA displays result, and tests cover the invariants).

## Context and Orientation

`pyproject.toml` defines the package `dojo` but there is no `src/` directory, code, or SQL yet. Dependencies already cover plotting libraries but not the application stack, so we must add FastAPI, Uvicorn, Pydantic, pytest plugins, Hypothesis (property tests), httpx, and pytest-asyncio on the Python side while relying on the flake to supply Node + Cypress for browser automation. `docs/rules/*.md` prescribe severe constraints: amounts must be integers in minor units, SQL must live in `.sql` files, DuckDB connections must be short-lived, and the temporal table cannot be mutated outside the SCD Type 2 pattern. Nix+direnv manage the environment: run commands directly inside an activated dev shell. If you disable `direnv`, start with `nix develop` before running any tooling. There is no `ARCHITECTURE.md` yet, but `docs/architecture/overview.md` already describes the required module layout; we must mirror that structure (`src/dojo/core`, `src/dojo/budgeting`, `src/dojo/investments`, etc.) even if some modules remain stubs. No database file exists; we will create `data/ledger.duckdb` (configurable). Tests must live under `tests/unit` (deterministic unit tests), `tests/property` (Hypothesis-based invariants), and `cypress/e2e` (UI automation). Tests that exercise DuckDB/SQL should use an appropriately scoped in-memory database to avoid polluting the production database or repository directory. All SQL files must live under the Python package tree (e.g., `src/dojo/sql/...`) so they ship with the wheel and can be loaded via `importlib.resources`. The SPA can be plain HTML/JS served by FastAPI's `StaticFiles` without introducing a JS build chain.

## Plan of Work

Describe and execute the work in two phases that mirror the roadmap narrative, each producing observable behavior.

Phase 1 — Foundational architecture and data integrity. Create `src/dojo/` with domain-first subpackages that mirror `docs/architecture/overview.md`: `src/dojo/core` (infra, config, DB connections, net worth aggregation), `src/dojo/budgeting` (transaction entry logic and routers), plus empty `src/dojo/investments`, `src/dojo/forecasting`, `src/dojo/optimization`, and `src/dojo/backtesting` to preserve the documented shape. Add `src/dojo/core/config.py` to centralize settings (currently only `db_path`, defaulting to `data/ledger.duckdb`). Implement `src/dojo/core/db.py` exposing `connection_dependency()` as a FastAPI dependency that opens a DuckDB connection per request and closes it in a `contextmanager`, satisfying the DuckDB Connectivity Principle. Place all SQL files under `src/dojo/sql/` so they ship with the package; under `src/dojo/sql/migrations/`, author `0001_core.sql` containing only the DDL for `schema_migrations`, `accounts`, `budget_categories`, `budget_category_monthly_state`, `positions`, `transactions`, and helper views. Seed data for testing or demos will be managed separately in `tests/fixtures/sql/`. Columns: all identifiers as UUID text; monetary amounts as BIGINT minor units; `transactions` with `transaction_version_id` (PK), `concept_id`, `account_id`, `category_id`, `amount_minor`, `occurred_on`, `memo`, `recorded_at`, `valid_from`, `valid_to`, and `is_active`. Accounts record `account_type` (asset/liability), `current_balance_minor`, and `is_active`. Budget categories include rollover policy and `is_active`. `budget_category_monthly_state` stores `category_id`, `month_start` (DATE), and running totals for allocation, activity, inflow, and available. Positions hold `position_id`, `accounting_class` (asset/liability), `current_value_minor`, and `is_active`. Write a lightweight migration runner in `src/dojo/core/migrate.py` that scans `src/dojo/sql/migrations/*.sql`, runs them inside a transaction via DuckDB, and logs completion into `schema_migrations`. Wire this runner into `src/dojo/core/app.py` to run on startup.

Still in Phase 1, implement the New Transaction Entry service within the budgeting domain. Create `src/dojo/budgeting/schemas.py` with Pydantic models describing `NewTransactionRequest`, `TransactionDTO`, plus invariants (amount must not be zero, accounts/categories must exist and be active, date cannot exceed an allowed drift). Implement `src/dojo/budgeting/sql.py` that loads parametrized SQL from `src/dojo/sql/budgeting/*.sql` via `importlib.resources` so Python never embeds multi-line SQL while ensuring the queries ship with the package. Implement `src/dojo/budgeting/services.py` containing `TransactionEntryService`. Steps per entry: generate a `concept_id` (`uuid4`) unless supplied, derive a `transaction_version_id`, open a SQL transaction (`BEGIN`), insert into `transactions` with `valid_from = recorded_at` and `valid_to = '9999-12-31'`, update the previous active version (if editing) to set `is_active = FALSE` and `valid_to = recorded_at`, update `accounts.current_balance_minor` by adding `amount_minor` (positive increases assets, liabilities invert sign), upsert the `budget_category_monthly_state` row for the transaction month (first day) adjusting `activity_minor` (spending is negative), and recompute `available_minor = allocated_minor + inflow_minor - activity_minor`. Commit only after all statements succeed; otherwise rollback. Enforce the Atomic Transaction Mandate by issuing `BEGIN`/`COMMIT` explicitly via the DuckDB cursor. Keep SQL statements in `src/dojo/sql/budgeting/*.sql`. Create FastAPI endpoints in `src/dojo/budgeting/routers.py` for POST `/api/transactions` that bind to a Pydantic schema, call the service, and return the inserted transaction metadata plus recalculated account/category states for immediate UI updates. Provide a companion GET `/api/reference-data` to feed SPA dropdowns by reading active accounts and categories.

Add focused, behavior-driven unit tests under `tests/unit/budgeting/test_transactions.py`. These tests should validate the service contract, not implementation details. For example, assert that calling `TransactionEntryService.create` with valid data results in the correct change to an account's balance as observed through a public-facing `get_balance` function. Use DuckDB's in-memory database seeded via test fixtures for deterministic runs. Add property-based tests in `tests/property/budgeting/test_transactions_properties.py` using Hypothesis to generate valid sequences of transactions and assert high-level invariants (e.g., the sum of account balances always equals total inflows minus total outflows; only one active version exists per transaction concept).

Phase 2 — Core business logic and visualization. Implement `src/dojo/core/net_worth.py` to load and execute `src/dojo/sql/core/net_worth_current.sql`, which sums `accounts.current_balance_minor` where `is_active = TRUE` and `account_type = 'asset'` minus liabilities, plus joins `positions` (if any). Expose GET `/api/net-worth/current` via `src/dojo/core/routers.py`, returning amounts in both minor units and Decimal strings for UI convenience. Ensure the query filters on `is_active = TRUE`. Add unit tests in `tests/unit/core/test_net_worth.py` that validate the public-facing `current_snapshot` service correctly computes net worth given a set of accounts, liabilities, and positions seeded from test fixtures. Add property-based coverage in `tests/property/core/test_net_worth_properties.py` for random account/position states to assert `assets - liabilities == net_worth`. The SPA must evolve from a single-entry form to a keyboard-first spreadsheet: render a scrollable table showing recent transactions (fetched from a new GET `/api/transactions?limit=...` endpoint) with the first row acting as an editable input line. Submission should be possible entirely via keyboard (tab/enter), and the list should refresh immediately so users can review prior entries without leaving the interface.

Create `src/dojo/frontend/static/index.html` (and a companion `app.js`) served by FastAPI's `StaticFiles` mount at `/`. The SPA needs a form with inputs for date, amount, account, and category. It uses `fetch` to POST JSON to `/api/transactions` and must be implemented to parse FastAPI's standard `RequestValidationError` JSON structure to display validation errors inline next to the correct fields. After a successful POST, it calls `/api/net-worth/current` and updates a dashboard card. Keep the JS simple (no framework), include a helper to convert dollars to cents before sending, and reflect the `is_active` semantics by disabling submission if the reference data fails to load. Provide Cypress end-to-end tests in `cypress/e2e/transaction_flow.cy.js` (driven by `cypress.config.cjs`) that spin up the FastAPI app (pointed at a test DuckDB file), run through the form submission, verify the displayed net worth delta, and confirm error handling when required fields are missing. Integrate the Cypress runner via `npx cypress run --e2e --browser <browser> [--headed]` so both `pytest` and the browser suite run cleanly before merging.

Update docs once behavior exists: amend `README.md` Quick Start (add instructions to run migrations, start the API, execute unit/property/e2e tests, and open the SPA), expand `docs/architecture/overview.md` and `docs/architecture/net_worth.md` with diagrams covering the ledger write path and net worth read path, and update `CHANGELOG.md` `[Unreleased]` summarizing the MVP. Add TODO entries only for deferred discoveries explicitly approved by the user. Ensure `pyproject.toml` and `uv.lock` include FastAPI, Uvicorn, Pydantic, Hypothesis, httpx, pytest-asyncio, and related typing backports, synced via `uv sync`. Browser automation is handled by the Nix-provided Cypress binary, so no Python dependency is necessary; document the `npx cypress run --e2e --browser <browser> [--headed]` workflow instead.

## Concrete Steps

1. Update `docs/rules/python.md` to codify the FastAPI application factory and dependency injection pattern, as agreed.

2. Extend `pyproject.toml` with FastAPI, Uvicorn, Pydantic, Hypothesis, httpx, pytest-asyncio, and related typing helpers, then sync and ensure package data includes SQL files (via `package-data = ["dojo/sql/**/*"]` in `pyproject.toml` or equivalent):

        uv sync

3. Create the domain-first directory scaffolding (`src/dojo/core`, `src/dojo/budgeting`, `src/dojo/frontend`, `src/dojo/investments`, `src/dojo/forecasting`, `src/dojo/optimization`, `src/dojo/backtesting`, `src/dojo/sql/migrations`, `src/dojo/sql/core`, `src/dojo/sql/budgeting`, `tests/unit`, `tests/property`, `tests/e2e`, `tests/fixtures/sql`, `cypress/e2e`, `data/`) and stub `__init__.py` files where applicable.

4. Author `src/dojo/sql/migrations/0001_core.sql` with the DDL schema described above. All seed data will be managed in separate files under `tests/fixtures/sql/`. Implement `src/dojo/core/migrate.py` (loading SQL via `importlib.resources`) and run it via

        uv run python -m dojo.core.migrate

5. Implement `src/dojo/core/config.py`, `src/dojo/core/db.py`, and `src/dojo/core/app.py` (FastAPI factory as `build_container`, dependency wiring, router registration, static files, SPA mount). Verify the app starts with

        uv run uvicorn dojo.core.app:create_app --factory --reload

6. Implement the budgeting SQL helpers, schemas, and transaction service/routers, including the reference-data endpoint. SQL helpers must read from `src/dojo/sql/budgeting`. Add behavior-driven unit tests plus Hypothesis property suites:

        pytest tests/unit/budgeting
        pytest tests/property/budgeting

7. Implement the net worth SQL query/service and router, with SQL in `src/dojo/sql/core`, plus unit/property tests:

        pytest tests/unit/core
        pytest tests/property/core

8. Build the SPA assets (`src/dojo/frontend/static/index.html`, `app.js`, `styles.css` if needed) and confirm the manual flow with curl/browser as described under Validation.

9. Create the Cypress config (`cypress.config.cjs`) and e2e spec (`cypress/e2e/transaction_flow.cy.js`) that boot the FastAPI server, seed `data/e2e-ledger.duckdb`, and exercise the SPA transaction flow:

        npx cypress run --e2e --browser <browser> [--headed]

10. Update docs (`README.md`, `docs/architecture/overview.md`, `docs/architecture/net_worth.md`) and `CHANGELOG.md`, then re-run the full regression suite:

        pytest
        npx cypress run --e2e --browser <browser> [--headed]
        ruff check .

## Validation and Acceptance

Acceptance requires observable behavior:

1. `uv run python -m dojo.core.migrate` creates `data/ledger.duckdb` and reports the applied migration.
2. `pytest` (which includes both deterministic and Hypothesis property suites) passes.
3. `npx cypress run --e2e --browser <browser> [--headed]` passes, running the automated SPA flow.
4. `uv run uvicorn dojo.core.app:create_app --factory --reload` starts FastAPI, serves the SPA at `http://localhost:8000/`, and the browser console shows successful fetches for reference data and net worth.
5. Submitting the SPA form inserts a transaction, immediately updates the displayed net worth, and a subsequent GET `/api/net-worth/current` via `curl` matches the UI.
6. `CHANGELOG.md` under `[Unreleased]` states that the Auditable Ledger and Net Worth MVP landed, and docs describe how to use it.

## Idempotence and Recovery

The migration runner must be idempotent: rerunning it checks `schema_migrations` and skips applied files. All tests must run against isolated, transient databases (e.g., an in-memory DuckDB instance) to prevent corrupting shared state. When the transaction service raises an error (e.g., unknown account), it must roll back the SQL transaction and return a 400 with a clear message; FastAPI dependency cleanup must close the DuckDB connection even on exceptions. The SPA should handle retries by disabling the submit button while awaiting the response and surfacing error text without duplicating inserts. Cypress e2e runs must seed/reset `data/e2e-ledger.duckdb` (via `tests.e2e.prepare_db`) before launching the test server to avoid cross-run contamination.

## Artifacts and Notes

Capture and attach (in this plan or linked docs) the following artifacts as work progresses:

- Migration output snippet showing `0001_core.sql` applied against a fresh database.
- Pytest transcript proving both unit and property suites run and pass.
- Cypress run output (or video) demonstrating the automated E2E flow succeeds.
- Sample `curl` transcript that posts a transaction and immediately reads `/api/net-worth/current`, demonstrating the net worth delta equals the transaction amount for assets.
- Screenshot or logging snippet confirming that each FastAPI request opens and closes its DuckDB connection (enable INFO-level logging in `core/db.py` for verification).

## Interfaces and Dependencies

Define these interfaces to keep the system coherent and aligned with the domain layout:

- `src/dojo/core/config.py`: `class Settings(BaseModel)` with `db_path: Path` (default `Path("data/ledger.duckdb")`), loaded once and injected.
- `src/dojo/core/app.py`: `def create_app(settings: Settings) -> FastAPI`. This factory function serves as the `build_container`, instantiating services and attaching them to `app.state`.
- `src/dojo/core/db.py`: `@contextmanager def get_connection(path: Path) -> Iterator[duckdb.DuckDBPyConnection]` plus FastAPI dependency `def connection_dep(settings: Settings = Depends(get_settings))`. No globals.
- `src/dojo/core/migrate.py`: `def apply_migrations(conn: duckdb.DuckDBPyConnection, migrations_pkg: Traversable) -> None` (using `importlib.resources.files("dojo.sql.migrations")`).
- `src/dojo/budgeting/schemas.py`: Pydantic models `NewTransactionRequest`, `TransactionResponse`, `AccountState`, `CategoryState`.
- `src/dojo/budgeting/services.py`: `class TransactionEntryService` with `def create(self, conn, cmd: NewTransactionRequest) -> TransactionResponse`, using SQL loaded from `sql/budgeting/*.sql`.
- `src/dojo/core/net_worth.py`: `def current_snapshot(conn) -> NetWorthSnapshot`.
- `src/dojo/budgeting/routers.py` and `src/dojo/core/routers.py`: FastAPI routers registered in `core/app.py`.
- `src/dojo/sql/core/net_worth_current.sql`: query that sums assets minus liabilities plus active positions, respecting `is_active`.
- `src/dojo/frontend/static/index.html`, `app.js`, and optional CSS: SPA assets served via `StaticFiles`.
- `tests/unit`, `tests/property`, and `cypress/e2e`: pytest + Hypothesis suites run via `pytest`, and the Cypress browser suite runs via `npx cypress run --e2e --browser <browser> [--headed]`.

All SQL touching temporal data must live in `.sql` files under `src/dojo/sql/` (so they package with the code) to honor docs/rules/sql.md. All API schemas must use Pydantic models with explicit typing. Monetary conversions should use `Decimal` at the edges and convert to integers before hitting DuckDB to comply with `docs/rules/cheatsheet.md`.
