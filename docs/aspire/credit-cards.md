# Aspire Credit Cards

This document captures Aspire’s credit card semantics.

## Observed structures

Credit card accounts

Aspire distinguishes “bank accounts” and “credit card accounts” in configuration:

- `cfg_Accounts` (`Configuration!P9:P24`): bank accounts
- `cfg_Cards` (`Configuration!Q9:Q24`): credit card accounts

Both are included in the derived account dropdown used by the transaction ledger (`TransactionAccounts`).

Debt-account rows in the category configuration

The main category configuration table (`r_ConfigurationData`, `Configuration!C11:K91`) includes a symbol/type column (C) that can mark “debt account” rows.

- Marker glyph: `v_DebtAccountSymbol` (defined on `BackendData`)

These debt-account rows are treated specially in derived lists:

- `CategoriesMinusCreditCards` filters out rows where `Configuration!C11:C91 == v_DebtAccountSymbol`.
- `TransactionCategories` uses `CategoriesMinusCreditCards`, implying that debt-account rows are excluded from the CATEGORY dropdown in the transaction ledger.

Interpretation: credit cards are represented as accounts in the ledger, while “debt account” rows likely represent the payment/reserve categories in the budget layer.

## Representation of purchases

Purchases on a credit card account are represented as ordinary transaction rows:

- ACCOUNT is the credit card account (must be present in `cfg_Cards` / `CreditCardAccounts`).
- CATEGORY is a normal spending category (not the debt-account/payment category).

This aligns with the dropdown behavior:

- Debt-account rows are excluded from `TransactionCategories` (via `CategoriesMinusCreditCards`), so they are not intended to be used as transaction categories.

## Representation of payments (bank -> credit card)

Aspire represents a credit card payment as an account-to-account transfer using the special CATEGORY label `v_AccountTransfer`.

In the observed sheet, these transfer rows follow a consistent pattern:

- The bank-side leg is OUTFLOW-only on a bank account.
- The credit-card-side leg is INFLOW-only on a credit card account.

Evidence (aggregate only, derived from `trx_*` ranges):

- Most `v_AccountTransfer` rows on bank accounts are outflows.
- Most `v_AccountTransfer` rows on credit card accounts are inflows.

This is also reflected in the reporting UI:

- `Account Reports` labels the transfer column as “Payments” (instead of “Transferred”) when the selected account is in `CreditCardAccounts`.

## Payment reserve / debt-category semantics (Dashboard)

Aspire’s dashboard treats credit card payment rows specially, based on name matching:

- Credit-card row detection: `COUNTIF(CreditCardAccounts, <row name>)` (not the debt marker symbol).

Available (running payment reserve)

For a credit-card row with name `X`, Dashboard column AVAILABLE (L) uses:

- `max(account_balance(X), 0)` where `account_balance` comes from `Calculations!A7:B37`
- plus net allocations to the payment category: `SUMIF(cts_ToCategories, X, cts_Amounts) - SUMIF(cts_FromCategories, X, cts_Amounts)`
- plus net card account cashflows over all time (purchases increase reserve, payments decrease):
  - `SUMIFS(trx_Outflows, trx_Accounts, X, trx_Categories <> v_BalanceAdjustment, trx_Categories <> v_StartingBalance)`
  - minus `SUMIFS(trx_Inflows, trx_Accounts, X, trx_Categories <> v_BalanceAdjustment)`

Activity (current month net change)

Dashboard column ACTIVITY (O) is month-filtered and separates transfer rows:

- `v_AccountTransfer` cashflows are included (on typical sheets, card-side transfers are inflows, so payments reduce activity)
- non-transfer cashflows exclude balance adjustments and starting balances

Overspending implication

- This payment-reserve formula does not check whether the spending category was “funded”; a credit card purchase contributes to the payment reserve even if the spending category goes negative.

## Open questions

- Confirm, via UI behavior, whether Aspire *intends* payment reserve to rise on overspent purchases (the formulas do).
- Determine whether Aspire ever allows debt-account symbol rows that do not match a name in `CreditCardAccounts` (would yield inconsistent dashboard behavior).
- Confirm whether any month-end normalization differs for credit categories vs normal categories.

## Migration relevance

Dojo has explicit credit payment reserve rules.

Correct migration requires either:

- matching Aspire’s behavior closely (if we want parity), or
- documenting an intentional divergence and translating Aspire history into Dojo’s reserve model.
