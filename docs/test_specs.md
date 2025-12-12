# Comprehensive Test Specifications

This document outlines the testing strategy required to stabilize the application and prevent regressions. It defines specific test specifications covering the full lifecycle of data—from onboarding and daily operations to complex temporal edits.

These specifications are agnostic of the testing tool (e.g., Pytest vs. Cypress) but are categorized by the recommended layer of the testing pyramid. The goal is to ensure robust data integrity, strictly adhering to the SCD-2 temporal model and the architectural invariance rules defined for the application.

---

## Domain 1: Account Onboarding and Initial State

**Goal:** Verify that creating accounts correctly initializes the ledger and respects the boundary between on-budget and tracking assets so downstream Net Worth and Budgeting calculations start from a clean, auditable base.

### Spec 1.1: Cash Account Onboarding (Budget Impact)
* **Test Level:** Integration
* **Initial Condition:** Pristine system; 0 accounts; Ready to Assign (RTA) = $0.00.
* **Action:** Create a Checking/Cash account with starting balance $5,000.00 via opening-balance flow.
* **Validations:**
    1. Account record exists with `type='Cash'`, `is_active=TRUE`.
    2. Opening-balance transaction exists with `amount=5000.00`, category `Inflow: Ready to Assign` (or equivalent), `is_active=TRUE`, `recorded_at` at creation time.
    3. RTA reads $5,000.00; no other categories show budgeted/activity change.
* **Expected End State:** Net Worth = $5,000.00; RTA fueled by opening balance; budget otherwise untouched.

### Spec 1.2: Credit Card Onboarding (On-Budget Liability)
* **Test Level:** Integration
* **Initial Condition:** Pristine system; RTA = $0.00.
* **Action:** Create credit card with starting balance -$1,200.00.
* **Validations:**
    1. Account `type='Credit/Borrowing'`, `is_active=TRUE`.
    2. Opening transaction `amount=-1200.00` recorded as liability; no budget category impact.
    3. RTA remains $0.00; budget categories show no activity.
* **Expected End State:** Net Worth decreases by $1,200.00; liability present; budget view unchanged.

### Spec 1.3: Tracking Loan/Mortgage Onboarding (Isolation)
* **Test Level:** Integration
* **Initial Condition:** Pristine system; RTA = $0.00.
* **Action:** Create tracking mortgage with starting balance -$350,000.00.
* **Validations:**
    1. Account `type='Long-Term Borrowing' (tracking)`, `is_active=TRUE`.
    2. Transaction `amount=-350000.00` stored without budget category (or system off-budget tag).
    3. RTA stays $0.00; no budgeted/activity entries created.
* **Expected End State:** Net Worth = -$350,000.00; budget unaffected by tracking liability.

### Spec 1.4: Tracking Asset Onboarding (Accessible Asset / Investment)
* **Test Level:** Integration
* **Initial Condition:** Pristine system; RTA = $0.00.
* **Action:** Create tracking asset (accessible asset or investment) with starting balance $20,000.00.
* **Validations:**
    1. Account classified as tracking asset; `is_active=TRUE`.
    2. Opening transaction `amount=20000.00` with transfer/off-budget category only.
    3. RTA unchanged; budget categories show no activity.
* **Expected End State:** Net Worth increases by $20,000.00; budget isolated.

---

## Domain 2: The SCD-2 Ledger (Transaction Lifecycle)

**Goal:** Enforce that edits and deletions are non-destructive, maintain historical versions, and that only the latest active version drives balances and budgeting.

### Spec 2.1: Correction Flow (Edit Transaction Net Impact)
* **Test Level:** Unit (service/DAO) + Integration
* **Initial Condition:** Transaction TX1: `amount=-50.00`, `category='Groceries'`, `account=cash`, `is_active=TRUE`; Groceries available $150.00; cash balance computed.
* **Action:** Edit TX1 amount to `-60.00`.
* **Validations:**
    1. Original row remains with `is_active=FALSE`.
    2. New row inserted with `amount=-60.00`, `is_active=TRUE`, `recorded_at` greater than prior, same `concept_id`/transaction_id, editor `user_id` captured.
    3. Groceries available becomes $140.00 (delta -$10.00); cash balance reduced by $10.00; RTA unchanged.
