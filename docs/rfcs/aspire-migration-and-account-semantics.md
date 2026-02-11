# RFC: Aspire Migration and Account Semantics in Dojo

Status: Draft

Last updated: 2026-02-04

## Why this exists

Dojo is a self-hosted personal finance app intended to replace a household spreadsheet workflow.
Aspire Budget is a popular Google Sheets template that combines envelope budgeting with a separate net worth tracking page.

This RFC defines:

- How we migrate Aspire data into Dojo without losing years of history.
- The accounting semantics Dojo should enforce moving forward so net worth is derived consistently.
- A lightweight reconciliation model for every account type (cash, credit, loans, investments, tangibles).
- The onboarding wizard flow and guardrails needed to keep the system trustworthy.

The goal is a migration and steady-state workflow that feels like Aspire (fast, practical, low-friction), but with:

- a single ledger as the source of truth for cashflow and principal movement,
- explicit measurement/reconciliation commits,
- SCD2 versioning for auditability,
- and "dummy fast" reporting.

## Audience

Readers should assume no prior knowledge of Aspire or Dojo.

Primary audiences:

- Dojo maintainers implementing the migration + semantics.
- Reviewers providing design feedback (correctness, UX, risk).

## Review prompts (what we want outside eyes to challenge)

- Does the split between ledger events (cashflows) and measurement events (reconciliations/valuations) make sense?
- Are there any double-counting paths left open?
- Is the investment valuation rule both correct and simple enough to keep users out of trouble?
- Are loans/mortgages delivering real value beyond Aspire-style "tracking marks" without forcing tedious data entry?
- Is the onboarding wizard minimal in choices and resilient to user drop-off?

## Glossary

- Ledger event: a transaction that represents money movement between accounts or between an account and the outside world.
- Measurement event: a statement/appraisal/reconcile that asserts the current state of an account (balance, positions, fair value).
- Mark: Aspire's net worth snapshot record (`ntw_*` log). A mark is stored with a date and amount.
- Bucket semantics (Aspire): net worth history is computed by summing marks that occurred in a month bucket; missing mark => 0 contribution.
- As-of semantics (Dojo): a value at time t is the latest known state at or before t (carry-forward).
- Duplicate net worth entity: a net worth category in Aspire that corresponds to a transaction-backed account (e.g. "Checking").
- Cutover: the moment we stop using Aspire legacy tracking for an entity and begin tracking it with Dojo's richer model.

## Background: how Aspire works

Aspire Budget is a Google Sheet with three distinct "domains" of data:

1) Transaction ledger (accounts + spending categories)

- Stored as rows on the `Transactions` sheet.
- Accessed via named ranges:
  - `trx_Dates`, `trx_Outflows`, `trx_Inflows`, `trx_Categories`, `trx_Accounts`, `trx_Memos`, `trx_Statuses`.
- These rows drive account balances and budget activity.

2) Envelope budgeting (allocations between categories)

- Stored as rows on the `Category Allocation` sheet.
- Accessed via named ranges: `cts_Dates`, `cts_Amounts`, `cts_FromCategories`, `cts_ToCategories`.
- These rows drive category "available" amounts.

3) Net worth tracking (explicit snapshot log)

- Stored as rows on the `Net Worth Reports` sheet.
- Accessed via named ranges:
  - `ntw_Dates`, `ntw_Amounts`, `ntw_Categories`, `ntw_Notes`, `ntw_Breakpoints`.
- Crucially: Aspire's net worth is NOT derived from the ledger. It is derived entirely from the net worth marks.

Configuration and special labels are also derived from named ranges:

- `cfg_Accounts`, `cfg_Cards`: account lists.
- `HiddenAccounts`, `HiddenCategories`: retired entities.
- `NetWorthAssets`, `NetWorthDebts`, `NetWorthCategories`: net worth category lists and their sign convention.
- `v_AccountTransfer`, `v_StartingBalance`, `v_BalanceAdjustment`, `v_AtoB`: special labels used in formulas.
- `v_Today`: today's date (used for "current month" reporting).

How these map into Dojo during migration:

- Aspire provides these as user-visible label strings; Dojo maps them to fixed Dojo system category ids.
- We do not import these as user categories.

| Aspire named value | Meaning in Aspire | Dojo system category id | Dojo meaning |
| --- | --- | --- | --- |
| `v_AccountTransfer` | transfer marker category | `account_transfer` | used for the destination leg of account-to-account transfers |
| `v_StartingBalance` | starting balance marker | `opening_balance` | initializes an account at an as-of date (explicit non-cashflow event) |
| `v_BalanceAdjustment` | adjustment marker | `balance_adjustment` | explicit correction to align Dojo to an external statement |
| `v_AtoB` | "Available to budget" | `available_to_budget` | Dojo's ready-to-assign / unallocated cash bucket |

Implementation note: Dojo marks system categories with `is_system=TRUE` and excludes them from envelope activity tracking.

### Aspire net worth formulas (high level)

Aspire uses `NetWorthAssets` vs `NetWorthDebts` to assign sign:

- `ntw_Amounts` are magnitudes.
- if `category in NetWorthAssets`: contribution is `+amount`.
- else (debt): contribution is `-amount`.

