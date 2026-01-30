# Aspire -> Dojo Migration: Domain Mapping Spec

## Background

Dojo models personal finance as two coupled domains:

- Ledger (accounts + transactions): the source of truth for cash movement and balances.
- Budgeting (envelopes + allocations): the plan for assigning cash to purposes.

Aspire exports typically contain all of the following conceptually (regardless of storage format):

- Budget structure: category groups and categories (envelopes).
- Allocation history: moves from "Ready-to-Assign" and/or between categories.
- Transaction ledger: dated inflow/outflow events against an account and category.
- Net worth snapshots: point-in-time balances for "net worth entities" (assets/liabilities), which may:
  - duplicate on-budget accounts already represented by ledger transactions,
  - represent tracking-only assets/liabilities with no transaction history,
  - represent aggregates (one entity standing for multiple real-world accounts).

This spec defines how those source domains map into Dojo entities and how to keep the import correct, idempotent, and future-proof (XLSX, GSheets, etc.).

Primary goals

- Correctness first: balances, category states, and net worth should reconcile by construction.
- No double counting: never let a single real-world balance contribute twice (ledger + snapshot).
- Allow "investment cutover": preserve historical net worth without requiring historical holdings entry.
- Preserve history for deprecated/renamed entities via soft-retirement (no destructive deletes).
- Idempotent imports: retries should not duplicate or drift state.

Key Dojo entity semantics (import-relevant)

- Money amounts are stored as integers in minor units (e.g., cents). No floats in persistence.
- Transactions are temporal/SCD2 by `concept_id` (UUID): re-import updates the same concept.
- Budget allocations are also temporal/SCD2 by `concept_id`.
- Accounts have:
  - `account_type`: asset | liability
  - `account_class`: cash | credit | loan | investment | accessible (and potentially others)
  - `account_role`: on_budget | tracking
  - lifecycle: active vs retired ("soft retirement")
- System categories exist to express bookkeeping events (names here are Dojo concepts, not Aspire-specific):
  - Ready-to-Assign (the envelope representing unallocated cash)
  - Account Transfer (neutral category used for transfers)
  - Opening Balance / Balance Adjustment (system categories for balance reconstruction)

Soft-retirement policy (domain requirement)

- "Soft-retired" accounts/categories must:
  - remain addressable by historical transactions/allocations (history never breaks),
  - not be selectable for new data entry by default,
  - remain included in historical reporting (especially net worth history) for the dates they were relevant.

Implementation note: if Dojo filters inactive entities out of historical reporting today, the importer must either (a) keep soft-retired entities visible-but-marked, or (b) evolve reporting queries to include historical-but-retired entities. This spec requires the behavior; the mechanism is flexible.

## Flow: sync workbook > onboard budgets > onboard accounts > sync category allocations > sync transactions > net worth (sync + account mapping)

### 1) Sync workbook (source dataset ingestion)

Treat Aspire as a source system providing a set of typed records. The importer must:

- Compute a dataset fingerprint (stable identifier for this exact export) for idempotency.
- Build a source catalog:
  - distinct category labels (including historical/deprecated ones),
  - distinct account labels (including historical/deprecated ones),
  - distinct net worth entity labels,
  - record counts and date ranges for allocations/transactions/snapshots.
- Establish a mapping layer from source labels -> Dojo IDs.
  - Allow multiple source labels to map to one Dojo entity (renames/aliases) only with explicit user confirmation.
- Enforce privacy boundaries:
  - never log raw source values,
  - do not encode raw values into identifiers.

Output: a complete set of source labels and required mappings, plus a stable dataset fingerprint.

### 2) Onboard budgets (Dojo budget groups + categories)

Domain mapping

- Source "categories" -> Dojo `budget_categories`.
- Source "category groups" -> Dojo `budget_category_groups`.

Rules

- Create Dojo categories for every budget (active or retired) in aspire 
  - This includes categories that are now hidden/renamed/deprecated in Aspire.
- Categories used only historically should be imported as soft-retired by default.
  - They must still resolve for historical transactions and allocation history.
- System categories:
  - Ready-to-Assign and other Dojo system categories should not be created from source labels.
  - If the source uses an "Available/Ready" category label, map it to Dojo's Ready-to-Assign category instead of creating a user envelope.

Output: a complete Dojo category set sufficient to import allocations and transactions without missing references.

### 3) Onboard accounts (Dojo accounts)

Domain mapping

- Source aspire "accounts" -> Dojo accounts with `account_role='on_budget'` by default.
- Additional accounts may be created later during Net Worth mapping (tracking accounts and handoff accounts).

Rules

- Create Dojo accounts for every account label referenced in aspire 
  - Accounts that are only historical (closed/renamed/deprecated) should be soft-retired by default.
- Account classification is semantic, not cosmetic:
  - cash/checking/savings -> `asset/cash/on_budget`
  - credit cards -> `liability/credit/on_budget`
  - loans/mortgage liabilities -> typically `liability/loan/tracking` (often created in Net Worth step, unless transactions explicitly target the loan account)
  - investments -> typically `asset/investment/tracking` (often created in Net Worth step)

Output: a complete Dojo account set sufficient to import transactions without missing references.

### 4) Sync category allocations (Dojo budget allocations)

Domain mapping

- Source allocation event (date + amount + from-category + to-category) -> Dojo budget allocation concept.

Rules