* **Expected End State:** Two rows for TX1 exist; only new row affects balances; history intact.

### Spec 2.2: Soft Retirement (Void/Delete)
* **Test Level:** Unit / Integration
* **Initial Condition:** Transaction TX2: `amount=-100.00`, `is_active=TRUE`; account/category balances reflect it.
* **Action:** Void TX2.
* **Validations:**
    1. TX2 active flag set to FALSE (no physical delete).
    2. Balances and category available reverse the original impact (+$100.00 to account/category where applicable).
    3. RTA/NW revert to pre-TX2 values.
* **Expected End State:** System state equals pre-TX2, with audit trail preserved.

### Spec 2.3: Concurrent Edit Protection
* **Test Level:** Unit
* **Initial Condition:** One concept_id with active version.
* **Action:** Simulate two edits in rapid succession.
* **Validations:**
    1. Only one latest active version remains.
    2. No overlapping `is_active=TRUE` rows for same concept.
    3. Failed edit rolls back fully (no partial balance changes).
* **Expected End State:** Deterministic last-writer-wins; invariants intact.

### Spec 2.4: Reconciliation Window Integrity
* **Test Level:** Integration
* **Initial Condition:** Account reconciled at T0; transactions prior to T0 immutable; balances captured in snapshot.
* **Action:** Add, edit, and void transactions after T0.
* **Validations:**
    1. Reconciliation diff shows only post-T0 versions.
    2. Historical as-of T0 balances unchanged.
    3. Current balances reflect post-T0 edits exactly once.
* **Expected End State:** Reconciliation log intact; temporal queries produce correct as-of and current states.

### Spec 2.5: Net Impact on Account/Category After Cross-Account Edit
* **Test Level:** Integration
* **Initial Condition:** TX3: `amount=-75.00`, `account=cash`, `category='Dining'`, active; balances computed.
* **Action:** Edit TX3 to move to `account=credit_card`, same amount/category.
* **Validations:**
    1. Cash balance increases by $75.00 (reversal); credit liability decreases by $75.00 (or increases negativity correctly).
    2. Dining available unchanged (no category change); RTA unchanged.
    3. Single active version for TX3 post-edit; prior version inactive.
* **Expected End State:** Balances reflect only new account leg; history preserved.

---

## Domain 3: Ready to Assign and Allocations

**Goal:** Ensure RTA changes only via cash-class inflows and explicit allocations, with zero-sum moves between envelopes and guard rails against over-allocation.

### Spec 3.1: Income to Cash Increases RTA
* **Test Level:** Integration
* **Initial Condition:** Cash account; RTA = $0.00; no budgeted funds.
* **Action:** Post income transaction $2,000.00 to cash with income category.
* **Validations:**
    1. RTA increases by $2,000.00; cash balance +$2,000.00.
    2. Category activity logs inflow; budgeted remains 0.
    3. Net Worth increases by $2,000.00.
* **Expected End State:** RTA = $2,000.00 until allocated; budgeted unchanged.

### Spec 3.2: Allocation Guard Rails (Zero-Sum)
* **Test Level:** Unit + Property
* **Initial Condition:** RTA = X; categories with various available balances.
* **Action:** Random sequences of allocations: RTA -> category, category -> category.
* **Validations:**
    1. Sum of budgeted equals total allocated from RTA; RTA never < 0.
    2. Category-to-category moves are zero-sum (source decreases, destination increases equally).
    3. Over-allocations raise 400/validation error and leave state unchanged.
* **Expected End State:** Conservation of funds across RTA and envelopes.

### Spec 3.3: Prevent Over-Allocation
* **Test Level:** Integration
* **Initial Condition:** RTA = $50.00.
* **Action:** Attempt allocation of $75.00 to any category.
* **Validations:**
    1. API returns error (stable shape); no ledger/category mutation.
    2. RTA and budgeted remain unchanged.
* **Expected End State:** Guard rail enforced; balances identical to initial.

