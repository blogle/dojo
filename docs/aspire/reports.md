# Aspire Reports

This document summarizes Aspire’s reporting sheets and the key formulas / named ranges behind them.

Aspire’s reporting UI is split across multiple “report” tabs, but much of the work is done on the hidden `Calculations` sheet and then referenced into each report.

## Balances

Purpose: quick “balance + transactions” view for either an account or a category.

Inputs

- Selector cell: `Balances!B3`.
  - Treated as either an account name (matches `UserDefAccounts`) or a category name (matches `Categories`).

Derived balances (status-aware)

`Calculations` computes status-separated totals (approved vs pending) and then `Balances` displays them.

Core formulas (`Calculations`):

- Actual balance: `Calculations!B206 = SUM(B207:B208) - SUM(B209:B210)`
- Approved-only net: `Calculations!B213 = B207 - B209`
- Pending-only net: `Calculations!B212 = B208 - B210`

The Balances sheet displays these via:

- `Balances!E3 = ROUND(Calculations!B211, 3)` (Actual; `B211` is an alias of `B206`)
- `Balances!F3 = ROUND(Calculations!B212, 3)` (Pending)
- `Balances!G3 = ROUND(Calculations!B213, 3)` (Settled/approved)

Notes on the accounting model:

- `Calculations!B207:B210` use status symbols (`v_ApprovedSymbol`, `v_PendingSymbol`).
- Balance math includes both:
  - flows where `trx_Accounts == Balances!B3` (normal account rows), and
  - counter-flows where `trx_Categories == Balances!B3` (category==account adjustment rows).

Transaction list

- `Balances!B8` filters and sorts the ledger for either “this category” or “this account”:
  - `IFERROR(sort(filter(Transactions!B9:H, (Transactions!E9:E = B3) + (Transactions!F9:F = B3)), 1, FALSE), "")`

## Account Reports

Purpose: month-by-month account summary and a transaction list for a selected month.

Inputs

- Account selector: `Account Reports!B7`.
- Timeframe selector: `Account Reports!B4`.
  - Options are “Last 12 months” plus years (see `YearsAndLast12` on `BackendData!AB2:AB27`).
- Selected month for the transaction detail list: `Account Reports!B25`.

Time window and month buckets (in `Calculations`)

- Timeframe window start/end:
  - `Calculations!B229` is the window start month (either 11 months ago or Jan 1 of the selected year).
  - `Calculations!B241` is the window end month boundary (either next month or Jan of the following year).
- Monthly labels are built like:
  - `Calculations!A238 = TEXT(B238, "MMMM") & " " & TEXT(B238, "YYYY")`
- The month-start boundaries used for aggregation are computed per row:
  - `Calculations!B238 = IF('Account Reports'!B4="Last 12 months", DATE(YEAR(v_Today), MONTH(v_Today)-2, 1), DATE('Account Reports'!B4, 10, 1))`
  - `Calculations!B239` is the next month start (and so on).
- `Calculations!C238 = IF(v_Today - B238 < 0, 0, 1)` gates out “future” months.

Monthly series (per account)

For a selected account `X = Account Reports!B7`, representative month computations are:

- Inflow (excluding transfers and starting balances): `Calculations!D238`
  - `SUMIFS(trx_Inflows, trx_Accounts, X, trx_Dates, ">="&month_start, trx_Dates, "<"&month_next, trx_Categories, "<>"&v_AccountTransfer, trx_Categories, "<>"&v_StartingBalance)`
- Outflow (excluding transfers and starting balances): `Calculations!F238`
  - same filters as inflow, but on `trx_Outflows`, multiplied by `-1` so it displays as positive magnitude.
- Transfer/payment total: `Calculations!E238`
  - `SUMIFS(trx_Outflows, trx_Accounts, X, trx_Categories, v_AccountTransfer, date in month) - SUMIFS(trx_Inflows, trx_Accounts, X, trx_Categories, v_AccountTransfer, date in month)`
- Running balance: `Calculations!G238`
  - net inflow minus outflow up to month end, plus adjustment for rows where `trx_Categories == X`.

Credit-card labeling

`Account Reports` switches wording based on whether the selected account is a credit card:

- `Account Reports!G20 = "Total " & IF(COUNTIF(CreditCardAccounts, B7), "Payments", "Transferred")`

Summary blocks (UI)

- “Last 12 months” / selected-year totals are surfaced via:
  - `Account Reports!E21 = ROUND(Calculations!B253, 3)` (inflow)
  - `Account Reports!F21 = ROUND(Calculations!A253, 3)` (outflow)
  - `Account Reports!G21 = ROUND(Calculations!C253, 3)` (transferred/payments)
- Selected-month totals (for `Account Reports!B25`) are surfaced via:
  - `Account Reports!E25 = ROUND(Calculations!B247, 3)`
  - `Account Reports!F25 = ROUND(Calculations!A247, 3)`
  - `Account Reports!G25 = ROUND(Calculations!C247, 3)`

Transaction list (month detail)

- The selected-month window is computed in `Calculations`:
  - `Calculations!A244 = TO_DATE(DATEVALUE('Account Reports'!B25))`
  - `Calculations!B244 = TO_DATE(EOMONTH(DATEVALUE('Account Reports'!B25), 0))`
- The list is then filtered and sorted at `Account Reports!B29`:
  - `IFERROR(sort(filter(Transactions!$B$9:$G, trx_Accounts = B7, trx_Dates >= Calculations!A244, trx_Dates <= Calculations!B244), 1, FALSE), "")`

## Category Reports

Purpose: rank categories by spending and show month-by-month series for multiple “facets” (available/ending/activity/budgeted).

Inputs

- Time period: `Category Reports!B4`
  - Options are “Last 12 months” plus years (see `YearsAndLast12` on `BackendData!AB2:AB27`).
- Selected category: `Category Reports!B7`.
  - Drives the rank readout (`Category Reports!B10`).
  - Drives the selected-category “Budgeted” / “Activity” totals (`Category Reports!P19` / `Category Reports!R19`) via the drill-down table on `Calculations!D261:D285`.
- Measure selector: `Category Reports!Q21`.
  - Dropdown options come from `BudgetAnalysisOptions` on `BackendData!AI2:AI5`:
    - Available Balance
    - Ending Balance
    - Activity
    - Budgeted

Category list + static attributes

- The ranked table is partitioned into blocks and seeded from `BackendData`:
  - `Category Reports!B24 = ArrayFormula(BackendData!C2:C26)` (first block)
  - `Category Reports!B50 = ArrayFormula(BackendData!C27:C51)` (second block)
  - `Category Reports!B76 = ArrayFormula(BackendData!C52:C76)` (third block)
  - `Category Reports!B102 = ArrayFormula(BackendData!C78:C102)` (fourth block)
- `BackendData!C2` derives the base list by filtering the configuration table:
  - `FILTER(Configuration!D11:D91, LEN(...), Configuration!C11:C91 <> v_CategoryGroupSymbol, Configuration!C11:C91 <> v_DebtAccountSymbol)`
  - Practical implication: category groups and debt rows (credit card payment categories) are excluded.
- Per-category targets/goals come directly from `Configuration`:
  - Monthly target: `Category Reports!D24 = SUMIF(Configuration!D11:D66, <category>, Configuration!G11:G66)`
  - Goal amount: `Category Reports!E24 = SUMIF(Configuration!D11:D66, <category>, Configuration!K11:K66)`
  - Goal flag glyph: `Category Reports!C24 = IF(E24 > 0, BackendData!V2, "")`

Ranking (amount spent)

- Per-category “amount spent” over the selected window is computed at `Category Reports!G24`:
  - `SUMIFS(trx_Outflows, ...) - SUMIFS(trx_Inflows, ...)` over `trx_Dates` in `[Calculations!A261, Calculations!A273)`.
- Rank of the selected category is displayed at `Category Reports!B10` using:
  - `RANK(SUMIF(B24:B100, B7, G24:G100), G24:G100, 0) & " of " & Calculations!A283`

Month boundaries + gating

- `Calculations!A261:A273` builds the month-start boundaries used by this report:
  - If `Category Reports!B4 == "Last 12 months"`, the start is `DATE(YEAR(v_Today), MONTH(v_Today)-11, 1)`.
  - Otherwise, it starts at `DATE(<selected_year>, 1, 1)` and proceeds month-by-month.