For history, Aspire computes month buckets and sums marks in each bucket:

- For a month row with end boundary `C_next` and previous boundary `C_prev`:
  - Asset category c: `SUMIFS(ntw_Amounts, ntw_Categories=c, ntw_Dates> C_prev, ntw_Dates<=C_next)`
  - Debt category c: `-1 * SUMIFS(...)`

Implications:

- If a category has no mark within a bucket, it contributes 0.
- If a category has multiple marks within a bucket, they sum.
- Exact string matching is used; emojis/case/spelling differences create distinct categories.

Important nuance (Aspire parity):

- Aspire's displayed net worth totals are driven by the exported `NetWorthAssets` and `NetWorthDebts` category lists.
- Marks whose category is not present in those lists are effectively inert in the standard net worth report until the user adds that category to the appropriate list.
- Aspire also includes presentation markers (`ntw_Breakpoints`) that do not affect totals.

### The migration complication Aspire creates

Aspire often has a dual reporting structure:

- The same real-world account appears in the ledger (as a transaction account) AND in net worth categories (as a mark-driven "tracking account").
- Example: "Checking" as a budget account and "Checking" as a net worth category.

If we import both naively, we double count.

## Background: how Dojo works today

Dojo is a FastAPI + DuckDB application with a SPA frontend.

Core design choices:

- Immutable temporal ledger: `transactions` are SCD2 by `concept_id`.
  - `transaction_version_id` identifies a specific version row.
  - `concept_id` identifies the conceptual event across edits (and can also link multiple legs, e.g. transfers).
  - Updating a transaction closes the prior active version(s) for that `concept_id` and inserts new row(s).
- Account balances are derived from the ledger and cached in `accounts.current_balance_minor` for speed.
- Account types/classes model semantics:
  - `account_type`: `asset` | `liability`
  - `account_class` (current): `cash`, `credit`, `loan`, `investment`, `tangible`, `accessible`
  - `account_role`: `on_budget` | `tracking`
    - `on_budget` accounts participate in envelope budgeting (contribute to ready-to-assign and category availability).
    - `tracking` accounts are excluded from envelope math but still contribute to net worth.
    - Common combinations: cash+on_budget, credit+on_budget, loan+tracking, investment+tracking, tangible+tracking.
    - Other combinations can be supported, but only when they have a clear user-facing meaning.
      - Example: cash+tracking for "off-budget" savings that should not affect ready-to-assign.
      - Non-example: investment+on_budget is usually confusing because its value is not a spendable cash balance.
- Reconciliation checkpoints exist via `account_reconciliations`.

Current net worth computation:

- Cash/credit/loan balances come from ledger-derived account balances.
- Investments use positions + market prices (with a "ledger fallback until reconcile" heuristic).
- Tangibles use fair value stored on tangible assets.

Important reality:

- Dojo is moving toward "net worth derived from the ledger + measurement commits" as the primary reporting model.
- Aspire net worth marks are a measurement log from a different worldview (bucketed marks, not ledger-derived).

## Goals

Migration goals:

- Preserve years of net worth history from Aspire without data loss.
- Eliminate double counting by mapping duplicates to the ledger.
- Keep onboarding decisions minimal; default the right thing wherever possible.
- Keep the migration resumable and privacy-safe.

Steady-state goals:

- Trustworthy net worth: assets - liabilities derived from consistent semantics.
- Lightweight reconciliation: weekly/monthly, not "tax prep".
- Investments: support holdings, valuation, and performance without forcing full historical reconstruction.
- Loans/mortgages: enable payoff/interest planning with minimal data entry.

Performance goal:

- Reporting should remain "dummy fast" (DuckDB queries + caches; avoid per-request Python loops over ledger rows).

## Principles and invariants (non-negotiable)

These are the rules that keep the system correct and trustworthy.

1) No double counting

- A single real-world balance must not contribute to net worth twice.
- If an account is transaction-backed, its net worth value comes from the ledger (not a parallel snapshot stream).

2) No fabricated money to force continuity

- Dojo must not synthesize cash balances, prices, or ledger transactions to "make the numbers line up".
- If two sources disagree (Aspire marks vs ledger vs statement), we record and surface drift explicitly.

3) Transfers are net worth neutral

- Moving money between two internal accounts must not change net worth.
- This invariant must hold even when one side is an investment account with reconciled holdings.

Transfer pairing invariant:

- A transfer is represented as two ledger legs that share one conceptual identifier.
- The system must prevent "orphan legs" (one side without its counter-leg) from reaching the committed ledger.
  Orphans break net worth neutrality and reconciliation.
- Migration pairing rule (Aspire): auto-pair only when deterministic.
  - Default heuristic: same absolute amount, different accounts, and within a small date tolerance window (start with +/- 3 days).
  - If a leg cannot be paired deterministically, it becomes a transfer exception that must be explicitly resolved before apply:
    - link exactly two exception legs as one transfer concept (with undo), or
    - map the orphan leg to a system correction category (`opening_balance` or `balance_adjustment`).

Marker-row guardrail:

