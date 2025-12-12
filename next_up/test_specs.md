# Test Specifications (Behavior-Focused)

Purpose: executable specs for budgeting correctness. Organized by domain; emphasize SCD2 integrity and net-impact (accounts, categories, RTA, net worth). Each test names pyramid level, initial conditions, actions, validations, and expected end state. Not an ExecPlan.

## 1) Core Temporal & Net Worth Invariants

### SCD2: single active version per concept
- Level: unit + property
- Initial: in-memory DB, N seeded concept_ids; clock fixed
- Actions: create versions, edit (change amount/category/account/date), void (mark inactive), attempt concurrent edit
- Validations: exactly one active row per concept; `valid_from < valid_to`; edits close prior row and insert new row; failed transaction rolls back all versions
- End state: account and category balances reflect only latest active versions; history preserved for audit

### SCD2: edit/void net impact deltas
- Level: integration
- Initial: one cash transaction (amount A) tied to category; balances precomputed
- Actions: edit amount to B, change category, change account, then void
- Validations: balance deltas equal (B-A) on affected account/category only once; moving category reverses old and applies new; void reverses original impact
- End state: balances and available match recomputed ledger; inactive rows remain for history

### Reconciliation window integrity
- Level: integration
- Initial: account reconciled at T0 with snapshot; transactions before T0 locked
- Actions: add, edit, void transactions after T0
- Validations: reconciliation diff includes only post-T0 versions; pre-T0 state untouched; balances post-delta consistent
- End state: reconciliation log unchanged; current balances include post-T0 changes; historical query as-of T0 unchanged

### Net worth equation
- Level: property
- Initial: randomized accounts (cash, credit, accessible assets, investments, loans) with transactions; optional positions
- Actions: compute net worth snapshot
- Validations: `assets - liabilities + positions + tangibles = reported_net_worth`; tracking accounts excluded from RTA; inactive accounts excluded from current view
- End state: equation holds across random seeds and after edits/voids

## 2) Onboarding & Opening Balances

### Cash account onboarding
- Level: integration
- Initial: empty ledger
- Actions: create cash account with opening balance via dedicated flow
- Validations: opening-balance transaction exists, categorized to special bucket; RTA increases by opening amount; account balance matches opening; net worth increases
- End state: cash account active; RTA and net worth reflect cash

### Credit card onboarding
- Level: integration
- Initial: empty ledger
- Actions: create credit card with opening liability
- Validations: opening balance recorded as liability transaction; no budget activity; RTA unchanged; net worth decreases by liability
- End state: card active with negative balance; budget untouched

### Loan/mortgage onboarding (tracking)
- Level: integration
- Initial: empty ledger
- Actions: create loan with principal via tracking account flow
- Validations: liability reflected in net worth; no budget activity or RTA change; loan shown as tracking
- End state: loan balance negative; budget untouched

### Investment / accessible asset onboarding (tracking)
- Level: integration
- Initial: empty ledger
- Actions: create tracking asset with opening balance
- Validations: balance contributes to net worth; no budget activity; RTA unchanged; category-free
- End state: tracking asset active with balance; budget untouched

## 3) Ready to Assign & Allocations

### Income to cash increases RTA
- Level: integration
- Initial: cash account, zero RTA
- Actions: post income transaction to cash with income category
- Validations: RTA increases by amount; account balance increases; category activity logs inflow; net worth increases
- End state: RTA equals cash inflow; available unchanged until allocated

### Allocation guard rails (zero-sum between RTA and envelopes)
- Level: unit + property
- Initial: RTA = X, categories with available balances
- Actions: random allocations from RTA to categories and between categories
- Validations: total budgeted equals sum allocations; RTA decreases by allocations from RTA; moves between categories are zero-sum; errors when RTA insufficient
- End state: RTA never negative; envelope totals conserved

### Prevent over-allocation
- Level: integration
- Initial: RTA = small amount
- Actions: attempt allocation exceeding RTA
- Validations: API 400 with stable error; no state change
- End state: balances unchanged

