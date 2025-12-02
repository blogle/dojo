# SQL Guide — Schema, Migrations, and DuckDB Usage

This guide focuses on **schema design, migrations, and correctness patterns** for DuckDB. Mechanical style (keyword case, `SELECT *`, indentation, etc.) is enforced by `sqlfluff` and formatters and should not be duplicated here.

Use this document when you are:

- Designing or evolving tables.
- Writing migrations.
- Implementing query-heavy features in Python.


## 1. Where SQL Lives

We use a hybrid approach:

- Small, one-off queries may live inline in Python.
- Anything reusable, performance-sensitive, or contract-bearing must live in `.sql` files.

Recommended layout:

    src/dojo/sql/
      migrations/      # schema evolution
      queries/         # canonical read / write paths
      etl/             # batch or maintenance jobs
      seeds/           # dev/demo seeds (never prod)
    tests/fixtures/    # test-only fixtures

Rules:

- If a query is used in multiple places, is non-trivial (joins, windows, CTEs), or is performance-tuned, promote it to a `.sql` file.
- All schema, temporal ledgers, and write-path logic must live in SQL files, not inline Python strings scattered around.


## 2. Migrations: Idempotent, Transactional, and Boring

Migrations are the **only** place we change schema. They must be:

- Idempotent: safe to run more than once.
- Transactional: wrapped in a transaction that fully succeeds or fully fails.
- Logged: recorded in a `schema_migrations` (or equivalent) table.

Rules:

1. One migration file per change, under `sql/migrations/` with a timestamped name, for example:

       sql/migrations/V20251130_01_add_transactions_table.sql

2. Use `IF [NOT] EXISTS` defensively:

       BEGIN;

       CREATE TABLE IF NOT EXISTS transactions (
           transaction_id      TEXT PRIMARY KEY,
           account_id          TEXT NOT NULL,
           amount_minor        BIGINT NOT NULL,
           transaction_date    DATE NOT NULL,
           recorded_at         TIMESTAMP NOT NULL,
           is_active           BOOLEAN NOT NULL
       );

       ALTER TABLE transactions
           ADD COLUMN IF NOT EXISTS memo TEXT;

       COMMIT;

3. Never mix schema changes with demo or dev data. Migrations are allowed to:

   - Create/alter tables and indexes.
   - Backfill or transform existing rows as part of a schema change.
   - Update audit columns as needed.

   Migrations are not allowed to:

   - Insert demo accounts or sample households.
   - Seed example budgets, categories, or test data.

   Those belong in seeds/fixtures.

4. Always wrap multi-step changes (backfills, table rewrites, index creation) in a transaction and roll back on failure.

5. Use a `schema_migrations` table to track applied versions. The Python migration runner is a thin orchestrator that:

   - Reads unapplied `V*.sql` files in order.
   - Executes each inside a transaction.
   - Records success/failure in `schema_migrations`.

6. Separate heavy DML from index/constraint creation:

   - Do not place `CREATE INDEX`/`CREATE UNIQUE INDEX` in the same transaction as `INSERT`/`UPDATE`/`DELETE` backfills; DuckDB rejects indexes with outstanding updates.
   - Prefer one concern per file: schema evolution, data backfill, then indexes in a follow-up file after prior changes have committed.
   - Make statements deterministic (no time-based defaults or non-repeatable selects) so reruns under `schema_migrations` are safe.

7. File ordering and execution:

   - Filenames must be zero-padded and strictly sequential with no gaps (for example `0001_core.sql`, `0002_account_classes.sql`, ...). The runner validates numbering and fails fast on gaps or non-numeric prefixes.
   - Use the runner CLI: `python -m dojo.core.migrate --database /path/to/db.duckdb [--target FILENAME] [--log-plan] [--dry-run]`. `--target` stops after a specific file for upgrade rehearsals; `--log-plan` prints per-file/per-statement execution.
   - `scripts/run-migrations-check [--log-plan]` applies migrations to a temp DB and should be used in CI/local preflight. CI also rehearse-upgrades by applying migrations to a DB seeded to a prior target before running the full set.
   - Production should run migrations out-of-band (init container or job) with `DOJO_RUN_STARTUP_MIGRATIONS=false`; dev/test may set `DOJO_RUN_STARTUP_MIGRATIONS=true` for convenience (see flake shellHook). Before production migrations, take a file copy backup (for example `cp /data/ledger.duckdb /data/ledger.duckdb.bak.$(date +%s)`). The deployment init container performs this backup automatically.


## 3. Seeds vs Fixtures vs Production Data

We separate three concepts:

1. Migrations (`sql/migrations/`)

   - Define and evolve schema.
   - Idempotent, production-safe.
   - No demo or test-only data.

2. Dev/demo seeds (`sql/seeds/`)

   - Insert realistic but fake data for humans to play with.
   - May include sample households, accounts, budgets.
   - Must be idempotent (`INSERT ... ON CONFLICT` or equivalent).
   - Never run in production.

3. Test fixtures (`tests/fixtures/*.sql`)

   - Minimal, deterministic datasets used in automated tests.
   - Tailored to each test suite; not shared across unrelated tests.
   - Loaded by test harnesses (Python or Cypress) before tests run.

