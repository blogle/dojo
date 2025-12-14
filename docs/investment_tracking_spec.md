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

*   **Net Asset Value (NAV)**:
    $$ NAV_t = C_{uninvested, t} + \sum (Q_{i,t} \times P_{i,t}) $$
    *   $C_{uninvested}$: Uninvested Cash (SCD2)
    *   $Q_{i}$: Quantity of asset $i$
    *   $P_{i}$: Closing price of asset $i$

*   **Total Return (Money-Weighted - MWR)**:
    $$ Return_{\$, MWR} = NAV_t - C_{ledger, t} $$
    *   $C_{ledger}$: `accounts.current_balance` (Net transfers from ledger)
    *   *Note on Dividends:* Dividends received in the brokerage account increase $C_{uninvested}$ (via the reconciliation workflow) but do *not* affect $C_{ledger}$ unless explicitly transferred out. Thus, they correctly contribute to the Investment Return.

*   **Total Return (%)**:
    $$ Return_{\%, MWR} = \frac{Return_{\$, MWR}}{C_{ledger, t}} $$
    *   *Edge Case:* If $C_{ledger} \le 0$, return % is undefined/null.

*   **Unrealized Gain ($) - Per Position**:
    $$ Gain_i = (Q_i \times P_i) - (Q_i \times CostBasis_i) $$

*   **Time-Weighted Return (TWR)**:
    *   Future implementation will utilize the granular SCD2 history to compute TWR for accurate performance benchmarking against indices.

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

#### `corporate_actions`
-   `action_id` (UUID, PK)
-   `security_id` (UUID, FK)
-   `action_date` (DATE)
-   `action_type` (TEXT) - 'DIVIDEND', 'SPLIT'
-   `value` (DECIMAL)
-   `recorded_at` (TIMESTAMP)

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
        -   Join `market_prices` (Pricing).
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
*   **Background:** `#fdfcfb` (Off-white).
*   **Surface:** `#ffffff` (White) with borders `#e0e0e0`.
*   **Typography:** Sans-serif (`Inter`) for UI text; Monospace (`JetBrains Mono`) for financial data and headers.
*   **Status Colors:** Success (`#6b8e23` - Green) and Danger (`#9c4843` - Red) used for performance metrics.

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
    -   Total Return value is color-coded based on performance.
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

*   **`components/investments/InvestmentAccountPage.js`**: Orchestrator. Fetches data, manages view state (loading/error/success).
*   **`components/investments/PortfolioChart.js`**: D3-less SVG logic. Handles path generation, gradient definitions, and mouse event listeners (drag-to-measure logic).
*   **`components/investments/HoldingsTable.js`**: Renders the table and the "Add Position" form.
*   **`styles/components/investments.css`**: Scoped styles using BEM naming (e.g., `.investment-header__value`, `.chart-tooltip`).

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
