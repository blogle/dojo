# Aspire Domains and Entities

This document describes Aspire’s conceptual domains (what “things” exist) and the fields Aspire uses to represent them.

The goal is to define Aspire in terms of typed records that can be extracted from a spreadsheet (primarily via named ranges).

## Domains (observed)

- Configuration: user-configured lists and parameters that define how the sheet behaves.
- Budget structure: category groups, categories/envelopes, and flags (reportable/non-reportable).
- Accounts: on-budget bank accounts and credit card accounts.
- Ledger: a chronological transaction log.
- Allocations: explicit “move money between categories” events.
- Net worth tracking: explicit snapshot entries for assets and debts.
- Goals/targets: per-category targets defined in configuration.

## Entities (observed record shapes)

Account

Configured on the `Configuration` sheet:

- `cfg_Accounts` (`Configuration!P9:P24`): bank accounts.
- `cfg_Cards` (`Configuration!Q9:Q24`): credit card accounts.

Fields

- `name` (string label)
- `account_type` (implicit: bank vs credit card)

Identity semantics

- Name-based. No stable id column is used in the exported named ranges.

Lifecycle semantics

- Hidden accounts exist (derived from a “Hidden Accounts” section of the configuration sheet and surfaced via `HiddenAccounts` in `BackendData`).

Budget category / envelope

Configured in the `r_ConfigurationData` table (`Configuration!C11:K91`).

Fields (minimum)

- `type_symbol` (column C): distinguishes category group rows vs category rows and other special row types.
- `name` (column D): the category or group label.
- `amount` (column G): a per-category configured amount (used by budgeting/goal logic).
- `due_date` (column H): configured due date.
- `goal_amount` (column K): configured goal amount.

Category types are marked using symbols defined in `BackendData`:

- `v_CategoryGroupSymbol`
- `v_ReportableCategorySymbol`
- `v_NonReportableCategorySymbol`
- `v_DebtAccountSymbol`

Identity semantics

- Name-based. Categories are referenced elsewhere by their label string.

Lifecycle semantics

- Hidden categories exist (derived from a “Hidden Categories” section of the configuration sheet and surfaced via `HiddenCategories` in `BackendData`).

Transaction

Stored as a row in the `Transactions` sheet.

Fields (from header row `Transactions!B8:H8` and the `trx_*` named ranges)

- `date`
- `outflow` (money leaving the account)
- `inflow` (money entering the account)
- `category` (string label)
- `account` (string label)
- `memo` (string)
- `status` (symbol)

Identity semantics

- No stable UUID/id column observed in this sheet; a named range `trx_Uuids` exists but is malformed/empty in one export.
- Importers should not assume a stable row id exists; idempotency must be implemented via deterministic hashing of row content plus position/date.

Allocation event

Stored as a row in the `Category Allocation` sheet.

Fields (from header row `Category Allocation!B7:E7` and the `cts_*` named ranges)

- `date`
- `amount` (positive number)
- `from_category` (string label)
- `to_category` (string label)

Identity semantics

- Name-based. No stable id column observed.

Net worth snapshot entry

Stored as a row in the `Net Worth Reports` sheet.

Fields (from header row `Net Worth Reports!B19:F19` and the `ntw_*` named ranges)

- `date`
- `amount` (magnitude; sign is applied based on asset vs debt classification)
- `net_worth_category` (string label)
- `notes` (string)
- `breakpoint` (symbol)

Configuration for net worth categories is derived from the `Configuration` sheet and surfaced via:

- `NetWorthAssets` / `NetWorthDebts` / `NetWorthCategories` named ranges on `BackendData`.

Net worth categories vs budget accounts

- Budget accounts are used by the transaction ledger (`trx_*`).
- Net worth categories are used by the net worth snapshot log (`ntw_*`).
- Users commonly duplicate account names into net worth categories (sometimes with minor spelling/case differences), but the sheet does not automatically link these concepts.

See `docs/aspire/net-worth.md` for the full rollup/reporting semantics.

## Migration relevance

Aspire’s entity semantics need to map cleanly onto Dojo’s:

- Ledger domain (accounts + transactions)
- Budgeting domain (envelopes + allocations)
- Net worth (tracking accounts + snapshots)

See `docs/plans/aspire-migration-domain-spec.md` for Dojo-side requirements.
