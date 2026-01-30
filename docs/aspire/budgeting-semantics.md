# Aspire Budgeting Semantics

This document captures Aspire’s budgeting rules as observed in named ranges, headers, and formulas.

## Key concepts and where they live

“Ready to Assign” / unallocated cash

Aspire’s “ready to assign” concept is represented as a special category label:

- Named range `v_AtoB` (in `BackendData`): “Available to budget”

This label appears as:

- the CATEGORY for most income inflows in the `Transactions` ledger, and
- the FROM CATEGORY for most allocation events in the `Category Allocation` log.

Categories and category groups

Aspire configures categories and groups on the `Configuration` sheet.

- The central configuration table is `r_ConfigurationData` (`Configuration!C11:K91`).
- The header row above it (`Configuration!C10:K10`) includes:
  - a symbol/type column (C)
  - CATEGORY / GROUP NAME (D)
  - AMOUNT (G)
  - DUE DATE (H)
  - GOAL AMOUNT (K)

The symbol/type column uses marker glyphs defined in `BackendData`:

- `v_CategoryGroupSymbol`: marks group header rows.
- `v_ReportableCategorySymbol`: marks reportable category rows.
- `v_NonReportableCategorySymbol`: marks non-reportable category rows.
- `v_DebtAccountSymbol`: marks debt-account rows (used for credit cards / liabilities).

## Canonical allocation / assignment log

Aspire’s canonical “money movement between envelopes” is stored as an explicit event log on the `Category Allocation` sheet.

- Header row observed at `Category Allocation!B7:E7`:
  - DATE
  - AMOUNT
  - FROM CATEGORY
  - TO CATEGORY

Named ranges (one per column):

- `cts_Dates` (`'Category Allocation'!B8:B2979`)
- `cts_Amounts` (`'Category Allocation'!C8:C2979`)
- `cts_FromCategories` (`'Category Allocation'!D8:D2979`)
- `cts_ToCategories` (`'Category Allocation'!E8:E2979`)

Observed semantics:

- AMOUNT is positive; direction is encoded by FROM CATEGORY -> TO CATEGORY.
- “Assigning” money from Ready-to-Assign uses FROM CATEGORY == `v_AtoB` (“Available to budget”), not a blank FROM field.

## Month boundaries

Aspire uses a calendar-month boundary derived from TODAY().

Evidence (Calculations sheet):

- `Calculations!B65 = DATE(YEAR(B4), MONTH(B4), 1)` (first day of the current month)
- `Calculations!B66 = EOMONTH(DATE(YEAR(B4), MONTH(B4), 1), 0)` (last day of the current month)

`B4` is `=TODAY()` via the named range `v_Today`.

## How balances are computed (envelope math)

Aspire treats category balances as a running total driven by:

- ledger activity (transactions categorized to that category), and
- allocation events (Category Allocation log).

A representative formula (Calculations!B121) computes the current balance for a selected category label `X`:

- if `X == v_AtoB` (Available to budget), use the dedicated AtoB balance (see below)
- otherwise:
  - `sum(inflows where category == X)`
  - minus `sum(outflows where category == X)`
  - plus `sum(allocation amounts where to_category == X)`
  - minus `sum(allocation amounts where from_category == X)`

This implies:

- rollovers are automatic (the balance is cumulative across time), and
- overspending is represented directly as a negative balance (no special month reset is required for the math to work).

## Available to budget (Ready-to-Assign) calculation

Aspire computes Available-to-budget as a running balance of both:

- inflows/outflows categorized to `v_AtoB`, and
- allocation events that move money into/out of `v_AtoB`.

Evidence (Calculations!B59):

- `B59 = (B61 + B62) - (B63 + B60)`
- `B61` is inflows to `v_AtoB`, plus `v_StartingBalance` inflows, plus balance adjustment inflows on bank accounts (`trx_Categories == v_BalanceAdjustment` and `trx_Accounts` in `BankAccounts`).
- `B60` is outflows from `v_AtoB` plus balance adjustment outflows on bank accounts.
- `B63` is allocations from `v_AtoB`
- `B62` is allocations to `v_AtoB`

## Dashboard budget table (primary budgeting UX)

The `Dashboard` sheet is the primary budgeting UI.

It contains a budget table with category groups, categories, and (optionally) debt-account rows (credit card payment categories).

Category rows and types

- Category/group metadata comes from the configuration table:
  - type symbol column: `Dashboard!H6 = ArrayFormula(Configuration!C11:C91)`
  - name column: `Dashboard!J6 = ArrayFormula(Configuration!D11:D91)`

The type symbol matches the marker glyph named ranges:

- `v_CategoryGroupSymbol`
- `v_ReportableCategorySymbol`
- `v_NonReportableCategorySymbol`
- `v_DebtAccountSymbol`

Group rows are computed as rollups:

- When a row is a group row (type == `v_CategoryGroupSymbol`), Aspire sums the values of the subsequent child rows until the next group row.