- Aspire reconciliation break rows (`v_BreakSymbol`) are non-financial markers and must never appear as transfer exceptions.

4) History must include retired/inactive entities (as-of correct)

- Aspire relies on "hidden/retired" entities remaining present historically.
- Dojo must treat "inactive/retired" as "not selectable for new entry by default", not "deleted".
- Current-state views may filter `is_active = TRUE`.
- Historical reports (including historical net worth) must be computed as-of the reporting date and must not drop entities merely because they are currently inactive.
- Any API/query that returns historical values must have an explicit include-retired/include-inactive behavior.

5) Investment ledger purity

- For investment accounts, the ledger should only reflect deposits/withdrawals (cashflows across accounts).
- Trades/dividends/interest must never be represented as ledger transactions.
- The system should enforce this with validation (block or require explicit "break glass" override) because violating it can double count.

6) Privacy and safety

- Never log raw user financial values.
- Never write OAuth tokens to disk/DB.
- Staging tables may contain PII; they must be scoped to a migration session and cleaned up on completion.

## Non-goals

- Reconstructing historical investment trades or lot-level history from Aspire (information does not exist).
- Backfilling historical mortgage principal/interest/escrow splits with fabricated precision.
- Perfect daily net worth accuracy for investments without reconciliation (we choose correctness + guardrails over heuristics).

## Core proposal: two event types, one net worth equation

We keep a single net worth equation, but we do not force every state change into the ledger.

- Ledger is for cashflow/principal movement.
- Measurement commits are for "state as observed" (statements/appraisals/holdings snapshots).

Net worth at time t:

```
NetWorth(t) =
  SumSignedLedgerBalances(t)
  + SumInvestmentNAV_Signed(t)
  + SumTangibleFairValues_Signed(t)
```

Sign convention:

- Asset values are positive.
- Liability values are negative.
- All balances and valuations are stored and computed as signed values in minor units.

Definitions:

- `SumSignedLedgerBalances(t)` is the sum of ledger-derived balances for all non-investment, non-tangible accounts.
  Those balances are already signed by `account_type`.
- `SumInvestmentNAV_Signed(t)` is the sum of investment account net asset values (NAV), with explicit semantics defined below.
- `SumTangibleFairValues_Signed(t)` is the sum of tangible fair values.

This equation is intentionally explicit about sources:

- Ledger events represent cashflow/principal movement.
- Measurement commits represent observed state (statements, holdings, appraisals).

We never compute net worth by summing two sources for the same real-world balance.

### Cash and credit accounts

Value source:

- Ledger only.

Reconciliation:

- Inputs: statement date + statement ending balance.
  - By default, "statement balance" means the posted/cleared balance (not the bank's "available" balance).
- Dojo tracks transaction status (`pending` vs `cleared`).
  - The reconciliation worksheet is driven by this status and SCD2 changes since the last commit.
  - Completion condition: sum of cleared transactions (as-of the statement date) matches the statement balance.
- Pending transactions are excluded from the reconcile target by default.

Net worth and pending:

- Dojo should provide two net worth views:
  - Default: "cleared-only" (statement-comparable), which excludes pending items.
  - Optional: "working" (includes pending), which is useful for forward-looking cashflow but can differ from statements.

### Tangibles

Value source:

- Measurement only (appraisals / fair value updates).

Ledger interaction:

- None, except when the asset is bought/sold (cash ledger events) and the tangible is retired/valued down.

### Loans/mortgages

Value source:

- The loan's contribution to net worth is the signed liability balance (negative), representing principal remaining.

Migration constraint:

- Aspire usually does not provide principal/interest splits.

Two supported tracking modes

Mode A: Statement principal (Aspire-style, recommended default)

- Record the mortgage payment as a single cash outflow in the ledger (like Aspire), categorized to the mortgage budget category.
- Periodically (recommended monthly), the user enters the statement principal balance and statement date.
  - Dojo records a measurement commit and updates the loan principal balance to match the statement.
- This mode does not require per-payment splits.

Timing disclosure:

- Between principal checkpoints, the liability balance will not necessarily move on payment dates.
  Cash decreases when the payment is recorded; principal decreases when the user records the statement principal.
  Over a full statement period this converges to the correct net worth change (interest/fees), but daily changes can look "lumpy".

Guardrail:

- In Mode A, Dojo should disallow ordinary ledger postings to the loan account itself (except `opening_balance` / `balance_adjustment`).
  This prevents double counting principal changes.

Mode B: Split payments (advanced, optional)

- The user records a payment with an explicit split into:
  - principal (modeled as a transfer to the loan, reducing the liability),
  - interest and escrow/fees (modeled as expenses),
  using statement-provided breakdowns.
- Principal then changes on payment dates, which makes daily net worth timing more intuitive.
- Periodic principal reconcile is still used as a checkpoint and to surface drift.

Optional linkage for UX/analytics (applies to both modes)

- Allow a user to link a loan to:
  - one or more payment source accounts (cash accounts), and
  - one or more payment categories (e.g., "Mortgage").
- This linkage does not change accounting, but the loan detail page can show related payments and compute estimated breakdowns.

What this enables (without backfill):

- Payoff and interest-savings planning from:
  - original principal
  - loan start date
  - loan term
  - interest rate
  - current principal (at cutover and then via periodic reconcile)

Optional enhancements (explicitly labeled):

- Infer principal paid over a period as the change in reconciled principal.
- Infer "interest+escrow" as payment total minus inferred principal.
- These inferences should be presented as estimates unless the user provides statement breakdown numbers.

### Investments (brokerage/401k)

Investment accounts require both:

- ledger cashflows (transfers in/out)
- internal statement state (positions + statement cash)

We must guarantee a critical invariant:

- Account-to-account transfers must not change net worth, even if the investment account has been reconciled.

#### Proposed investment valuation rule (post-reconcile)

At each investment reconcile commit at time t0:

- store the statement cash (uninvested cash) `cash_stmt(t0)`
- store positions snapshot for holdings
- store a baseline ledger balance `ledger_baseline(t0)` equal to the investment account's ledger-derived balance as-of t0

Persistence requirement:

- `ledger_baseline(t0)` is a persisted field of the reconcile commit (not a derived value recomputed later),
  so historical NAV remains stable and auditable.

Then for any later time t:

```
ledger_delta(t) = cleared_ledger_balance(t) - cleared_ledger_balance(t0)
cash_derived(t) = cash_stmt(t0) + ledger_delta(t)
NAV(t) = holdings_value(t) + cash_derived(t)
```

Notes:

- `holdings_value(t)` is the mark-to-market value of positions only (it excludes cash).
- `cash_stmt(t0)` and `cash_derived(t)` represent uninvested cash in the brokerage account.
- Trades/dividends/interest MUST NOT hit the ledger. They are internal account activity and are reflected only when the user reconciles positions/cash.
- Transfers in/out DO hit the ledger and are incorporated via `ledger_delta(t)` so net worth remains transfer-neutral.
- For investment accounts, the ledger should only reflect deposits/withdrawals (cashflows across accounts), not internal brokerage activity.
- If holdings are stale (no reconcile), NAV will be stale; UI must surface this.

Drift at reconcile (no fabricated money):

- Each investment reconcile commit must record an explicit drift value that explains any mismatch between:
  - statement NAV (statement cash + statement holdings valued by the chosen price source/date), and
  - Dojo-computed NAV under the same valuation inputs.
- Drift is surfaced to the user as pricing/rounding drift; it is never "plugged" by inventing cash or fake transactions.

Ledger purity enforcement:

- For investment accounts, restrict ledger categories to system bookkeeping categories and transfers.
  Any attempt to record a dividend, trade, or internal activity as a ledger transaction should be blocked (or require an explicit override).

#### Price precision: do not impute cash to "make it match"

Dojo should never fabricate cash balances (or other money fields) to force continuity.

If a reconcile snapshot cannot match an external value exactly due to rounding/precision:

- record the difference explicitly as drift, or
- increase precision of price storage so that rounding drift is minimized.

Concrete requirements:

- Persist prices at a precision higher than cents (e.g., 1/10,000 USD or finer) and specify the rounding rule used when converting to minor units.
- Persist position quantities at a fixed decimal precision (do not store as binary floating point).
- Define where rounding is permitted:
  - internal valuation math may use high-precision decimals,
  - rounding to minor units happens only at explicit boundaries (storage/output),
  - drift is recorded when it appears.

Notes on data sources and reconciliation:

- Yahoo Finance (via `yfinance`) returns prices as floating point numbers. Many instruments are effectively 2 decimal places, but some have more.
- Storing at higher precision is still beneficial even when the upstream feed is 2 decimals:
  - it prevents downstream rounding from forcing us to invent cash,
  - and it gives room for sources that provide finer precision.
- Reconciliation UX should not require the computed NAV to match a brokerage's "right now" NAV if Dojo is valuing using an end-of-day close.
  - Users reconcile positions + statement cash; NAV differences caused by price timing are surfaced as pricing drift.
  - Provide an "Update prices" action and display the price date used for valuation.

## Migration plan

### High-level approach

We split migration into:

1) Import Aspire's budgeting ledger (accounts, categories, allocations, transactions) into Dojo's ledger/budget.
2) Import Aspire's net worth marks into a legacy measurement log for reporting.
3) Resolve duplicate net worth entities by mapping them to ledger accounts (no snapshot-driven duplication).
4) For assets/liabilities tracked forward with Dojo's richer model, perform an explicit cutover.

### What data we ingest from Aspire

From named ranges (canonical):

- Ledger: `trx_*` (transactions), including `trx_Statuses`
- Budget allocations: `cts_*` (allocations)
- Net worth marks: `ntw_*` (net worth snapshots)

From configuration lists:

- Account lists: `cfg_Accounts`, `cfg_Cards`
- Retired lists: `HiddenAccounts`, `HiddenCategories`
- Net worth classification: `NetWorthAssets`, `NetWorthDebts`, `NetWorthCategories`
- Special labels: `v_AccountTransfer`, `v_StartingBalance`, `v_BalanceAdjustment`, `v_AtoB`, and (recommended) `v_Today`
- Status symbols (Aspire templates): `v_ApprovedSymbol`, `v_PendingSymbol`, `v_BreakSymbol`

