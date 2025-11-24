SQL Best Practices for Python Codebases


## Scope and Intent

This document sets a pragmatic standard for writing, organizing, testing, and operating SQL—specifically with DuckDB—inside a Python project. It aims to be actionable for everyday engineering and durable enough to live in developer docs or a README. Where practices involve judgment, we provide clear decision criteria, examples, and anti-patterns. All guidance assumes a modest concurrency environment and that DuckDB tables are the curated data store for the application.


## Guiding Principles

Write SQL that is explicit, testable, and composable. Prefer set-based transformations, keep data close to the compute, and evolve schemas with idempotent migrations guarded by transactions. Optimize for pushdown and minimal data movement. Make correctness measurable with unit and property tests. Where performance matters, optimize layout and materialization—not just query text.


## Where SQL Lives (Hybrid: Inline + Files)

Small, local queries may live inline in Python; reusable or complex queries must be first-class `.sql` files.

Promotion rules (when a query “graduates” to a `.sql` file):

- Reuse: The query is used in ≥2 places or call sites.
- Complexity: The query has a CTE and a join, or uses window functions, or spans > ~12 logical lines.
- Contract-bearing: Downstream jobs depend on its exact columns/semantics (e.g., a canonical view).
- Performance-tuned: The query required EXPLAIN/ANALYZE work, layout assumptions, or materialization.
- Write paths & migrations: All DDL and DML for ETL/migrations live in `.sql`.
- Security/policy sensitive: The query enforces business rules or filters PII/roles.

Inline is acceptable when the query is ≤ ~6 lines, read only, and tightly scoped to nearby code (e.g., fetching a single row by key).

Recommended layout for package data:

- src/dojo/sql/<domain>/<name>.sql
- src/dojo/sql/migrations/VYYYYMMDD__<slug>.sql
- src/dojo/sql/etl/<job>/<step>.sql
- src/dojo/sql/seeds/<scenario>.sql (dev/demo data only)
- tests/fixtures/<feature>.sql (tiny deterministic fixtures)


## Migrations vs Seed Data vs Test Fixtures

Keep three explicit tracks for schema, human-friendly demo data, and automated test fixtures.

- **Migrations (`sql/migrations/`)** define and evolve schema. They must stay idempotent, transactional, and production-safe. They may backfill or transform existing rows but must never ship demo data.
- **Seed scripts (`sql/seeds/`)** exist for developers and demos. They insert realistic but fake accounts/categories so humans can click around. Keep them idempotent (INSERT .. ON CONFLICT) and never run them in production.
- **Fixtures (`tests/fixtures/`)** back tests only. They should be tiny, deterministic datasets loaded during test setup. Never reuse dev/demo seeds here—tests deserve purpose-built data so failures are obvious.

Workflow:

1. Run migrations to create or upgrade a database.
2. Optionally run one or more seed scripts locally/staging to populate fake data.
3. During tests, apply migrations, then load only the minimal fixture files needed for that test suite.

This separation prevents demo data from leaking into production, keeps tests fast, and makes it trivial to start with a clean slate.


## Parameterization & Composition

Use pure SQL with bound parameters (no free-form string interpolation):

- Bind parameters from Python rather than composing literals into SQL.
- Keep dynamic SQL limited to optional clauses that are safely toggled (e.g., adding a filter only if present).
- Avoid heavy templating; if you must, keep a strict allow-list for identifiers and never inline raw values.

Example (good):

    con.execute(
      "SELECT id, amount FROM payments WHERE merchant_id = ? AND date >= ?",
      [merchant_id, start_date]
    )

Anti-pattern (unsafe):

    con.execute(f"SELECT id FROM payments WHERE merchant_id = {merchant_id}")


## Performance in DuckDB: Posture and Heuristics

DuckDB executes vectorized, columnar plans with strong predicate/projection pushdown. Speed comes from reading fewer columns/rows, minimizing materializations, and maintaining helpful sort/layout characteristics.

Adopt these in priority order:

1) Pushdown-first (always)
- Select explicit columns; avoid SELECT * in app code.
- Filter early; push predicates into the scan when possible.
- Prefer EXISTS over IN for correlated membership checks.

2) Data-layout aware (for curated tables)
- Create/refresh curated tables with intentional ordering to support common groupings/filters.
- Choose compact types and consistent encodings; avoid unnecessary casting churn.
- Pre-aggregate hot rollups used in dashboards or repetitive reports.

3) Views + cache tables (selectively)
- Define canonical views for logic clarity.
- Materialize heavy views as tables where latency/SLA requires; refresh via stage-then-swap (see Transactions).

About DuckDB indexes:

- DuckDB supports explicit indexes (e.g., on sort keys or selective predicates). Use them judiciously for point lookups or selective filters on curated tables.
- For analytics, sorted/clustered layout plus pushdown typically dominates; verify index benefit with EXPLAIN/ANALYZE, not assumption.

Minimal EXPLAIN habit:

- Keep a small fixture dataset and occasionally verify that expensive queries exhibit predicate/column pushdown and avoid unnecessary re-scans.


## Compute Placement: SQL vs Pandas/Numpy vs Python UDFs

Default to SQL for set-based operations; use Pandas/Numpy for specialized math on small, post-aggregated frames; reach for Python UDFs sparingly.

Decision cues:

- Joins, filters, group-bys, window functions, pivots: SQL.
- Iterative algorithms, specialized numeric routines, branchy row-wise transforms: reduce in SQL first, then Pandas/Numpy on the smaller result.
- Must stay in SQL but need custom logic: consider a Python UDF only when its scope is small and measured.

Examples:

- Good (pushdown first):

    -- Curate minimal columns before Python
    WITH base AS (
      SELECT order_id, merchant_id, dispatch_date, total_cents
      FROM orders
      WHERE dispatch_date BETWEEN ? AND ?
        AND merchant_id = ?
    )
    SELECT merchant_id, dispatch_date, SUM(total_cents) AS gross_cents
    FROM base
    GROUP BY merchant_id, dispatch_date

- Anti-pattern (shipping the world to Python):

    -- Avoid selecting wide fact tables to Pandas only to re-group there
    SELECT * FROM orders


## Migrations & Schema Evolution (SQL-First, Python-Orchestrated)

All migrations are idempotent `.sql` files executed by a thin Python runner that adds pre/post assertions and transaction control.

Practices:

- Use IF NOT EXISTS/IF EXISTS where appropriate.
- Maintain a schema_migrations table recording applied versions.
- Wrap each migration in a transaction; fail closed.
- Add pre-checks (does input table exist? columns?) and post-checks (row counts, nullability).
- Keep data backfills in separate, explicit steps.

Example (idempotent DDL):

    BEGIN;
    CREATE TABLE IF NOT EXISTS payments (
      id            BIGINT PRIMARY KEY,
      merchant_id   INTEGER NOT NULL,
      amount_cents  BIGINT NOT NULL,
      created_at    TIMESTAMP NOT NULL,
      updated_at    TIMESTAMP NOT NULL
    );
    ALTER TABLE payments
      ADD COLUMN IF NOT EXISTS currency VARCHAR NOT NULL DEFAULT 'USD';
    COMMIT;

Anti-pattern:

    -- Blind “CREATE TABLE” without IF NOT EXISTS; no transaction; no checks.


## Transactions & Safety (Stage-Then-Swap)

Default to transactions for small updates; use stage-then-swap for heavy rewrites or refreshes to avoid partial reads.

Pattern:

- Write results to table__staging.
- Validate: counts, sums/hashes, min/max ranges.
- Swap inside a single transaction:

    BEGIN;
    DROP TABLE IF EXISTS table__backup;
    ALTER TABLE table RENAME TO table__backup;
    ALTER TABLE table__staging RENAME TO table;
    COMMIT;

If validation fails, ROLLBACK and investigate. Prefer a dedicated staging schema or a naming convention; keep swaps predictable and scripted.


## Testing Strategy (Unit + Properties)

Unit tests (fixtures):

- Use an in-memory DuckDB or a temporary file.
- Seed small, deterministic fixtures (including nulls and duplicates).
- Assert schema, key uniqueness, specific cell values, and edge-case behavior.

Property tests (invariants):

- Key uniqueness and non-negativity, conservation (credits = debits), monotonic timestamps, no future dates, controlled null rates, bounded ranges.
- For floats, use explicit tolerances.

Optional (nice to have):

- Perf smoke on fixtures to catch accidental quadratic plans or missing pushdown.


## Data Modeling & Layout

We assume curated data lives in DuckDB tables (no external Parquet). Optimize the layout you materialize:

- Define surrogate keys where appropriate; document business keys.
- Choose minimal column types; avoid accidental BIGINT/DOUBLE creep.
- For hot tables, load or rebuild with ORDER BY on frequent group/filter keys.
- Consider summary marts (daily/weekly rollups) for repeated aggregations, refreshed via stage-then-swap.

Example (curated rebuild):

    CREATE OR REPLACE TABLE orders_curated AS
    SELECT
      CAST(id AS BIGINT)               AS order_id,
      CAST(merchant_id AS INTEGER)     AS merchant_id,
      CAST(total_cents AS BIGINT)      AS total_cents,
      CAST(dispatch_date AS DATE)      AS dispatch_date,
      created_at,
      updated_at
    FROM orders_raw
    WHERE status = 'complete'
    ORDER BY merchant_id, dispatch_date;


