# ExecPlan: Investment Tracking (Positions + Market Valuation, Dual-State Cash Model)

This ExecPlan is a living document and must be maintained in strict accordance with `.agent/PLANS.md`. Every section below is mandatory and must remain self-contained so that a novice engineer can implement the feature using only this file plus the working tree.

## Purpose / Big Picture

After this work, a user can treat “investment accounts” (brokerage, retirement, crypto) as first-class accounts: they can record transfers in/out via the normal ledger, then reconcile the brokerage’s real-world state (uninvested cash + holdings) and see an automatically valued portfolio (NAV), total return, and per-position gains. Market prices are fetched automatically from Yahoo Finance (via `yfinance`) and stored as a time series so the account has both a current snapshot and a historical chart. Net worth uses live valuations so it reflects reality without manually updating “market value” numbers.

A novice can see it working by:

- Starting the server locally.
- Creating an investment account and transferring money into it (ledger cash / net invested capital).
- Reconciling the portfolio with uninvested cash and one or more positions.
- Triggering a market data update and observing:
  - Current NAV and returns on the investment account page.
  - Net worth reflecting investment valuations (not the investment account’s ledger cash).

This ExecPlan includes, verbatim, the complete Investment Tracking specification in Appendix A so no external file is required to understand requirements.

## Progress

- [x] (2025-12-14) Authored initial ExecPlan.
- [x] (2025-12-17) Revised ExecPlan with schema fixes and optimizations.
- [ ] Run `scripts/run-migrations-check --log-plan` after adding migration 0013 and ensure it is idempotent.
- [ ] Implement database migration for securities, prices, SCD2 positions, and uninvested cash column.
- [ ] Implement backend investment domain models, SQL loaders, DAO helpers, and `MarketClient` wrapper.
- [ ] Implement `InvestmentService` (portfolio state, reconcile workflow, market sync, history).
- [ ] Implement API routes and integrate them into `dojo.core.app:create_app`.
- [ ] Implement the SPA investment account view, chart, sidebar reconciliation controls, holdings table, and styling.
- [ ] Add unit/property/integration tests described in Appendix A and update any obsolete investment tests.
- [ ] Update net worth query and ensure the UI continues to display coherent totals.
- [ ] Add deployment CronJob to trigger market updates and update deployment documentation.
- [ ] Run `scripts/lint` and `scripts/run-tests` (full matrix) and record outputs in Artifacts.
- [ ] Write outcomes/retrospective once feature is demonstrably working.

## Surprises & Discoveries

Record unexpected behaviors, library quirks, DuckDB SQL limitations, yfinance edge cases, or performance findings here during implementation. This section starts empty by design.

## Decision Log

- Decision: Implement investment-domain SQL as packaged files under `src/dojo/sql/investments/` and load via `importlib.resources`, matching existing `dojo.core.sql` / `dojo.budgeting.sql` patterns.
  Rationale: Keeps SQL discoverable, sqlfluff-linted, and consistent with existing architecture; prevents failures from the repo’s “no long inline SQL strings” guard.
  Date/Author: 2025-12-14 / Codex

- Decision: Implement the investment SPA view using the existing Vue + Vite frontend (`src/dojo/frontend/vite/src/…`), while still matching the required UI layout, styling, and behaviors described in Appendix A.
  Rationale: The repository’s active frontend is Vue/Vite (not ad-hoc static JS modules); implementing within the current framework reduces duplication and leverages existing routing, API helpers, and styles.
  Date/Author: 2025-12-14 / Codex

- Decision: Treat the `positions_minor` field in the existing net worth response as the “Investments” component (total NAV across investment accounts) to preserve backwards compatibility of `GET /api/net-worth/current`.
  Rationale: Avoids a breaking API change while implementing the required valuation semantics. Any UI labels or docs that previously implied “positions table sum” must be updated to the new meaning.
  Date/Author: 2025-12-14 / Codex

- Decision: Make the portfolio reconciliation semantics “full state upsert”: the request body represents the complete desired set of positions for the account, and any active positions not present are closed as liquidated.
  Rationale: Matches Appendix A’s reconcile workflow, is simple to reason about, and supports idempotent retries.
  Date/Author: 2025-12-14 / Codex

- Decision: Accept the "Net Worth Dip" behavior. When funds are transferred to an investment account, they effectively disappear from Net Worth (removed from Asset Cash) until the user manually reconciles the Investment Account (added to Uninvested Cash/NAV).
  Rationale: Simplifies logic by avoiding heuristics or auto-creation of investment records. The system reflects the *tracked* reality.
  Date/Author: 2025-12-17 / Codex

- Decision: Drop the existing `positions` table in Migration 0013 and replace it with the new SCD2 schema.
  Rationale: The existing table was a placeholder/MVP artifact. Data loss for current dev/test datasets is acceptable to ensure a clean schema going forward.
  Date/Author: 2025-12-17 / Codex

- Decision: Defer `corporate_actions` table creation.
  Rationale: YAGNI. We are not implementing split/dividend automation yet, and the schema is modular enough to add it later without breaking `securities` or `market_prices`.
  Date/Author: 2025-12-17 / Codex

## Outcomes & Retrospective