Important observed edge case:

- `ntw_Categories` values can include categories not currently present in `NetWorthCategories` (historical categories).
- Therefore, the importer must treat `DISTINCT ntw_Categories` as first-class input, not only the config lists.

### Statuses and marker rows (Aspire -> Dojo)

Aspire's STATUS column (`trx_Statuses`) typically includes:

- an "approved/cleared" symbol,
- a "pending" symbol,
- and a "break" symbol (`v_BreakSymbol`) used as a reconciliation cadence marker (not a financial transaction).

Import rules:

- approved/cleared -> Dojo `cleared`
- pending -> Dojo `pending`
- break rows must not be imported as money movement.
  - They may be imported as a marker/metadata record (or ignored), but must not affect balances, budgets, or net worth.

Net worth breakpoints (`ntw_Breakpoints`) are presentation markers in Aspire's net worth log.
They are preserved as metadata on the legacy marks stream and do not affect totals.

### Duplicate detection and mapping (Aspire -> Dojo)

Goal: prevent double counting by defaulting duplicates to ledger-derived value, while preserving marks as audit checkpoints.

Normalization and matching:

- Normalization is used only to propose matches (e.g., strip emoji/punctuation/extra whitespace; case-fold).
- Exact normalized matching is the first pass.
- If there is no exact match, Dojo may offer fuzzy suggestions (e.g., edit distance / token similarity) but must require explicit user confirmation.
- If multiple source labels normalize to the same key (a collision), Dojo must not auto-map; it must ask the user.

Default treatment for duplicates:

- Aspire marks are preserved verbatim in the legacy marks log and always power the Aspire-parity (bucket) view.
- For Dojo's derived net worth (ledger + measurement commits), duplicates contribute via the ledger-backed account only.
  Duplicate marks remain visible as checkpoints for drift validation but are not summed into Dojo-derived totals.

Trust UX requirements:

- Every proposed mapping must show:
  - the proposed match (what),
  - the reason (why this looks like the same thing),
  - a preview comparing marks vs ledger balances over an overlap window,
  - and an escape hatch to override.

Drift framing:

- Expected differences:
  - Aspire bucketed marks vs Dojo as-of semantics.
  - Date-only ordering limits (a mark recorded on the same date as a large inflow/outflow may differ depending on timing).
- Actionable drift:
  - mismatches beyond a configured date window (e.g., +/- 3 days) and amount tolerance,
  - which likely indicate missing transfers, missing transactions, or misclassification.

### Legacy net worth history

We preserve Aspire's net worth history verbatim as a "legacy marks" time series.

Key point:

- We do NOT reconstruct a ledger history from marks (no backfilled `balance_adjustment` transactions).
- We store the raw mark log (date, category, amount, note) and derive views from it.

Derived views:

- Aspire-parity view (bucket semantics): compute the same monthly buckets Aspire computes (missing mark => 0).
- Dojo convenience view (as-of semantics): carry-forward the latest mark as-of a date to support as-of charts.

Sign and inclusion rules:

- Aspire-parity totals use the exported `NetWorthAssets` / `NetWorthDebts` lists to assign sign and to determine which categories are included.
- Marks for categories not present in those lists are still preserved in the raw marks log, but they do not affect Aspire-parity totals until classified.

Both views are derived from the same raw marks and clearly labeled in the UI so users understand the semantic difference.

Rationale:

- Backfilling ledger events from marks is underdetermined and introduces fabricated accounting.
- The legacy marks log matches Aspire exactly and preserves user trust.

### Cutover to Dojo-native tracking

For each non-duplicate net worth entity, the user chooses one of:

- Legacy only: keep marks for history; do not create a live Dojo account.
- Track forward: create one or more Dojo accounts of the appropriate class and reconcile them starting at cutover.

Cutover asks for minimal statement data:

- A cutover date (default: the day the user runs migration; user can edit).
- The external "as-of" balance/value.
- Account-class-specific metadata (see account type sections below).

One Aspire entity -> multiple Dojo accounts (split cutover):

- Aspire often tracks aggregates (e.g., one "Retirement" line representing multiple 401k/IRA accounts).
- Dojo should support mapping a single Aspire entity into multiple destination accounts at cutover.
  - The user provides destination accounts and starting values.
  - The sum of destination starting values should equal the cutover as-of value.
  - Any mismatch is recorded and surfaced as drift (not hidden by fabricating cash).

What gets recorded at cutover:

- Cutover creates an explicit measurement commit for the new Dojo account(s).
- Whether a ledger entry exists depends on account type:
  - Loan principal: initialized via a system-category opening balance (explicitly non-cashflow).
  - Investments: initialized via a holdings + statement-cash reconcile commit plus a ledger baseline; the investment ledger then tracks only deposits/withdrawals after cutover.
  - Tangibles: initialized via a valuation record (no ledger cashflow is implied).

Any difference between:

- last Aspire mark (legacy series)
- and cutover statement value

is recorded and surfaced as drift.

Do not hide drift by fabricating cash/transactions.

## Evidence from real data (sanity checks)

We ran these validations on an extracted Aspire dataset staged in DuckDB.