Key columns (conceptual)

- AMOUNT/DATE (`Dashboard` column K): appears to be user-entered per row (no formulas observed). This functions as a “notes / due date / amount reminder” column rather than a calculation input.
- AVAILABLE (`Dashboard` column L): category “envelope balance” as a running total.
  - For normal categories, this is the cumulative balance driven by:
    - categorized transaction inflows/outflows
    - plus allocations to the category
    - minus allocations from the category
  - For credit card payment rows (detected by `COUNTIF(CreditCardAccounts, <row name>)`), Aspire switches to an account-based reserve model:
    - `AVAILABLE ~= max(account_balance(card), 0) + net_allocations(card) + (card_outflows - card_inflows)` (running total)
    - outflows/inflows are sums on the card ACCOUNT; payments are represented as inflows with CATEGORY `v_AccountTransfer` and therefore reduce AVAILABLE
- ACTIVITY (`Dashboard` column O): net activity for the current month.
  - For normal categories: `sum(inflows) - sum(outflows)` filtered to the current month.
  - For credit card payment rows: computed from the card account’s current-month cashflows; transfers are handled explicitly so payments reduce ACTIVITY.
- TARGET (`Dashboard` column P): per-category “monthly amount” input surfaced from `Configuration!G11:G66`.
- GOAL (`Dashboard` column Q): per-category goal amount surfaced from `Configuration!K11:K66`.
  - In the observed sheet, goal amounts are often derived from monthly amounts (e.g. `goal = amount * 12` for annual targets).
- BUDGETED (`Dashboard` column R): allocations in the current month:
  - `sum(cts_Amounts where to_category == X within month)`
  - minus `sum(cts_Amounts where from_category == X within month)`

Progress and icons

- The dashboard uses image/icon cells stored in `BackendData` to render progress bars and other UI affordances.
- These icons are not exported via the basic `values` API (images do not appear as formulas/values), so tooling must treat them as presentation-only.

Top-of-dashboard summary cards

The dashboard includes summary values derived from `Calculations`:

- Available to budget (Ready-to-Assign): `Dashboard!J3 = ROUND(Calculations!B59, 3)`
- “Spent this month”: `Dashboard!L3 = ROUND(Calculations!B64, 3)`
- “Budgeted this month”: `Dashboard!O3 = ROUND(Calculations!B68, 3)`
- Pending transaction count: `Dashboard!V3 = COUNTIF(trx_Statuses, v_PendingSymbol)` (and a message that pluralizes based on the count)

Optional net worth block

A configuration flag controls whether net worth appears on the dashboard:

- `Configuration!O4` (“Show net worth on the Dashboard”)

When enabled, `Calculations!A157:D157` combines the accounts list and net worth categories for display.

## Emergency fund calculation

Aspire’s Configuration sheet includes an “emergency fund” target derived from budget targets (not from actual spending history).

Evidence:

- Emergency-fund flag column: `Configuration!L10` contains a `"✓ ✕"` header and `Configuration!L11:L66` contains ✓/✕ values.
  - The ✓/✕ options come from `EmergencyFundCalc` (`BackendData!T2:T3`), which contains a ✕ row and a ✓ row.
- 6-month emergency fund amount:
  - `Configuration!K4` label: `"6-month Emergency Fund"`
  - `Configuration!K5` formula: `ROUND((SUMIF(L11:L66, BackendData!T3, G11:G66))*6, 3)`

Interpretation:

- A category is “in the emergency fund” when its flag cell equals the ✓ marker (`BackendData!T3`).
- The emergency fund target equals 6 × the sum of monthly TARGET amounts (`Configuration!G11:G66`) for flagged categories.

## Goals and progress indicators

Aspire distinguishes:

- TARGET: a monthly target amount (`Dashboard!P6 = ArrayFormula(Configuration!G11:G66)`).
- GOAL: a goal amount (`Dashboard!Q6 = ArrayFormula(Configuration!K11:K66)`).
  - Many goal cells are derived from monthly targets (e.g. `Configuration!K16 = G16 * 12` to represent an annual goal).

The dashboard’s progress icon column (Dashboard column M) selects different icon “bands” based on:

- If GOAL > 0: the ratio `AVAILABLE / GOAL`.
- Else: the ratio `AVAILABLE / TARGET`.
- If AVAILABLE is negative: a dedicated “negative” icon is shown.

Note: the icons are stored on `BackendData` (often as images), which are not exported via the basic values API.

## Open questions

- Confirm whether Aspire intends payment reserve to rise even on overspent purchases (the dashboard formulas do).
- Identify any month-end normalization beyond the basic running-total math.
- `r_DashboardData` appears in metadata but was missing a `sheetId` in the Sheets API response. No references were found in exported `Dashboard!H6:R91` or `Calculations!A1:Z220` formulas; likely legacy / deleted.