### Spec 3.4: Category Rollover
* **Test Level:** Integration
* **Initial Condition:** Prior month available = $120.00 for Category A; budgeted/activity present; current month begins.
* **Action:** Advance to new month without new transactions.
* **Validations:**
    1. Available carries over $120.00; budgeted resets to $0.00; activity resets to $0.00.
    2. RTA unchanged by month flip.
* **Expected End State:** New month state reflects rollover formula precisely.

### Spec 3.5: Internal Cash Transfer (Budget Neutral)
* **Test Level:** Integration
* **Initial Condition:** Two cash accounts; RTA known; no pending allocations.
* **Action:** Transfer $300 between cash accounts categorized as transfer.
* **Validations:**
    1. Total cash conserved; RTA unchanged.
    2. No budget category activity unless explicitly categorized.
* **Expected End State:** Net Worth unchanged; balances shifted only between accounts.

---

## Domain 4: Spending Flows

**Goal:** Validate that spending alters the correct envelopes and accounts, respecting RTA rules and liability handling.

### Spec 4.1: Cash Spend
* **Test Level:** Integration
* **Initial Condition:** Cash account; Category Groceries funded with $200.00; RTA already reduced by allocation.
* **Action:** Record cash outflow $60.00 to Groceries.
* **Validations:**
    1. Cash balance -$60.00.
    2. Groceries activity +$60.00; available becomes $140.00.
    3. RTA unchanged.
    4. Net Worth -$60.00.
* **Expected End State:** Account and category reflect spend; RTA intact.

### Spec 4.2: Credit Spend Against Funded Category
* **Test Level:** Integration
* **Initial Condition:** Credit card liability -$500.00; Groceries available $200.00; RTA already reduced by allocation.
* **Action:** Record credit purchase $80.00 to Groceries.
* **Validations:**
    1. Credit liability becomes -$580.00 (more negative).
    2. Groceries available becomes $120.00; activity +$80.00.
    3. RTA unchanged.
    4. Net Worth -$80.00.
* **Expected End State:** Liability reflects charge; envelope reduced; RTA untouched.

### Spec 4.3: Refund/Return on Credit
* **Test Level:** Integration
* **Initial Condition:** Prior credit spend $80.00 to Groceries recorded.
* **Action:** Record inflow $30.00 on credit card to Groceries.
* **Validations:**
    1. Credit liability improves by $30.00.
    2. Groceries available increases by $30.00; activity decreases net.
    3. RTA unchanged.
* **Expected End State:** Partial reversal applied cleanly.

### Spec 4.4: Split Transaction Across Categories
* **Test Level:** Integration
* **Initial Condition:** Cash account; Categories A/B funded.
* **Action:** Record split spend $90.00 ($50 to A, $40 to B).
* **Validations:**
    1. Cash balance -$90.00.
    2. Category A available -$50; Category B available -$40.
    3. RTA unchanged.
* **Expected End State:** Each envelope reflects its share; total matches spend.

---

## Domain 5: Transfers, Contributions, and Payments

**Goal:** Ensure transfers and funding flows obey budget rules, keep RTA correct, and reflect proper net worth effects.

### Spec 5.1: Cash → Credit Payment Using Payment Category
* **Test Level:** Integration
* **Initial Condition:** Payment: Card category funded $300.00; cash balance $1,000.00; credit liability -$800.00.
* **Action:** Transfer $250.00 from cash to credit card, categorized to Payment: Card.
* **Validations:**
    1. Cash -$250.00; credit liability improves by $250.00.
    2. Payment category activity +$250.00; available reduces accordingly.
    3. RTA unchanged.
* **Expected End State:** Liability reduced; envelope consumed; RTA intact.

### Spec 5.2: Cash → Accessible Asset (Off-Budget Stash)
* **Test Level:** Integration
* **Initial Condition:** Cash with RTA $500.00; accessible asset balance $0.00; category Short-Term Savings funded from RTA.
* **Action:** Outflow $400.00 from cash categorized to Short-Term Savings; matching transfer inflow to accessible asset.
* **Validations:**
    1. RTA decreases by $400.00 at allocation; cash decreases by $400.00.
    2. Accessible asset balance increases $400.00.
    3. Budget activity only on cash leg; receiving leg has no budget effect.
    4. Net Worth unchanged (asset swap).
