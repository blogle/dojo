# Behavioral Test Suite Specification

This document outlines a comprehensive suite of behavior-focused tests for the Dojo personal finance application. It is designed to verify the correctness, reliability, and financial integrity of the system, spanning from unit/property tests to end-to-end user journeys.

**Goal:** Ensure 100% confidence in financial math, ledger integrity, and SCD2 temporal correctness.

---

## 1. Property-Based Tests (Invariants)

These tests assert that fundamental rules of the system hold true under *any* sequence of valid operations. They should be implemented using `hypothesis` or similar property-based testing tools.

### 1.1 The Fundamental Budget Equation
**Invariant:** `Available = (Carryover + Allocations + Activity)` for every category, in every month.
*   **Scope:** Budgeting Domain.
*   **Property:**
    For any sequence of:
    -   Allocations (positive/negative)
    -   Transactions (inflows/outflows)
    -   Month rollovers
    The "Available" balance of a category in month `M` must equal:
    `Available(M-1) + Allocations(M) + Activity(M)`
*   **Constraint:** `Available(M-1)` includes negative balances. If a category is overspent in month `M-1`, that negative amount carries over to month `M`, reducing the available funds.

### 1.2 The Global Zero-Sum (RTA Invariant)
**Invariant:** `Total Cash in On-Budget Accounts = Total Available in Envelopes + RTA + Future Allocations`.
*   **Scope:** Budgeting / Accounts.
*   **Property:**
    Sum of `current_balance` of all `is_active` on-budget accounts must equal:
    Sum of `available_balance` of all categories in current month
    + `RTA` (Ready to Assign)
    + Funds assigned in future months (stealing from the future)
*   **Validation:** This ensures no money is created or destroyed outside the double-entry system.

### 1.3 SCD2 Temporal Integrity & Churn
**Invariant:** Time must be continuous and non-overlapping for any single entity, and history must be immutable yet correctable.
*   **Scope:** Transactions, Allocations, Accounts.
*   **Property:**
    For any entity (identified by a stable `concept_id`):
    -   Versions must form a continuous chain: `Version[i].valid_to == Version[i+1].valid_from`.
    -   Exactly one version has `is_active = True`.
    -   The latest version has `valid_to = "infinity"` (e.g., 9999-12-31).
    -   No gaps, no overlaps.

*   **Fuzzing A: Transaction Churn**
    Randomized sequence of Add/Edit/Delete on *Transactions*.
    **Validation:**
    -   `Net Worth` matches `Sum(Assets) - Sum(Liabilities)`.
    -   `Category.activity` matches sum of active transactions for that category.
    -   `Category.available` updates correctly based on new activity.

*   **Fuzzing B: Allocation Churn**
    Randomized sequence of Add/Edit/Delete on *Budget Allocations*.
    **Validation:**
    -   `RTA` matches `Total Cash - Sum(Active Allocations)`.
    -   `Category.budgeted` matches sum of active allocations for that category.
    -   `Category.available` matches `Carryover + Budgeted + Activity`.
    -   **Invariant:** `RTA` cannot be negative (unless explicitly allowed by config, but strictly tracked).

### 1.4 Net Worth Aggregation
**Invariant:** `Net Worth = Sum(Assets) - Sum(Liabilities)`.
*   **Scope:** Net Worth Domain.
*   **Property:**
    The calculated Net Worth must equal the sum of:
    -   `current_balance` of all Asset accounts (Cash, Investment, Property)
    -   MINUS `current_balance` (absolute value) of all Liability accounts (Credit Cards, Loans)
    *   **Specific Check:** Ensure `is_active=False` accounts are excluded unless historical queries are performed.

---

## 2. Onboarding & Account Lifecycle Tests

Tests covering the creation and initialization of financial entities.

### 2.1 Account Creation & Opening Balance
**Scenario:** User creates a new Checking Account with a starting balance.
*   **Initial State:** No accounts.
*   **Action:** Create "Chase Checking" (On-Budget) with balance $1,000.00.
*   **Validations:**
    1.  `accounts` table has 1 row: "Chase Checking", balance 100000 (minor units).
    2.  `transactions` table has 1 row: "Opening Balance", inflow 100000, Category="Opening Balance".
    3.  **RTA Impact:** RTA increases by $1,000.00 immediately.
    4.  **Net Worth:** Increases by $1,000.00.

### 2.2 Credit Card Onboarding (Liability)
**Scenario:** User onboards a Credit Card with existing debt.
*   **Initial State:** RTA = $0.
*   **Action:** Create "Amex Gold" (Liability) with balance -$500.00.
*   **Validations:**
    1.  `accounts` table has 1 row: "Amex Gold", balance -50000.
    2.  `transactions` table has 1 row: "Opening Balance", outflow 50000.
    3.  **RTA Impact:** RTA remains $0. (Pre-existing debt is not budgeted spending yet).
    4.  **Net Worth:** Decreases by $500.00.
    5.  **Category Impact:** No category activity generated (assigned to "Opening Balance" or implicit debt category).

