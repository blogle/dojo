# Dojo

<!-- Badges: Build Status, License, Version -->
[![Status](https://img.shields.io/badge/status-alpha-orange.svg)](./CHANGELOG.md)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)

A brief table of contents for easy navigation.

- [Purpose](#purpose)
- [Quick Start](#quick-start)
- [Status](#status)
- [Setup](#setup)
- [Usage](#usage)
- [Operations](#operations)
- [Contributing](#contributing)
- [Trust & License](#trust--license)

## Purpose

Dojo is a self-hosted personal finance application for a household, designed to replace manual budgeting spreadsheets. It integrates an envelope budgeting system with a primary focus on net worth tracking, forecasting, and portfolio optimization. The goal is to provide a holistic view of financial health by directly linking day-to-day budgeting decisions to their long-term impact on wealth accumulation and preservation.

## Quick Start

This section provides the fastest path to exercising the Auditable Ledger MVP.

### 1. Bootstrap the environment

```bash
git clone <repository-url>
cd dojo
direnv allow .
```

The development shell installs Python, DuckDB, uv, and other pinned tooling. If you do not use `direnv`, run `nix develop` from the repo root before the commands below and run them directly inside that shell.

### 2. Apply migrations (creates `data/ledger.duckdb`)

```bash
python -m dojo.core.migrate
```

This leaves the ledger completely empty so you can start from a clean slate at any time by deleting `data/ledger.duckdb`, rerunning migrations, and skipping the next (optional) step.

### 3. (Optional) Load dev/demo seed data

```bash
python -m dojo.core.seed
```

The seed scripts insert the `house_*` accounts and baseline categories so the SPA works immediately. Skip this step if you want to create every account/category yourself.

### 4. Run the API + SPA locally

```bash
uvicorn dojo.core.app:create_app --factory --reload
# open http://127.0.0.1:8000/ in your browser
```

The landing page now behaves like a lightweight spreadsheet: the first row is an input line, arrow/tab keys move across cells, Enter submits, and the table below scrolls to show prior transactions.

### 5. Execute the automated tests

```bash
pytest
npx cypress run --e2e --browser <browser> [--headed]
```

The Cypress run spins up a dedicated DuckDB database (`data/e2e-ledger.duckdb`) and launches the FastAPI server automatically via `cypress.config.cjs`, so no additional setup is required.

## Architecture Snapshot

- **FastAPI Monolith**: `dojo.core.app:create_app` is the sole entry point. It wires routers from each domain package (budgeting, core, investments, etc.) and builds dependencies through `build_container` so every request receives a scoped DuckDB connection and typed services.
- **DAO Layer**: All SQL lives under `src/dojo/sql/**` and is loaded through DAO classes (`src/dojo/*/dao.py`). Services only consume typed dataclasses returned by the DAO methods, which keeps business rules pure Python and ensures the temporal ledger constraints stay centralized.
- **SPA Composition**: `src/dojo/frontend/static/main.js` bootstraps hash-based routing, registers each page module (`components/{transactions,accounts,budgets,allocations,transfers}/index.js`), and integrates the shared `store.js`. State updates are immutable (`store.setState`/`patchState`) and all DOM fetches go through `services/api.js` + `services/dom.js` helpers.
- **Styles & Assets**: Styles are broken into global primitives (`styles/base.css`, `styles/forms.css`, `styles/layout.css`, `styles/ledger.css`) plus feature-scoped bundles in `styles/components/*.css` that follow the documented BEM conventions.

## Status

- **What it does today**: [List of current features]
- **Out of Scope**: [List of non-goals]
- **Stability**: The project is currently in **alpha**. APIs may change.
- **Changelog**: All changes are documented in the [CHANGELOG.md](./CHANGELOG.md).

## Setup

### Supported Platforms

- **Operating Systems**: Linux, macOS (via Nix)

### Prerequisites

- [Nix Package Manager](https://nixos.org/download.html)
- [direnv](https://direnv.net/docs/installation.html)

### Installation Steps

This project manages system dependencies via Nix and Python dependencies via `uv`. We use `direnv` to automate the environment setup.

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd dojo
    ```

2.  **Allow direnv:**
    When you first `cd` into the directory, `direnv` will prompt you for permission.
    ```bash
    direnv allow .
    ```
    This command triggers the activation of the Nix flake development shell, which in turn sets up the `uv` virtual environment based on `pyproject.toml`.

3.  **Sync Python Dependencies (if needed):**
    If you modify `pyproject.toml` or need to manually resync, run:
    ```bash
    uv sync
    ```

### Manual Environment Activation

If you do not enable `direnv`, start a shell with `nix develop` from the repository root and run commands directly inside that shell.

```bash
nix develop
```

### Configuration

- **`DOJO_DB_PATH`**: Override the DuckDB ledger location (defaults to `data/ledger.duckdb`). Set this before running migrations or starting the API, e.g. `DOJO_DB_PATH=/tmp/ledger.duckdb python -m dojo.core.migrate`.
- **Seed scripts**: Run `python -m dojo.core.seed` (optionally with `DOJO_DB_PATH` set) to populate dev/demo data. Skip it or delete the DuckDB file if you want a pristine ledger.
- **`dojo_` prefixed env vars**: All settings inherited from `dojo.core.config.Settings` can be supplied via environment variables (e.g., `DOJO_DB_PATH`).
- **Secrets**: The MVP stores only local household data and does not require external credentials yet. Do not commit secrets; once services require them, document the process in this section.

## Usage

### SPA Budgeting Flows

- **Transactions (`#/transactions`)**: Use the compact transaction form above the ledger to record inflows or outflows. Pick the account & category, set the type toggle (Outflow/Inflow), enter the memo/amount (always dollars), and submit to post `/api/transactions`. Click any ledger row (or its status pill) to edit inline—change the amount, account, category, flow, or pending/cleared flag—and save without leaving the table. Hero cards surface spent vs. budgeted month-to-date totals sourced directly from the ledger and allocation APIs so they reconcile with Ready-to-Assign.
- **Allocations (`#/allocations`)**: Dedicated summary chips show “Inflow (this month)” and “Available to budget,” and the ledger lists every movement between envelopes. The form captures date, optional source category (defaulting to Ready-to-Assign), destination category, memo, and amount before posting to `/api/budget/allocations`.
- **Budgets (`#/budgets`)**: The summary bar shows Ready-to-Assign, activity, available amounts, and the active month for quick context. Use “Add category” to open the modal (slug auto-fills from the name) and manage envelopes; the Allocate button routes to the allocations page with the destination pre-selected.
- **Categorized transfers (`#/transfers`)**: The dedicated Transfers page hosts the dual-leg form. Select distinct source/destination accounts plus a reimbursement category, enter the amount in dollars, and submit to hit `/api/transfers`. The toast exposes concept + transaction ids so you can cross-check the ledger rows (`data-concept-id` attributes).

### Manual Validation Walkthrough

To verify the end-to-end flows manually:

1.  **Transaction capture & reconciliation**:
    - Navigate to `#/transactions`.
    - Record a $50.00 outflow for "Dining Out".
    - Click the row to edit, change the amount to $60.00 (adding a tip), and toggle status to "Cleared".
    - Verify the row updates and the "Spent This Month" card increases.

2.  **Allocation logging**:
    - Navigate to `#/budgets` and click a category row (e.g., "Groceries").
    - Use the "Quick Allocations" buttons in the modal to fund the category.
    - If you try to allocate more than your "Ready to Assign" balance, observe the error message preventing the action.

3.  **Budget hierarchy management**:
    - Navigate to `#/budgets`.
    - Click "+ Add group" to create a "Subscriptions" group.
    - Create a new budget "Netflix" and assign it to "Subscriptions".
    - Verify the hierarchy renders correctly and the "Uncategorized" group hides if it becomes empty.

### CLI

The MVP focuses on the FastAPI + SPA surface; there is no standalone CLI today. All interactions happen via HTTP:

```bash
# Insert a transaction via the API
python - <<'PY'
import requests
payload = {
    "transaction_date": "2025-11-11",
    "account_id": "house_checking",
    "category_id": "groceries",
    "amount_minor": -1234,
}
print(requests.post("http://127.0.0.1:8000/api/transactions", json=payload, timeout=10).json())
PY
```

For detailed architectural background see [docs/architecture/overview.md](./docs/architecture/overview.md).

## Operations

- **Logging**: The FastAPI app logs to STDOUT; DuckDB connections log open/close events via `dojo.core.db`.
- **Troubleshooting**:
    - **Problem**: `npx cypress run --e2e --browser <browser> [--headed]` stalls because the test server never becomes healthy. **Solution**: Check the inline server logs printed by Cypress, ensure no other process is using `data/e2e-ledger.duckdb`, delete the file if needed, and rerun so `tests.e2e.prepare_db` can recreate it.
    - **Problem**: DuckDB file not found. **Solution**: Run the migration command (Step 2) or set `DOJO_DB_PATH`.
- **Performance Tips**: Use in-memory DuckDB (`:memory:`) for tests/experiments to avoid disk I/O when iterating on SQL.
- **Updating**: After pulling new changes, run `uv sync --extra dev` to refresh dependencies.
- **Uninstalling**: Remove the repo directory; DuckDB data lives under `data/`.

## Contributing

We welcome contributions! Please follow these guidelines.

- **Run Tests**:
  ```bash
  scripts/run-tests
  ```
  Use the `--skip-*` flags explained in `scripts/README.md` when suites aren’t relevant.
- **Lint & Format**:
  ```bash
  scripts/lint
  ```
- **Tooling Details**: See [`scripts/README.md`](./scripts/README.md) for how lint/test scripts orchestrate Ruff, sqlfluff, Biome, and the inline SQL guard.
- **Branch/PR Guidelines**: See [CONTRIBUTING.md](./CONTRIBUTING.md).
- **Issue Templates**: Use the provided templates for bug reports and feature requests.
- **Code of Conduct**: See [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md).

## Trust & License

- **License**: This project is licensed under the [MIT License](./LICENSE).
- **Security Policy**: For responsible disclosure, please see our [SECURITY.md](./SECURITY.md).
- **Provenance**: [Note on data/models used]
- **Telemetry**: This project [does/does not] collect telemetry data. [Link to privacy policy if applicable].
- **Get Help**:
    - Open an issue on GitHub.
    - [Link to Discord/Slack/Forum]
