# ExecPlan: Investment Tracking and Net Worth Domain

This ExecPlan consolidates the following completed plans into a single domain-scoped document:
- `auditable-ledger-net-worth.md` (COMPLETED - net worth portion)
- `investment-tracking.md` (COMPLETED)

All major milestone work for these features is complete. This document serves as a historical record and reference for future work in the investment and net worth domain.

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

## Purpose / Big Picture

Provide a complete portfolio tracking system with position management, market data synchronization, performance analytics (returns, risk, Sharpe), and net worth aggregation across all account types. Users can track investment holdings, reconcile positions against broker statements, view historical performance with charts, and monitor their overall financial health through a unified net worth dashboard.

## Progress

- [x] (2025-12-XX) Portfolio state management with positions and cash
- [x] (2025-12-XX) Investment reconciliation workflow (holdings verification)
- [x] (2025-12-XX) Market data integration (Yahoo Finance or similar)
- [x] (2025-12-XX) Portfolio history and time-series data
- [x] (2025-12-XX) Performance metrics (returns, volatility, drawdowns)
- [x] (2025-12-XX) Investment account detail pages with charts
- [x] (2025-12-XX) Net worth computation aggregating all accounts
- [x] (2025-12-XX) Net worth history API with interval queries
- [x] (2025-12-XX) Dashboard landing page with interactive chart

## Surprises & Discoveries

- Observation: Investment reconciliation uses position-based concept IDs tied to account + security.
  Evidence: `_POSITION_CONCEPT_NAMESPACE = UUID("2f7f9ea4-2fd0-4c21-9bb1-7a5eb5e7a0ac")` in `src/dojo/investments/service.py`.
  Resolution: This ensures each account's positions are conceptually isolated while still sharing security metadata.

- Observation: Cash model for investments splits into `uninvested_cash` (ledger cash) and `positions` (securities).
  Evidence: PortfolioState includes both `ledger_cash_minor` and `uninvested_cash_minor`.
  Resolution: Allows users to track brokerage cash separately from marketable holdings.

- Observation: Net worth history needs different intervals (1D, 1W, 1M, 3M, YTD, 1Y, 5Y, Max) for interactive dashboard.
  Evidence: DashboardPage.vue exposes interval buttons `1D, 1W, 1M, 3M, YTD, 1Y, 5Y, Max`.
  Resolution: API supports `interval` parameter; frontend handles all cases with efficient chart rendering.

- Observation: Market data sync is a background job to avoid blocking API requests.
  Evidence: `/api/jobs/market-update` endpoint returns 202 Accepted and runs asynchronously.
  Resolution: Good UX pattern for heavy price data fetching.

## Decision Log

- Decision: Use UUID-based security identification with ticker normalization (uppercase).
  Rationale: Tickers are case-insensitive but database normalization matters for joins and lookups.
  Date/Author: 2025-12-XX / Codex

- Decision: Store uninvested cash as SCD-2 row in `investment_positions` table.
  Rationale: Users need to reconcile brokerage cash independently of marketable holdings. Temporal modeling ensures historical tracking of cash changes.
  Date/Author: 2025-12-XX / Codex

- Decision: Implement portfolio history as pre-aggregated time-series snapshots.
  Rationale: Performance optimization: historical views need fast queries without recomputing from scratch each time.
  Date/Author: 2025-12-XX / Codex

- Decision: Use dual-state cash model for investments (ledger cash vs uninvested cash).
  Rationale: Ledger cash tracks total deposits/withdrawals; uninvested cash tracks current brokerage cash balance. This enables proper return calculations.
  Date/Author: 2025-12-XX / Codex

- Decision: Calculate portfolio returns using ledger cash as cost basis.
  Rationale: Total return = (NAV - ledger_cash) captures all gains including those from sold positions.
  Date/Author: 2025-12-XX / Codex

## Outcomes & Retrospective

Delivered complete investment tracking and net worth system with the following capabilities:

**Completed:**
- Portfolio state management with positions (ticker, quantity, cost basis, market value)
- Investment reconciliation workflow for verifying holdings and cash
- Market data sync via background job fetching OHLC prices
- Portfolio history API with time-series data (NAV, cash flow, returns)
- Performance metrics: total return, total return percentage, today's return
- Investment account detail pages with performance chart and holdings table
- Net worth aggregation across all account classes (assets - liabilities)
- Net worth history API with interval-based queries
- Dashboard landing page with interactive chart, account panel, and budget watchlist

**Remaining Work (tracked in Beads):**
- `dojo-aur`: Write Outcomes & Retrospective for Investment Tracking
- `dojo-pjb.2`: UX-002 - Fix investment portfolio entry point navigation redirect

**Implementation Notes:**
- Investment tracking is fully functional with reconciliation, history, and market sync
- Net worth computation properly excludes inactive accounts from current snapshot while preserving historical data
- Dashboard provides interactive chart with drag-to-select for interval analysis
- Performance metrics align with financial math conventions (log returns for time aggregation)

## Context and Orientation

All investment and net worth functionality lives in two domain modules:

**Investment Tracking** (`/investments`):
- `src/dojo/investments/service.py` - InvestmentService with portfolio state, reconciliation, and market sync
- `src/dojo/investments/dao.py` - InvestmentDAO for position and security data access
- `src/dojo/investments/routers.py` - FastAPI endpoints for investment operations
- `src/dojo/investments/domain.py` - Pydantic models for PortfolioState, PositionView, etc.
- `src/dojo/investments/market_client.py` - External market data provider (Yahoo Finance)
- `src/dojo/sql/migrations/0013_investment_tracking.sql` - Positions, securities, market prices tables