### 2.3 Tracking Account (Mortgage) Onboarding
**Scenario:** User adds a Mortgage tracking account.
*   **Initial State:** RTA = $5000.
*   **Action:** Create "Mortgage" (Liability, Off-Budget/Tracking) with balance -$350,000.
*   **Validations:**
    1.  `accounts` table entry exists.
    2.  **RTA Impact:** RTA remains $5000. (Off-budget accounts never touch RTA).
    3.  **Activity Impact:** No "spending" activity recorded in budget.
    4.  **Net Worth:** Decreases by $350,000.

---

## 3. Daily Operations: Transaction & Budgeting Logic

Tests covering the "Meat and Potatoes" of the app.

### 3.1 Income & RTA Assignment
**Scenario:** User receives a paycheck and assigns it.
*   **Initial State:** Checking = $100, RTA = $0.
*   **Action:**
    1.  Add Transaction: Inflow $2,000 to Checking, Category = "Available to Budget" (Income).
    2.  Allocate $1,000 to "Rent".
    3.  Allocate $500 to "Groceries".
*   **Validations:**
    1.  **Intermediate RTA:** After step 1, RTA = $2,000.
    2.  **Final RTA:** After step 3, RTA = $500.
    3.  **Balances:** Checking = $2,100.
    4.  **Category Available:** Rent = $1,000, Groceries = $500.

### 3.2 Credit Card Spending (Funded)
**Scenario:** Spending money already budgeted for Groceries using a Credit Card.
*   **Initial State:**
    -   Credit Card Balance = $0.
    -   Groceries Available = $100.
    -   "CC Payment" Category Available = $0.
*   **Action:** Add Transaction: Outflow $40 from Credit Card, Category = "Groceries".
*   **Validations:**
    1.  **Account:** Credit Card Balance = -$40.
    2.  **Category Activity:** Groceries Activity = -$40.
    3.  **Category Available:** Groceries Available = $60 ($100 - $40).
    4.  **Payment Movement:** "CC Payment" Category Available = $40. (Money moved from Groceries to Payment to cover the debt).
    5.  **RTA:** Unchanged.

### 3.3 Credit Card Spending (Overspending)
**Scenario:** Spending more than available on Credit Card.
*   **Initial State:**
    -   Credit Card Balance = $0.
    -   Dining Out Available = $20.
*   **Action:** Add Transaction: Outflow $50 from Credit Card, Category = "Dining Out".
*   **Validations:**
    1.  **Account:** Credit Card Balance = -$50.
    2.  **Category Available:** Dining Out = $0 (or -$30 depending on strict envelope rules, usually 0 with an "Overspent" indicator).
    3.  **Payment Movement:** "CC Payment" Category Available = $20 (Only covered amount moves).
    4.  **Debt Creation:** $30 becomes new debt (uncategorized/unfunded debt).

### 3.4 Transfer to Tracking Account (Spending)
**Scenario:** Paying the Mortgage from Checking.
*   **Initial State:**
    -   Checking = $5,000.
    -   Mortgage (Tracking) = -$200,000.
    -   "Mortgage Payment" Category Available = $2,000.
*   **Action:**
    1.  Transfer $2,000 from Checking to Mortgage.
    2.  Category = "Mortgage Payment".
*   **Validations:**
    1.  **Checking:** Decreases to $3,000.
    2.  **Mortgage:** Increases to -$198,000.
    3.  **Budget Impact:** Treated as *Spending*. "Mortgage Payment" Activity = -$2,000. Available = $0.
    4.  **Net Worth:** Unchanged (Asset -2000, Liability +2000).

---

## 4. SCD2 & Temporal Corrections

Tests ensuring that editing history correctly propagates changes without corrupting the ledger.

### 4.1 Editing a Past Transaction (Amount)
**Scenario:** User corrects a typo in a transaction from last month.
*   **Initial State:**
    -   Month: Feb (Current).
    -   Jan Transaction: -$50 (Groceries).
    -   Jan Groceries Balance: $0 remaining.
    -   Feb Groceries Carryover: $0.
*   **Action:** Edit Jan Transaction: Change amount from -$50 to -$40.
*   **Validations:**
    1.  **Jan Ledger:**
        -   Old transaction marked `is_active=False`.
        -   New transaction (-$40) inserted `is_active=True`.
    2.  **Jan Budget:** Groceries Activity changes from -$50 to -$40.
    3.  **Jan Available:** Groceries Available increases by $10.
    4.  **Feb Carryover:** Feb Groceries Starting Balance increases by $10.
    5.  **Feb Available:** Feb Groceries Available increases by $10.

### 4.2 Changing Transaction Category (Past)
**Scenario:** Moving a transaction from "Dining" to "Groceries" in the past.
*   **Initial State:** Transaction -$100 in "Dining".
*   **Action:** Edit Category to "Groceries".
*   **Validations:**
    1.  **Dining:** Activity decreases (gets closer to 0), Available increases.
    2.  **Groceries:** Activity increases (more negative), Available decreases.
    3.  **Roll-over:** Future months reflect the change in available carryover for *both* categories.

