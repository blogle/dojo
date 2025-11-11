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

The development shell installs Python, DuckDB, uv, and other pinned tooling.

### 2. Apply migrations (creates `data/ledger.duckdb`)

```bash
python -m dojo.core.migrate
```

### 3. Run the API + SPA locally

```bash
uvicorn dojo.core.app:app --reload
# open http://127.0.0.1:8000/ in your browser
```

The landing page now behaves like a lightweight spreadsheet: the first row is an input line, arrow/tab keys move across cells, Enter submits, and the table below scrolls to show prior transactions.

### 4. Execute the automated tests

```bash
pytest
npx cypress run --e2e --browser <browser> [--headed]
```

The Cypress run spins up a dedicated DuckDB database (`data/e2e-ledger.duckdb`) and launches the FastAPI server automatically via `cypress.config.cjs`, so no additional setup is required.

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

If you do not enable `direnv`, you can manually activate the environment for any command using `direnv exec`:

```bash
direnv exec . <your-command>
```

or manually invoke the flake to build the dev environment:

```bash
nix develop
```

### Configuration

- **`DOJO_DB_PATH`**: Override the DuckDB ledger location (defaults to `data/ledger.duckdb`). Set this before running migrations or starting the API, e.g. `DOJO_DB_PATH=/tmp/ledger.duckdb python -m dojo.core.migrate`.
- **`dojo_` prefixed env vars**: All settings inherited from `dojo.core.config.Settings` can be supplied via environment variables (e.g., `DOJO_DB_PATH`).
- **Secrets**: The MVP stores only local household data and does not require external credentials yet. Do not commit secrets; once services require them, document the process in this section.

## Usage

*(Copy-pasteable snippets for CLI/API usage)*

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
  pytest
  npx cypress run --e2e --browser <browser> [--headed]
  ```
- **Style Rules**: We rely on Ruff for lint+format and Pyright for type checking.
  ```bash
  ruff check .
  pyright
  ```
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
