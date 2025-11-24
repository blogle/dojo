"""Shared helpers for loading SQL fixtures in tests."""

from pathlib import Path

import duckdb

# Define the absolute path to the directory containing SQL fixture files.
# This path is constructed relative to the current file to ensure portability.
FIXTURES_DIR = Path(__file__).resolve().parents[3] / "tests" / "fixtures"


def apply_sql_fixture(conn: duckdb.DuckDBPyConnection, filename: str) -> None:
    """
    Executes a named SQL file from the `tests/fixtures` directory.

    This function is used in testing to set up specific database states
    by running predefined SQL scripts. Each script is executed within
    a transaction to ensure atomicity.

    Parameters
    ----------
    conn : duckdb.DuckDBPyConnection
        The DuckDB connection object to execute the SQL against.
    filename : str
        The name of the SQL fixture file (e.g., "my_test_data.sql").

    Raises
    ------
    FileNotFoundError
        If the specified fixture file does not exist.
    Exception
        If an error occurs during SQL execution, the transaction is rolled back.
    """
    # Construct the full path to the SQL fixture file.
    fixture_path = FIXTURES_DIR / filename
    # Defensive guard: ensure the fixture file exists.
    if not fixture_path.exists():  # pragma: no cover - defensive guard for CI misconfig
        msg = f"Fixture file not found: {fixture_path}"
        raise FileNotFoundError(msg)
    # Read the SQL content from the fixture file.
    sql = fixture_path.read_text(encoding="utf-8")
    # Begin a transaction for the SQL execution.
    conn.execute("BEGIN")
    try:
        # Execute the SQL script.
        conn.execute(sql)
        # Commit the transaction if successful.
        conn.execute("COMMIT")
    except Exception:  # pragma: no cover - pytest surfaces SQL errors better
        # Rollback the transaction on any error.
        conn.execute("ROLLBACK")
        raise


def apply_base_budgeting_fixture(conn: duckdb.DuckDBPyConnection) -> None:
    """
    Loads the canonical budgeting fixture used across test suites.

    This is a convenience function that applies a standard set of budgeting
    data to the database, providing a consistent baseline for tests.

    Parameters
    ----------
    conn : duckdb.DuckDBPyConnection
        The DuckDB connection object.
    """
    # Call the generic fixture application function with the specific base budgeting SQL file.
    apply_sql_fixture(conn, "base_budgeting.sql")