Populate this after completing major milestones. At minimum: what shipped, how to validate, what was harder than expected, and what follow-ups remain.

## Context and Orientation

Dojo is a single-process FastAPI application that uses DuckDB as an embedded database stored in a file (the default is controlled by `DOJO_DB_PATH`). The application exposes JSON APIs under the `/api` prefix and serves a Single Page Application (SPA) frontend.

Backend high-level layout:

- `src/dojo/core/app.py` contains the FastAPI app factory `create_app`. This is where routers are registered and application-scoped services are stored on `app.state`.
- `src/dojo/core/db.py` provides `connection_dep`, a FastAPI dependency that yields a short-lived DuckDB connection. A global lock serializes connection acquisition to avoid concurrent-writer issues.
- `src/dojo/sql/migrations/*.sql` are forward-only, idempotent schema migrations applied by `python -m dojo.core.migrate` and by the initContainer in Kubernetes.
- Domain SQL is stored as package data and loaded with `importlib.resources` helpers (examples: `src/dojo/core/sql.py` loads from `dojo.sql.core`; `src/dojo/budgeting/sql.py` loads from `dojo.sql.budgeting`). This repo also has a linter that rejects long SQL-like Python string literals, so investment SQL must be kept in `.sql` files.

Frontend high-level layout:

- The SPA source code lives under `src/dojo/frontend/vite/src/…` and is built with Vite into `src/dojo/frontend/static/dist/`.
- Routing is hash-based (`/#/…`) via `src/dojo/frontend/vite/src/router.js`.
- Global navigation layout is in `src/dojo/frontend/vite/src/App.vue`.
- Shared API utilities are in `src/dojo/frontend/vite/src/services/api.js` and formatting helpers in `src/dojo/frontend/vite/src/services/format.js`.
- Global CSS lives under `src/dojo/frontend/static/styles/…` and is imported by `src/dojo/frontend/vite/src/main.js`.

Testing and scripts:

- Run commands inside the repo’s Nix dev shell (`direnv allow .` or `nix develop`).
- Prefer wrapper scripts:
  - `scripts/run-migrations-check` applies all migrations to a temp DuckDB file.
  - `scripts/run-tests` runs the full test matrix (unit, property, integration, Cypress).
  - `scripts/lint` runs ruff, sqlfluff, biome, actionlint, and the SQL-string guard.

Terminology used throughout this plan (defined in plain language):

- Minor units: integer cents (USD) stored as `*_minor` columns. Derived money values are rounded to the nearest cent only at I/O boundaries.
- SCD2 (Slowly Changing Dimension Type 2): a table pattern that preserves history by never editing business fields in place. Instead, an update closes the current row (sets `is_active=FALSE` and `valid_to=<timestamp>`) and inserts a new row version with `is_active=TRUE`.
- OHLC: Open/High/Low/Close prices for an instrument per day.
- NAV (Net Asset Value): the total account value = uninvested cash + value of all positions.
- Money-Weighted Return (MWR) in this feature: total return defined as `NAV - ledger cash` (this is not an IRR solver).
- Ledger cash (net invested capital): the ledger-derived principal transferred into the account (cost basis for account-level return).

## Scope and Non-Goals

Scope (what this plan delivers):

- Database schema to represent securities, daily market prices, SCD2 positions, and uninvested cash.
- Backend services and APIs to:
  - reconcile (manually update) uninvested cash and current holdings,
  - compute current portfolio state (NAV and returns),
  - compute daily history for charting,
  - ingest market price data automatically via `yfinance`.
- Frontend investment account view with an interactive SVG chart, holdings table, and cash/positions reconciliation controls.
- Net worth integration so investment value is computed dynamically from holdings + prices.

Non-goals (explicitly deferred, but must not block the core feature):

- True Time-Weighted Return (TWR) calculation and benchmarking against indices; Appendix A calls this “future implementation”.
- Automated corporate action adjustments (splits/dividends); ingestion and application logic can come later.
- Fully generalized multi-currency support; Appendix A defaults currency to USD.
- Perfect broker-grade precision for fractional shares; quantity is stored as `DOUBLE` per Appendix A, so the feature must be robust to small floating point error and must round only at I/O boundaries.

## Plan of Work

### Milestone 1: Database schema and net worth valuation primitives

Goal: Create the schema required for investment tracking and adjust net worth to use dynamic investment valuations.

Work:

- Add a new migration file `src/dojo/sql/migrations/0013_investment_tracking.sql`. This file must:
  - **Drop the existing `positions` table** (`DROP TABLE IF EXISTS positions;`) to resolve the schema collision with `0001_core.sql`.
  - Create tables described in Appendix A:
    - `securities`
    - `market_prices`
    - `positions` (New SCD2 schema)
  - Add `uninvested_cash_minor` column to `investment_account_details` (use `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`).

- Update `src/dojo/sql/core/net_worth_current.sql` logic:
  - **Assets**: `SUM(current_balance_minor)` where `account_type = 'asset'` **AND** `account_class != 'investment'`. (This prevents double counting the ledger cash).
  - **Investments** (mapped to `positions_minor` output): `SUM(uninvested_cash_minor)` (from active investment_account_details) + `SUM(market_value_minor)` (from active positions * latest price).
  - Ensure the output columns (`assets_minor`, `liabilities_minor`, `positions_minor`, etc.) map correctly to the `NetWorthRecord` dataclass in `dojo.core.dao`.

