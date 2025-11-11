"""Shared pytest fixtures."""

from collections.abc import Generator
from importlib import resources

import duckdb
import pytest

from dojo.core.migrate import apply_migrations


@pytest.fixture()
def in_memory_db() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Provide an in-memory DuckDB connection with schema + seed data."""

    conn = duckdb.connect(database=":memory:")
    migrations_pkg = resources.files("dojo.sql.migrations")
    apply_migrations(conn, migrations_pkg)
    try:
        yield conn
    finally:
        conn.close()