### Category rollover
- Level: integration
- Initial: prior-month available > 0; current month start
- Actions: advance month, no activity
- Validations: available rolls over; budgeted resets to 0; activity resets; RTA persists
- End state: new month state matches rollover formula

## 4) Spending Flows

### Cash spend
- Level: integration
- Initial: cash account funded category
- Actions: record cash outflow against category
- Validations: cash balance decreases; category activity increases, available decreases; RTA unchanged; net worth decreases
- End state: balances consistent with outflow

### Credit spend against funded category
- Level: integration
- Initial: funded category; credit card liability balance; RTA unaffected
- Actions: record credit purchase assigned to category
- Validations: liability increases by amount; category available decreases; RTA unchanged; net worth decreases by spend
- End state: card more negative; envelope reduced; RTA intact

### Refund / return (credit)
- Level: integration
- Initial: prior credit spend recorded
- Actions: record inflow on credit card to same category
- Validations: liability decreases; category available increases; RTA unchanged
- End state: net effect offsets original spend

### Split transaction across categories
- Level: integration
- Initial: funded categories A/B; cash account
- Actions: record split spend
- Validations: per-split activity and available adjust; account balance decreases by total; RTA unchanged
- End state: categories reflect split amounts

## 5) Transfers, Contributions, Payments

### Cash → credit payment using payment category
- Level: integration
- Initial: funded "Payment: Card" category; cash and credit balances
- Actions: transfer cash to credit card categorized to payment envelope
- Validations: cash decreases; credit liability decreases; payment category activity reflects outflow; RTA unchanged; available in payment category decreases
- End state: reduced liability; envelopes consistent

### Cash ↔ accessible asset (off-budget stash)
- Level: integration
- Initial: cash with RTA; empty accessible asset account
- Actions: outflow from cash categorized "Short-Term Savings" plus matching transfer inflow to accessible asset
- Validations: RTA decreases by allocation; accessible asset balance increases; net worth unchanged; no budget activity on receiving leg
- End state: stash funded; budget reflects allocation

### Accessible asset → cash (withdrawal)
- Level: integration
- Initial: funded accessible asset balance
- Actions: transfer back to cash; categorize cash inflow as income
- Validations: cash increases; RTA increases by inflow; accessible asset decreases; net worth unchanged; category reflects inflow type
- End state: liquidity restored; RTA boosted

### Cash → investment contribution
- Level: integration
- Initial: cash with funded investment contribution category
- Actions: cash outflow categorized to contribution + matching transfer to investment account
- Validations: cash decreases; investment balance increases; envelope decreases/RTA decreases; net worth unchanged (asset swap)
- End state: contribution recorded without double-counting

### Investment → cash withdrawal
- Level: integration
- Initial: investment balance
- Actions: transfer to cash; categorize inflow as income or reimbursement
- Validations: cash increases; investment decreases; RTA or category adjusts per categorization; net worth unchanged
- End state: liquidation reflected correctly

### Internal cash transfer (on-budget to on-budget)
- Level: integration
- Initial: two cash accounts; RTA known
- Actions: transfer between cash accounts categorized as transfer
- Validations: total cash conserved; RTA unchanged; no category impact unless explicitly categorized; net worth unchanged
- End state: balances moved with zero net impact

## 6) Month Boundary & Activity Reset

### Month flip with pending allocations and spends
- Level: integration
- Initial: month M with budgeted, activity, available computed; RTA known
- Actions: advance to month M+1; post new allocations and spends
- Validations: previous available rolls; new budgeted/activity start at 0; RTA persists; reports partitioned by month
- End state: month states isolated; cumulative available correct

## 7) Editing & Deleting Transactions (SCD2 Focus)

### Edit amount/category/account
- Level: integration
- Initial: one active transaction
- Actions: edit amount, then change category, then change account
- Validations: previous version inactive; new version active with new `recorded_at`; balances adjust by delta; if account changed, source reversed and destination applied
- End state: only latest version affects balances; history visible

