# Harden DuckDB migrations for deploy safety

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. Maintain this document in accordance with `.agent/PLANS.md` and keep it fully self-contained; do not rely on other specs to explain requirements.

## Purpose / Big Picture

A production deploy failed because DuckDB aborted a migration with `TransactionContext Error: Cannot create index with outstanding updates`. This plan delivers a migration strategy and tooling that make migrations safe to author, rehearse, and run in CI and during deploys. After executing this plan a novice can: (1) reproduce the failing migration on a copy of the database, (2) apply all migrations safely on fresh and existing databases, (3) run an offline preflight before starting the app, and (4) rely on documented guardrails that prevent mixed DML/DDL causing DuckDB transaction errors.

## Progress

- [x] (2025-12-01 14:10Z) Drafted initial ExecPlan describing migration hardening scope.
- [x] (2025-12-01 14:25Z) Started reproduction work: inspecting migrations to locate the failing file and error pattern on a controlled DB copy.
- [x] (2025-12-01 14:55Z) Reproduced `TransactionContext Error: Cannot create index with outstanding updates` by running `0011_ensure_scd2_columns.sql` in one transaction against a DB with sample allocations.
- [ ] (2025-12-01 15:20Z) Began runner hardening: per-statement execution with index/DML separation, CLI flags, and a temp migration check script.
- [x] (2025-12-01 15:40Z) Added startup toggle `RUN_STARTUP_MIGRATIONS`, documented DML/index rule, and wired CI job `migrations-check` using `scripts/run-migrations-check --log-plan`.
- [x] (2025-12-01 16:00Z) Validated fresh DB via `scripts/run-migrations-check --log-plan` and upgrade DB by applying to `tmp/upgrade-pre.duckdb` seeded through `--target 0010...` then full run succeeded (0015 no longer fails).
- [x] (2025-12-01 16:10Z) Validated FastAPI startup with `run_startup_migrations` true/false against temp DBs; app factory returns without migration errors.
- [x] (2025-12-01 16:45Z) Added initContainer preflight with backup in K8s deployment and defaulted `DOJO_RUN_STARTUP_MIGRATIONS` to false (dev shell sets true).
- [x] (2025-12-01 17:00Z) Extended CI migrations job to cover fresh and upgrade (target 0010 ➜ latest) and added regression tests/docs for migration splitting.

## Surprises & Discoveries

- Observation: Migration `0011_ensure_scd2_columns.sql` includes DML (`UPDATE budget_allocations`) followed by `CREATE INDEX` in the same file, which matches the DuckDB constraint on outstanding updates.
  Evidence: File contents show UPDATE at line 4 and CREATE INDEX at line 11 in `src/dojo/sql/migrations/0011_ensure_scd2_columns.sql`.

## Decision Log

- Decision: Start with an explicit ExecPlan to harden migrations instead of hot-patching a single migration.
  Rationale: The failure indicates a systemic risk in how migrations are authored and run; a plan ensures reproducible fixes and future guardrails.
  Date/Author: 2025-12-01 / Codex

## Outcomes & Retrospective

- Migrations run via initContainer preflight with automatic DuckDB file backup; `DOJO_RUN_STARTUP_MIGRATIONS` defaults to false so prod relies on preflight while dev enables it via shellHook.
- CI now validates fresh and upgrade paths (target 0010 ➜ latest) using `python -m dojo.core.migrate`, failing fast if statement splitting or numbering breaks.
- Added regression coverage for DML/index transaction splitting and documented migration authoring/runner usage in `docs/rules/sql.md`.

## Context and Orientation

- Current runner: `src/dojo/core/migrate.py` tracks applied files in `schema_migrations`, executes each pending SQL file inside a single `BEGIN … COMMIT`, and records filenames. It is invoked at process start via `_apply_startup_migrations` in `src/dojo/core/app.py` against `Settings.db_path`.
- Migration files live in `src/dojo/sql/migrations/` and are applied in lexicographic order. Files may contain multiple statements separated by semicolons; today the runner passes the entire file to DuckDB as one execute call.
- DuckDB constraint: `CREATE INDEX` cannot run while the same transaction has uncommitted table updates; mixing large `INSERT/UPDATE` with `CREATE INDEX` in one transaction can raise `Cannot create index with outstanding updates`.
- Operational flow: production currently depends on auto-run migrations on app start. For safety we will introduce an offline preflight command, keep startup migrations optional (on for dev/test, off for prod), and make the runner usable in CI and deploy pipelines.
- Data safety rules to embed directly in this plan: migrations must be deterministic, idempotent via `schema_migrations`, avoid non-repeatable reads, and separate heavy DML from index/constraint creation. Seeds remain in `src/dojo/sql/seeds/`; tests use fixtures under `tests/fixtures/` and must not be mixed with migrations.