### 4.3 Backdated Transaction Insertion
**Scenario:** User forgot to enter a transaction from 2 months ago.
*   **Action:** Insert new transaction dated T-60 days.
*   **Validations:**
    1.  Transaction is inserted with correct `transaction_date` but `recorded_at` is NOW.
    2.  Budget balances for T-60 days (Month M-2), Month M-1, and Month M (Current) are all recalculated and updated.
    3.  Account running balance is updated for all subsequent transactions (if running balance is materialized, otherwise computed on fly).

---

## 5. Account Transfers & Reconciliations

### 5.1 On-Budget Transfers (Neutrality)
**Scenario:** Transfer $500 from Checking to Savings (both On-Budget).
*   **Initial State:** Checking $1000, Savings $0. RTA $0.
*   **Action:** Transfer $500 Checking -> Savings.
*   **Validations:**
    1.  Checking = $500.
    2.  Savings = $500.
    3.  **RTA:** Unchanged ($0).
    4.  **Categories:** No category required (or special "Transfer" category that has no budget impact).
    5.  **Net Worth:** Unchanged.

### 5.2 Reconciliation Adjustment
**Scenario:** User reconciles account, finding a $5 discrepancy.
*   **Initial State:** App Balance $95. Bank Balance $100.
*   **Action:** Create Reconciliation Adjustment (Inflow $5).
*   **Validations:**
    1.  Creates a transaction for $5.
    2.  Category defaults to "Inflow: RTA" (increasing RTA) or requires categorization (e.g., "Interest Income" or "Misc").
    3.  Account Balance updates to $100.

---

## 6. Edge Cases & Stress Tests

### 6.1 Deleting a Category with Activity
**Scenario:** User attempts to delete a category that has transactions.
*   **Action:** Delete Category "Old Expenses".
*   **Validations:**
    -   **Option A (Block):** Error "Cannot delete category with transactions".
    -   **Option B (Merge):** Prompt user to reassign transactions to another category.
    -   **Invariant:** Transactions must never be orphaned (null category).

### 6.2 Massive Scale (Stress Test)
**Scenario:** 10,000 transactions over 10 years.
*   **Action:** Generate synthetic history.
*   **Validation:**
    -   RTA calculation returns in < 200ms.
    -   Net Worth query returns in < 100ms.
    -   Running balance calculation remains accurate to the penny.

### 6.3 Currency Precision
**Scenario:** Fractional cents / Rounding.
*   **Action:** Split a $10.00 transaction between 3 people ($3.3333...).
*   **Validations:**
    -   System enforces integer minor units.
    -   User must explicitly handle the penny (3.33, 3.33, 3.34).
    -   No floating point drift (e.g., 3.3333333 stored).

---

## 7. Integration Tests

Tests covering multi-step service workflows to ensure domain components interact correctly.

### 7.1 Payday Routine
**Scenario:** Full flow from income receipt to zero-based allocation.
*   **Action:**
    1.  Record Paycheck Inflow (increases RTA).
    2.  Check "Underfunded" amount for current month.
    3.  Auto-assign funds to match goals/targets.
    4.  Manually adjust remaining funds to zero out RTA.
*   **Validations:**
    -   `RTA` becomes 0.
    -   `Budgeted` column increases by exact inflow amount.
    -   `Available` column reflects new totals.

### 7.2 End-of-Month Reconciliation
**Scenario:** Locking in the month and verifying roll-over.
*   **Context:** Simulated environment (no external bank connection). User manually asserts the "Bank Balance".
*   **Action:**
    1.  User enters simulated Bank Balance matching App Balance.
    2.  System marks account as Reconciled at timestamp `T`.
    3.  User advances to Month + 1.
*   **Validations:**
    -   Negative Available amounts in Month M carry over to reduce Available in Month M+1.
    -   Positive Available amounts in Month M carry over to increase Available in Month M+1.
    -   `RTA` in Month M+1 reflects any "Income for Next Month" or over-budgeting in Month M.

### 7.3 Data Correction & Budget Consistency
**Scenario:** Correcting a mis-categorized transaction and verifying downstream budget updates.
*   **Initial State:** Transaction T1 (-$100) assigned to "Dining". "Dining" Available = $0. "Groceries" Available = $500.
*   **Action:** User edits T1 -> reassigns to "Groceries".
*   **Validations:**
    -   **Dining Budget:** Activity decreases ($-100 -> $0). Available increases ($0 -> $100).
    -   **Groceries Budget:** Activity increases ($0 -> -$100). Available decreases ($500 -> $400).
    -   **Ledger Invariant:** Sum of all category activity = Sum of all expense transactions.
    -   **History:** "Dining" history shows correction; "Groceries" history shows correction.