### Delete/Void transaction
- Level: integration
- Initial: active transaction present
- Actions: void/delete
- Validations: active flag false; reversing entry applied to balances/categories; net worth and RTA revert
- End state: as if transaction absent, with audit trail retained

### Concurrent edit protection
- Level: unit
- Initial: same concept edited twice in rapid succession
- Actions: apply second edit while first in-flight (simulated)
- Validations: one wins; invariants preserved; no duplicate active versions
- End state: deterministic latest version active

## 8) Reconciliation Flows

### Record reconciliation snapshot
- Level: integration
- Initial: account with transactions; known external balance
- Actions: reconcile at T0 with matching amount
- Validations: snapshot stored with app balance; no ledger mutation; subsequent diff queries reference T0
- End state: reconciliation log entry persisted

### Post-reconciliation correction
- Level: integration
- Initial: reconciled at T0; later discrepancy
- Actions: add correcting transaction after T0
- Validations: diff shows new transaction; balances updated; historical as-of T0 unchanged
- End state: account current balance matches external after correction

## 9) Net Worth Snapshots & Reporting

### Snapshot aggregation by account class
- Level: integration
- Initial: mixed accounts with balances; positions present
- Actions: fetch net worth snapshot API
- Validations: per-class totals sum to grand total; tracking accounts included; budget categories excluded; minor units preserved; decimals mirrored
- End state: snapshot consistent with ledger

### Inactive/retired accounts
- Level: integration
- Initial: active and inactive accounts with history
- Actions: retire account (zero balance then set inactive)
- Validations: current snapshot excludes inactive; historical as-of date includes; balances unaffected by status flip
- End state: lifecycle respected without data loss

## 10) UI / E2E Journeys (Cypress)

### Onboard + first paycheck + allocate
- Level: e2e
- Initial: reset DB
- Actions: create cash account, record paycheck, allocate to envelopes
- Validations: RTA increases then decreases by allocations; budgeted column equals allocations; net worth equals cash; cards reflect values
- End state: ready-to-use budget with correct totals

### Credit spend and payment
- Level: e2e
- Initial: funded Groceries and Payment: Card; cash + credit accounts
- Actions: record credit grocery purchase, then payment from cash via payment category
- Validations: purchase reduces Groceries available and increases card liability; payment reduces liability and payment envelope; RTA unchanged throughout
- End state: balances consistent; UI cards update

### Off-budget savings loop
- Level: e2e
- Initial: cash and accessible asset accounts
- Actions: allocate to savings, transfer cash→accessible; later withdraw and categorize as income
- Validations: budget activity only on cash side; accessible asset movements budget-neutral; withdrawal boosts RTA; net worth stable across moves
- End state: correct balances and budget figures

### Investment contribution and withdrawal
- Level: e2e
- Initial: cash, investment accounts; contribution category funded
- Actions: contribution transfer; later withdrawal categorized as income
- Validations: envelopes decrease on contribution; RTA unchanged; withdrawal increases RTA; net worth unchanged across transfers
- End state: UI reflects swaps correctly

### Month rollover
- Level: e2e
- Initial: month with allocations and spends
- Actions: advance month via UI fixture; view new month
- Validations: available rolled forward; budgeted/activity reset; RTA preserved; history view intact
- End state: new month dashboard accurate

### Edit/void transaction from UI
- Level: e2e
- Initial: transaction exists
- Actions: edit amount/category; then void
- Validations: UI shows single active version; balances update by delta; after void balances revert; history shows prior versions
- End state: UX demonstrates SCD2 without duplicating effects

### Reconciliation UX
- Level: e2e
- Initial: account with known balance
- Actions: reconcile; add erroneous transaction; correct it
- Validations: reconciliation diff surfaces new transaction; after correction diff clears; balances match external
- End state: users can trust reconciliation workflow

## Flakiness and Determinism Requirements
- Fix clock and month boundaries in tests; seed random property tests per run.
- Reset DB per test/spec; use paired transfer entries explicitly.
- Assert on integer minor units and stable error shapes.
- Prefer property/state-machine tests for sequence coverage; E2E limited to critical user journeys.
