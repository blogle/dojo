# Aspire Named Ranges

Named ranges are the closest thing an Aspire sheet has to a stable API.

Users can move UI blocks around and insert/delete rows, so cell coordinates are not reliable for extraction. Named ranges (and formulas that reference them) are far more stable and are the primary anchor for Aspire -> Dojo migration tooling.

This catalog is derived from exports created by `dojo.aspire.gsheets_export` (see `docs/aspire/overview.md`). We do not commit raw values from personal sheets; we only commit structural evidence (names, shapes, and key formulas/constants).

Note: not all migration-relevant formulas are covered by named ranges (e.g. parts of the `Dashboard` and `Calculations` sheets). Use the exporter’s `--a1-range ... --include-a1-range-formulas` support to extract those formulas into gitignored `artifacts/` for analysis.

## Core source-of-truth ranges (migration-critical)

These are the ranges that represent user-entered “records” Aspire expects to persist.

Transactions ledger (sheet `Transactions`)

- `trx_Dates` (`'Transactions'!B9:B10291`, 10283x1): transaction date column.
- `trx_Outflows` (`'Transactions'!C9:C10291`, 10283x1): outflow amount column.
- `trx_Inflows` (`'Transactions'!D9:D10291`, 10283x1): inflow amount column.
- `trx_Categories` (`'Transactions'!E9:E10291`, 10283x1): category / envelope label column.
- `trx_Accounts` (`'Transactions'!F9:F10291`, 10283x1): account label column.
- `trx_Memos` (`'Transactions'!G9:G10291`, 10283x1): memo / payee text column.
- `trx_Statuses` (`'Transactions'!H9:H10291`, 10283x1): status / cleared column (uses the status symbols below).
- `trx_Uuids` (expected “stable row id” / UUID column): observed as malformed in one export (0-width). Treat as optional and prefer deriving stable ids during import.

Category allocations / envelope moves (sheet `Category Allocation`)

- `cts_Dates` (`'Category Allocation'!B8:B2979`, 2972x1): allocation event date.
- `cts_Amounts` (`'Category Allocation'!C8:C2979`, 2972x1): allocation amount.
- `cts_FromCategories` (`'Category Allocation'!D8:D2979`, 2972x1): source category (often explicitly `v_AtoB` / “Available to budget”, not blank).
- `cts_ToCategories` (`'Category Allocation'!E8:E2979`, 2972x1): destination category.

Net worth snapshot log (sheet `Net Worth Reports`)

- `ntw_Dates` (`'Net Worth Reports'!B20:B1500`, 1481x1)
- `ntw_Amounts` (`'Net Worth Reports'!C20:C1500`, 1481x1)
- `ntw_Categories` (`'Net Worth Reports'!D20:D1500`, 1481x1)
- `ntw_Notes` (`'Net Worth Reports'!E20:E1500`, 1481x1)
- `ntw_Breakpoints` (`'Net Worth Reports'!F20:F1500`, 1481x1)

Configuration (sheet `Configuration`)

- `cfg_Accounts` (`'Configuration'!P9:P24`, 16x1): user-configured “bank” accounts.
- `cfg_Cards` (`'Configuration'!Q9:Q24`, 16x1): user-configured credit card accounts.
- `r_ConfigurationData` (`'Configuration'!C11:K91`, 81x9): central configuration table that drives category lists, reporting behavior, and other semantics.

## Derived / lookup ranges (mostly sheet `BackendData`)

Most `BackendData` named ranges are derived lists used for dropdowns and reporting.

Examples (key for interpretation):

- `Categories` is derived from `UserDefCategories` plus the special “Available to budget” label.
- `TransactionCategories` is a derived dropdown list that concatenates special categories (transfer/balance adjustment/starting balance), “Available to budget”, the category list (minus some types), and hidden categories.
- `TransactionAccounts` is a derived dropdown list that concatenates configured accounts/cards plus hidden accounts.

## Constants and symbols

These values are used as “markers” inside the configuration table and ledger UI.

Status symbols (sheet `BackendData`)

- `v_ApprovedSymbol` (`'BackendData'!Q2`) + `v_PendingSymbol` (`'BackendData'!Q3`) + `v_BreakSymbol` (`'BackendData'!Q4`)
- `ClearedSymbols` (`'BackendData'!Q2:Q4`) is the list form.

Category / row-type markers (sheet `BackendData`)

- `v_CategoryGroupSymbol` (`'BackendData'!U2`) marks category group rows.
- `v_ReportableCategorySymbol` (`'BackendData'!U3`) marks reportable categories.
- `v_NonReportableCategorySymbol` (`'BackendData'!U4`) marks non-reportable categories.
- `v_DebtAccountSymbol` (`'BackendData'!U5`) marks debt-account rows.

Special labels used in category lists (sheet `BackendData`)

- `v_AtoB` (`'BackendData'!O2`): “Available to budget”.
- `v_AccountTransfer` (`'BackendData'!P2`): a special category label representing account-to-account transfers (label includes an arrow/emoji prefix in the sheet).
- `v_BalanceAdjustment` (`'BackendData'!P3`): a special category label for balance adjustments.
- `v_StartingBalance` (`'BackendData'!P4`): a special category label for starting balances.

Other constants

- `v_Version` (`'BackendData'!AP2`): Aspire sheet/template version.
- `v_Today` (`'Calculations'!B4`): today’s date (used for time-relative calculations).

## Full inventory (grouped by sheet)

Unknown / malformed

- `r_DashboardData` (missing `sheetId` in the Sheets API response; cannot be exported reliably)