1) Aspire parity from marks

- Computing monthly net worth buckets from `ntw_*` marks reproduces Aspire's net worth history exactly.

2) Hybrid substitution for duplicates

We identified duplicate net worth entities by "same name sans emoji" (e.g., `Checking` vs `[emoji] Checking`) and replaced the net worth marks for those entities with ledger-derived balances.

We tested two substitution semantics:

- Mark-date substitution (Aspire-aligned): use the ledger balance as-of the mark date in that month bucket.
- Month-end substitution (Dojo-aligned): use the ledger balance as-of the month end boundary.

Results (sample dataset):

- Mark-date substitution:
  - 2019-11-30: Aspire $56,597.75 -> Hybrid $56,179.36 (diff -$418.39)
  - 2026-01-31: Aspire $3,586,110.71 -> Hybrid $3,595,811.22 (diff +$9,700.51)
  - For months where the ledger exists (2021-01..2026-01):
    - median absolute diff: $2,583.01
    - p90 absolute diff: $9,652.95
    - max absolute diff: $53,044.58

- Month-end substitution:
  - For months where the ledger exists (2021-01..2026-01):
    - median absolute diff: $7,305.92
    - p90 absolute diff: $38,471.05
    - max absolute diff: $142,511.80

Duplicate drift checkpoints (post-ledger-start, comparing mark vs ledger as-of mark date):

- Checking: 61 marks used
  - median abs drift: $2,498.14
  - p90 abs drift: $11,243.37
  - max abs drift: $55,197.79
  - exact matches: 16/61
- Reserve Card: 61 marks used
  - median abs drift: $896.38
  - p90 abs drift: $7,653.59
  - max abs drift: $11,847.00
  - exact matches: 3/61

Interpretation:

- Substituting ledger-derived balances for duplicate net worth entities does not radically change net worth.
- Differences are expected because Aspire is bucketed and date-only, while Dojo is as-of and cannot model intra-day ordering.
- Many marks match the ledger exactly on certain dates, so marks are useful as checkpoints/validation even after switching to ledger-derived balances.
- For validation UX, Dojo should compare within a small date window (e.g., +/- 3 days) and an amount tolerance.
  - This handles common user behavior like recording a month-end balance on the next day, or recording on a weekend.

## Account type semantics: onboarding + reconcile requirements

This section defines what we need to ask the user for each Dojo account type during onboarding and what the periodic reconcile looks like.

### Cash (on-budget)

Onboarding inputs:

- Opening balance date + amount (or derive from imported transactions).
- Optional metadata: institution name, APY, overdraft.

Reconcile:

- Statement date + statement balance (posted/cleared balance).
- User clears/unclears transactions to match.
- User may need to add or correct transactions during reconcile:
  - missing transaction -> create it
  - wrong amount/date -> edit it (SCD2 correction)
  - pending -> leave pending; it will appear in the next worksheet

Pending contribution:

- Pending transactions are excluded from the cleared-balance reconcile target.
- Dojo should make it clear whether net worth views include pending or cleared-only balances.

### Credit (on-budget liability)

Credit cards have two linked concepts:

1) A liability ledger account that records purchases, refunds, and payments.
2) A dedicated "payment reserve" budget category that reserves cash to pay the card.

Onboarding inputs:

- Current statement balance at cutover.
- Optional metadata: APR, limit.

Aspire-parity expectation (payment reserve):

- Aspire presents a per-card payment row whose available behaves like a running payment reserve.
  Users expect:
  - card purchases increase the payment reserve (even if the spending category is overspent),
  - card payments decrease the payment reserve.

Dojo semantics:

- Dojo must ensure a corresponding payment reserve category exists for each credit account and that the reserve behavior matches the expectation above.
- Card purchases:
  - recorded as normal transactions on the credit account categorized to the spending category.
  - the system adjusts the payment reserve accordingly.
- Card payments:
  - represented as a paired transfer from a cash account to the credit account.
  - cash-side leg is categorized to the card's payment reserve category (consumes the reserved envelope).
  - card-side leg is categorized as `account_transfer` (budget-neutral) and reduces the liability.

Reconcile:

- Same worksheet concept as cash: statement date + statement balance.
- Pending vs cleared follows the same rules as cash accounts.

### Loan / Mortgage (tracking liability)

Onboarding inputs:

- Current principal balance at cutover (statement).
- Interest rate (APY).
- Loan start date and original term (or term end date).
- Original principal (recommended; required for "principal paid to date" and lifetime-interest analysis).
- Optional escrow notes.

Tracking mode (choose once; default preserves Aspire workflow):

- Mode A (recommended): statement principal checkpoints (no per-payment split required).
- Mode B (advanced): split payments into principal vs interest/escrow/fees.

Optional linkage metadata (recommended for UX):

- Linked payment category (e.g., "Mortgage")
- Linked payment source accounts (e.g., "Checking")

This linkage does not change ledger accounting, but it allows the loan detail page to show related payments and estimate principal vs interest over time.

Reconcile (lightweight default):

- Mode A: monthly (or statement cadence) enter statement principal balance and date.
  - Dojo records a measurement commit and updates the loan balance to match.