- Add investment-domain SQL package scaffolding:
  - Create `src/dojo/sql/investments/__init__.py` (empty marker file).

Proof / acceptance:

- Run `scripts/run-migrations-check --log-plan` from the repo root; it must succeed.
- Existing test suites must still import and run (do not fix unrelated failures).
- Verify via a temporary test script that creating an account with `account_class='investment'` excludes it from the `assets_minor` sum in `net_worth_current`.

### Milestone 2: Backend domain models, SQL loaders, and market client

Goal: Create the backend building blocks (models + market fetching) without yet wiring the full feature.

Work:

- Create `src/dojo/investments/domain.py` containing Pydantic models listed in Appendix A. Extend them as needed to be usable by API endpoints. At minimum:

  - Request models:
    - `CreatePositionRequest`: `{ ticker, quantity, avg_cost_minor }`.
    - `ReconcilePortfolioRequest`: `{ uninvested_cash_minor, positions: list[CreatePositionRequest] }`.

  - Response/view models:
    - `Security`
    - `Position` (SCD2 row representation)
    - `PositionView` (enriched: includes current price, market value, gain)
    - `PortfolioState` (cash, holdings_value, nav, total_return, and any additional fields needed by the UI)
    - `PortfolioHistoryPoint` (date, nav, cash_flow, return) as described in Appendix A.

  Define all money fields as integer minor units and document that `quantity` is a float.

- Create `src/dojo/investments/market_client.py` implementing `MarketClient` per Appendix A. The key is to isolate all yfinance + pandas handling here so the rest of the system works with plain Python types:

  - `fetch_prices(tickers: list[str], start_date: date) -> dict[str, pandas.DataFrame]`
    - Use `ThreadPoolExecutor` because yfinance is blocking.
    - Normalize DataFrames so each returned DataFrame has a daily index and the expected columns (`Open`, `High`, `Low`, `Close`, `Adj Close`, `Volume`).
    - Do not leak network calls into tests; unit tests must mock yfinance.

  - `fetch_metadata(ticker: str) -> dict`
    - Extract at least a name and type classification if available; default sensibly when yfinance has gaps.

- Create `src/dojo/investments/sql.py` as a loader for investment SQL files, mirroring `src/dojo/core/sql.py`:

  - `load_sql(name: str) -> str` loads from `dojo.sql.investments`.

Proof / acceptance:

- Add unit tests for MarketClient in `tests/unit/investments/test_market_client.py`. Use mocking to:
  - ensure `fetch_prices` returns normalized frames for multiple tickers,
  - ensure price conversion is robust to NaN / missing fields,
  - ensure the function handles empty ticker lists gracefully (return empty dict).

- Run `scripts/run-tests --filter unit:investments` (or `pytest tests/unit -k investments` if you must), expect pass.

### Milestone 3: Investment service (current snapshot + reconciliation + market sync)

Goal: Implement the business logic so the API can serve current portfolio state and accept reconciliation writes.

Work:

- Create `src/dojo/investments/dao.py` to centralize DuckDB reads/writes. Keep it small and explicit. This DAO should:
  - validate account existence and that `accounts.account_class == 'investment'` when performing investment-domain operations,
  - read current ledger cash (`accounts.current_balance_minor`) for an account,
  - read current uninvested cash for an account from `investment_account_details` (the active SCD2 row),
  - read active positions for an account and join them to security metadata and latest market prices,
  - implement SCD2 update helpers for:
    - investment_account_details (uninvested cash),
    - positions.

  Use a transaction context manager pattern similar to `dojo.budgeting.dao.BudgetingDAO.transaction()` (BEGIN/COMMIT), so higher-level services can guarantee atomicity.

- Create `src/dojo/investments/service.py` implementing `InvestmentService` as described in Appendix A:

  - `get_portfolio_state(account_id)`:
    - Inputs:
      - ledger cash = `accounts.current_balance_minor`
      - uninvested cash = latest `investment_account_details.uninvested_cash_minor`
      - active positions with latest close price
    - Outputs:
      - NAV in minor units,
      - total return $ and % as defined in Appendix A,
      - enriched `PositionView` rows including market value and per-position gain.

    Rounding rule for derived values:

    - Market price columns and all stored money are integers (minor units).
    - When computing `quantity * price_minor`, convert to Decimal using `Decimal(str(quantity))` to avoid the worst float artifacts, then round to the nearest integer cent with “half up”. Document this rule; keep it consistent across the backend and frontend.

  - `reconcile_portfolio(account_id, uninvested_cash_minor, positions)`:
    - Must run as a single database transaction.
    - Update uninvested cash using SCD2 semantics (close active row, insert new row version).
    - Positions are reconciled by ticker symbol:
      - Normalize tickers to uppercase.
      - Ensure a `securities` row exists for the ticker (create if missing).
      - Compute a stable `concept_id` for the (account_id, security_id) pair. A deterministic UUID5 based on a fixed namespace plus `f"{account_id}:{security_id}"` is recommended so idempotent reconciliations don’t create accidental duplicates.
      - If a position exists and quantity/avg_cost differ, close the old row and insert a new row.
      - If no position exists, insert a new row.
      - If an active DB position is absent from the request, close it (implicit liquidation).

  - `sync_market_data()`:
    - Select all distinct tickers from active positions.
    - For each ticker, determine the earliest date to fetch (e.g., max market_date or conservative default).
    - Use MarketClient to fetch OHLC data.
    - Upsert into `market_prices` by `(security_id, market_date)` using `ON CONFLICT DO UPDATE`.
    - Always set `recorded_at` to the ingestion time.

