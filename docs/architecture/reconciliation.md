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

## Detecting Historical Drift (SCD2 Integration)

A key feature of this design is using the SCD2 ledger to detect if previously reconciled history has been tampered with.

Since `account_reconciliations` records the `created_at` timestamp of the verification, we can detect "Backdated Changes" (Drift).

**The Drift Query:**
We must identify any transaction *version* that affects the reconciled period (`date <= Last_Reconciliation.statement_date`) but was created or retired *after* the reconciliation occurred (`> Last_Reconciliation.created_at`).

This covers:
1.  **New Backdated Transactions:** `valid_from > Last_Commit` AND `date <= Last_Statement_Date`.
2.  **Modifications/Deletions of Reconciled Items:** `valid_to > Last_Commit` AND `date <= Last_Statement_Date`.
3.  **Moving Items Out of Period:** The old version (which was in the period) will be caught by rule #2.
4.  **Moving Items Into Period:** The new version (which is now in the period) will be caught by rule #1.

> **Drift =** Any `concept_id` where at least one version matches:
> `(valid_from > Last_Commit OR valid_to > Last_Commit) AND transaction_date <= Last_Statement_Date`

These changes represent corruptions of the reconciled state and must be presented to the user as a "Drift Report" to be resolved (usually by accepting the new balance) before a new reconciliation can be finalized.

## Invariants

1.  **Never Automatic:** The system never auto-creates adjustment transactions. Discrepancies must be resolved by finding the user error.
2.  **Point-in-Time:** A reconciliation is an assertion about the state of the ledger at `created_at`.
3.  **Continuity:** The "Starting Balance" for the next reconciliation is the "Ending Balance" of the previous one.

## API Changes

-   `POST /api/accounts/{id}/reconciliations`: Create a new reconciliation (commit).
-   `GET /api/accounts/{id}/reconciliations/latest`: Get the last checkpoint to determine the starting point.
-   `GET /api/accounts/{id}/reconciliations/drift`: specific query to find SCD2 diffs since the last reconciliation.