- Mode B: reconcile is still used as a checkpoint and to surface drift; it should be rare if payments are accurately split.

Planning utility:

- From principal + rate + term, Dojo can compute:
  - payoff date under various payment assumptions
  - interest saved under overpayments
  - remaining interest under the current schedule

### Investment (tracking asset)

Onboarding inputs (minimum to reconcile):

- Cutover date (statement date).
- Statement cash balance at cutover (uninvested cash).
- Holdings list:
  - ticker/security id
  - quantity
  - average cost / cost basis (recommended; required for realized/unrealized gain attribution)

Ledger prerequisite:

- All deposits/withdrawals to/from the investment account must be recorded in the ledger (typically as transfers).
- Dividends/interest/trades must not be recorded as ledger transactions.

Reconcile:

- Enter statement cash + holdings.
- System stores `ledger_baseline` at reconcile so transfers remain net-worth-neutral.

Guardrails:

- Show "unreconciled since X days" badge.
- Show ledger cashflow delta since last reconcile (transfers in/out) to help users notice missing transfer entries.
- Show the as-of market date used for pricing and warn that statement NAV may differ from Dojo NAV if the statement is intraday.

### Tangible (tracking asset)

Onboarding inputs:

- Cutover date.
- Appraised fair value.
- Optional metadata: asset name, acquisition cost.
- Recommended provenance metadata:
  - valuation source (user estimate / appraisal / comps)
  - optional note

Reconcile:

- Periodic valuation update (enter value + date + optional provenance).
- UI should show value staleness ("last updated") and treat values as estimates unless sourced.

## Onboarding wizard: proposed UX flow

The wizard should minimize choices, default correctly, and remain resumable.

Dojo style direction: minimalist earth tones.
See `docs/rules/style_guide.md`.

Note: the active SPA is Vue/Vite; some legacy docs describe vanilla JS.

### Step 1: Choose onboarding path

- "Start empty" (manual) vs "Migrate from Aspire".

### Step 2: Connect Google + choose sheet

- OAuth web flow (self-host friendly).
- Credentials configured via environment variables:
  - `GOOGLE_CLIENT_ID`
  - `GOOGLE_CLIENT_SECRET`
  - `GOOGLE_REDIRECT_URI` (recommended)

Privacy:

- OAuth credentials are stored only in memory with a short TTL.
- No tokens are written to disk or DB.

### Step 3: Verify + extract

- Verify required named ranges exist.
- Extract into DuckDB staging tables.
- Show counts + date ranges only (no values).

Resumability:

- The UI is a one-time onboarding wizard, but the backend persists progress in a "migration session" so the user can refresh/close the tab and resume.
- Extraction persists in staging tables keyed by `migration_session_id`.
- A dataset fingerprint identifies the exact extracted dataset.
- Starting over can create a new session and discard prior staging data; this is an implementation detail, not a multi-run user workflow.

### Step 4: Map budgeting domain

- Accounts: create on-budget cash/credit accounts from `trx_Accounts` and `cfg_*` lists.
- Categories: create budget categories/groups; handle hidden/retired.
- Transfers: detect transfer-category legs and auto-pair deterministically.
  - Use the pairing heuristic described in the invariant section (amount + date tolerance + account mismatch).
  - Present a focused transfer-exceptions UI for unresolved legs only:
    - allow linking exactly two unresolved legs as a transfer concept,
    - allow mapping unresolved single legs only to `opening_balance` / `balance_adjustment`,
    - allow undo for both resolution types.
  - Do not allow arbitrary budget-category remapping for transfer exceptions.
  - The "Apply import" step is blocked by unresolved transfer exceptions.

### Step 5: Map net worth domain

For each net worth category (union of config + marks categories):

- Auto-classify duplicates (same normalized name as a transaction account).
  - Default: "derived from ledger; keep marks as checkpoints".
- For non-duplicates:
  - Default: "legacy only" (preserve history)
  - Optional: "track forward in Dojo" (choose account type + cutover inputs)
    - Support split cutover: one Aspire entity can map into multiple Dojo accounts at cutover.

Keep user choices minimal:

- Most entities should require at most one click ("track forward?").
- Only "track forward" requires extra fields.

### Step 6: Preview + validate

- Show Aspire net worth history (legacy marks) and Dojo-hybrid net worth for overlap period.
- Show drift stats for duplicates.
- For duplicates, show drift using a date window + tolerance (not only exact-date matching).
- Show warnings:
  - marks categories not in current config
  - configured categories with no marks
  - unmatched transfer candidates and duplicate-mapping collisions (must be resolved before apply)
  - legacy mark categories present in marks but missing asset/debt classification (stored, but excluded from parity totals until classified)

Budget parity (trust check):

- Validate that Dojo's post-import envelope math matches Aspire-derived expectations computed from the extracted records.
- Default month: the Aspire "today" month (`v_Today`) when present; otherwise the system current month.
- What we compare (current-month view, per category):
  - `allocated` (budgeted)
  - `activity` (spent/income; Dojo convention is outflows increase activity)
  - `available`
  - and top-line `Ready to Assign` (`available_to_budget`)