Proof / acceptance:

- Add unit tests in `tests/unit/investments/test_investment_service.py` that run against an in-memory DuckDB with migrations applied.

  - Test SCD2 position update: reconcile position AAPL with quantity=10, then reconcile with quantity=12 and verify:
    - old row is inactive and has a finite `valid_to`,
    - new row is active and shares the same `concept_id`.

  - Test implicit liquidation: reconcile with positions [AAPL], then reconcile with [] and verify the position is closed.

  - Test NAV calculation: seed uninvested_cash_minor, seed a price, seed a position, and assert NAV and Return match Appendix A formulas.

- Add property tests in `tests/property/investments/test_fin_math.py`:

  - `NAV = cash + sum(quantity * price)`
  - `return = nav - ledger_cash`

  These should generate random but bounded inputs and assert identities exactly in minor units after rounding.

- Update or remove obsolete tests that reference the old `positions` schema, notably `tests/property/investments/test_investments_properties.py`.

- Run `scripts/run-tests --filter unit:investments` and `scripts/run-tests --filter property:investments`, expect pass.

### Milestone 4: Portfolio history (daily chart data)

Goal: Provide the data needed for the interactive chart: daily NAV and return series over arbitrary date ranges.

Work:

- Implement `src/dojo/sql/investments/portfolio_history.sql`. The query must accept parameters:

  - `account_id`
  - `start_date`
  - `end_date`

  The query must output one row per day in `[start_date, end_date]` inclusive.

  **Implementation Detail (ASOF JOIN Optimization):**

  - Generate a date series:
    - Use DuckDB’s `generate_series` to create `daily.market_date` rows.

  - Ledger cash series:
    - Compute “ledger cash as of day” as the cumulative sum of all active ledger transactions for the account up to that date.

  - Uninvested cash series:
    - Join `investment_account_details` SCD2 rows by “as-of timestamp” at end-of-day.

  - Positions series:
    - Join SCD2 positions “as-of” the end of each day.
    - **Crucial Optimization:** Use `ASOF LEFT JOIN` to attach the most recent market price for each position on each day.
      ```sql
      FROM positions_daily p
      ASOF LEFT JOIN market_prices mp
        ON p.security_id = mp.security_id
        AND mp.market_date <= daily.market_date
      ```
    - Handle missing prices by treating value as 0 or null (explicit choice).

  - Compute per-day aggregates:
    - `holdings_value_minor = SUM(quantity * close_minor)` rounded to integer.
    - `nav_minor = uninvested_cash_minor + holdings_value_minor`.
    - `return_minor = nav_minor - ledger_cash_minor`.
    - `cash_flow_minor`: day-over-day delta of ledger_cash_minor (or 0 on first day).

- Implement `InvestmentService.get_portfolio_history(account_id, start_date, end_date)` to execute this SQL and map rows into `PortfolioHistoryPoint` models.

Proof / acceptance:

- Add an integration-style test (still runnable in unit suite) that:
  - Creates an investment account.
  - Posts ledger transactions to create a $1000 ledger cash basis.
  - Reconciles uninvested cash and one position.
  - Seeds two days of market prices (e.g., $100 and $110).
  - Fetches history and asserts:
    - rows exist for each day,
    - nav and return values are correct per day.

### Milestone 5: API routers and job trigger endpoint

Goal: Expose the investment functionality over HTTP and integrate it into the FastAPI app.

Work:

- Create `src/dojo/investments/routers.py` with the endpoints described in Appendix A. Use FastAPI’s dependency injection to access the DuckDB connection and the InvestmentService instance stored on `app.state`.

  Required endpoints (exact paths and semantics):

  - `GET /api/investments/accounts/{account_id}` → `PortfolioState`
  - `GET /api/investments/accounts/{account_id}/history?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` → `list[PortfolioHistoryPoint]`
  - `POST /api/investments/accounts/{account_id}/reconcile` → reconciliation result (either PortfolioState or a dedicated response; keep it consistent)
  - `POST /api/jobs/market-update` → returns HTTP 202 and triggers background market sync

- Update `src/dojo/core/app.py`:
  - instantiate and attach `InvestmentService` on app creation (e.g., `app.state.investment_service = InvestmentService()`),
  - include the investments router with `/api` prefix, alongside existing routers.

Proof / acceptance:

- Run the server and exercise endpoints with curl:
  - `GET /api/investments/accounts/<id>` returns 200 once account exists.
  - `POST /api/jobs/market-update` returns 202.

- Add integration tests under `tests/integration/investments/` (or a single file `tests/integration/test_investments_api.py`) that follow Appendix A’s end-to-end flow.