BackendData

- `AccountsAndCategories` (`'BackendData'!N2:N133`, 132x1)
- `BankAccounts` (`'BackendData'!J2:J16`, 15x1)
- `BudgetAnalysisOptions` (`'BackendData'!AI2:AI5`, 4x1)
- `Categories` (`'BackendData'!B2:B102`, 101x1)
- `CategoriesMinusCreditCards` (`'BackendData'!C2:C101`, 100x1)
- `CategoryHeaderSymbols` (`'BackendData'!U2:U5`, 4x1)
- `CategoryTransfersCategories` (`'BackendData'!H2:H147`, 146x1)
- `ClearedSymbols` (`'BackendData'!Q2:Q4`, 3x1)
- `CreditCardAccounts` (`'BackendData'!K2:K16`, 15x1)
- `EmergencyFundCalc` (`'BackendData'!T2:T3`, 2x1)
- `HiddenAccounts` (`'BackendData'!L2:L16`, 15x1)
- `HiddenCategories` (`'BackendData'!F2:F46`, 45x1)
- `MonthAndYear` (`'BackendData'!AA2:AA73`, 72x1)
- `Months` (`'BackendData'!Y2:Y13`, 12x1)
- `NetWorthAssets` (`'BackendData'!AD2:AD9`, 8x1)
- `NetWorthCategories` (`'BackendData'!AC2:AC17`, 16x1)
- `NetWorthChangeRanges` (`'BackendData'!AH2:AH5`, 4x1)
- `NetWorthDebts` (`'BackendData'!AE2:AE9`, 8x1)
- `NetWorthYearRanges` (`'BackendData'!AG2:AG5`, 4x1)
- `SpendingReportCategories` (`'BackendData'!D2:D101`, 100x1)
- `TransactionAccounts` (`'BackendData'!M2:M46`, 45x1)
- `TransactionCategories` (`'BackendData'!G2:G150`, 149x1)
- `TrendReportCategories` (`'BackendData'!E2:E102`, 101x1)
- `UserDefAccounts` (`'BackendData'!I2:I31`, 30x1)
- `UserDefAmounts` (`'BackendData'!R2:R101`, 100x1)
- `UserDefCategories` (`'BackendData'!A2:A101`, 100x1)
- `UserDefGoals` (`'BackendData'!S2:S101`, 100x1)
- `Years` (`'BackendData'!Z2:Z26`, 25x1)
- `YearsAndLast12` (`'BackendData'!AB2:AB27`, 26x1)
- `v_AccountTransfer` (`'BackendData'!P2:P2`, 1x1)
- `v_ApprovedSymbol` (`'BackendData'!Q2:Q2`, 1x1)
- `v_AtoB` (`'BackendData'!O2:O2`, 1x1)
- `v_BalanceAdjustment` (`'BackendData'!P3:P3`, 1x1)
- `v_BreakSymbol` (`'BackendData'!Q4:Q4`, 1x1)
- `v_CategoryGroupSymbol` (`'BackendData'!U2:U2`, 1x1)
- `v_DebtAccountSymbol` (`'BackendData'!U5:U5`, 1x1)
- `v_GoalSymbol` (`'BackendData'!V2:V2`, 1x1)
- `v_NonReportableCategorySymbol` (`'BackendData'!U4:U4`, 1x1)
- `v_PendingSymbol` (`'BackendData'!Q3:Q3`, 1x1)
- `v_ReportableCategorySymbol` (`'BackendData'!U3:U3`, 1x1)
- `v_StartingBalance` (`'BackendData'!P4:P4`, 1x1)
- `v_Version` (`'BackendData'!AP2:AP2`, 1x1)

Calculations

- `v_Today` (`'Calculations'!B4:B4`, 1x1)

Category Allocation

- `cts_Amounts` (`'Category Allocation'!C8:C2979`, 2972x1)
- `cts_Dates` (`'Category Allocation'!B8:B2979`, 2972x1)
- `cts_FromCategories` (`'Category Allocation'!D8:D2979`, 2972x1)
- `cts_ToCategories` (`'Category Allocation'!E8:E2979`, 2972x1)

Configuration

- `cfg_Accounts` (`'Configuration'!P9:P24`, 16x1)
- `cfg_Cards` (`'Configuration'!Q9:Q24`, 16x1)
- `r_ConfigurationData` (`'Configuration'!C11:K91`, 81x9)

Net Worth Reports

- `ntw_Amounts` (`'Net Worth Reports'!C20:C1500`, 1481x1)
- `ntw_Breakpoints` (`'Net Worth Reports'!F20:F1500`, 1481x1)
- `ntw_Categories` (`'Net Worth Reports'!D20:D1500`, 1481x1)
- `ntw_Dates` (`'Net Worth Reports'!B20:B1500`, 1481x1)
- `ntw_Notes` (`'Net Worth Reports'!E20:E1500`, 1481x1)

Transactions

- `trx_Accounts` (`'Transactions'!F9:F10291`, 10283x1)
- `trx_Categories` (`'Transactions'!E9:E10291`, 10283x1)
- `trx_Dates` (`'Transactions'!B9:B10291`, 10283x1)
- `trx_Inflows` (`'Transactions'!D9:D10291`, 10283x1)
- `trx_Memos` (`'Transactions'!G9:G10291`, 10283x1)
- `trx_Outflows` (`'Transactions'!C9:C10291`, 10283x1)
- `trx_Statuses` (`'Transactions'!H9:H10291`, 10283x1)
- `trx_Uuids` (`'Transactions'!I9:H6105`, 6097x0, malformed)
