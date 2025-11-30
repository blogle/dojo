# Dojo Rules Cheatsheet (Non-Linter Invariants Only)

This cheatsheet captures **semantic rules** that linters and formatters cannot enforce. Use it as a quick reference for changes that touch money, returns, DuckDB, or temporal tables.

For language-level style and formatting, rely on linters and the detailed docs in `docs/rules/python.md` and `docs/rules/sql.md`.


## Financial Math & Money

See `docs/rules/fin_math.md` for full details.

- **Returns: cross-section vs time**
  - Never weight log returns across assets in a single period.
  - Always compute portfolio period returns using **simple returns** (`s_rt`) and start-of-period weights, then convert to log if needed.
  - For time aggregation across periods, sum **log returns** and convert back with `expm1`.

- **Stability & naming**
  - Always use `np.log1p` / `np.expm1` for small quantities; never use bare `np.log(1 + x)` or `np.exp(x) - 1`.
  - Be explicit about return types: use `s_rt` for simple returns and `log_rt` for log returns. Never use a generic `rt`.

- **Annualization**
  - Never annualize by `mean(simple_return) * K`.
  - Always annualize via **mean log returns** and `exp(mean_log * K) - 1` for CAGR; volatility via `std * sqrt(K)` with `ddof=1`.

- **Risk-free & Sharpe**
  - Never subtract a simple risk-free rate from log returns.
  - Always convert the risk-free rate to per-period log space and subtract that.

- **Ledgers & money types**
  - Never store ledger balances as floats.
  - Always store money as **integers in minor units** (e.g., cents) or `Decimal` with fixed quantization.
  - Only round/format at I/O boundaries (UI, reports, exports); analytics may work in float64 internally.

- **Data hygiene**
  - Never compute returns from unadjusted prices; always use split/dividend-adjusted prices or add distributions.
  - Never proceed with NaNs/inf silently; always validate and apply an explicit, documented policy.


## DuckDB, Temporal Model, and Data Integrity

See `docs/rules/engineering_guide.md` and `docs/rules/sql.md` for full context.

- **Connections & concurrency**
  - Never use long-lived global DuckDB connections.
  - Always create a per-request/per-unit-of-work connection via dependency injection and close it when done.
  - Never allow multiple writers to the same DuckDB file; enforce single-writer, many-readers.

- **Transactions**
  - Never write multi-step modifications without a transaction.
  - Always wrap multi-step writes in `BEGIN … COMMIT` so partial failures roll back.

- **Temporal tables (SCD2-style)**
  - Never `UPDATE` or `DELETE` temporal fact rows in place.
  - Always:
    - Mark the current version inactive (e.g. `is_active = FALSE`) and
    - Insert a new row with updated data in the same transaction.
  - Never physically delete rows for “business deletions”; treat them as soft-deletes via the temporal pattern.

- **Current vs historical queries**
  - Never assume “latest row” without filters.
  - Always:
    - Use `is_active = TRUE` for “current state”.
    - Use `recorded_at` and grouping by conceptual ID for historical “as of” queries.

- **Seeds, migrations, fixtures**
  - Never mix schema migrations, dev/demo seed data, and test fixtures.
  - Always:
    - Put migrations under `sql/migrations/` (idempotent, transactional, production-safe).
    - Put dev/demo seeds under `sql/seeds/` (never run in prod).
    - Put test fixtures under `tests/fixtures/` (small, deterministic).


## Testing & E2E Behavior

- **Cypress E2E**
  - Never rely on test execution order or cross-test state.
  - Always reset the database and seed a known scenario in `beforeEach` using `cy.resetDatabase()` and `cy.seedDatabase(...)`.

- **Invariants in tests**
  - For financial math and portfolio logic, prefer property tests where possible (e.g., conversion identities between simple/log returns; portfolio return equals weighted sum of simple returns).
  - For temporal tables, test that corrections create a new row and mark the prior version inactive rather than updating in place.


## Documentation & Changelog

These are process invariants that linters can’t enforce:

- For user-facing or behavior-changing work, always:
  - Update `CHANGELOG.md` under `[Unreleased]`.
  - Update `ARCHITECTURE.md` if you change system-level behavior or flows.
  - Update the relevant ExecPlan or ExecResearch doc if your work is guided by one.
- Never let `ARCHITECTURE.md` or plans drift away from reality; update them in the same PR that changes behavior.

