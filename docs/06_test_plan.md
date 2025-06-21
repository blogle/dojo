# Dojo – Test Plan

*Version 0.2 – 2025‑06‑20*

> Goal: guarantee **functional parity** with the Aspire Budget sheet, detect regressions quickly, and keep deployment risk near zero while running on hobby‑tier hardware.

---

## 1 Scope & objectives

* Validate every **Functional Story US‑01…US‑13** and **NFR‑01…NFR‑10** (see `01_requirements.md`).
* Confirm migration from legacy Google‑Sheet CSV yields identical balances.
* Ensure temporal queries (`as_of`) return correct historic states.
* Guard against auth bypass, SQLi, XSS (static + dynamic scans).
* Detect performance regressions in critical code paths via micro‑benchmarks.

---

## 2 Test layers

| Layer                | Framework                                         | Runs in CI  | Purpose                                                                        |
| -------------------- | ------------------------------------------------- | ----------- | ------------------------------------------------------------------------------ |
| **Unit**             | Rust `cargo test`, TS `vitest`                    | ✅           | Pure functions & domain rules (e.g. envelope arithmetic).                      |
| **DB‑conv**          | `sqlx::query!` compile‑time checks                | ✅           | SQL type safety against schema.                                                |
| **Property**         | Rust `proptest`, TS `fast‑check`                  | ✅           | Property‑based tests for envelope math & state invariants.                     |
| **Contract**         | Dredd vs `03_api_contract.yaml`                   | ✅           | Ensure API responses conform to OpenAPI.                                       |
| **Integration**      | Rust `tokio::test` hitting containerised Postgres | ✅           | Multi‑table workflows (record tx → category balance).                          |
| **Migration‑parity** | Python `pytest` + DuckDB diff                     | ✅ (nightly) | Import CSV from sheet, compare per‑month balances.                             |
| **E2E**              | Cypress 13 (Chromium & Firefox)                   | ✅           | User stories click‑through with mocked Plaid.                                  |
| **Benchmarks**       | Rust `criterion`, TS `vitest bench`               | ✔︎ nightly  | Detect >10 % runtime regressions in hot paths (dashboard query, balance calc). |
| **Security**         | GitHub CodeQL analysis                            | ✔︎ weekly   | Static analysis for OWASP Top‑10; zero high‑severity alerts.                   |

---

## 3 Test data fixtures

* **seed.sql** – minimal household with 2 users, 2 accounts, 3 categories.
* **sample\_tx.csv** – 100 realistic transactions incl. pending/settled variants.
* **legacy\_sheet/** – exported CSVs from Aspire sheet (used by migration tests).

All fixtures live under `tests/fixtures/` and load via `docker compose exec postgres psql`.  SQLx manages teardown with `transaction.rollback()`.

---

## 4 CI matrix (GitHub Actions)

| Job             | Image                    | Steps                                               | Artefacts             |
| --------------- | ------------------------ | --------------------------------------------------- | --------------------- |
| **lint**        | `rust:1.78-bullseye`     | fmt, clippy, eslint                                 | –                     |
| **unit**        | same + `node:20`         | cargo test, vitest                                  | coverage xml          |
| **property**    | same                     | cargo test `--features proptest`, vitest fast‑check | –                     |
| **integration** | services: api + pg       | docker compose, cargo test `--test integration`     | –                     |
| **contract**    | `dreddimage`             | run Dredd vs local api                              | –                     |
| **bench**       | same + `node:20`         | cargo bench, vitest bench → compare to baseline     | benchmark report      |
| **e2e**         | `cypress/included:13.10` | spin stack, cypress run                             | video, screenshots    |
| **codeql**      | GitHub/codeql‑action     | code scan (`javascript`,`python`,`cpp`,`rust`)      | SARIF report          |
| **docker‑push** | –                        | build & push image on `master`                      | ghcr.io/dojo/api\:sha |
| **deploy**      | `flyctl`                 | deploy, health check; auto‑revert on fail           | –                     |

---

## 5 Pass / fail criteria

| Requirement            | Metric                                                          | Pass threshold |
| ---------------------- | --------------------------------------------------------------- | -------------- |
| Functional stories     | Cypress scenario passes                                         | 100 %          |
| Micro‑benchmarks       | Criterion & vitest bench runtime change vs last `master` ≤ 10 % | ✅              |
| Migration parity       | Per‑month category & account balances diff = 0                  | ✅              |
| Bitemporal correctness | Time‑travel query equals snapshot export                        | ✅              |
| Static security scan   | CodeQL high severity = 0                                        | ✅              |

CI workflow blocks merge/deploy if any **required** check fails.

---

## 6 Local test commands

```bash
# spin stack
just up                # or docker compose up -d
# unit + integration + property
cargo test --all
# micro‑benchmarks
cargo bench --bench core
pnpm vitest bench
# OpenAPI contract
just contract-test      # runs dredd
# e2e UI
pnpm cypress open
```

---

## 7 Future extensions

* **Mutation testing** (`cargo‑mutants`) after MVP.
* **Accessibility audit** (`axe-core`).
* **Spectral** lint on OpenAPI spec.

---

