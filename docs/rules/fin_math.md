# Financial Maths Rulebook

This document prescribes **must-follow** engineering practices for modeling returns, performance, and portfolio math in Python. It emphasizes **correctness**, **numerical stability**, and **clear reporting**. It is intentionally opinionated and avoids model-choice debates. Use it as a developer guide or README artifact.

All examples assume `numpy as np` and `pandas as pd`.


## Scope & Principles

Adopt these principles whenever writing analytics code:

1) **Time-series vs cross-section:** Use **log returns** for time aggregation; use **simple returns** for cross-sectional aggregation (e.g., portfolio period returns). Never mix them implicitly.

2) **Numerical stability first:** Prefer `log1p` / `expm1`, test finiteness, and guard domains. Avoid fragile arithmetic.

3) **Explicit naming** of return type: use `s_rt` for **simple** returns and `log_rt` for **log** returns. Never use generic `rt`.

4) **UTC, adjusted prices, typed money:** Use UTC timestamps, fully adjusted prices for return computation, and integer/Decimal for ledger money. Use float64 for analytics arrays.

5) **User-facing clarity:** For end users, prefer **simple returns** and **CAGR** in reports. Internally, compute with log returns when it improves stability and correctness.

6) **Property tests & invariants:** Embed tests that assert identities (e.g., conversion idempotence, portfolio return equals weighted sum of simple returns, etc.).


## Conventions & Types

- **Indexing:** `DatetimeIndex` is **tz-aware UTC**. Rows are time, columns are instruments. Shapes `(T, N)`.

- **Naming:**
  - Prices: `.px`
  - Simple returns: `.s_rt`
  - Log returns: `.log_rt`
  - Weights: `.w`

- **Dtypes:**
  - Ledgers (balances, transactions): **integers in minor units** (e.g., cents) or `Decimal` with fixed quantization.
  - Analytics (prices, returns): **float64**. Round/quantize only at I/O boundaries.

- **Frequency tags:** Maintain a frequency `K` (periods per year) derived from context:
  - Equities: `K=252`
  - Crypto/cash daily: `K=365`
  - Weekly: `K=52`
  - Monthly: `K=12`


## Returns: Definitions & Conversions

**Rule:** Store **log returns** as the canonical time-series representation for analytics; derive simple returns when needed (especially for user-facing reporting and cross-sectional ops).

Recipe (stable conversion):
```
# simple → log (domain guard: s_rt > -1)
eps = 1e-15
assert np.all((df.s_rt.values > -1.0 + eps) | df.s_rt.isna().values)
df["log_rt"] = np.log1p(df.s_rt)

# log → simple
df["s_rt"] = np.expm1(df.log_rt)
```

Anti-patterns:

```
# Wrong or unstable for small x near 0 or -1:
df["log_rt"] = np.log(1 + df.s_rt)      # avoid
df["s_rt"]   = np.exp(df.log_rt) - 1    # less stable than expm1

```
Properties (must hold):

```
# Within numerical tolerance:
np.allclose(np.expm1(np.log1p(df.s_rt)) , df.s_rt, atol=1e-12, equal_nan=True)
np.allclose(np.log1p(np.expm1(df.log_rt)), df.log_rt, atol=1e-12, equal_nan=True)
```


## Cross-Section vs Time Aggregation

**Rule:** Cross-sectional aggregation (assets within the same period) must use **simple returns**. Time aggregation (compounding across periods) should use **log returns**.

Correct period portfolio return:

```
# w_t sums to ~1 at the start of period t; shapes (N,) and (N,)
r_p_t = np.dot(w_t, s_rt_t)  # simple returns only

# If you need the portfolio log return for time aggregation:
log_rt_p_t = np.log1p(r_p_t)
```

Anti-pattern:
```
# Incorrect: summing asset log returns cross-sectionally with weights
# This is a math error for portfolios within a single period.
wrong = np.dot(w_t, log_rt_t)   # DO NOT DO THIS
```

## Cumulative Performance & Reporting

**Rule:** For long horizons, compute cumulative performance via sums of **log returns** (stable) and convert to user-facing simple returns or **CAGR**.

Recipe (cumulative return & wealth path):

```
# Time aggregation: use log returns
cum_log = log_rt.cumsum()
cum_s_rt = np.expm1(cum_log)            # cumulative simple return
wealth   = np.exp(cum_log)              # 1 + cumulative simple return, starting at 1.0
```

User-facing reporting:

```
# Prefer CAGR (annualized geometric mean simple return) for users:
# If mean_log is mean of per-period log returns and K is periods per year:
nn_simple = np.exp(mean_log * K) - 1   # user-facing "annualized return" (CAGR)
```

Anti-pattern:

```
# Over very long series this can accumulate floating error and be less stable:
cum_s_rt_naive = (1 + s_rt).prod() - 1  # permitted, but prefer log path when long

```

## Annualization & Scaling

**Rule:** Use **log-return mean** for annualizing returns; use **std * sqrt(K)** for volatility (either return type, with log preferred for consistency).

