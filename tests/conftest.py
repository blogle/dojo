"""
Shared pytest fixtures for setting up and tearing down test environments.

This module provides common fixtures, such as an in-memory DuckDB database,
to ensure consistent and isolated testing for the Dojo application.
"""

from collections.abc import Generator
from importlib import resources

import duckdb
import pytest

from dojo.core.migrate import apply_migrations
from dojo.testing.fixtures import apply_base_budgeting_fixture


@pytest.fixture()
def in_memory_db() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """
    Provides a pre-configured in-memory DuckDB connection for tests.

    This fixture initializes an in-memory DuckDB database, applies all schema
    migrations, and then populates it with base budgeting seed data. The
    connection is yielded to the test and closed upon test completion.

    Yields
    ------
    Generator[duckdb.DuckDBPyConnection, None, None]
        A DuckDB in-memory database connection object.
    """
    # Establish an in-memory DuckDB connection.
    conn = duckdb.connect(database=":memory:")
    # Get the package path where migration SQL files are located.
    migrations_pkg = resources.files("dojo.sql.migrations")
    # Apply all schema migrations to the in-memory database.
    apply_migrations(conn, migrations_pkg)
    # Apply a base set of budgeting data for tests.
    apply_base_budgeting_fixture(conn)
    try:
        # Yield the configured connection to the test function.
        yield conn
    finally:
        # Ensure the connection is closed after the test completes.
        conn.close()
