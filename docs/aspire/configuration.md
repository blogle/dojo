# Aspire Configuration Sheet

This document catalogs the user-facing “knobs” on Aspire’s `Configuration` sheet and shows where they feed into calculations.

Important: the Configuration sheet contains user-defined account/category names. This repo’s docs avoid quoting those names directly; we describe structure, formulas, and named ranges instead.

## Global toggles

These are boolean flags (TRUE/FALSE) on the Configuration sheet.

- Highlight editable fields and tables
  - Value: `Configuration!O2`
  - Label: `Configuration!P2`
  - Observed default: FALSE
  - Usage: cosmetic (highlighting), not migration-critical.

- Disable new version notification
  - Value: `Configuration!O3`
  - Label: `Configuration!P3`
  - Observed default: FALSE
  - Usage: cosmetic UX.

- Show net worth on the Dashboard
  - Value: `Configuration!O4`
  - Label: `Configuration!P4`
  - Usage: when TRUE, Aspire includes net worth tables on the Dashboard via `Calculations!A157:D157`.

## Budget planning inputs

Monthly income (planning aid)

- Label: `Configuration!C4` (“Monthly income”)
- User input: `Configuration!C5`

“To allocate in budget” (planning aid)

- Label: `Configuration!G4` (“To allocate in budget”)
- Formula: `Configuration!G5 = ROUND(C5 - SUM(G11:G87), 3)`

Interpretation: this is a planning number computed from the configured monthly income minus the sum of configured monthly TARGET amounts.

## Accounts (budget ledger accounts)

Budget accounts are configured as two lists:

- Bank accounts: `cfg_Accounts` (`Configuration!P9:P24`)
- Credit card accounts: `cfg_Cards` (`Configuration!Q9:Q24`)

Derived lists on `BackendData`:

- `BankAccounts` (`BackendData!J2:J16`) filters `Configuration!P9:P24`
- `CreditCardAccounts` (`BackendData!K2:K16`) filters `Configuration!Q9:Q24`
- `UserDefAccounts` (`BackendData!I2:I31`) combines bank + card lists

Transaction entry uses a dropdown list derived from accounts plus “hidden accounts” (see below):

- `TransactionAccounts` (`BackendData!M2:M46`) is `unique({UserDefAccounts; HiddenAccounts})`.

## Categories, groups, targets, goals

The central budgeting configuration table is:

- Named range: `r_ConfigurationData`
- Range: `Configuration!C11:K91`

Columns in this table that have observable semantics:

- `Configuration!C11:C91`: row type symbol
  - `v_CategoryGroupSymbol` (group header rows)
  - `v_ReportableCategorySymbol` (reportable categories; appear in Spending/Trend reports)
  - `v_NonReportableCategorySymbol` (non-reportable categories)
  - `v_DebtAccountSymbol` (debt/payment rows; used for credit cards)

- `Configuration!D11:D91`: category / group name
  - Used to drive the Dashboard category list (`Dashboard!J6 = ArrayFormula(Configuration!D11:D91)`).

- `Configuration!G11:G66`: monthly TARGET amount
  - Surfaced on the Dashboard (`Dashboard!P6 = ArrayFormula(Configuration!G11:G66)`).

- `Configuration!K11:K66`: GOAL amount
  - Surfaced on the Dashboard (`Dashboard!Q6 = ArrayFormula(Configuration!K11:K66)`).
  - Many rows compute an annual goal as 12×monthly target (e.g. `Configuration!K16 = G16 * 12`).

Due-date / reminder column

- Header label exists at `Configuration!H10` (“DUE DATE”).
- The Dashboard appears to treat due-date/amount fields as reminders/notes rather than calculation inputs.

## Emergency fund inclusion + 6-month emergency fund target

Aspire includes a dedicated emergency fund calculation based on selected categories’ monthly targets.

Emergency fund flag column

- `Configuration!L10` header contains `"✓ ✕"`.
- Flag cells: `Configuration!L11:L66` contain ✓/✕.
- The valid options come from:
  - `EmergencyFundCalc` (`BackendData!T2:T3`), which contains ✕ and ✓.

Emergency fund target

- Label: `Configuration!K4` (“6-month Emergency Fund”)
- Formula: `Configuration!K5 = ROUND((SUMIF(L11:L66, BackendData!T3, G11:G66)) * 6, 3)`

Interpretation:

- A category is included when its flag equals ✓ (`BackendData!T3`).
- The target equals 6 × the sum of monthly TARGET amounts (`Configuration!G11:G66`) for included categories.

## Net worth categories (snapshot-driven)

Net worth categories are configured separately from budget accounts.

- Section header: `Configuration!P28` (“Net Worth Categories”)
- User lists:
  - `Configuration!P30:P37`: asset categories
  - `Configuration!Q30:Q37`: debt categories

Derived lists on `BackendData`:

- `NetWorthAssets` (`BackendData!AD2:AD9`)
- `NetWorthDebts` (`BackendData!AE2:AE9`)
- `NetWorthCategories` (`BackendData!AC2:AC17`) combines both

Net worth reporting uses the snapshot log (`ntw_*`), not ledger transactions; see `docs/aspire/net-worth.md`.

## Hidden / retired categories

Aspire supports “hiding” categories by removing them from the main configuration table but keeping them addressable.

- Hidden categories list: `Configuration!P44:P70`
  - Instructional text at `Configuration!P41` indicates the intended workflow:
    - add a category name to the hidden list
    - remove it from the main categories list

The hidden categories list is exported into `HiddenCategories` (`BackendData!F2:F46`) and then included in the transaction CATEGORY dropdown (`TransactionCategories`).

Balance display for hidden categories

- `Configuration!Q43` label: “CATEGORY BALANCE”
- `Configuration!Q44:Q70` compute balances for each hidden category name in `P44:P70`.
  - These formulas include special handling when the hidden category name matches a credit card account (using `COUNTIF(CreditCardAccounts, P44)` and a reserve-style computation similar to the Dashboard credit card row logic).

This means hidden categories can still have meaningful balances (and can still be referenced by transactions), but they no longer appear in the main Dashboard category table.

## Hidden / retired accounts

Hidden accounts use a similar pattern.

- Hidden accounts list: `Configuration!P77:P91`
  - Instructional text at `Configuration!P74` indicates the intended workflow:
    - add an account name to the hidden list
    - remove it from the main accounts list

The hidden accounts list is exported into `HiddenAccounts` (`BackendData!L2:L16`) and included in:

- `TransactionAccounts` (`BackendData!M2:M46`): the transaction ACCOUNT dropdown list

Balance display for hidden accounts

- `Configuration!Q76` label: “ACCOUNT BALANCE”
- `Configuration!Q77:Q91` compute a balance per hidden account name:
  - `ROUND(SUMIF(trx_Accounts, P77, trx_Inflows) - SUMIF(trx_Accounts, P77, trx_Outflows), 3)`

Practical implication: hiding an account/category is closer to “retirement” than deletion. The entity is removed from the primary configuration UI but remains referenceable for historical data and reporting.
