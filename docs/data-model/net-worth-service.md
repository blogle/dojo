# Net Worth Service Data Model

*See also: [Global Data Model Overview](./overview.md)*

The Net Worth Service is a read-only, computational service responsible for calculating and reporting on a user's net worth over time. Unlike other services, it does not own any tables. Instead, it reads data from tables owned by the Accounts, Investments, and Transactions services to generate its reports.

## Tables Owned by the Net Worth Service

The Net Worth Service owns **no tables**. It is purely a consumer of data from other parts of the system.

## Shared Tables Used by the Net Worth Service

The service aggregates data from across the entire data model to perform its calculations.

-   **`accounts` (Read-Only):** This is the most critical table for the service. The service queries this table to get a list of all assets and liabilities, along with their current balances.
    -   The `account_type` column is used to distinguish between assets and liabilities.
    -   The `current_balance_minor` column provides the value for most accounts.
-   **`positions` (Read-Only):** For investment accounts, the `accounts.current_balance_minor` is a cache. The Net Worth service may read directly from the `positions` table to get the most accurate, up-to-date market value of all investment holdings, which are then summed to determine the total value of investment accounts.
-   **`tangible_assets` / `tangible_asset_details` (Read-Only):** To include the value of physical assets like real estate, the service reads the `current_fair_value_minor` from these tables.
-   **`transactions` (Read-Only):** To calculate historical net worth, the service needs to be able to reconstruct account balances at a specific point in time. It does this by reading the transaction log up to the desired date.

## Core Operations and Their Data Flows

The Net Worth Service's operations are read-only queries that aggregate data.

### 1. Calculating Current Net Worth

This is the primary operation of the service.

-   **Inputs:** None.
-   **Sequence of SQL Changes:** This is a read-only operation and involves no SQL changes. The logical query process is as follows:
    1.  **Sum all Assets:**
        -   Query the `accounts` table for all rows where `account_type = 'asset'`.
        -   Sum the `current_balance_minor` for all these accounts.
    2.  **Sum all Liabilities:**
        -   Query the `accounts` table for all rows where `account_type = 'liability'`.
        -   Sum the `current_balance_minor` for all these accounts.
    3.  **Calculate Net Worth:**
        -   The final net worth is `(Sum of Assets) - (Sum of Liabilities)`.

### 2. Calculating Historical Net Worth

This operation provides a snapshot of net worth at some point in the past.

-   **Inputs:** A specific date (`snapshot_date`).
-   **Logical Query Process:**
    1.  For each `account_id` in the `accounts` table:
        a.  Query the `transactions` table.
        b.  Sum the `amount_minor` for all transactions belonging to that account where `transaction_date` is on or before the `snapshot_date`. This gives the historical balance for that account.
    2.  Once the historical balance for every account is known, the process is the same as calculating the current net worth: sum the asset balances, sum the liability balances, and find the difference.

## Invariants

-   **Computational Integrity:** The Net Worth Service relies on the invariants of the other services being upheld. Its correctness is entirely dependent on:
    -   The `accounts.current_balance_minor` cache being consistent with the `transactions` log.
    -   The sum of `positions.market_value_minor` for an investment account being correctly reflected in that account's balance.
-   **Asset/Liability Classification:** The calculation depends on every account being correctly classified as either an `asset` or a `liability`.
