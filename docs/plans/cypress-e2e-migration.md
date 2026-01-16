# Cypress E2E Migration

This ExecPlan is a living document maintained under `.agent/PLANS.md`. Update every section as discoveries occur so a brand-new contributor can finish the migration end to end using only this file and the working tree.

## Purpose / Big Picture

Playwright-based SPA tests cannot run inside the current Nix + sandbox environment because the browser installers attempt to execute dynamically linked binaries that violate the sandbox, blocking automation of the ledger UI. The Nix flake now ships `nodejs` and the prebuilt `cypress` Electron runner, so we will port the existing Playwright spec to Cypress. Success means contributors can run `npx cypress run --e2e --browser <browser> [--headed]` to exercise the full transaction flow (validation errors plus net-worth delta) against the FastAPI server backed by the seeded DuckDB file, with the server lifecycle handled automatically by the Cypress runner.

## Progress

- [x] (2025-11-11T16:40Z) Captured the migration scope, constraints, and acceptance tests in this ExecPlan.
- [x] (2025-11-11T17:10Z) Implemented `cypress.config.cjs`, ported the transaction flow spec, and removed the Playwright harness.
- [x] (2025-11-11T17:25Z) Updated README, CHANGELOG, TODO, architecture docs, and the original MVP ExecPlan to describe the Cypress workflow.
- [ ] Record passing runs for `pytest` and `npx cypress run --e2e --browser <browser> [--headed]`, then capture outcomes.

## Surprises & Discoveries

- Observation: `playwright.config.ts` starts the FastAPI server by chaining `tests.e2e.prepare_db` and `uvicorn` behind `bash -lc`. We must replicate this behavior so the Cypress suite touches the same database file (`data/e2e-ledger.duckdb`) and honors `DOJO_DB_PATH`.
- Observation: The SPA selectors used by the existing spec (`select[name="account_id"]`, `[data-error-for="amount_minor"]`, `#submission-status`, etc.) live in `src/dojo/frontend/static/index.html` and `app.js`; retaining them keeps the spec stable no matter which runner we use.
- Observation: The flake sets `CYPRESS_INSTALL_BINARY=0` and `CYPRESS_RUN_BINARY=${pkgs.cypress}/bin/Cypress`, so we should depend on the packaged binary and avoid `npm install` entirely. Run commands directly inside an activated dev shell (via `direnv` or `nix develop`).
- Observation (2025-11-11): Launching the packaged Electron runner inside this sandbox currently crashes with `FATAL:sandbox_host_linux.cc(41) Check failed: . shutdown: Operation not permitted (1)` even when `--no-sandbox`/`--disable-setuid-sandbox` flags are injected. We need follow-up debugging to determine whether Chromium requires kernel-level user namespaces or whether a non-Electron browser (e.g., Chromium via `xvfb-run`) is necessary.

## Decision Log

- Decision: Replace Playwright with Cypress Electron (packaged in the flake) to avoid dynamic browser installs. The Cypress config will own the server lifecycle (`tests.e2e.prepare_db` + `uvicorn`) via `child_process.spawn` with the same environment variables, keeping the FastAPI app unchanged. Date/Author: 2025-11-11 / Codex.
- Decision: Keep the Python-side utilities (`tests/e2e/prepare_db.py`) and DuckDB fixture as-is so e2e runs share schema seeding logic with the previous runner, minimizing churn and satisfying `Simple by Design`. Date/Author: 2025-11-11 / Codex.

## Context and Orientation

- Source tree already holds the FastAPI app (`src/dojo/core/app.py`), SPA assets (`src/dojo/frontend/static/{index.html,app.js,styles.css}`), and DuckDB migration utilities (`dojo.core.migrate`, `tests/e2e/prepare_db.py`). No Node project files exist yet.
- Playwright artifacts live at the repo root (`playwright.config.ts`) and under `tests/e2e/transaction_flow.spec.ts`. They assume the server listens on `http://127.0.0.1:8765` and rely on Playwright's `webServer` helper to launch it.
- The SPA form posts to `/api/transactions` and refreshes `/api/net-worth/current` plus `/api/transactions?limit=100`. It renders validation errors into `[data-error-for="..."]` spans and writes status copy into `#submission-status`.
- Tests must keep the database isolated via `DOJO_DB_PATH`, so the Cypress runner needs to point at `data/e2e-ledger.duckdb` (creating directories as needed) and run `tests.e2e.prepare_db` before starting `uvicorn`.
- Docs currently cite Playwright as a known gap (README Quick Start step 4, Operations troubleshooting, Contributing guide notes, Architecture testing map, TODO.md entry, CHANGELOG `[Unreleased]` bullet, and `docs/plans/auditable-ledger-net-worth.md`). All must be updated once Cypress replaces the suite.

## Implementation Plan

### Milestone 1 — Scaffold Cypress and retire Playwright harness