Rules:

- Do not reuse dev seeds as test fixtures. Test fixtures should be tiny and explicit so failures are easy to reason about.
- Do not reference fixture tables from production code. Fixtures are for tests only.


## 4. Temporal and Auditable Tables

The ledger is temporal: we treat important tables as **append-only with versions**, not mutable rows.

For temporal tables (for example, `transactions`, `positions`):

- Each logical entity has:
  - A stable conceptual ID (`transaction_id`, `position_id`).
  - A `recorded_at` timestamp (system time of the version).
  - An `is_active` flag or `[valid_from, valid_to)` pair.

- Never overwrite or delete rows to “edit” history. Instead:
  - Close the prior version (`is_active = FALSE` or `valid_to = now()`).
  - Insert a new version with the updated values.

Example pattern (simplified SCD2):

    BEGIN;

    UPDATE transactions
    SET is_active = FALSE
    WHERE transaction_id = $transaction_id
      AND is_active = TRUE;

    INSERT INTO transactions (
        transaction_id,
        account_id,
        amount_minor,
        transaction_date,
        recorded_at,
        is_active
    )
    VALUES (
        $transaction_id,
        $account_id,
        $amount_minor,
        $transaction_date,
        now(),
        TRUE
    );

    COMMIT;

When querying:

- For “current state”, filter `WHERE is_active = TRUE`.
- For “as-of” reconstructions, pick the row with the latest `recorded_at <= AS_OF` per conceptual ID and respect `is_active` (or `valid_to > AS_OF` for range-based tables).

Implement complex as-of logic once and reuse it (views or canonical queries under `sql/queries/`).


## 5. Transactions and Stage-Then-Swap

For small updates, a regular `BEGIN; ... COMMIT;` is enough.

For heavy rewrites (for example, rebuilding a summary table):

- Write into a staging table.
- Validate.
- Swap in a single transaction.

Pattern:

    -- Build staging table
    CREATE OR REPLACE TABLE balances__staging AS
    SELECT
        account_id,
        SUM(amount_minor) AS balance_minor
    FROM transactions
    WHERE is_active = TRUE
    GROUP BY account_id;

    -- Optional: validate counts, ranges, etc.

    BEGIN;

    DROP TABLE IF EXISTS balances__backup;
    ALTER TABLE balances RENAME TO balances__backup;
    ALTER TABLE balances__staging RENAME TO balances;

    COMMIT;

Rules:

- Never silently truncate or rewrite a core table in place without a staging/backup step.
- Always validate (counts, sums, ranges) before or immediately after the swap.
- Keep swaps fast to minimize lock times.


## 6. Compute Placement: SQL vs Python

Default posture:

- Use SQL for joins, filters, group-bys, windows, and aggregations.
- Use Python (Pandas/Numpy) for specialized math on small, aggregated result sets.

Rules:

- Avoid pulling large raw tables into Python just to group or aggregate; do that in SQL and return a small, tidy result.
- Only reach for DuckDB Python UDFs when:
  - You can’t express the logic in SQL reasonably, and
  - The data volume is small enough that the UDF cost is acceptable.
- When you do use UDFs, test them specifically and document their semantics.


## 7. Query Contracts and Reuse

For core flows (ledger, budgets, net worth):

- Define canonical queries in `sql/queries/` and call them via DAOs.
- Avoid “just one little inline query” in random modules for important behavior.

Examples:

- Canonical query for current balances.
- Canonical query for month-to-date activity by category.
- Canonical query for net worth over time.

When you need a new core behavior, either:

- Extend an existing canonical query, or
- Add a new one and wire it through a DAO so it’s discoverable and testable.


## 8. Auditing and Observability

Important tables (for example, ledger-related tables) should include:

- `created_at` and `updated_at`.
- `source` (where the row came from: API, import job, seed).
- `job_id` or similar for batch jobs.
- Optional `row_hash` when you need strong integrity checks.

Rules:

- Populate audit columns in migrations and seeds where relevant.
- When backfilling, record a clear `source` (for example, `migration_20251130_add_positions`).
- Don’t silently overwrite audit columns; treat them as part of the contract.


## 9. What Linters Cover (So We Don’t Repeat It Here)

The following are enforced by `sqlfluff` / formatters and should not be duplicated as prose rules:

- Keyword casing and consistent spacing.
- Avoiding `SELECT *` in app code where the linter is configured to forbid it.
- Disallowing unparameterized literals where we expect binds.
- Style conventions (snake_case, clause-per-line, etc.).

If a mechanical SQL pattern bothers you, first check whether we can enforce it via linter configuration. This doc should stay focused on **schema design, migrations, temporal semantics, and transaction patterns**.


## 10. Testing SQL

When adding or changing SQL:

- Add tests (Python or DuckDB-only) that:
  - Load small fixture `.sql` files.
  - Exercise the query or migration.
  - Assert on specific rows or aggregates, not just “no exception”.

For migrations that change data:

- Include tests that:
  - Start from a pre-migration fixture.
  - Apply the migration.
  - Assert that schema matches expectations and that key invariants hold (no lost transactions, no negative balances beyond what is allowed, etc.).

This is how we prove that migrations and queries are safe, not just syntactically valid.