- Status semantics:
  - Default comparison uses the same status inclusion that Dojo uses for budget reporting.
  - If Dojo exposes both "cleared-only" and "working (incl pending)", compute and display both.
- Presentation:
  - Table showing only diffs by default (with "show all").
  - Explain known expected differences (especially month-rollover overspending behavior) and treat them as an explicit, labeled semantic difference.
- Apply gating:
  - Budget parity failures are treated as correctness blockers unless the user explicitly acknowledges a documented semantic difference.

### Step 7: Apply import

- Apply is blocked until correctness-critical ambiguities are resolved:
  - unresolved transfer exceptions,
  - duplicate-mapping collisions,
  - and any net worth categories the user chose to include in Dojo-derived totals without an asset/debt classification.
- Transactional apply: a single DB transaction across all phases; no partial commits.
- Idempotent per migration session and dataset fingerprint:
  - Imported concepts use deterministic identifiers derived from (dataset fingerprint + record kind + stable staging key).
  - We do not promise "merge" semantics across different source snapshots; if the spreadsheet changes, the dataset fingerprint changes and the user starts a new session.
  - Do not rely on staging `row_index` alone as a cross-extract identity.
- Set-based writes where feasible; avoid per-row Python loops over the full ledger for performance.
- On success: rebuild caches.
- On failure: rollback; the session remains resumable.

### Step 8: Post-onboarding "Reconcile Now" checklist

- Present a short checklist of accounts that should be reconciled soon.
- Encourage weekly/monthly cadence.
- Consider surfacing this as a persistent dashboard section ("finance todos") so users see it on each app open.

## Tradeoffs and gotchas

- Aspire's net worth marks are bucketed; Dojo's net worth is as-of. Small differences are expected even for the same month.
- Date-only marks and date-only transactions cannot capture intra-day ordering; exact matches are not guaranteed.
- Some Aspire categories appear only in historical marks and not in current config; migration must preserve them.
- Investment accounts require reconcile to reflect internal returns (dividends/interest/price moves). The UI must make this obvious.
- Pending transactions: users may record pending items; Dojo must be explicit about whether net worth views include pending or cleared-only balances.
- Loans/mortgages: if users do not split payments, principal changes appear at reconcile checkpoints (correct over the period, but not always day-accurate between reconciles).

## Required technical changes (implementation notes)

This RFC intentionally defines semantics before implementation, but the following changes are implied:

- Add first-class storage for legacy net worth marks (post-staging), plus APIs to compute:
  - Aspire-style bucket reports (parity)
  - an as-of carry-forward view (convenience)
- Make net worth reporting include historical-but-inactive entities (paid-off loans, closed accounts) and avoid using `is_active=TRUE` as a reporting filter.
  Consider an explicit include/exclude-from-net-worth flag distinct from UI active/inactive.
- Update investment reconcile + net worth SQL to incorporate `ledger_baseline` at reconcile.
- Increase market price precision (e.g., 1/10,000 USD) so valuation rounding does not force fake cash.
- Consider increasing position quantity precision (avoid relying on binary floats for share quantities).
- Add a loan-payment linkage model (loan <-> payment category and source accounts) for UX and analytics without changing ledger semantics.
- Add a net worth "cleared-only" view that excludes pending transactions for statement comparisons.
- Enforce investment ledger purity (block internal-activity categories on investment accounts).
- Import and preserve Aspire status symbols and marker rows (`trx_Statuses`, `v_BreakSymbol`, `ntw_Breakpoints`) without letting them affect balances.
- Persist transfer pairing decisions and enforce no orphan transfer legs.
- Staging cleanup lifecycle:
  - purge session staging tables on successful completion,
  - purge abandoned sessions after a TTL,
  - ensure logs and error messages never contain raw values.
- Define reconcile "commit" types per account class (cash/credit/loan/investment/tangible) under a unified UX.

## Appendix: developer tools used to validate

These internal scripts were created to validate semantics against extracted data:

- `python -m dojo.aspire_migration.net_worth_parity` (Aspire bucket series from marks)
- `python -m dojo.aspire_migration.net_worth_duplicate_drift` (mark vs ledger drift for duplicates)
- `python -m dojo.aspire_migration.net_worth_hybrid` (hybrid substitution of duplicates)

## Appendix: suggested UX copy blocks

These are non-normative examples intended to improve clarity and reduce drop-off.

Duplicate mapping (net worth category <-> transaction account)

"Some Aspire net worth lines look like the same real-world account as your Transactions accounts.
To avoid double-counting, Dojo will use Transactions as the source of truth and keep Aspire marks as checkpoints you can compare against."

Drift preview

"Aspire net worth is based on monthly snapshots. Dojo uses latest-known values and transaction timing,
so small differences are normal, especially around month-end. Large drift usually means a missing transfer
or an account that needs a reconcile."

Investment reconcile

"Transactions should only include money moving into or out of this account (deposits/withdrawals).
Trades, dividends, and interest stay inside the account and are captured when you reconcile holdings and statement cash."

Loan principal update

"Enter the principal balance from your statement. Payments can stay as one budget outflow.
Dojo updates principal at each statement checkpoint and uses this to power payoff planning."