### Milestone 6: Frontend investment account page (interactive chart + reconciliation UI)

Goal: Deliver a working investment account page in the SPA that meets the design and interaction requirements from Appendix A.

Work (mapping Appendix A to this repository’s Vue/Vite structure):

- Add a new route to `src/dojo/frontend/vite/src/router.js`:

  - Path: `/investments/:accountId`
  - Component: `src/dojo/frontend/vite/src/pages/InvestmentAccountPage.vue`

- Add investment API helpers to `src/dojo/frontend/vite/src/services/api.js` under a new `api.investments` namespace:

  - `getAccount(accountId)`
  - `getHistory(accountId, startDate, endDate)`
  - `reconcile(accountId, payload)`
  - `triggerMarketUpdate()` (calls `/api/jobs/market-update` and then invalidates relevant queries)

- Implement UI components:

  - `InvestmentAccountPage.vue`: orchestrates data fetching, manages view state, and composes subcomponents.
  - `PortfolioChart.vue`: implements the SVG chart, hover tooltip, drag-to-measure overlay, and time interval controls.
  - `HoldingsTable.vue`: renders holdings, the add-position form, and triggers reconcile calls.

- Styling:

  - Create `src/dojo/frontend/static/styles/components/investments.css` implementing the earth-tone palette, typography, and BEM classes described in Appendix A.
  - Import this CSS from `src/dojo/frontend/vite/src/main.js`.

- Navigation:

  - In `src/dojo/frontend/vite/src/pages/AccountsPage.vue`, when the selected account’s `account_class` is `"investment"`, show a “View portfolio” button in the modal detail view that routes to `/investments/<account_id>`.

- Interactions and behaviors to implement:

  - Responsive grid layout.
  - Account header showing account name, NAV, and performance.
  - SVG chart with hover cursor, tooltip, and drag-to-measure.
  - Sidebar with cash input (editable on blur/Enter).
  - Holdings table with toggleable add-position form.

Proof / acceptance:

- Build and serve the frontend.
- Manual UI verification:
  - Create an investment account, reconcile cash and at least one position, trigger market update, and confirm the page shows values and the chart updates when changing time ranges.
- Add at least one Cypress test under `cypress/e2e/user-stories/` that verifies the core investment flow.

### Milestone 7: Deployment augmentation (scheduled market updates)

Goal: Ensure production deployments automatically keep market prices up to date without manual intervention.

Work:

- Add a Kubernetes CronJob manifest in `deploy/k8s/base/` (for example `market-update-cronjob.yaml`) that calls the internal service endpoint:

  - Runs `curl` (or `wget`) against `http://dojo/api/jobs/market-update`.
  - Uses `concurrencyPolicy: Forbid` so runs do not overlap.
  - Uses `restartPolicy: OnFailure`.

- Update `deploy/k8s/base/kustomization.yaml` to include the CronJob manifest.

- Update `docs/deploy.md` to document the CronJob and outbound network requirements.

Proof / acceptance:

- `kubectl apply -k deploy/k8s/base` in a test cluster should create the CronJob cleanly. (this is a human step; document it).
- In production logs, a scheduled run should show market update start/end lines and row counts.

## Concrete Steps

Run everything from the repository root.

1. Enter the development environment:

    direnv allow .
    # or:
    nix develop

2. Apply migrations safely (without touching real data) and inspect the ordered plan:

    scripts/run-migrations-check --log-plan

3. Run the backend locally:

    uv run uvicorn dojo.core.app:create_app --factory --reload --host 127.0.0.1 --port 8000

4. (Optional but recommended) Run the Vite dev server for frontend work:

    npm --prefix src/dojo/frontend/vite install
    npm --prefix src/dojo/frontend/vite run dev

5. Run tests frequently:

    scripts/run-tests --filter unit:investments
    scripts/run-tests --filter property:investments
    scripts/run-tests --filter integration:investments

6. Before finishing, run the full lint and test matrix:

    scripts/lint
    scripts/run-tests

## Validation and Acceptance

Backend acceptance (API):

- After starting the server, `GET /api/investments/accounts/<account_id>` returns HTTP 200 and includes:
  - `nav` (or `nav_minor`) = uninvested cash + sum(quantity * closing price),
  - `total_return` = nav - ledger cash,
  - `return_pct` is null when ledger cash <= 0.

- The reconciliation endpoint:
  - is atomic: either both cash and position updates occur or neither,
  - closes missing positions as liquidated,
  - preserves full history via SCD2 (rows are not updated in place).

- The market update job endpoint:
  - returns HTTP 202 quickly,
  - persists OHLC rows in `market_prices`.

Frontend acceptance (SPA):

- Navigating to `/#/investments/<accountId>` shows:
  - account name (uppercase, monospace),
  - current NAV (large, bold),
  - performance for selected time period (delta $ and %) with correct green/red styling.

- The chart supports hover tooltip and drag-to-measure with temporary color change and correct delta computations.

- The sidebar cash input updates uninvested cash and causes NAV and return numbers to refresh.

- Adding, updating, and removing a position via reconcile updates the holdings table and historical chart (once prices exist).

Net worth acceptance:

- `GET /api/net-worth/current` reflects investment valuations using uninvested cash and market-priced holdings, not the investment account’s ledger cash.