## Plan of Work

Narrative milestones that encode the migration strategy and how to implement it without referencing other docs:

1) Reproduce and isolate the failing migration
- Make a disposable copy of the pre-upgrade database (never touch production directly). Use `cp /path/to/prod.duckdb tmp/prod-copy.duckdb` or rebuild from fixtures if a copy is unavailable.
- Run `python -m dojo.core.migrate tmp/prod-copy.duckdb`. If the error surfaces, capture the migration filename and statement ordering. If not obvious, temporarily add logging to print each filename before execution and rerun to pinpoint the offending file.
- Document the exact file and statements that trigger `Cannot create index with outstanding updates`, noting whether the file mixes DML and `CREATE INDEX` in one transaction.

2) Codify migration authoring rules inside this plan and the repo
- Rules to enforce:
  * One concern per file: schema changes (`CREATE TABLE/ALTER TABLE`) separate from data backfills, and `CREATE INDEX` in its own file after prior changes have committed.
  * No mixed heavy DML with `CREATE INDEX` or `CREATE UNIQUE INDEX` in the same transaction; indexes must run after a commit.
  * Statements must be deterministic and idempotent under `schema_migrations` tracking (avoid time-based defaults or non-deterministic selects for backfills).
  * Use explicit ordering via filenames (prefix with zero-padded sequence numbers) and avoid reliance on file system mtime.
  * Backfills that depend on prior schema must assert preconditions (e.g., check column existence) using defensive SQL.
- Encode these rules in `docs/rules/sql.md` (or a new short section) and in the runner validation so violations fail fast.

3) Harden the migration runner to enforce the rules
- Parse each SQL file into statements split on semicolons while preserving order.
- Execute statements sequentially with per-statement logging. Group DML statements inside an explicit transaction; when a `CREATE INDEX` (or other index/constraint) is encountered after DML, commit first, then run the index in its own transaction to avoid outstanding updates.
- Add validation that flags files containing both DML and index creation; either auto-split into two transactions or reject with a clear error unless an override flag is set.
- Add CLI options to `python -m dojo.core.migrate`:
  * `--database PATH` (defaults to `Settings.db_path`),
  * `--dry-run` (parse and log planned statements without executing),
  * `--target MIGRATION_FILENAME` to apply up to and including that file,
  * `--log-plan` to print the ordered migrations and statements before execution.
- Preserve `schema_migrations` tracking; ensure partial runs record only committed files.

4) Add CI and deploy guardrails that use the hardened runner
- Create a script or makefile target (e.g., `scripts/run-migrations-check`) that creates a fresh DuckDB file in `tmp/`, applies all migrations with `--log-plan`, and removes the temp file afterward.
- In `.github/workflows/ci.yml`, add a job that runs the migration check on a fresh DB and on a fixture representing the last released version (e.g., seeded from `tests/fixtures/e2e_*` or a snapshot committed to `tests/fixtures/previous_release.duckdb`). Job should fail if any migration or validation rule fails.
- Add a deploy preflight step that runs `python -m dojo.core.migrate --database $DB_PATH --log-plan` before launching uvicorn. Introduce a setting `RUN_STARTUP_MIGRATIONS` (default true for dev/test, false for prod) to control `_apply_startup_migrations` so production relies on the preflight instead of in-process auto-migrate.

5) Validate across fresh install, upgrade, and runtime startup
- Fresh DB: run migrations on an empty DuckDB file; expect all files applied and reruns to report zero pending migrations.
- Upgrade: run migrations on the pre-upgrade copy that used to fail; verify the previously failing migration now succeeds and indexes are built.
- Startup: start the app with `uvicorn dojo.core.app:create_app --factory --reload` pointing at the upgraded DB and confirm it boots without migration errors; hit `/healthz` and expect `{"status": "ok"}`.
- Add an automated test that exercises the failing migration path (e.g., via a fixture DB missing that migration) to prevent regressions.

## Concrete Steps

Commands assume repo root `/home/ogle/src/dojo` inside the Nix dev shell (`nix develop` or `direnv allow .` already done).

1. Reproduce the failure
    - Prepare a copy of the pre-upgrade DB: `cp /path/to/prod.duckdb tmp/prod-copy.duckdb` (never mutate production). Ensure `tmp/` exists.
    - Run `python -m dojo.core.migrate tmp/prod-copy.duckdb`.
    - If the failing file is unknown, temporarily add logging in `apply_migrations` to print each filename before execution, rerun, and record the first file that throws.

