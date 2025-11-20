"""Ensure the E2E DuckDB database is migrated and seeded."""

import os
from importlib import resources
from pathlib import Path

import duckdb

from dojo.core.migrate import apply_migrations
from dojo.core.seed import apply_seeds

DEFAULT_DB_PATH = Path("data/e2e-ledger.duckdb")


def main() -> None:
    db_path = Path(os.environ.get("DOJO_DB_PATH", DEFAULT_DB_PATH))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(db_path))
    try:
        migrations_pkg = resources.files("dojo.sql.migrations")
        apply_migrations(conn, migrations_pkg)
        seeds_pkg = resources.files("dojo.sql.seeds")
        apply_seeds(conn, seeds_pkg)
        conn.execute("DELETE FROM transactions")
        conn.execute("DELETE FROM budget_category_monthly_state")
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
        conn.close()


if __name__ == "__main__":
    main()