Testing acceptance:

- Unit tests for `MarketClient` and `InvestmentService` pass.
- Property tests assert NAV/Return identities.
- Integration/API test reproduces Appendix A’s full flow.
- Cypress E2E includes at least one investment tracking scenario.

## Idempotence and Recovery

- Migrations must be idempotent (`CREATE TABLE IF NOT EXISTS`, `ALTER TABLE … ADD COLUMN IF NOT EXISTS`) so they can be applied repeatedly.
- Reconciliation is designed to be safe to retry: sending the same full portfolio state twice should not create duplicate active positions; it should result in a no-op.
- Market data ingestion must be safe to retry: upserts by `(security_id, market_date)` guarantee idempotence.

## Appendix A: Embedded Specification (complete, verbatim)

# Specification: Investment Tracking

## 1. Overview

The Investment Tracking feature allows users to track the performance and composition of their investment portfolios. Unlike the transactional ledger, which tracks cash flows, this domain tracks **positions** (holdings) and their market value over time.

The system relies on a **"Dual-State Cash Model"** to reconcile ledger balances with brokerage reality:
1.  **Ledger Cash (Net Invested Capital):** Derived from `accounts.current_balance`. Represents the net principal transferred into the account from the budget. Used as the cost basis for the *account as a whole*.
2.  **Uninvested Cash (Brokerage Cash):** Explicitly tracked via SCD2 in `investment_account_details`. Represents the actual buying power in the account. Used to calculate *Current Market Value*.

**Key Capabilities:**
-   Track detailed holdings (Ticker, Quantity, Cost Basis).
-   SCD2 versioning for Positions and Uninvested Cash (full history).
-   Automatic market data ingestion (OHLC) via `yfinance`.
-   Calculated performance metrics: Market Value, Total Return, Unrealized Gain.
-   Integration with Net Worth (replacing static balance with live valuation).

---

## 2. Domain & Financial Logic

### 2.1 Cash vs. Value Semantics

| Concept | Definition | Source | Usage |
| :--- | :--- | :--- | :--- |
| **Ledger Cash** | Net Transfers In - Net Transfers Out | `accounts.current_balance` (Ledger) | **Cost Basis** for the Account Level Return. |
| **Uninvested Cash** | Actual cash sitting in brokerage. | `investment_account_details.uninvested_cash_minor` (SCD2) | Component of **Current Market Value**. |
| **Positions Value** | Sum of (Quantity * Market Price). | `positions` table * `market_prices` table | Component of **Current Market Value**. |
| **NAV** | Uninvested Cash + Positions Value | Derived | **Current Market Value** of the account. |

### 2.2 Performance Formulas

All math must strictly adhere to `docs/rules/fin_math.md`.

* **Net Asset Value (NAV)**:
    $$ NAV_t = C_{uninvested, t} + \sum (Q_{i,t} \times P_{i,t}) $$
    * $C_{uninvested}$: Uninvested Cash (SCD2)
    * $Q_{i}$: Quantity of asset $i$
    * $P_{i}$: Closing price of asset $i$

* **Total Return (Money-Weighted - MWR)**:
    $$ Return_{\$, MWR} = NAV_t - C_{ledger, t} $$
    * $C_{ledger}$: `accounts.current_balance` (Net transfers from ledger)
    * *Note on Dividends:* Dividends received in the brokerage account increase $C_{uninvested}$ (via the reconciliation workflow) but do *not* affect $C_{ledger}$ unless explicitly transferred out. Thus, they correctly contribute to the Investment Return.

* **Total Return (%)**:
    $$ Return_{\%, MWR} = \frac{Return_{\$, MWR}}{C_{ledger, t}} $$
    * *Edge Case:* If $C_{ledger} \le 0$, return % is undefined/null.

* **Unrealized Gain ($) - Per Position**:
    $$ Gain_i = (Q_i \times P_i) - (Q_i \times CostBasis_i) $$

* **Time-Weighted Return (TWR)**:
    * Future implementation will utilize the granular SCD2 history to compute TWR for accurate performance benchmarking against indices.

---

## 3. Database Schema

### 3.1 Migration: `0013_investment_tracking.sql`

#### `securities`
Registry of tradable assets.
-   `security_id` (UUID, PK)
-   `ticker` (TEXT, Unique, Upper Case)
-   `name` (TEXT)
-   `type` (TEXT) - Enum: 'STOCK', 'ETF', 'MUTUAL_FUND', 'CRYPTO', 'INDEX'
-   `currency` (TEXT) - Default 'USD'
-   `created_at`, `updated_at`

#### `market_prices`
Time-series pricing data.
-   `security_id` (UUID)
-   `market_date` (DATE)
-   `open_minor` (BIGINT)
-   `high_minor` (BIGINT)
-   `low_minor` (BIGINT)
-   `close_minor` (BIGINT)
-   `adj_close_minor` (BIGINT)
-   `volume` (BIGINT)
-   `recorded_at` (TIMESTAMP)
-   **Primary Key:** `(security_id, market_date)`

