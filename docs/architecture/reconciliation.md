# Reconciliation Specification

## Overview

Reconciliation is the manual process of ensuring the Dojo ledger matches the external source of truth (bank statement). It serves as a "checkpoint" or "commit" in the financial history. When an account is reconciled, the user asserts that the cleared balance in Dojo matches the bank's balance at a specific point in time.

## Core Concepts

-   **Source of Truth:** The real-world bank or brokerage statement.
-   **Cleared Balance:** The sum of all transactions in Dojo marked as `status = 'cleared'`.
-   **Statement Balance:** The ending balance on the bank statement.
-   **Reconciliation Event:** A persistent record (commit) that signifies the Cleared Balance equaled the Statement Balance at a specific timestamp.
-   **Discrepancy:** The difference between the Cleared Balance and Statement Balance. This must be zero to complete a reconciliation.

## Data Model

### `account_reconciliations` Table

This table stores the history of successful reconciliations.

| Column | Type | Description |
| :--- | :--- | :--- |
| `reconciliation_id` | `UUID` (PK) | Unique identifier for the reconciliation event. |
| `account_id` | `TEXT` (FK) | The account being reconciled. |
| `created_at` | `TIMESTAMP` | System time when the reconciliation was completed (the "commit" timestamp). |
| `statement_date` | `DATE` | The "as of" date from the bank statement. |
| `statement_balance_minor` | `BIGINT` | The balance confirmed by the user from the statement. |
| `previous_reconciliation_id` | `UUID` (FK, Nullable) | Pointer to the previous reconciliation for continuity. |

## Workflow

1.  **Initiation:** User selects an account and provides the `statement_date` and `statement_balance` from their bank statement.
2.  **Matching (The "Work"):**
    -   The system displays a list of *uncleared* transactions up to `statement_date`.
    -   User compares these against the bank statement.
    -   User marks transactions as `cleared` in Dojo as they are found on the statement.
    -   If a transaction is missing in Dojo, the user creates it.
    -   If a transaction has the wrong amount, the user edits it.
3.  **Validation:**
    -   The system continuously calculates: `Difference = Statement Balance - Sum(All Cleared Transactions)`.
    -   The "Finish Reconciliation" action is disabled until `Difference == 0`.
4.  **Commit:**
    -   User clicks "Finish".
    -   A new row is inserted into `account_reconciliations`.
    -   The system may optionally "lock" reconciled transactions (prevent editing without explicit warning) - *Implementation TBD*.

## The Reconciliation Worksheet (The Diff)

There is no separation between a "Diff Report" and a "Worksheet". There is only **The Reconciliation Worksheet**.

The Worksheet presents the user with the set of transactions that explain the difference between the **Last Reconciled State** and the **Current Statement**.

### The Query Logic

The Worksheet contains all **Active** transaction versions that meet *either* of these criteria:

1.  **New or Modified Since Last Commit:** Any transaction where the current version was created *after* the last reconciliation (`recorded_at > Last_Commit`).
    *   This catches **new transactions** added since the 1st.
    *   This catches **modifications** to previously pending items (e.g., the tip adjustment from $20 -> $25).
    *   This catches **corrections** to previously reconciled items (e.g., fixing a wrong date).
2.  **Pending from Previous Cycle:** Any transaction that existed before the last commit but was left as `status='pending'` (or `uncleared`).
    *   This catches the $20 pending charge from the 1st that hasn't changed yet.

> **Worksheet Query:**
> ```sql
> SELECT * FROM transactions
> WHERE is_active = TRUE
> AND (
>   recorded_at > Last_Reconciliation.created_at  -- Created/Modified since last time
>   OR
>   status != 'cleared'                           -- Still pending from before
> )
> ORDER BY transaction_date
> ```

### The User Experience

When the user starts a reconciliation for the 5th of the month:
1.  They see the $25 cleared charge (modified from $20). It appears because `recorded_at > Last_Commit`.
2.  They see the 10 new rows added between the 1st and 5th. They appear because `recorded_at > Last_Commit`.
3.  They see the corrected transaction with the new date. It appears because its new version has `recorded_at > Last_Commit`.

The user's task is simply to review this list against their bank statement.
-   If the $25 matches the bank, they mark it `cleared`.
-   If the 10 new rows match, they mark them `cleared`.
-   Once the calculated **Cleared Balance** matches the **Statement Balance**, they commit.

## Invariants

1.  **Never Automatic:** The system never auto-creates adjustment transactions. Discrepancies must be resolved by finding the user error.
2.  **Point-in-Time:** A reconciliation is an assertion about the state of the ledger at `created_at`.
3.  **Continuity:** The "Starting Balance" for the next reconciliation is the "Ending Balance" of the previous one.

## API Changes

-   `POST /api/accounts/{id}/reconciliations`: Create a new reconciliation (commit).
-   `GET /api/accounts/{id}/reconciliations/latest`: Get the last checkpoint to determine the starting point.
-   `GET /api/accounts/{id}/reconciliations/diff`: specific query to find SCD2 diffs since the last reconciliation.