- Allocation amounts are positive in Dojo; direction is carried by from/to.
- Aspire may encode Ready-to-Assign explicitly (e.g., `v_AtoB` / “Available to budget”) in the from-category column. Treat either (a) from-category == Ready-to-Assign label, or (b) missing/blank from-category, as “from Ready-to-Assign”.
- The importer must validate:
  - destination categories allow allocations,
  - source has sufficient available funds (unless the system explicitly permits overdraft semantics).
- Idempotency:
  - allocate with deterministic `concept_id` derived from (namespace + dataset fingerprint + stable source record id).
  - re-import updates/retire+replace the same SCD2 concept.

Output: Dojo monthly category states reflect the source allocation history.

### 5) Sync transactions (Dojo ledger transactions)

Domain mapping

- Source transaction event (date + amount + account + category + optional metadata) -> Dojo ledger transaction concept.

Rules

- Sign convention:
  - inflows are positive `amount_minor`
  - outflows are negative `amount_minor`
- Category mapping:
  - normal spending/income categories map to user/system envelopes.
  - system bookkeeping categories map to Dojo system categories (Account Transfer, Balance Adjustment, etc.).
- Transfers:
  - if the source provides enough information to identify both sides of a transfer, import as a Dojo transfer concept (two legs sharing one `concept_id`) using the Account Transfer category.
  - if not, import as a single ledger entry only when explicitly requested, since it can distort net worth by moving value without a counter-leg.
- Credit cards:
  - represent card purchases as transactions in the credit account with the spending category.
  - ensure Dojo's credit payment envelope exists and is adjusted according to Dojo's credit-reserve rules.
- Deprecated categories/accounts:
  - transactions may reference soft-retired entities; this is allowed.
  - soft-retirement means "no new entry by default" not "history disappears".
- Idempotency:
  - deterministic transaction `concept_id` from (namespace + dataset fingerprint + stable source record id).
  - re-import must update the same concept (SCD2) and reverse prior effects before applying the new version.

Output: Dojo ledger balances and budget activity reflect the source transaction history.

### 6) Net worth (sync + account mapping)

Net worth in Dojo is computed from account balances over time. Aspire net worth snapshots require an explicit per-entity mapping to avoid double counting and to enable investment cutover.

Domain mapping

- Source net worth entity (label) + snapshots (date -> balance) -> one of the treatments below.

Treatment A: derive from ledger (no snapshot import)

Use when the net worth entity is actually an on-budget account (cash, credit card, etc.) whose balance is fully determined by imported transactions.

- Map the source net worth entity to the corresponding Dojo on-budget account.
- Do not import its snapshots.
- Duplicate-reporting resolution: this is the default for entities that overlap with transaction-backed accounts.

Treatment B: tracking snapshot account (import snapshots)

Use when the entity is not represented by imported ledger flows (or you choose not to reconstruct flows).

- Create a Dojo tracking account (asset or liability) for the entity.
- Import snapshot history as Balance Adjustments that reconstruct the time series.
  - Prefer delta adjustments: for each date D, write an adjustment equal to snapshot(D) - snapshot(previous).
  - Use deterministic concept_ids per snapshot record.

Treatment C: handoff (placeholder) account for aggregates + cutover split

Use when one source net worth entity represents multiple real-world accounts (e.g., an aggregate "Investments" category) and you want:

- historical net worth contribution without historical holdings entry, and
- a clean handoff into real Dojo investment accounts for ongoing position/performance tracking.

Approach

- Create one Dojo investment tracking account as the handoff container.
- Import snapshots into the handoff account up to a cutover date.
- At cutover:
  - create one or more real Dojo investment accounts (the actual brokerages),
  - transfer the handoff balance into the destination accounts using Account Transfer semantics so budgets are unaffected,
  - after transfer, the handoff account should remain at 0 and be treated as historical-only.

Important: handoff accounts exist specifically to avoid double counting and to avoid forcing historical trades/positions.

Treatment D: loans/mortgages with payments + snapshots

Aspire often represents loans as both:

- transaction flows (monthly payments), and
- net worth snapshots (principal remaining).

In Dojo we want payments to reduce the loan balance over time and snapshots to reconcile drift.

Approach

- Create a Dojo loan tracking account for the liability.
- Map the payment-related transactions so that principal reduction affects the loan account balance (often via transfer-like semantics rather than a pure spending category).
- Use snapshots as periodic reconciliation:
  - at each snapshot date D compute correction = snapshot_balance(D) - ledger_balance_as_of(D)
  - record a Balance Adjustment of `correction`.

This preserves payment-driven amortization while letting snapshots correct for interest/escrow/rounding without reconstructing a full amortization schedule.

Duplicate reporting rules (net worth vs budget/ledger)

- A single real-world balance must live in exactly one place in Dojo at a time:
  - either it is ledger-derived (Treatment A),
  - or it is snapshot-derived in a tracking account (Treatment B),
  - or it is snapshot-derived in a handoff account until cutover, then ledger/holdings-derived in real accounts (Treatment C),
  - or it is loan ledger-driven with snapshot corrections (Treatment D).
- The importer must surface and block ambiguous mappings by default:
  - if a net worth entity could map to an existing Dojo account, require explicit confirmation before importing snapshots.
  - warn that importing both ledger transactions and snapshots for the same underlying balance will double count.

Soft-retirement in net worth

- Historical net worth entities that no longer exist in the current source config must still be represented so history is preserved.
- Default behavior:
  - create them (as tracking or handoff accounts as appropriate),
  - mark them soft-retired for UI/new-entry,
  - ensure historical net worth reporting still includes their balances for the relevant date range.

Output: Dojo net worth history matches the source intent without double counting, and investment/liability handoffs are possible without backfilling historical holdings.