#### `positions` (SCD2 Refactor)
Drops existing table. Tracks holdings history.
-   `position_id` (UUID, PK)
-   `concept_id` (UUID) - Stable ID for (Account + Security) pair.
-   `account_id` (TEXT, FK)
-   `security_id` (UUID, FK)
-   `quantity` (DOUBLE) - Allow fractional shares.
-   `avg_cost_minor` (BIGINT) - Per-share cost basis.
-   **SCD2 Columns:** `valid_from`, `valid_to`, `is_active`, `recorded_at`.
-   **Indexes:** `(concept_id, is_active)`, `(account_id, is_active)`.

#### `investment_account_details` (Migration Update)
Add column to existing table.
-   `uninvested_cash_minor` (BIGINT) - Defaults to 0.

---

## 4. Backend Architecture (`src/dojo/investments/`)

### 4.1 Domain Models (`domain.py`)
-   `Security`: Pydantic model for security metadata.
-   `Position`: Pydantic model for SCD2 row.
-   `PositionView`: Enriched model (includes `current_price`, `market_value`, `gain`).
-   `PortfolioState`: Aggregate view (`cash`, `holdings_value`, `nav`, `total_return`).
-   `PortfolioHistoryPoint`: Model for chart data (`date`, `nav`, `cash_flow`, `return`).

### 4.2 Market Client (`market_client.py`)
Wrapper for `yfinance` to handle blocking I/O safely.
-   **Dependencies:** `yfinance`, `pandas`.
-   **Pattern:** `ThreadPoolExecutor` for fetching data.
-   **Methods:**
    -   `fetch_prices(tickers: list[str], start_date: date) -> dict[str, DataFrame]`
    -   `fetch_metadata(ticker: str) -> dict`

### 4.3 Service Layer (`service.py`)
**`InvestmentService`**
-   **`get_portfolio_state(account_id)`**:
    -   Fetches `accounts.current_balance` (Ledger Cash).
    -   Fetches `investment_account_details.uninvested_cash` (Uninvested Cash).
    -   Fetches active positions joined with latest `market_prices`.
    -   Computes NAV and Returns (MWR).
-   **`reconcile_portfolio(account_id, uninvested_cash_minor, positions: list[CreatePositionRequest])`**:
    -   **Atomic Transaction**:
        1.  Update Uninvested Cash (SCD2).
        2.  For each submitted position:
            -   Match against active DB positions by Ticker.
            -   If changed: Close old row, Insert new row.
            -   If new: Insert new row.
        3.  For any active DB positions *missing* from the request:
            -   Close them (Implicit delete/liquidation).
-   **`get_portfolio_history(account_id, start_date, end_date)`**:
    -   Executes complex query (`sql/queries/investments/portfolio_history.sql`).
    -   Reconstructs daily state:
        -   Join `accounts` (Ledger Cash) history.
        -   Join `investment_account_details` (Uninvested Cash) history.
        -   Join `positions` (Holdings) history.
        -   Join `market_prices` (Pricing) using **ASOF JOIN**.
    -   Returns time-series of NAV and Returns.
-   **`sync_market_data()`**:
    -   Selects all distinct tickers from active `positions`.
    -   Calls `MarketClient`.
    -   Upserts into `market_prices` (using ON CONFLICT DO UPDATE).

### 4.4 Net Worth Integration (`src/dojo/sql/core/net_worth_current.sql`)
Update the SQL query to calculate Investment components dynamically:
-   **Assets**: `SUM(current_balance)` where `account_class != 'investment'`.
-   **Investments**: `SUM(uninvested_cash) + SUM(positions.qty * market_prices.close)`.

---

## 5. API & Scheduling (`routers.py`)

### 5.1 Endpoints
-   `GET /api/investments/accounts/{account_id}`
    -   Response: `PortfolioState` (Current)
-   `GET /api/investments/accounts/{account_id}/history`
    -   Query Params: `start_date`, `end_date`
    -   Response: `list[PortfolioHistoryPoint]`
-   `POST /api/investments/accounts/{account_id}/reconcile`
    -   Body: `ReconcilePortfolioRequest` (`uninvested_cash_minor`, `positions: list[CreatePositionRequest]`)
    -   Action: Calls `reconcile_portfolio`.
-   `POST /api/jobs/market-update`
    -   Status: `202 Accepted`
    -   Action: Triggers `InvestmentService.sync_market_data` in `BackgroundTasks`.
---

## 6. Frontend Specification

**Style:** Minimalist Earth Tones.
* **Background:** `#fdfcfb` (Off-white).
* **Surface:** `#ffffff` (White) with borders `#e0e0e0`.
* **Typography:** Sans-serif (`Inter`) for UI text; Monospace (`JetBrains Mono`) for financial data and headers.
* **Status Colors:** Success (`#6b8e23` - Green) and Danger (`#9c4843` - Red) used for performance metrics.

### 6.1 UI Components

The UI will be built as a Single Page Application (SPA) view, mounted into the existing layout.

#### `InvestmentAccountPage` (Main View)
-   **Route:** `/investments/:accountId`
-   **Layout:** Responsive Grid (Desktop: Two-column layout, Main content (Chart) takes remaining width (`1fr`); Sidebar takes fixed width (`320px`). Mobile: Single-column stacked layout.)

