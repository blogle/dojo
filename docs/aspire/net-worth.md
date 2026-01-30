# Aspire Net Worth

This document captures Aspire’s net worth tracking semantics.

Aspire’s net worth is **not derived from the transaction ledger**. Instead, it is rolled up from explicit “mark” (snapshot) entries recorded on the `Net Worth Reports` sheet.

## Canonical net worth input surface (snapshot log)

Aspire includes an explicit net worth snapshot log on the `Net Worth Reports` sheet.

- Header row observed at `Net Worth Reports!B19:F19`:
  - DATE
  - AMOUNT
  - NET WORTH CATEGORY
  - NOTES
  - (a breakpoint marker column)

Named ranges (one per column):

- `ntw_Dates` (`'Net Worth Reports'!B20:B1500`)
- `ntw_Amounts` (`'Net Worth Reports'!C20:C1500`)
- `ntw_Categories` (`'Net Worth Reports'!D20:D1500`)
- `ntw_Notes` (`'Net Worth Reports'!E20:E1500`)
- `ntw_Breakpoints` (`'Net Worth Reports'!F20:F1500`)

These rows are the source of truth for net worth reporting.

## Net worth category configuration

Net worth categories are configured separately from budget categories and accounts.

Derived lists on `BackendData`:

- `NetWorthAssets` (`BackendData!AD2:AD9`) is `=ArrayFormula(Configuration!P30:P37)`
- `NetWorthDebts` (`BackendData!AE2:AE9`) is `=ArrayFormula(Configuration!Q30:Q37)`
- `NetWorthCategories` (`BackendData!AC2:AC17`) combines those two columns:
  - `=FILTER({Configuration!$P$30:$P$37;Configuration!$Q$30:$Q$37}, LEN({Configuration!$P$30:$P$37;Configuration!$Q$30:$Q$37}))`

Important: users commonly duplicate on-budget account names into these net worth category lists (sometimes with spelling/case variations). This is expected: net worth totals only “see” what is recorded via `ntw_*` snapshots.

Note: the rollups use exact string matching (`SUMIFS` / `FILTER` against `ntw_Categories`). Spelling/case/emoji differences create distinct categories.

## Amount sign convention

Aspire treats `ntw_Amounts` as a magnitude and applies sign based on whether the category is an asset or a debt.

Evidence (`Calculations!A40:D55` current-value table):

- `Calculations!A40 = ARRAYFORMULA(NetWorthCategories)`
- `Calculations!B40` (for one category `A40`) selects the latest snapshot for that category and applies sign:
  - if `COUNTIF(NetWorthAssets, A40)` then use amount as-is
  - else multiply by `-1`

This yields:

- assets contribute positively
- debts contribute negatively

## Monthly rollups (“marks”) and history series

Aspire builds a month-bucketed net worth history table in `Calculations`, driven entirely by `ntw_*`.

Category header row

- `Calculations!D289:K289` selects up to 8 asset category labels from `NetWorthAssets` (`BackendData!AD2:AD9`)
- `Calculations!L289:S289` selects up to 8 debt category labels from `NetWorthDebts` (`BackendData!AE2:AE9`)
- Empty category slots fall back to a placeholder (`BackendData!AF2` in this sheet; observed as a bullet). This keeps the table shape stable.

Month buckets

For each month row `r`, Aspire computes a month-end boundary in column C and then sums snapshot amounts that fall into that month.

Year range selection

- `NetWorthYearRanges` (`BackendData!AG2:AG5`) provides options like “2 years”, “5 years”, “7 years”, “10 years”.
- `Calculations!C412 = SPLIT('Net Worth Reports'!E3, " years")` converts the selected label into a numeric year count.
- The month-bucket tables are gated by checks like `IF(C412 >= 10, ...)` so that only the selected horizon is populated.

Representative formula (10-year history rows):

- `Calculations!C290 = IF(C412 >= 10, EOMONTH(DATE(YEAR($B$4), MONTH($B$4)-120, 1),0), "")`
- `Calculations!D290 = IF($C290, SUMIFS(ntw_Amounts, ntw_Categories, D$289, ntw_Dates, ">" & $C290, ntw_Dates, "<=" & $C291), "")`
- Debt columns apply a sign flip:
  - `Calculations!L290 = IF($C290, -1 * SUMIFS(ntw_Amounts, ntw_Categories, L$289, ntw_Dates, ">" & $C290, ntw_Dates, "<=" & $C291), "")`

Current month bucket

The latest row in this sheet uses `v_Today` as the end bound (so the “current month” is month-to-date):

- `Calculations!C409 = EOMONTH(DATE(YEAR($B$4), MONTH($B$4)-1, 1),0)` (end of previous month)
- `Calculations!D409 = IF($C409, SUMIFS(ntw_Amounts, ntw_Categories, D$289, ntw_Dates, ">" & $C409, ntw_Dates, "<=" & $B$4), "")`