**Net Worth** (`/core`):
- `src/dojo/core/net_worth.py` - Net worth computation services
- `src/dojo/core/routers.py` - Net worth API endpoints (/api/net-worth/current, /api/net-worth/history)
- `src/dojo/sql/` - Aggregation queries for account balances across all classes

**Frontend**:
- `src/dojo/frontend/vite/src/pages/AccountDetailPage.vue` - Investment portfolio view (charts, holdings, cash input)
- `src/dojo/frontend/vite/src/pages/DashboardPage.vue` - Net worth landing page with interactive chart

The system uses DuckDB with SCD-2 for positions. Investment accounts track both ledger cash (transactions) and uninvested cash (brokerage balance). Market data is fetched asynchronously and stored in `market_prices` table.

## Plan of Work

This plan documents completed work. For future enhancements in this domain, refer to the outstanding issues listed in Outcomes & Retrospective.

## Concrete Steps

For historical context, these steps were already completed:

1. Created `investment_positions` table with SCD-2 versioning in `src/dojo/sql/migrations/0013_investment_tracking.sql`
2. Implemented InvestmentService.get_portfolio_state() returning PortfolioState with positions and totals
3. Built portfolio reconciliation workflow updating positions and uninvested cash atomically
4. Implemented market data sync job fetching OHLC prices from external provider and upserting to `market_prices`
5. Created net worth aggregation service querying all accounts and computing assets - liabilities
6. Built dashboard page with interactive SVG chart supporting drag-select interval analysis
7. Implemented investment account detail page with performance chart, holdings table, and cash reconciliation

## Validation and Acceptance

All acceptance criteria from original plans were met:
- `scripts/run-tests --filter integration:test_investments_api` passes with green results
- Investment portfolio page renders with NAV, cost basis, deposits, total return, and share of portfolio
- Portfolio history API returns time-series data with proper pagination and date range filtering
- Reconciliation updates positions and uninvested cash with immediate UI refresh
- Net worth current endpoint returns correct aggregation excluding inactive accounts
- Net worth history API supports interval parameter (1D, 1W, 1M, 3M, YTD, 1Y, 5Y, Max)
- Dashboard interactive chart works with mouse hover, drag-select, and tooltip display
- Market sync job runs successfully in background and updates position market values

## Idempotence and Recovery

- Portfolio reconciliation is idempotent: closing and inserting new position versions safely handles repeated calls
- Market data upserts are idempotent: same date/security combination replaces existing data
- Net worth computations are read-only queries, no state changes

## Artifacts and Notes

Key artifacts from completed work:

```
src/dojo/investments/service.py
  - InvestmentService.get_portfolio_state() - Returns positions + portfolio totals
  - InvestmentService.reconcile_portfolio() - Updates positions and uninvested cash
  - InvestmentService.sync_market_data() - Fetches and stores OHLC prices
  - compute_portfolio_totals() - Calculates NAV, holdings value, total return

src/dojo/investments/routers.py
  - GET /investments/accounts/{account_id} - Portfolio state
  - GET /investments/accounts/{account_id}/history - Portfolio history
  - POST /investments/accounts/{account_id}/reconcile - Reconcile holdings
  - POST /jobs/market-update - Trigger market sync

src/dojo/investments/domain.py
  - PortfolioState: nav_minor, holdings_value_minor, total_return_minor, positions[]
  - PositionView: security_id, ticker, quantity, avg_cost_minor, price_minor, gain_minor
  - PortfolioHistoryPoint: market_date, nav_minor, cash_flow_minor, return_minor

src/dojo/core/routers.py
  - GET /api/net-worth/current - Current net worth (excludes inactive)
  - GET /api/net-worth/history?interval={interval} - Historical time series

src/dojo/frontend/vite/src/pages/DashboardPage.vue
  - Interactive chart with 7 interval buttons (1D, 1W, 1M, 3M, YTD, 1Y, 5Y, Max)
  - Mouse hover for single-point data, drag-select for range analysis
  - Accounts panel with top 8 accounts sorted by balance
  - Budget watchlist with progress bars for 6 categories

src/dojo/frontend/vite/src/pages/AccountDetailPage.vue
  - Investment-specific layout with portfolio chart
  - HoldingsTable showing ticker, quantity, cost basis, market value, gain
  - Cash balance input with blur/Enter save
  - "Update prices" button triggering market sync
```

## Interfaces and Dependencies

**External Dependencies:**
- Yahoo Finance API (via yfinance): Historical OHLC price data for securities
- DuckDB: Storage for positions, securities, market prices, and account aggregation
- FastAPI: Web framework exposing investment and net worth APIs
- TanStack Query (Vue): Data fetching and caching for portfolio and net worth data

**Internal Modules:**
- `dojo.investments.dao`: InvestmentDAO for position and security queries
- `dojo.investments.market_client`: MarketClient for external price data
- `dojo.core.net_worth`: NetWorthService for aggregation logic

**Key Invariants:**
- Portfolio NAV = uninvested_cash + Σ(security_quantity * market_price)
- Total return = NAV - ledger_cash (cost basis from deposits)
- Net worth = Σ(active_assets) - Σ(active_liabilities)
- Inactive accounts excluded from current snapshot but included in historical queries