- `Calculations!B261:B272` is a per-month “not future” gate: `IF(v_Today - A261 < 0, 0, 1)`.
- `Calculations!B273 = SUM(B261:B272)` is the count of months included; used for averages (e.g. `Category Reports!F24` divides by this).

Per-category month series (the 4 measurement modes)

- The month columns are `Category Reports!H:S`. Each cell is gated by `Calculations!B261:B272` and switches behavior based on `Category Reports!Q21`.
- Definitions for a category `X`, with `start = Calculations!A261` and `end = Calculations!A262` (shifting per month):
  - Ending Balance: cumulative balance through month end
    - `sum(trx_Inflows where category==X and trx_Dates < end)`
    - minus `sum(trx_Outflows where category==X and trx_Dates < end)`
    - plus `sum(cts_Amounts where to_category==X and cts_Dates < end)`
    - minus `sum(cts_Amounts where from_category==X and cts_Dates < end)`
  - Available Balance: balance after budgeting but before the month’s Activity
    - same as Ending Balance, but transaction sums use `trx_Dates < start` (so the month’s Activity is excluded)
  - Activity: net transaction flow within the month
    - `sum(trx_Inflows where category==X and start <= trx_Dates < end) - sum(trx_Outflows where category==X and start <= trx_Dates < end)`
  - Budgeted: net category transfers (allocations) within the month
    - `sum(cts_Amounts where to_category==X and start <= cts_Dates < end) - sum(cts_Amounts where from_category==X and start <= cts_Dates < end)`

Notes

- `cts_*` is the Category Allocation log (`Category Allocation!B8:E...`) and includes both transfers from Ready-to-Assign (FROM == `v_AtoB`) and category-to-category moves.
- This report uses exact string matching on category labels (`SUMIF` / `SUMIFS`); spelling/case differences create distinct categories.

## Spending Reports

Purpose: reportable-category totals over a user-selected date range, plus a per-category transaction list.

Reportable category list

- `SpendingReportCategories` (`BackendData!D2:D101`) filters categories where `Configuration!C == v_ReportableCategorySymbol`.

Date range (month granularity)

`Calculations` computes month boundaries from `Spending Reports` dropdowns:

- `Calculations!D436 = TO_DATE(DATEVALUE('Spending Reports'!D3 & " " & 'Spending Reports'!E3))` (from month/year)
- `Calculations!D438 = EOMONTH(TO_DATE(DATEVALUE('Spending Reports'!F3 & " " & 'Spending Reports'!G3)), 0)` (to month end)
- `Calculations!D443 = DATEDIF(D436, D438, "M") + 1` (# months)

Per-category totals

- `Calculations!B435` / `C435` compute outflow/inflow per category over that date range.
- `Calculations!D439` / `D440` sum totals across all reportable categories.

Average outflow

- `Calculations!D445 = SUMIF(A435:A534, 'Spending Reports'!B36, B435:B534) / D443`

Transaction list

- `Spending Reports!B40` filters the ledger by selected category and date range.

## Trend Reports

Purpose: compare up to 6 categories’ monthly outflows over a selected year or the last 12 months.

Inputs

- Timeframe: `Trend Reports!B5` is either “Last 12 months” or a year.
- Category picks are referenced in `Calculations!C538:H538` (pulled from `Trend Reports` cells).

Monthly outflow series

- `Calculations!B539:B550` build month start dates based on the selected year/timeframe.
- `Calculations!C539:H550` compute per-category monthly outflows via `SUMIFS(trx_Outflows, trx_Categories, <category>, trx_Dates between month_start and month_next)`.

Per-category month lookup

- `Calculations!B553:C553` compute the start/end of a selected month (`Trend Reports!B30`).
- `Calculations!B556:C556` compute outflow/inflow for a selected category (`Trend Reports!B28`) within that month.

## Net Worth Reports

Net worth reporting is snapshot-driven and uses the `ntw_*` log.

See `docs/aspire/net-worth.md` for the full semantics, including:

- how `NetWorthAssets` / `NetWorthDebts` define signs
- how month buckets are computed
- how percent changes are calculated and selected