Recipes:

```
# Annualized return (CAGR)
mean_log = log_rt.mean()
ann_return = np.exp(mean_log * K) - 1

# Annualized volatility
ann_vol = log_rt.std(ddof=1) * np.sqrt(K)
```

Anti-patterns:

```
# Biased: arithmetic mean of simple returns × K
bad_ann_return = s_rt.mean() * K

# Inconsistent ddof across the codebase
bad_vol = log_rt.std(ddof=0) * np.sqrt(K)  # use ddof=1 for sample stats

```

## Excess Returns & Sharpe

**Rule:** Align risk-free to the same frequency, convert properly, and keep return types consistent.

Recipe:

```
# Given an annualized risk-free simple rate rf_annual (e.g., T-bill):
# Convert to per-period log RF that matches K
rf_per_period_simple = (1 + rf_annual)**(1/K) - 1
rf_per_period_log    = np.log1p(rf_per_period_simple)

# Excess log returns (preferred for Sharpe consistency)
ex_log_rt = log_rt - rf_per_period_log

# Annualized Sharpe
sharpe = ex_log_rt.mean() / ex_log_rt.std(ddof=1) * np.sqrt(K)
```

Anti-pattern:

```
# Mixing types: subtracting simple RF from log returns
wrong_excess = log_rt - rf_per_period_simple   # DO NOT DO THIS
```


## Weights, Rebalancing, Fees

**Rules:**
- Weights are **start-of-period** and sum to 1 within tolerance.
- Default reporting uses **rebalanced** series; provide drifted as a diagnostic.
- Apply fees/slippage/taxes as **simple-return** deductions at the period.

Recipe:

```
# Start-of-period normalization
tol = 1e-9
w_t = w_t / w_t.sum()
assert abs(w_t.sum() - 1.0) < 1e-9

# Net simple return after costs
r_net_t = r_gross_t - cost_rate_t   # cost_rate_t is a simple rate

# Drifted vs rebalanced simulation should be explicitly labeled in outputs
```


## Prices, Corporate Actions & Data Hygiene

**Rules:**
- Use **split- and dividend-adjusted prices** for return computations; otherwise compute total return explicitly (price + distributions).
- Never forward-fill **returns**. Forward-fill **prices** only under explicit, constrained session rules.
- Explicit left-close/right-open labeling: return at `t` maps to `(t-1, t]`.

Recipe (returns from adjusted prices):

```
# Daily simple returns from adjusted prices
s_rt = px_adj.pct_change()
```

Anti-pattern:

```
# Using unadjusted close to compute returns → dividend/split errors
s_rt_wrong = px_unadj.pct_change()   # DO NOT USE FOR PERFORMANCE

```

## Time, Alignment & Missing Data

**Rules:**
- Timestamps are UTC, tz-aware.
- Align series explicitly before arithmetic. Do not rely on implicit alignment with mismatched indices.
- If an asset is missing a price at `t`, its weight should be masked or the return should be NaN; never silently reuse an older value.

Recipe:

```
# Explicit alignment
s_rt_aligned = s_rt.reindex(index=common_index).sort_index()
w_aligned    = w.reindex(index=common_index).sort_index()

# Mask weights where returns are NaN
mask = s_rt_aligned.isna()
w_masked = w_aligned.where(~mask, 0.0)
w_masked = w_masked.div(w_masked.sum(axis=1), axis=0).fillna(0.0)
```


## Ledgers & Money Types

**Rules:**
- **Ledgers:** store money as integers in minor units or `Decimal` with fixed quantization. Never store ledger balances as float.
- **Analytics:** use float64 arrays; convert to Decimal only at I/O boundaries.

Recipe:

```
# Ledger: cents as int; exact summation
txn_amount_cents = 1999  # $19.99
balance_cents += txn_amount_cents
```

Anti-pattern:

```
# Float ledger values subject to rounding error
balance = 0.0
balance += 19.99  # DO NOT DO THIS FOR LEDGERS
```


## Numerical Stability & Guards

**Rules:**
- Always use `log1p` and `expm1` for small quantities; guard the domain for `log1p`.
- Check finiteness (`np.isfinite`) after key transforms and halt or mask with a documented policy.
- Use `ddof=1` for sample statistics; never change ddof silently.

Recipe:

```
eps = 1e-15
assert np.all((s_rt > -1 + eps) | s_rt.isna())
log_rt = np.log1p(s_rt)

assert np.isfinite(log_rt).all() or raise_error(...)
vol = log_rt.std(ddof=1)
```


## Time-Weighted vs Money-Weighted

**Policy:**
- **TWR** is default in dashboards (strategy/portfolio evaluation).
- **(X)IRR** reserved for planning modules with irregular cash flows.
- If both are shown, they must be clearly labeled and described.

Recipe (user-facing):

```
# Reporting: convert internal log stats to simple metrics for clarity
user_cagr = np.exp(log_rt.mean() * K) - 1
user_vol  = log_rt.std(ddof=1) * np.sqrt(K)
```