1. Remove `playwright.config.ts` and `tests/e2e/transaction_flow.spec.ts`. Keep `tests/e2e/prepare_db.py` and supporting modules intact.
2. Add `cypress.config.cjs` at the repo root:
       - Import `defineConfig` from `cypress` plus Node `child_process`, `path`, and `http`.
       - Compute `const e2eDbPath = path.join(__dirname, "data", "e2e-ledger.duckdb")`.
       - Implement `startServer()` that spawns `bash -lc 'DOJO_DB_PATH="..." uv run python -m tests.e2e.prepare_db && DOJO_DB_PATH="..." uv run uvicorn dojo.core.app:create_app --factory --host 127.0.0.1 --port 8765'` with inherited stdio and merged env. Resolve once an HTTP probe to `/api/health` (or `/api/net-worth/current` if no health route) succeeds; reject after a timeout with cleanup.
       - Implement `stopServer()` that sends `SIGTERM` and waits for exit (force `SIGKILL` after a grace period).
       - In `setupNodeEvents`, register `on("before:run", async () => { await startServer(); })` and `on("after:run", async () => { await stopServer(); })`, plus `process.on("exit", ...)`/`SIGINT` guards to kill the child.
       - Configure `e2e: { baseUrl: "http://127.0.0.1:8765", specPattern: "cypress/e2e/**/*.cy.js", supportFile: false, video: false, defaultCommandTimeout: 10000 }`.
3. Ensure the config mentions that all commands must be run via `npx cypress run --e2e --browser <browser> [--headed]`. Document any env vars (e.g., `DOJO_DB_PATH`, `CYPRESS_RUN_BINARY`) inline as comments.

### Milestone 2 — Port the transaction flow spec to Cypress

1. Create `cypress/e2e/transaction_flow.cy.js`. No build tooling is required; rely on Node's ES module features if desired, but CommonJS keeps things simple.
2. Implement helper functions inside the spec:
       - `const currencyFormatter = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });`
       - `function loadInitialNetWorth() { return cy.request("/api/net-worth/current").its("body.net_worth_minor"); }`
       - `function waitForNetWorth(expectedMinor) { cy.get("#net-worth-value", { timeout: 10000 }).should(($el) => { expect($el.text().trim()).to.eq(currencyFormatter.format(expectedMinor / 100)); }); }`
3. Recreate the two Playwright tests:
       - **Validation error**: `cy.visit("/")`, wait for reference data (`cy.get('select[name="account_id"] option').should("have.length.at.least", 1)`), clear the amount input, submit, and assert `[data-error-for="amount_minor"]` contains `"Enter a numeric amount."`.
       - **Transaction success**: Fetch the initial net worth via helper, `cy.visit("/")`, select account/category via `.select("house_checking")` / `.select("groceries")`, input `12.34`, set flow to `"expense"`, fill memo `"Cypress test"`, submit, assert `#submission-status` text equals `"Transaction recorded."`, then compute `const expectedMinor = initial + amountMinor` (with amountMinor = `-Math.round(amountDollars * 100)`), and call `waitForNetWorth(expectedMinor)` to ensure the dashboard updates. Optionally, `cy.request("/api/net-worth/current")` after the UI assertion to double-check the backend state.
4. Keep selectors identical to the SPA to minimize future brittleness. Avoid Cypress-specific plugins so the spec runs with the stock binary.

### Milestone 3 — Documentation, changelog, and verification

1. Update README Quick Start step 4, Operations troubleshooting, and Contributing sections to describe running Cypress instead of deferring Playwright. Include the exact command (`npx cypress run --e2e --browser <browser> [--headed]`) and mention `cypress open` for local debugging if helpful.
2. Update `docs/architecture/overview.md` testing map (and any other references) to state that Cypress e2e coverage is checked in and runnable.
3. Remove the Playwright TODO entry from `TODO.md` (it is no longer relevant) and mention the resolved state in `CHANGELOG.md` `[Unreleased] -> Added` (e.g., “Cypress e2e suite exercises the SPA transaction flow”).
4. Amend `docs/plans/auditable-ledger-net-worth.md` progress + references so it acknowledges Cypress as the runnable e2e suite instead of Playwright.
5. Run `pytest` covering existing Python suites, then execute `npx cypress run --e2e --browser <browser> [--headed]`. Capture their passing status in the eventual commit description and this plan’s `Outcomes`.

## Validation and Acceptance

- `pytest` passes (unit + property suites intact).
- `npx cypress run --e2e --browser <browser> [--headed]` boots the FastAPI server automatically, seeds the DuckDB e2e database, and reports both Cypress specs green with no flake.
- The README Quick Start includes Cypress instructions, and no docs mention Playwright as a pending task.

## Idempotence and Recovery

- Re-running the Cypress suite is safe: `tests/e2e/prepare_db.py` truncates transactional tables and resets balances before the server starts, so the DuckDB state returns to baseline each run.
- If `cypress run` is interrupted, ensure any lingering `uvicorn` child is killed (config’s exit handlers cover this). Manually delete `data/e2e-ledger.duckdb` to reset if corruption is suspected; the next run recreates it.
- If the HTTP readiness probe times out, inspect the runner logs for `uv`/`uvicorn` errors, fix them, and re-run the suite; no manual cleanup is needed.

## Outcomes & Retrospective

To be filled in after Cypress runs successfully and the docs accurately describe the workflow.
