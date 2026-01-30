# Aspire -> Dojo Mapping

This document is the bridge between:

- Aspire’s sheet semantics (what the source means), and
- Dojo’s domain models (what we need to import / recreate).

It is intentionally evidence-driven and should be read alongside `docs/plans/aspire-migration-domain-spec.md`.

## References

- Dojo-side import requirements: `docs/plans/aspire-migration-domain-spec.md`
- Aspire-side source-of-truth semantics: `docs/aspire/*.md`

## Aspire source-of-truth inputs (named ranges)

- Accounts:
  - `cfg_Accounts` (bank accounts)
  - `cfg_Cards` (credit card accounts)
- Categories/groups/goals:
  - `r_ConfigurationData` (Configuration table)
  - marker symbols: `v_CategoryGroupSymbol`, `v_ReportableCategorySymbol`, `v_NonReportableCategorySymbol`, `v_DebtAccountSymbol`
- Transactions ledger:
  - `trx_*`
- Allocation event log:
  - `cts_*`
- Net worth snapshot log:
  - `ntw_*`

## Mapping to Dojo (high-level)

Accounts

- `cfg_Accounts` entries map to Dojo on-budget asset accounts (typically `asset/cash/on_budget`).
- `cfg_Cards` entries map to Dojo on-budget credit accounts (`liability/credit/on_budget`).

Categories and groups

- `r_ConfigurationData` group rows (type symbol `v_CategoryGroupSymbol`) map to Dojo budget category groups.
- Category rows map to Dojo budget categories (envelopes).
- Debt-account rows (type symbol `v_DebtAccountSymbol`) require special handling:
  - In Aspire they behave like a budget-layer representation of a liability/payment target.
  - In Dojo they likely map to credit payment categories / reserve handling (see Dojo budgeting rules).

Ready-to-Assign

- Aspire’s `v_AtoB` (“Available to budget”) is the semantic equivalent of Dojo’s Ready-to-Assign system category.

Transactions

- Convert OUTFLOW/INFLOW into Dojo’s signed amount.
- Map CATEGORY labels into Dojo budget categories, with special labels treated as system categories:
  - “Account Transfer” (`v_AccountTransfer`) -> Dojo Account Transfer
  - “Starting Balance” (`v_StartingBalance`) -> Dojo Opening Balance / Balance Adjustment
  - “Balance Adjustment” (`v_BalanceAdjustment`) -> Dojo Balance Adjustment
- Pair “Account Transfer” rows conservatively to create Dojo transfer concepts when possible.

Allocations

- `cts_*` rows map to Dojo budget allocation concepts.
- Aspire represents Ready-to-Assign explicitly via `v_AtoB` in FROM CATEGORY; the importer should treat FROM == `v_AtoB` as “from Ready-to-Assign”.
- Allocation amounts are positive; direction is encoded in FROM -> TO.

Net worth

- `ntw_*` rows map to Dojo net worth tracking accounts and snapshot imports.
- Amounts appear to be recorded as positive magnitudes (even for debts), so liabilities must be handled via explicit classification, not sign.

## Divergences and translation rules

Documented differences (so far):

- Aspire allocation rows appear to use explicit FROM CATEGORY values (often `v_AtoB`) instead of leaving FROM blank. Dojo’s importer should treat blank FROM as a fallback, not the primary encoding.

As new divergences are discovered, record:

- Aspire behavior
- Dojo current behavior
- Proposed Dojo change (if we want parity) vs importer translation rule (if we keep Dojo semantics)