* **Expected End State:** Off-budget stash funded; envelopes reflect allocation; RTA reduced.

### Spec 5.3: Accessible Asset → Cash Withdrawal (Income)
* **Test Level:** Integration
* **Initial Condition:** Accessible asset balance $1,000.00; RTA $0.00.
* **Action:** Transfer $300.00 back to cash; categorize cash inflow as income to RTA.
* **Validations:**
    1. Accessible asset -$300.00; cash +$300.00.
    2. RTA increases by $300.00; category mirrors inflow type if not income.
    3. Net Worth unchanged.
* **Expected End State:** Liquidity restored; RTA boosted by inflow categorization.

### Spec 5.4: Cash → Investment Contribution
* **Test Level:** Integration
* **Initial Condition:** Cash balance $2,000.00; Investment balance $0.00; Contribution category funded $500.00.
* **Action:** Outflow $500.00 from cash categorized to Contribution; matching transfer to investment account.
* **Validations:**
    1. Cash -$500.00; investment +$500.00.
    2. Contribution category available decreases $500.00; RTA unchanged (already reduced when funded).
    3. Net Worth unchanged (asset swap).
* **Expected End State:** Contribution recorded without double-counting; envelopes consistent.

### Spec 5.5: Investment → Cash Withdrawal
* **Test Level:** Integration
* **Initial Condition:** Investment balance $5,000.00; RTA $0.00.
* **Action:** Transfer $400.00 to cash; categorize inflow as income (or reimbursement variant in subcase).
* **Validations:**
    1. Investment -$400.00; cash +$400.00.
    2. If income: RTA +$400.00; else category available +$400.00 per choice.
    3. Net Worth unchanged.
* **Expected End State:** Withdrawal represented correctly with chosen categorization impact.

### Spec 5.6: On-Budget Cash Transfer (Neutral)
* **Test Level:** Integration
* **Initial Condition:** Two cash accounts with balances; RTA known.
* **Action:** Transfer $200.00 from cash A to cash B categorized as transfer.
* **Validations:**
    1. Total cash unchanged; RTA unchanged.
    2. No category activity unless explicitly specified.
* **Expected End State:** Pure balance move with zero budget effect.

---

## Domain 6: Month Boundary and Activity Reset

**Goal:** Ensure month transitions roll over available funds, reset budgeted/activity, and preserve RTA.

### Spec 6.1: Month Flip with Rollover
* **Test Level:** Integration
* **Initial Condition:** Month M has budgeted and activity values; Category A available $120.00; RTA known.
* **Action:** Advance to month M+1; no new transactions during flip.
* **Validations:**
    1. Category A available starts at $120.00; budgeted/activity = $0.00 in M+1.
    2. RTA unchanged by flip.
    3. Reports partitioned by month show correct M vs M+1 values.
* **Expected End State:** Clean monthly boundaries with correct carryover.

---

## Domain 7: Net Worth Snapshots and Reporting

**Goal:** Guarantee that net worth aggregation aligns with ledger balances, respects tracking vs on-budget boundaries, and honors account lifecycle.

### Spec 7.1: Snapshot Aggregation by Account Class
* **Test Level:** Integration
* **Initial Condition:** Mixed accounts (cash, credit, tracking assets, investments, loans) with balances; positions present.
* **Action:** Fetch net worth snapshot API.
* **Validations:**
    1. Per-class totals sum to grand total; sign conventions correct.
    2. Tracking accounts included; budget categories excluded; inactive accounts filtered from current view.
    3. Minor units preserved; Decimal mirrors returned; no floats.
* **Expected End State:** Snapshot matches ledger equation.

### Spec 7.2: Inactive/Retired Accounts
* **Test Level:** Integration
* **Initial Condition:** Account with zero balance; others active; history present.
* **Action:** Mark account inactive.
* **Validations:**
    1. Current snapshot excludes inactive account.
    2. Historical as-of dates still include it when active.
    3. No balance mutation on status flip.
* **Expected End State:** Lifecycle respected without data loss.

