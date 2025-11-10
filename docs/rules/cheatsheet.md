# [Financial Math](./fin_math.md)

* Never weight log returns across assets; Always compute portfolio period return with simple returns (s_rt) then convert to log_rt if needed.
* Never compound across time with products of (1 + s_rt) on long spans; Always sum log_rt and use expm1/exp to get back to simple space.
* Never mix return types implicitly; Always use explicit names: s_rt (simple), log_rt (log).
* Never use np.log(1 + x) or np.exp(x) - 1; Always use np.log1p(x) and np.expm1(x) for stability.
* Never compute returns from unadjusted prices; Always use split/dividend-adjusted prices or add distributions for total return.
* Never forward-fill returns; Always leave NaNs and mask/renormalize weights when data is missing.
* Never assume alignment or local time; Always align indices explicitly and use tz-aware UTC timestamps.
* Never store ledger money as floats; Always use integers in minor units (e.g., cents) or Decimal with fixed quantization (analytics stay float64).
* Never show internal log metrics to users; Always report in simple terms (period s_rt, CAGR) with clear labels.
* Never annualize by arithmetic mean of s_rt × K; Always annualize via mean log_rt then exp(mean_log*K) - 1.
* Never compute volatility with ddof=0; Always use ddof=1 and scale by sqrt(K).
* Never subtract a simple risk-free from log_rt; Always convert RF to per-period log and subtract in log space.
* Never let weights drift without clarity or fail to sum to 1; Always use start-of-period weights, normalize within tolerance, and label series rebalanced vs drifted.
* Never ignore the log1p domain (x > -1); Always guard with epsilon and check finiteness after transforms.
* Never round during analytics; Always round/quantize only at I/O boundaries.
* Never hardcode frequency blindly or mix frequencies; Always carry a frequency tag and use the correct annualization factor (K=252/365/52/12 as policy).
* Never proceed with infs/NaNs silently; Always validate (np.isfinite) and halt or apply an explicit, documented imputation policy.
* Never apply fees/slippage/taxes in log space; Always subtract costs as simple rates at the period, then convert if needed.
* Never rely on implicit index matching for weights/returns; Always assert aligned shapes/indices before arithmetic.
* Never leave compounding semantics ambiguous; Always state the interval convention (left-close/right-open) and what each return maps to (t-1, t]

# [Python](./python.md)

* Never modify `sys.path`; Always place imports at the top, grouped stdlib/third-party/local.
* Never use dynamic, nested, or try/except imports; Always declare explicit dependencies.
* Never use `from __future__ import annotations`; Always use builtin types (e.g., `list[str] | None`).
* Never mix refactors with features; Always separate them into distinct commits.
* Never change behavior without traceability; Always record breaking changes in **CHANGELOG.md › Unreleased** and label the PR.
* Never reference ephemeral or untracked files; Always reference paths present in `git ls-files`.
* Never sprinkle feature flags throughout code; Always read flags once at the edge and inject inward.
* Never organize code by convenience-only layers; Always organize by domain with a small shared `infra/`.
* Never write untyped functions or omit return annotations; Always write pure, typed functions with `->`.
* Never use mutable default arguments or hidden globals; Always pass state explicitly and keep functions pure.
* Never use `assert` for user/data validation; Always perform explicit checks and raise typed exceptions (asserts only for internal invariants).
* Never catch exceptions you can’t handle or use `except:`; Always catch at the innermost layer and wrap/re-raise with domain context.
* Never build deep `if/elif` chains over enums/states; Always use `match/case`.
* Never mutate shared DataFrames in place; Always use vectorized, functional composition that returns new objects.
* Never optimize before measuring; Always profile first and document the context of changes.
* Never rely on nondeterministic randomness; Always set a single global constant seed at process start.
* Never hardcode time/UUID randomness in tests; Always parameterize or fake via dependency injection.
* Never scatter configuration reads across modules; Always load config once at startup, validate eagerly, and inject a typed settings object.
* Never use `None` sentinels for required dependencies; Always fail fast with explicit validation.
* Never print from library code; Always use structured `logging` with appropriate levels.
* Never leave code unexplained; Always precede each 2–5 lines of logic with a “why-first” comment.
* Never skip documentation of public APIs; Always write NumPy-style docstrings with concise examples.
* Never rely on ad-hoc tooling; Always use `uv` with a locked env and `extras:dev` for ruff/pyright/pytest.
* Never let formatting nits block reviews; Always let Autofix CI apply formatting/import-sort and ensure code type-checks locally.
* Never put I/O in the core domain logic; Always isolate side effects in an imperative shell with a functional core.
* Never use `getattr` or `setattr`; Their use is a strong indication of a design flaw.
* Never use dictionaries for structured data; Always use `dataclasses` or Pydantic `BaseModel`.

# [SQL](./sql.md)

* Never SELECT *, Always project just the columns you need.
* Never inline literals into SQL, Always bind parameters.
* Never copy-paste complex/reused queries inline, Always promote them to .sql files.
* Never bury DDL/DML in Python, Always keep migrations and write paths in .sql.
* Never write non-idempotent migrations, Always use IF [NOT] EXISTS and a schema_migrations log.
* Never skip transactions, Always wrap migrations/ETL in a transaction.
* Never rewrite big tables in place, Always stage-then-swap with validation.
* Never materialize views “just because,” Always materialize only for measured latency/SLA wins.
* Never assume an index/layout helps, Always verify with EXPLAIN/ANALYZE.
* Never rely on wide scans and late filters, Always filter early and push predicates down.
* Never move huge raw tables to Pandas to aggregate, Always aggregate in SQL and hand off small results.
* Never default to Python UDFs, Always prefer native SQL; use UDFs sparingly with tests.
* Never mix compute without reason, Always keep set-based ops in SQL and niche math in Pandas/Numpy.
* Never guess data types, Always choose minimal, consistent types at ingest.
* Never overwrite versioned rows, Always use valid_from/valid_to and close the prior version.
* Never drop auditability, Always include created_at, updated_at, source, job_id (and optional row hashes).
* Never allow multiple writers to the same DB file, Always enforce single-writer/many-readers.
* Never hold global connections, Always use context-managed connections per unit of work.
* Never hide critical SQL in code, Always organize .sql under sql/queries, sql/migrations, and sql/etl.
* Never leave query performance undocumented, Always keep brief notes where plans/layout matter.
* Never skip tests, Always cover unit fixtures and property/invariant checks (and optional perf smoke).
* Never ship unreadable SQL, Always uppercase keywords, use snake_case identifiers, and one clause per line.
* Never trust manual formatting, Always let the CI linter/formatter enforce style.
* Never duplicate business logic across queries, Always define a canonical view or query and reuse it.
* Never refresh data blindly, Always validate counts/ranges/hashes before swapping.
* Never expand dynamic SQL freely, Always toggle strictly allow-listed clauses (and still bind values).

# [Engineering Guide](./engineering_guide.md)

* Never use a long-lived, global database connection; Always use a dependency injection function to create a new, temporary connection.
* Never write multi-step data modifications without a transaction; Always wrap them in a single, atomic SQL transaction block.
* Never use standard `UPDATE` or `DELETE` on temporal tables; Always use the two-step atomic transaction for modifications and soft deletion.
* Never query temporal data without considering history; Always use the `is_active` flag for current state and the `recorded_at` timestamp for historical queries.
* Never repeat complex temporal query logic; Always abstract it into reusable functions.