Implication: net worth reporting assumes you record a “mark” during the month. If there is no snapshot for a category during that month bucket, it contributes 0 for that month. If there are multiple entries for a category within a month bucket, the table will sum them.

## Net worth totals and % change

Totals

- Net worth (current month bucket): `Calculations!B415 = SUM(D409:S409)`
- Assets: `Calculations!B418 = SUM(D409:K409)`
- Debts: `Calculations!B421 = SUM(L409:S409)`

Percent change

Aspire computes percent changes by comparing the current bucket to earlier buckets:

- `Calculations!C424` (1-month net worth change):
  - `(SUM(D409:S409) - SUM(D408:S408)) / ABS(SUM(D408:S408))` with error handling
- `Calculations!C425` (3-month net worth change) compares to row 406
- `Calculations!C426` (6-month net worth change) compares to row 403
- `Calculations!C427` (12-month net worth change) compares to row 397

Assets use the same structure on the assets-only range.

Debts use an ABS-based change computation (because debts are represented as negative values in the table):

- `Calculations!E424 = IF(SUM(L409:S409)=0, "", IFERROR((ABS(SUM(L409:S409)) - ABS(SUM(L408:S408))) / ABS(SUM(L408:S408)), "N/A"))`

Selected change horizon

The Net Worth Reports page selects which change horizon to display using `NetWorthChangeRanges` and a FILTER:

- `Calculations!C415 = FILTER(C424:C427, B424:B427 = 'Net Worth Reports'!H5)`
- `Calculations!C418 = FILTER(D424:D427, B424:B427 = 'Net Worth Reports'!H8)`
- `Calculations!C421 = FILTER(E424:E427, B424:B427 = 'Net Worth Reports'!H11)`

## Net Worth Reports summary blocks (UI)

Net Worth Reports surfaces the computed totals and selected change values by referencing `Calculations`:

- Net worth total: `Net Worth Reports!J4 = IF(Calculations!B415, ROUND(Calculations!B415, 3), "No data for")`
- Net worth change label/value: `Net Worth Reports!J5 = IF(OR(Calculations!C415, Calculations!C415 = "N/A"), Calculations!C415, TEXT(Calculations!B4, "MMMM"))`
- Assets total: `Net Worth Reports!J7 = IF(OR(Calculations!B418, Calculations!B418 = "N/A"), ROUND(Calculations!B418, 3), "No data for")`
- Assets change: `Net Worth Reports!J8 = IF(OR(Calculations!C418, Calculations!C418 = "N/A"), Calculations!C418, TEXT(Calculations!B4, "MMMM"))`
- Debts total: `Net Worth Reports!J10 = IF(OR(Calculations!B421, Calculations!B421 = "N/A"), ROUND(Calculations!B421, 3), "No data for")`
- Debts change: `Net Worth Reports!J11 = IF(OR(Calculations!C421, Calculations!C421 = "N/A"), Calculations!C421, TEXT(Calculations!B4, "MMMM"))`

## Per-category month totals (Net Worth Reports UI)

Net Worth Reports includes a per-category lookup for a selected category and month.

Evidence:

- `Calculations!C429 = TO_DATE(DATEVALUE('Net Worth Reports'!I16))` (start of selected month)
- `Calculations!D429 = TO_DATE(EOMONTH(DATEVALUE('Net Worth Reports'!I16), 0))` (end of selected month)
- `Calculations!B430 = IFERROR(SUMIFS(ntw_Amounts, ntw_Categories, 'Net Worth Reports'!I15, ntw_Dates, "<=" & D429, ntw_Dates, ">=" & C429), "N/A")`
- Displayed at: `Net Worth Reports!I17 = Calculations!B430`

## Budget accounts vs net worth categories (critical distinction)

Aspire has *two* different “account-like” concepts:

- Budget accounts (`cfg_Accounts`, `cfg_Cards`, and derived lists like `UserDefAccounts`) are the accounts used by the transaction ledger (`trx_*`).
- Net worth categories (`NetWorthAssets`, `NetWorthDebts`) are the entities used by the net worth snapshot log (`ntw_*`).

They often overlap by name, but they are not linked by the sheet logic. Net worth reporting is entirely driven by snapshots.

## Dashboard net worth block (optional)

A configuration toggle controls whether a net worth block appears on the dashboard:

- `Configuration!O4` (label at `Configuration!P4`: “Show net worth on the Dashboard”)

When enabled, Aspire concatenates the ledger-derived budget-account balance table (`Calculations!A7:D37`) and the snapshot-derived net worth category table (`Calculations!A40:D55`) into a combined display table (`Calculations!A157:D157`).

This is a display convenience; it does not change the fact that net worth reporting uses `ntw_*`.