2. Document and bake in authoring rules
    - Edit `docs/rules/sql.md` (or create a migration rules subsection) to include the explicit rules listed above with examples of splitting DML and `CREATE INDEX` into separate files.

3. Implement runner hardening
    - Update `src/dojo/core/migrate.py` to parse and execute statements sequentially, introduce DML/index separation with commits, add validation for mixed files, and add CLI flags (`--database`, `--dry-run`, `--target`, `--log-plan`).
    - Update `src/dojo/core/app.py` to honor a new `RUN_STARTUP_MIGRATIONS` setting so production can disable auto-run when preflight is used.

4. Add CI/deploy checks
    - Add a helper script (e.g., `scripts/run-migrations-check`) that creates `tmp/migrations-check.duckdb`, runs migrations with logging, and cleans up.
    - Modify `.github/workflows/ci.yml` to run the helper on a fresh DB and a previous-version fixture.
    - Add deploy documentation or a script that runs the migration preflight before starting uvicorn; ensure production config sets `RUN_STARTUP_MIGRATIONS=false`.

5. Validate end to end
    - Fresh DB: `python -m dojo.core.migrate tmp/fresh.duckdb` twice; second run should report no pending migrations.
    - Upgrade DB: rerun on `tmp/prod-copy.duckdb` and confirm success.
    - Start app: `uvicorn dojo.core.app:create_app --factory --reload` and GET `/healthz`; expect `{"status": "ok"}` with no migration crash.
    - Run the full test suite or a focused subset: `scripts/run-tests --skip-e2e` at minimum, plus the new migration test.

## Validation and Acceptance

- The offending migration is identified and documented in this plan with filename and statements (update this file when known).
- Fresh and upgrade databases apply all migrations without `Cannot create index with outstanding updates`; reruns are clean due to `schema_migrations`.
- CI job that runs migrations on fresh and previous-version DBs passes and would fail on mixed DML/index files.
- Production deploys use an explicit preflight migration run; app startup succeeds with `RUN_STARTUP_MIGRATIONS=false` in prod and true in dev/test.
- Documentation in `docs/rules/sql.md` states the authoring rules, and the runner enforces them via validation or automatic transaction splitting.

## Idempotence and Recovery

- Re-running migrations is safe: already applied files are skipped via `schema_migrations`, and dry-run mode does not mutate the DB.
- If a migration fails, the runner rolls back the current transaction, logs the failing filename, and leaves prior migrations intact. Fix the file and rerun.
- Temporary databases created for CI/preflight live under `tmp/` and can be deleted safely; scripts should clean them automatically.

## Artifacts and Notes

- Record here the failing migration filename and statement once identified, plus a short log excerpt proving the fix (e.g., runner output showing separate DML and index transactions).
- Reproduction: `tmp/mig-repro.duckdb` created via `python - <<'PY'` (see shell history) that inserts a sample allocation and runs `0011_ensure_scd2_columns.sql` in a single transaction; DuckDB raised `TransactionContext Error: Cannot create index with outstanding updates` as expected.
- Upgrade validation: `tmp/upgrade-pre.duckdb` created with `python -m dojo.core.migrate --database tmp/upgrade-pre.duckdb --target 0010_credit_payment_group.sql`, then full `python -m dojo.core.migrate --database tmp/upgrade-pre.duckdb --log-plan` completed without error, confirming index/DML split in `0011_ensure_scd2_columns.sql` resolves the previous failure.
- Keep a sample `--log-plan` output for both fresh and upgrade runs to aid future debugging.

## Interfaces and Dependencies

- Runner interface: `python -m dojo.core.migrate [--database PATH] [--dry-run] [--target MIGRATION_FILENAME] [--log-plan]`.
- Settings: add `RUN_STARTUP_MIGRATIONS` (default true) consumed by `_apply_startup_migrations` in `src/dojo/core/app.py`; set false in production deploy configs once preflight is in place.
- DuckDB: honor constraint that `CREATE INDEX` must not run with outstanding updates; runner enforces commit boundaries accordingly.

## Specification

# Dojo Database Reliability Hardening and Migration Strategy

## 1. Purpose / Big Picture

This document defines a reliability-focused strategy for managing the Dojo application’s DuckDB schema, migrations, and data durability.

The goals are:

- To make schema migration safe, transactional, and recoverable.
- To ensure migration failures never leave the database in a partially upgraded or inconsistent state.
- To support both local development and Kubernetes-based deployments with the same core migration logic.
- To provide a simple, reliable backup and restoration process.