## Observability: Audit Columns and Temporal (Valid-Time) Tables

Audit columns:

- created_at, updated_at, source, job_id, version, and optionally a row_hash for integrity.
- Populate/refresh in ETL steps; never backfill silently.

Valid-time (SCD2-style) tables:

- Add valid_from (NOT NULL) and valid_to (NOT NULL, sentinel '9999-12-31'), and a generated is_current flag.
- On change, close the prior version (valid_to = now()) and insert a new row with valid_from = now().
- Point-in-time queries filter: valid_from <= t AND valid_to > t.

Example (upsert pattern):

    -- Close current version
    UPDATE user_config
      SET valid_to = now(), updated_at = now()
    WHERE user_id = ?
      AND valid_to = '9999-12-31';

    -- Insert new version
    INSERT INTO user_config (
      user_id, setting_a, setting_b,
      valid_from, valid_to, created_at, updated_at, source, job_id
    )
    VALUES (?, ?, ?, now(), '9999-12-31', now(), now(), ?, ?);

Anti-pattern:

    -- Overwriting “current” rows in place without closing valid_to; breaks time travel.


## Style & Readability

- Keywords UPPERCASE; identifiers snake_case; short, meaningful aliases.
- One major clause per line; break long SELECT lists across lines.
- Never use SELECT * in application code; be explicit.
- Comment only non-obvious logic; keep comments high-signal.

Example (readable):

    SELECT
      o.order_id,
      o.merchant_id,
      o.dispatch_date,
      SUM(oi.ext_price_cents) AS gross_cents
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.dispatch_date BETWEEN ? AND ?
    GROUP BY o.order_id, o.merchant_id, o.dispatch_date


## Tooling & CI

- Use a SQL formatter/linter in CI to enforce style and safe patterns; allow an autofix bot to apply formatting so it doesn’t block human review.
- Keep unit/property tests mandatory in CI; optionally include a small EXPLAIN/perf smoke.
- Treat formatting as automation: the doc states rules; the linter encodes them.

Practical tips:

- Mark inline SQL strings clearly (e.g., with a preceding comment) so linters can target them.
- Fail CI on unsafe patterns (e.g., SELECT * in app code) and on parsing errors.


## Patterns Library (Suggested Contents)

Keep short, prose-first pattern pages with a rationale and a compact example:

- Surrogate key generation and de-duplication.
- Stage-then-swap refresh workflow.
- Temporal (valid-time) table upserts and time-travel queries.
- Window function idioms: first/last per group, retention, rolling metrics, percentiles.
- EXISTS vs IN: when and why EXISTS tends to outperform for correlated checks.
- Materialization cues: when to cache a view into a table and how to refresh safely.


## Examples & Anti-Patterns

Selective retrieval (good):

    SELECT id, created_at, amount_cents
    FROM payments
    WHERE merchant_id = ?
      AND created_at >= ?
    ORDER BY created_at DESC
    LIMIT 500

Anti-pattern: broad scans and late filters:

    -- Selects everything, then filters later in Python
    SELECT * FROM payments

Join ordering for clarity and pushdown (good):

    SELECT
      m.merchant_id,
      d.dispatch_date,
      SUM(o.total_cents) AS gross_cents
    FROM merchants m
    JOIN orders o ON o.merchant_id = m.merchant_id
    JOIN dispatches d ON d.order_id = o.order_id
    WHERE d.dispatch_date BETWEEN ? AND ?
    GROUP BY m.merchant_id, d.dispatch_date

Anti-pattern: mixing logic between SQL and Python without reason:

    -- Compute partial sums in SQL, finish aggregations in Python for the same grain
    -- (push the full aggregation into SQL unless you truly need Python-only math)


## FAQ-Style Notes

- “Do we need indexes?”  
  Consider them when repeated selective filters benefit measurably; validate with EXPLAIN/ANALYZE. For many analytics workloads, sorted layout + pushdown + pre-aggregation yield bigger wins.

- “When do we cache a view as a table?”  
  When it’s hot, latency-sensitive, or composes several joins/windows repeatedly. Refresh with stage-then-swap and test the row counts/hashes.

- “When should I move code from Pandas back to SQL?”  
  If the Pandas step starts reading large frames only to do group-bys/joins/filters, move that work into SQL and return a small result to Python.


## Closing

Favor explicit, pushdown-friendly SQL and intentional data layout. Keep migrations idempotent and guarded by transactions. Test correctness with unit and property checks. Materialize selectively when performance or stability requires it. Use automation to enforce style; use patterns to share the winning playbooks.

This standard should evolve with real metrics and post-mortems—tune the rules where evidence merits, but keep the core principles: explicitness, testability, and pushdown.

