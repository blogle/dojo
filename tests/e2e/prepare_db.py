"""
Prepares the E2E (End-to-End) test database.

This script ensures that the DuckDB database used for E2E tests is
properly migrated to the latest schema and seeded with a baseline dataset.
It also includes logic to reset specific tables to a known state for tests.
"""

import os
from importlib import resources
from pathlib import Path

import duckdb

from dojo.core.migrate import apply_migrations
from dojo.core.seed import apply_seeds

# Default path for the E2E test database file.
DEFAULT_DB_PATH = Path("data/e2e-ledger.duckdb")


def main() -> None:
    """
    Main function to prepare the E2E test database.

    This function performs the following steps:
    1. Determines the database path, prioritizing `DOJO_DB_PATH` environment variable.
    2. Ensures the parent directory for the database file exists.
    3. Connects to the DuckDB database.
    4. Applies all schema migrations.
    5. Applies all seed data.
    6. Resets specific tables (`transactions`, `budget_category_monthly_state`)
       to ensure a clean state for E2E tests.
    7. Updates initial account balances and activity status.
    8. Closes the database connection.
    """
    # Determine the database path, allowing override via environment variable.
    db_path = Path(os.environ.get("DOJO_DB_PATH", DEFAULT_DB_PATH))
    # Ensure the parent directory for the database file exists.
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # Connect to the DuckDB database.
    conn = duckdb.connect(str(db_path))
    try:
        # Get the package path where migration SQL files are located and apply them.
        migrations_pkg = resources.files("dojo.sql.migrations")
        apply_migrations(conn, migrations_pkg)
        # Get the package path where seed SQL files are located and apply them.
        seeds_pkg = resources.files("dojo.sql.seeds")
        apply_seeds(conn, seeds_pkg)

        # Reset transactions and budget monthly state for a clean test run.
        conn.execute("DELETE FROM transactions")
        conn.execute("DELETE FROM budget_category_monthly_state")
        # Update specific account balances and activation status to a known state for tests.
        conn.execute(
            """
            UPDATE accounts
            SET current_balance_minor = CASE account_id
                WHEN 'house_checking' THEN 500000
                WHEN 'house_savings' THEN 1250000
                WHEN 'house_credit_card' THEN 250000
                ELSE current_balance_minor
            END,
            is_active = TRUE
            """
        )
    finally:
        # Ensure the database connection is closed.
        conn.close()


if __name__ == "__main__":
    main()