The design is tailored to DuckDB’s single-file, single-writer model and the relatively low concurrency of the Dojo application.

---

## 2. Goals and Non-Goals

### 2.1 Goals

- Represent all schema changes as explicit, ordered migrations.
- Execute migrations transactionally and record them in a dedicated metadata table.
- Provide a migration runner that:
  - Works in local development.
  - Runs in CI for validation.
  - Can be invoked in staging/production during deployments.
- Ensure that failed migrations:
  - Roll back changes.
  - Do not corrupt or partially modify the schema.
- Implement a lightweight backup strategy suitable for DuckDB’s single-file storage model.

### 2.2 Non-Goals

- No support for multi-writer concurrent access to DuckDB.
- No attempt at online, zero-downtime schema migrations with multiple active schema versions.
- No multi-database abstraction; DuckDB is the primary and assumed engine.
- No heavy external backup system; file-level snapshots are acceptable.

---

## 3. Context and Assumptions

- Dojo uses DuckDB as its primary persistence layer, persisted as a single file (for example, `dojo.duckdb`).
- In Kubernetes, this file is stored on a persistent volume and accessed by a small number of processes, effectively making the system a single logical writer.
- Historically, migrations were run on application startup, leading to issues when migrations failed and the app crashed.
- Concurrency requirements are modest; typical usage involves a single user or a small household.

---

## 4. Schema and Migration Design

### 4.1 Migration Files

Migrations are stored as SQL files in a well-defined directory:

- For example: `sql/migrations/`.
- File naming convention:
  - `0001_initial_schema.sql`
  - `0002_add_transaction_tags.sql`
  - `0003_refactor_budget_views.sql`
- Rules:
  - Prefix with a monotonically increasing, zero-padded numeric identifier.
  - There should be NO gaps in numeric identifier prefixes.
  - Follow with a short, descriptive name.
  - Once added, a migration file must not be renamed or deleted.

### 4.2 Migration Metadata Table

A dedicated table tracks applied migrations:

- Table: `schema_migrations`.
- Schema:

  - `version TEXT PRIMARY KEY`
  - `applied_at TIMESTAMP DEFAULT current_timestamp`

Responsibilities:

- Ensure each migration is applied at most once.
- Provide an ordered record of schema evolution.
- Allow the migration runner to determine which migrations are pending: all files with versions not present in the table.
- Failed migrations should not persist to the metadata table.

### 4.3 Transactional Execution

Each migration is executed within an explicit transaction:

- The migration runner:

  - Begins a transaction.
  - Executes the SQL contents of the migration file.
  - Inserts a row into `schema_migrations` with the migration version.
  - Commits the transaction.

- On any error:

  - The transaction is rolled back.
  - No entry is inserted into `schema_migrations`.
  - The runner fails fast and reports the error.

This guarantees that a migration either completes fully and is recorded, or is not applied at all.

---

## 5. Migration Runner

### 5.1 Responsibilities

The migration runner is a function or CLI tool within the Dojo codebase that:

- Connects to the configured DuckDB file.
- Ensures `schema_migrations` exists.
- Discovers all migration files in the migration directory.
- Determines which migrations are pending.
- Applies pending migrations in ascending version order.
- Logs progress and errors in logfmt format.

### 5.2 CLI Interface

A typical CLI entrypoint might look like:

- `python -m dojo.migrate --db-path=/path/to/dojo.duckdb --migrations-dir=sql/migrations`

Parameters:

- `--db-path`:
  - Required; path to the DuckDB file.
- `--migrations-dir`:
  - Optional; defaults to `sql/migrations`.

Logs:

- Example logfmt lines:

  - `level=info component=migrations action=start db_path=/data/dojo.duckdb`
  - `level=info component=migrations action=apply version=0003_refactor_budget_views`
  - `level=info component=migrations action=complete version=0003_refactor_budget_views`
  - `level=error component=migrations action=failed version=0003_refactor_budget_views err="syntax error at or near..."`

### 5.3 Local Development Workflow

For local development:

- Developers run the migration command whenever schema changes are introduced:

  - `python -m dojo.migrate --db-path=./local.duckdb`

- On startup, the application may also:
  - Check the current schema version.
  - Run migrations automatically in development only, guarded by configuration.

Developers can reset their local databases by:

- Creating a new DuckDB file.
- Running the migration runner from scratch to reconstruct the schema.

---

## 6. CI Validation

### 6.1 Purpose

Before any migration reaches staging or production, CI must validate that:

- All migrations apply cleanly on a fresh database.
- Basic invariants about the schema hold after migrations are applied.

### 6.2 CI Migration Step

The CI pipeline includes a step that:

- Creates a temporary DuckDB file, for example, in `/tmp`.
- Runs the migration runner to apply all migrations.
- Runs simple data invariants, for example:
  - Ensuring key tables exist.
  - Verifying critical columns and constraints.
  - Running a small number of sample insert/select operations.

If any step fails, CI fails the build, blocking merges or releases until the migration is corrected.

---

## 7. Runtime Execution in Staging and Production

### 7.1 Single-Writer Model and Coordination

DuckDB is not designed for concurrent writers to a single file. For Dojo:

- Environments (staging, production) must ensure only one process writes to the DuckDB file at a time.
- Deployments should be configured such that:
  - At most one pod can run migrations.
  - The app’s normal serving process does not compete for write access during migrations.
- If deployment fails we roll back the migration (or revert to db backup)

### 7.2 Migration During Deployment

#### Dedicated Migration Mode in Application Container

- The container image provides two entrypoints:

  - Migration entrypoint (for example, `python -m dojo.migrate`).
  - Application server entrypoint (for example, `python -m dojo.app`).

- For staging/production deployment:

  - Before updating the application Deployment, run the container in “migration mode” against the shared DuckDB file.
  - If migrations succeed:
    - Proceed to rollout the new application pods.
  - If migrations fail:
    - Abort rollout and investigate, using backup and logs.

This pattern can be orchestrated by Kubernetes Jobs or an external script (specified in the CD spec).

---

## 8. Backup and Recovery

### 8.1 Backup Strategy

DuckDB’s data is stored in a single file, making backups straightforward:

- Before running migrations in staging or production:

  - Copy the database file to a timestamped backup, for example:

    - `cp /data/dojo.duckdb /data/dojo.duckdb.bak.$(date +%s)`

- Keep a bounded number of backups (for example, the last N backups) by removing older backups on creation of a new one.

Backups may be created by the same mechanism that triggers migrations, ensuring there is always a pre-migration snapshot.

### 8.2 Recovery Procedure

If a migration is suspected to have caused corruption or undesirable changes:

- Stop the application or prevent new pods from starting.
- Restore the backup:

  - Copy the desired backup file over the main database file, for example:

    - `cp /data/dojo.duckdb.bak.<timestamp> /data/dojo.duckdb`

- Re-run migrations:

  - If they fail again, the migration must be corrected.
  - Only allow the application to start after migrations succeed.

The process must be documented so operators can execute it reliably and quickly. (Ideally this is automated)

---

## 9. Safety Invariants

The migration strategy must maintain the following invariants:

- `schema_migrations` accurately represents all fully applied migrations.
- No migration is recorded in `schema_migrations` unless it completed without error.
- A failed migration leaves the database in the same schema revision as before the migration attempt, from the application’s perspective.
- Backups exist for every migration attempt in staging and production.
- The application never relies on schema changes that are not enforced by a migration.

---

## 10. Observability and Logging

### 10.1 Migration Logs

Migration logs must:

- Use logfmt style with keys such as:
  - `level`, `component=migrations`, `action`, `version`, `db_path`, `err`.
- Indicate:
  - Start and completion of the overall migration process.
  - Start and completion of each individual migration file.
  - Any errors encountered, including the SQL file and version associated with the failure.

### 10.2 Application Logs

Application logs should:

- Record the schema version at startup.
- Log any mismatches between expected and actual schema version.
- Include context when database errors occur, allowing correlation with migration history.

These logs allow operators and automation to quickly determine whether a failure is due to schema drift, a migration error, or an unrelated bug.

---

## 11. Failure Modes and Handling

Common failure modes include:

- Syntax error in a migration file:
  - Caught during CI migration validation.
  - If it reaches staging, the migration runner fails, and the database remains unchanged.
- Logical errors in migration assumptions (for example, unexpected data states):
  - May only surface in staging or production.
  - Backup and recovery allow rollback.
  - Migration must be corrected and revalidated.
- Unexpected DuckDB or I/O errors:
  - Cause transaction rollback.
  - May require infrastructure-level investigation.
- Misconfiguration of migration runner (incorrect DB path):
  - Must be surfaced via clear error messages and logs.
  - Should be caught by configuration validation.

---

## 12. End State Summary

In the target end state:

- All schema changes are described as ordered, transactional SQL migrations tracked by `schema_migrations`.
- A single migration runner is used for development, CI validation, and staging/production deployments.
- Before any production or staging migration, a file-level DuckDB backup is created.
- Migration failures never leave the database in a partially applied state; recovery is straightforward and documented.
- Logs and invariants provide strong observability into migration behavior and schema health.

## Revision Note

