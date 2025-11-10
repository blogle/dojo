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

This section provides the fastest path to getting the project up and running.

### Installation

The single command to get started, assuming you have `nix` and `direnv` installed and configured:

```bash
# This will automatically set up the environment when you enter the directory
cd dojo
```

### Example

Here is a minimal example of how to use the project.

```bash
# Example command
direnv exec . your_command --with --args
```

**Expected Output:**

*(A screenshot, GIF, or text block showing the expected result)*

```
Success! The command completed as expected.
```

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

If you do not use `direnv`, you can manually activate the environment for any command using `direnv exec`:

```bash
direnv exec . <your-command>
```

### Configuration

- **Environment Variables**: [List of ENV_VARS and their purpose]
- **Secrets Handling**: Secrets are managed via [SECRET_MANAGEMENT_TOOL/PROCESS]. Do not commit secrets to the repository. See `/.env.example` for required variables.

## Usage

*(Copy-pasteable snippets for CLI/API usage)*

### CLI

```bash
# Example CLI command
direnv exec . dojo-cli --action "perform-task" --output "result.json"
```

### API

```python
# Example API usage
from dojo import api

result = api.do_something(param="value")
print(result)
```

For more detailed information, see the [fuller docs](./docs/README.md).

## Operations

- **Logging**: Logs are sent to [STDOUT/FILE/LOGGING_SERVICE].
- **Troubleshooting**:
    - **Problem**: `direnv` is not activating.
    - **Solution**: Ensure `direnv` is installed and hooked into your shell. Run `direnv allow .`.
    - **Problem**: Python dependencies are out of sync.
    - **Solution**: Run `uv sync`.
- **Performance Tips**: [Tips for optimal performance]
- **Updating**: To update the project, pull the latest changes and re-sync the environment.
    ```bash
    git pull origin main
    uv sync
    ```
- **Uninstalling**: To remove the project and its environment, simply remove the project directory.

## Contributing

We welcome contributions! Please follow these guidelines.

- **Run Tests**:
  ```bash
  direnv exec . pytest
  ```
- **Style Rules**: We use Ruff (linting), Black (formatting), and Pyright (type-checking).
  ```bash
  # Check for linting and formatting issues
  direnv exec . ruff check .
  direnv exec . black --check .
  
  # Run type-checking
  direnv exec . pyright
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
