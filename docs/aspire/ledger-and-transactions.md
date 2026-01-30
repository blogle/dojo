# Aspire Ledger and Transactions

This document captures how Aspire represents transactions in the spreadsheet and the semantics required to import them into Dojo.

## Canonical source-of-truth transaction table

Aspire’s canonical transaction log lives on the sheet named `Transactions`.

- Header row observed at `Transactions!B8:H8`:
  - DATE
  - OUTFLOW
  - INFLOW
  - CATEGORY
  - ACCOUNT
  - MEMO
  - STATUS

The corresponding named ranges (one per column) are:

- `trx_Dates` (`'Transactions'!B9:B10291`)
- `trx_Outflows` (`'Transactions'!C9:C10291`)
- `trx_Inflows` (`'Transactions'!D9:D10291`)
- `trx_Categories` (`'Transactions'!E9:E10291`)
- `trx_Accounts` (`'Transactions'!F9:F10291`)
- `trx_Memos` (`'Transactions'!G9:G10291`)
- `trx_Statuses` (`'Transactions'!H9:H10291`)

See `docs/aspire/named-ranges.md` for the full inventory.

## Amount semantics

Aspire uses two separate amount columns:

- OUTFLOW: money leaving the account
- INFLOW: money entering the account

A single transaction row is typically “one-sided”: either OUTFLOW is filled or INFLOW is filled, but not both.

For migration into Dojo (which uses a single signed amount), a robust convention is:

- If OUTFLOW is present: `amount_minor = -outflow_minor`
- If INFLOW is present: `amount_minor = +inflow_minor`

## Category semantics (special labels)

Aspire treats categories as labels in the CATEGORY column.

There are several special category labels defined in `BackendData` and included in dropdown lists:

- “Available to budget” (named range `v_AtoB`): used as the CATEGORY label for most income inflows.
  - Evidence (aggregate only): rows categorized as Available-to-budget are overwhelmingly INFLOW-only.
- “Account Transfer” (named range `v_AccountTransfer`): used to represent transfers between accounts.
- “Balance Adjustment” (named range `v_BalanceAdjustment`): used to correct balances.
- “Starting Balance” (named range `v_StartingBalance`): used for opening balances.

These labels include emoji/symbol prefixes in the sheet; do not assume plain ASCII string equality when importing. For migration, treat these as *semantic tokens* and match on normalized text (e.g. strip leading symbols) or via an explicit mapping step.

## Transfers (account-to-account)

Aspire supports account-to-account movement in a way that the sheet’s balance math can recognize as “not spending”.

Explicit transfer category

- `v_AccountTransfer` (stored on `BackendData`) is a dedicated CATEGORY label for transfers.
- Reporting and rollups treat these as non-spending:
  - `Calculations!B64` (“spent this month”) explicitly excludes `trx_Categories == v_AccountTransfer`.
  - `Calculations` account reports break out transfers/payments separately (e.g. `Calculations!E238`, `Calculations!C247`).

Category==account adjustment (transfer-like rows)

Several account-balance and reconciliation computations treat rows where `trx_Categories` matches an account label as affecting that account’s balance.

Evidence:

- Account running balance includes both account-side cashflows and category==account adjustments:
  - `Calculations!G238 = SUMIFS(trx_Inflows, trx_Accounts, <acct>) - SUMIFS(trx_Outflows, trx_Accounts, <acct>) + SUMIFS(trx_Outflows, trx_Categories, <acct>) - SUMIFS(trx_Inflows, trx_Categories, <acct>)`
- Balances/reconciliation similarly use both `trx_Accounts` and `trx_Categories` when tallying inflows/outflows:
  - `Calculations!B207` / `B209` include terms like `SUMIFS(trx_Outflows, trx_Categories, Balances!$B3, ...)`.

Practical implication: when interpreting ledger data, Aspire’s own formulas allow for transfer-like effects to be expressed either via the explicit transfer category (`v_AccountTransfer`) and/or via category values that match account labels.

Note: a named range `trx_Uuids` exists but was malformed/empty in one export; do not assume a stable transfer id exists.

## STATUS column

Aspire uses a symbolic STATUS column (`trx_Statuses`). The sheet defines the symbol set in `BackendData`:

- `v_ApprovedSymbol`
- `v_PendingSymbol`
- `v_BreakSymbol`

These appear to be used for:

- cleared/approved transactions
- pending/uncleared transactions
- visual separators / grouping markers

Migration implication: Dojo should import these into a transaction status field (e.g. posted vs pending), but the mapping should be explicit and resilient to the exact symbol glyph.

## Reconciliation markers

Aspire appears to implement a lightweight “reconciliation cadence” signal using the STATUS column.

Evidence (Transactions sheet):

- “Accounts last reconciled on” is computed by scanning for rows where STATUS equals the break symbol (`v_BreakSymbol`) and taking the maximum DATE value among those rows.
  - In the observed sheet this is implemented at `Transactions!B5`:
    - `IFERROR(IF(MAX(FILTER(Transactions!B9:H, Transactions!H9:H = "*️⃣")) = 0, "Not reconciled", MAX(FILTER(Transactions!B9:H, Transactions!H9:H = "*️⃣"))), "Not reconciled")`
- The warning banner is driven off that last-reconciled date.
  - In the observed sheet this is implemented at `Transactions!B7`:
    - `IF(Transactions!B5 = "Not reconciled", "", IF(DAYS(v_Today, Transactions!B5) > 30, "You last reconciled your accounts over a month ago", IF(DAYS(v_Today, Transactions!B5) > 14, "You last reconciled your accounts " & DAYS(v_Today, Transactions!B5) & " days ago", "")))`

Practical implication: a row with STATUS == `v_BreakSymbol` is treated as a reconciliation marker (not a real transaction) and should be skipped or imported as a non-financial marker.

## Splits and other features

Splits

- No dedicated “split transaction” table, named range, or sheet was found in the exported structure.
- The transaction ledger schema exposed via `trx_*` has exactly one CATEGORY column (`trx_Categories`) and one ACCOUNT column (`trx_Accounts`).
  - Evidence: the `Transactions` header row is `DATE / OUTFLOW / INFLOW / CATEGORY / ACCOUNT / MEMO / STATUS` (see `Transactions!B8:H8` from `artifacts/.../20260130T011844Z/a1_ranges/formulas/Transactions_A1_K12.json`).

Working hypothesis (until contradictory evidence appears): if Aspire users “split” a real-world transaction across categories, they represent it as multiple ledger rows (same date/account/memo, different category and amounts).

Migration implication: treat each row as a transaction line item; avoid guessing grouping semantics unless you have a deterministic rule the sheet itself enforces.

## Migration relevance

Transactions are the backbone of the Dojo ledger import. The minimum safe importer should:

- read rows from the `trx_*` named ranges,
- compute a signed amount from OUTFLOW/INFLOW,
- treat “Available to budget” as Dojo’s Ready-to-Assign category,
- treat “Account Transfer” rows as transfer candidates and pair them conservatively,
- import STATUS into Dojo’s posted/pending semantics.