#### `GlobalNavigation` (Part of overall app layout)
-   **Location:** Top of viewport.
-   **Items:** Logo (DOJO), Transactions, Transfers, Allocations, Assets & Liabilities (Active), Budgets.
-   **Style:** Simple text links; active state uses primary text color.

#### `AccountHeader`
-   **Elements:**
    -   Account Name (Uppercase, muted, monospace font, e.g., "ROBINHOOD INDIVIDUAL").
    -   Current Value (Large, bold typography displaying the total account value (NAV)).
    -   Performance (Displays absolute change (`$`) and percentage change (`%`) for the selected time period, color-coded Green if positive, Red if negative).

#### `InteractiveHeroChart` (SVG)
A responsive SVG-based area chart visualizing account value over time.
-   **Visual Construction:**
    -   **Line Path:** A solid stroke representing the value trend.
    -   **Area Path:** A filled path beneath the line, using a linear gradient (Opacity: 40% top -> 10% mid -> 0% bottom).
    -   **Coloring:** Dynamic based on trend. If `End Value >= Start Value`, the theme is Green; otherwise, Red.
-   **Interactions:**
    -   **Hover:** Displays a vertical cursor line, a data point dot, and a tooltip containing the Date and Value.
    -   **Drag-to-Measure:**
        -   **Action:** Click and drag horizontally.
        -   **Visual:** Renders a semi-transparent overlay rectangle covering the selected time range.
        -   **Tooltip:** Updates to show the specific change (Delta $ and %) between the start and end of the drag selection.
        -   **Dynamic Styling:** The chart color temporarily changes to reflect the performance of *only* the selected range (e.g., a green chart might turn red if measuring a drawdown period).
-   **Time Interval Controls:**
    -   **Options:** 1D, 1W, 1M (Default), 3M, YTD, 1Y, Max.
    -   **Behavior:** Fetches/generates new data points and re-renders the chart. Active tab is highlighted with a solid background.
-   **Technical Behaviors:** The chart is split into two distinct SVG paths (Stroke vs. Fill) to prevent the gradient fill from clipping or overlapping the stroke line visually. Responsiveness via SVG `viewBox` scaling.

#### `SidebarDetails`
-   **Details Card:**
    -   Key-value pairs for: NAV, Cost Basis, Cash, Total Return, and Account Type.
    -   **Total Return** value is color-coded based on performance.
-   **Cash Balance Card:**
    -   Input field displaying the uninvested cash amount.
    -   Right-aligned, monospace, large font weight.
    -   Intended for quick manual adjustments.
    -   `onBlur` / `Enter`: Triggers API update (`POST .../cash`).

#### `HoldingsSection`
-   **Header:** Title ("Holdings") and a "Toggle" button (`+ Add Position` / `Cancel`).
-   **Add Position Form** (Hidden by default, shown by toggle button):
    -   Fields: Ticker, Quantity, Avg Cost, Current Price.
    -   Actions: Cancel, Save Position.
-   **Holdings Table:**
    -   Columns: Ticker, Qty, Price, Avg Cost, Market Value, Total Return.
    -   Rows: Highlight on hover.
    -   Data Formatting: Currency values are formatted; Total Return uses color coding (Green/Red).

### 6.2 Frontend Architecture (`src/dojo/frontend/static/`)

* **`components/investments/InvestmentAccountPage.js`**: Orchestrator. Fetches data, manages view state (loading/error/success).
* **`components/investments/PortfolioChart.js`**: D3-less SVG logic. Handles path generation, gradient definitions, and mouse event listeners (drag-to-measure logic).
* **`components/investments/HoldingsTable.js`**: Renders the table and the "Add Position" form.
* **`styles/components/investments.css`**: Scoped styles using BEM naming (e.g., `.investment-header__value`, `.chart-tooltip`).

---

## 7. Testing Strategy

### 7.1 Unit Tests
-   **`test_market_client.py`**: Mock `yfinance` to verify DataFrame normalization.
-   **`test_investment_service.py`**:
    -   Verify SCD2 logic (updating a position creates new row, closes old).
    -   Verify NAV calculation (math check).

### 7.2 Property Tests (`hypothesis`)
-   **`test_fin_math.py`**:
    -   Assert `NAV = Cash + Sum(Pos * Price)`.
    -   Assert `Return = NAV - LedgerBasis`.

### 7.3 Integration / E2E
-   **Database**: Verify foreign keys and uniqueness constraints.
-   **API**: Test full flow:
    1.  Create Account (Ledger Cash = 0).
    2.  Add Cash (Ledger Cash = 1000).
    3.  Update Uninvested Cash (1000).
    4.  Add Position (AAPL, 10, $100).
    5.  Sync Market Data (Mock Price = $110).
    6.  Check Portfolio State (NAV = $1100, Return = $100).

---

## 8. Implementation Steps

1.  **Database Migration:** Create `0013_investment_tracking.sql`.
2.  **Domain Core:** Implement `domain.py` and `market_client.py`.
3.  **Service Layer:** Implement `InvestmentService` with SCD2 logic.
4.  **API:** Implement `routers.py`.
5.  **Integration:** Update `net_worth_current.sql`.
6.  **Frontend:** Build `InvestmentAccountPage`, `PortfolioChart`, `HoldingsTable`.
7.  **Verify:** Run tests.