## Invariants & Property Tests (embed in your test suite)

These properties must hold within tolerances; violations indicate bugs or data quality issues.

```
# 1) Conversion idempotence
assert np.allclose(np.expm1(np.log1p(s_rt)), s_rt, atol=1e-12, equal_nan=True)
assert np.allclose(np.log1p(np.expm1(log_rt)), log_rt, atol=1e-12, equal_nan=True)

# 2) Portfolio period return equals weighted sum of simple returns
r_p_t = (w_t * s_rt_t).sum()
assert np.isscalar(r_p_t)

# 3) Cross-sectional misuse of log returns must fail fast
def portfolio_return_from_log(log_rt_t, w_t):
	raise AssertionError("Cross-sectional portfolio return must use simple returns")

# 4) Annualization identity when K=1
K1 = 1
ann_identity = np.exp(log_rt.mean() * K1) - 1
assert np.allclose(ann_identity, np.expm1(log_rt.mean()), atol=1e-12)

# 5) Rebalance vs drift labeling is preserved
assert "rebalanced" in series_meta or "drifted" in series_meta

# 6) Finite checks at each step
assert np.isfinite(px.values).all()
assert np.isfinite(log_rt.values | np.isnan(log_rt.values)).all()

# 7) Weights sum to 1 (within tolerance) and align with returns
assert abs(w_t.sum() - 1.0) < 1e-9
assert (w.index == s_rt.index).all()
```


## API Ergonomics & Lintable Contracts

**Rule:** Separate APIs by operation type and enforce return-kinds with names and runtime asserts (optionally `typing.NewType`).

Examples:

```
# Time aggregation API (accepts log returns)
def cumulative_from_log(log_rt: pd.Series) -> pd.Series:
	assert "log_rt" in log_rt.name or log_rt.attrs.get("kind") == "log"
	return np.expm1(log_rt.cumsum())

# Cross-sectional API (requires simple returns)
def period_portfolio_s_rt(s_rt_t: pd.Series, w_t: pd.Series) -> float:
	assert "s_rt" in s_rt_t.name or s_rt_t.attrs.get("kind") == "simple"
	assert abs(w_t.sum() - 1.0) < 1e-9
	return float(np.dot(w_t.values, s_rt_t.values))

```

## Positive vs Negative Examples (End-to-End)

**Scenario:** Two assets, daily data, rebalanced portfolio, user-facing performance.

Positive:

```
# 1) Compute simple returns from adjusted prices
s_rt = px_adj.pct_change()

# 2) Convert to log returns for time aggregation
log_rt = np.log1p(s_rt)

# 3) Compute period portfolio simple return (cross-section)
r_p_t = (w_t * s_rt.loc[t]).sum()

# 4) Convert that period return to log for time aggregation
log_rt_p_t = np.log1p(r_p_t)

# 5) Aggregate over time for cumulative performance
cum_s_rt = np.expm1(log_rt_p_t_series.cumsum())

# 6) User-facing metrics
user_cagr = np.exp(log_rt_p_t_series.mean() * 252) - 1
user_vol  = log_rt_p_t_series.std(ddof=1) * np.sqrt(252)
```

Negative:

```
# A) Cross-sectional log-return weighting (wrong)
wrong_r_p_t = (w_t * log_rt.loc[t]).sum()   # math error

# B) Annualized arithmetic mean of simple returns (biased)
wrong_ann = s_rt.mean().mean() * 252        # misleading

# C) Unadjusted prices for returns (incorrect around dividends/splits)
wrong_s_rt = px_unadj.pct_change()

# D) Float ledger balances (rounding drift)
ledger_balance = 0.0
ledger_balance += 19.99                     # not allowed
```


## Reporting Guidance (User-Facing)

- Favor **CAGR** and period **simple returns** in dashboards and summaries.
- Clearly label **rebalanced** vs **drifted** results.
- Avoid jargon where possible; when shown, explain Sharpe and excess returns briefly.
- When internal math used log returns, convert outputs to **simple** metrics for display and narrative clarity.


## Checklist for PR Review (interpret, not copy-paste)

- Are cross-sectional operations using **simple** returns only?
- Are time aggregations using **log** returns with `log1p`/`expm1`?
- Are price series **adjusted** and time indexes **UTC**?
- Are ledgers **integer/Decimal**, analytics **float64**?
- Are annualization formulas consistent (CAGR via mean log, vol via sqrt(K))?
- Are user-facing figures in **simple** terms (CAGR, simple returns) and clearly labeled?
- Do tests assert the properties listed above?


## Summary

- **Cross-section:** simple returns.
- **Time:** log returns.
- **Reporting:** user-friendly simple metrics (CAGR, period simple returns) with clear labels.
- **Stability:** `log1p`/`expm1`, finiteness checks, adjusted prices, UTC time.
- **Money:** integer/Decimal for ledgers, float64 for analytics.
- **Tests:** property-based guardrails to catch misuse early.

Adhering to these rules prevents common analytics bugs, maintains numerical stability, and ensures users see accurate, interpretable performance figures.

