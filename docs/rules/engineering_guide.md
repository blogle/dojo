# Engineering Implementation Guide

This guide establishes the mandatory standards, patterns, and principles for developing the application's backend logic. Its primary focus is to ensure data integrity and correct usage of the DuckDB single-store architecture and the temporal data model.

## 1. DuckDB Connectivity and Management

### Connection Principle (Single-Threaded Access)

DuckDB is designed for high-speed analytical processing within a single process. To ensure stability and prevent concurrency issues in a multithreaded environment like FastAPI, developers must **never** use a long-lived, global database connection.

Instead, the application must:

-   Provide a dependency injection function (e.g., a FastAPI `Depends` function) that creates a new, temporary connection to the `/data/app.duckdb` file for the duration of a single API request.
-   The connection **must** be explicitly closed upon the completion or failure of the request.

### Data Writes: The Atomic Transaction Mandate

All operations that involve writing or modifying data across multiple steps (e.g., creating a transaction, editing an investment position) **must** be wrapped in a single, atomic SQL transaction block.

This ensures that the application state is never partially updated, and that if any step fails (e.g., an update to an account balance), all preceding operations are automatically rolled back.

```sql
BEGIN;

-- All INSERT/UPDATE statements here

COMMIT;
-- If any statement fails, the transaction is automatically rolled back.
```

## 2. Temporal Data Model (SCD Type 2) Implementation

The core principle is **immutability and versioning**. The `transactions` and `positions` tables are temporal; developers **must not** use standard `UPDATE` or `DELETE` on them.

### Rule 1: Creating a New Record

A new record is always an `INSERT` statement. The record must include the following metadata:

-   A unique conceptual identifier (`transaction_id` or `position_id`) shared by all versions of that record.
-   The system time of creation (`recorded_at` timestamp).
-   The flag `is_active` set to `TRUE`.

### Rule 2: Modifying an Existing Record (The Correction Flow)

To correct or modify an existing active record, developers must execute a two-step, atomic transaction:

1.  **Close the Old Version**: Execute an `UPDATE` on the old version, setting its `is_active` flag to `FALSE`. The `WHERE` clause must target the `transaction_id` AND the current `is_active = TRUE` flag.
2.  **Insert the New Version**: Execute a new `INSERT` of the corrected data, setting the new row's `is_active` flag to `TRUE` and providing a new `recorded_at` timestamp.

### Rule 3: Deleting a Record (Soft Deletion)

Records are **never** physically deleted. To remove a record, developers must execute an atomic transaction to:

1.  **Close the Active Version**: Execute an `UPDATE` on the active version, setting its `is_active` flag to `FALSE`.
2.  **Recalculate State**: Update any dependent state tables (e.g., `accounts` or `budgets`) to remove the effect of the transaction.

## 3. Querying Temporal Data (Time Travel)

When retrieving data for reports, dashboards, or reconciliation, developers must remember they are querying history, not just the current state.

### Current State Queries

For displaying the current ledger, only query records where the `is_active` flag is `TRUE`.

### Historical Queries (Reconciliation)

When reconstructing the application's state as it existed at a specific historical point in time (`AS_OF_DATE`), the query must use the following pattern:

1.  Identify all records where the `recorded_at` timestamp is before or equal to `AS_OF_DATE`.
2.  Group these records by the conceptual ID (`transaction_id`).
3.  Within each group, select only the record with the maximum (`MAX`) `recorded_at` timestamp.
4.  Filter this result set to exclude any records that were soft-deleted (i.e., those where the final version at that time was an `is_active = FALSE` record).

This complex logic **must** be abstracted into reusable functions within the domain's `service.py` file to prevent errors.
