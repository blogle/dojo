"""Shared fixtures for integration tests."""

from collections.abc import Generator
from pathlib import Path
from importlib import resources

import duckdb
import pytest
from fastapi.testclient import TestClient

from dojo.core.app import create_app
from dojo.core.config import Settings
from dojo.core.db import connection_dep
from dojo.core.migrate import apply_migrations


@pytest.fixture()
def pristine_db() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Provide a fresh in-memory DuckDB connection with migrations applied."""
    conn = duckdb.connect(database=":memory:")
    migrations_pkg = resources.files("dojo.sql.migrations")
    apply_migrations(conn, migrations_pkg)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture()
def api_client(pristine_db: duckdb.DuckDBPyConnection) -> Generator[TestClient, None, None]:
    """FastAPI TestClient wired to the shared pristine in-memory database."""
    settings = Settings(
        db_path=Path("integration-tests.duckdb"),
        run_startup_migrations=False,
        testing=True,
    )
    app = create_app(settings)

    def override_db() -> Generator[duckdb.DuckDBPyConnection, None, None]:
        yield pristine_db

    app.dependency_overrides[connection_dep] = override_db

    with TestClient(app) as client:
        yield client