### Spec 7.3: Net Worth Equation Property
* **Test Level:** Property
* **Initial Condition:** Randomized sets of accounts, transactions, positions, optional tangibles.
* **Action:** Compute net worth across seeds and after random edits/voids.
* **Validations:**
    1. `assets - liabilities + positions + tangibles = reported_net_worth` always holds.
    2. Tracking accounts never affect RTA.
    3. Inactive accounts excluded from current snapshot.
* **Expected End State:** Equation invariant holds across generated scenarios and temporal edits.

---

## Domain 8: UI / E2E Journeys (Cypress)

**Goal:** Validate end-to-end user flows and UI/state coherence for critical budgeting journeys.

### Spec 8.1: Onboard, Paycheck, Allocate
* **Test Level:** E2E
* **Initial Condition:** Reset DB; no accounts.
* **Action:** Create cash account; record paycheck; allocate to envelopes.
* **Validations:**
    1. RTA increases by paycheck, then decreases by allocations; budgeted column equals allocations.
    2. Net Worth equals cash balance; cards show consistent values.
* **Expected End State:** User ready to operate with balanced budget and accurate UI.

### Spec 8.2: Credit Spend and Payment
* **Test Level:** E2E
* **Initial Condition:** Cash + credit accounts; Groceries funded; Payment: Card funded.
* **Action:** Record credit grocery purchase; then payment from cash via payment category.
* **Validations:**
    1. Purchase increases card liability and reduces Groceries available; RTA unchanged.
    2. Payment decreases liability and payment envelope; RTA unchanged; UI reflects updates.
* **Expected End State:** Balances consistent; UI cards accurate after both steps.

### Spec 8.3: Off-Budget Savings Loop
* **Test Level:** E2E
* **Initial Condition:** Cash and accessible asset accounts; RTA funded.
* **Action:** Allocate to savings; transfer cash→accessible; later withdraw and categorize as income.
* **Validations:**
    1. Budget activity only on cash leg; accessible leg budget-neutral.
    2. Withdrawal increases RTA; net worth stable across moves.
* **Expected End State:** Correct balances and budget figures; UI consistent.

### Spec 8.4: Investment Contribution and Withdrawal
* **Test Level:** E2E
* **Initial Condition:** Cash and investment accounts; contribution category funded.
* **Action:** Transfer contribution; later withdraw categorized as income.
* **Validations:**
    1. Contribution reduces envelope and moves cash→investment; RTA unchanged.
    2. Withdrawal increases RTA (or chosen category); net worth unchanged.
* **Expected End State:** UI shows correct swaps without double-counting.

### Spec 8.5: Month Rollover Experience
* **Test Level:** E2E
* **Initial Condition:** Month with allocations and spends.
* **Action:** Advance month via UI fixture; view new month.
* **Validations:**
    1. Available rolled forward; budgeted/activity reset; RTA preserved.
    2. History view retains prior month values.
* **Expected End State:** New month dashboard accurate and isolated.

### Spec 8.6: Edit/Void Transaction from UI
* **Test Level:** E2E
* **Initial Condition:** Existing transaction displayed.
* **Action:** Edit amount/category; then void from UI.
* **Validations:**
    1. UI shows single active version post-edit; balances adjust by delta.
    2. After void, balances revert; history panel shows prior versions.
* **Expected End State:** UX demonstrates SCD2 without duplicate effects.

### Spec 8.7: Reconciliation UX
* **Test Level:** E2E
* **Initial Condition:** Account with known external balance.
* **Action:** Reconcile; add erroneous transaction; correct it.
* **Validations:**
    1. Reconciliation diff surfaces new transaction; after correction diff clears.
    2. Balances match external value; RTA and categories unaffected by reconciliation action itself.
* **Expected End State:** Users can trust reconciliation workflow end-to-end.

---

## Flakiness and Determinism Requirements
* Fix clock and month boundaries in tests; seed random property/state-machine tests per run.
* Reset DB per test/spec; use paired transfer entries explicitly.
* Assert on integer minor units and stable error shapes.
* Prefer property/state-machine tests for sequence coverage; keep E2E to critical journeys.
