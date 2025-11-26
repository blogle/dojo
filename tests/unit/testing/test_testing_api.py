"""
Unit tests for the testing API endpoints.

This module contains tests for the `/api/testing` endpoints, which provide
functionalities to reset and seed the database for development and testing purposes.
It ensures that these endpoints work as expected in testing mode and are
correctly disabled in non-testing (production) mode.
"""

from collections.abc import Generator
from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

from dojo.core.app import create_app
from dojo.core.config import Settings, get_settings


@pytest.fixture
def test_db_path(tmp_path: Path) -> Path:
    """
    Pytest fixture that provides a temporary file path for the test database.

    The database file will be created within a temporary directory managed by pytest.

    Parameters
    ----------
    tmp_path : Path
        Pytest's fixture for a temporary directory unique to the test session.

    Returns
    -------
    Path
        A `Path` object pointing to the temporary database file.
    """
    return tmp_path / "test_ledger.duckdb"


@pytest.fixture
def testing_settings(test_db_path: Path) -> Settings:
    """
    Pytest fixture that returns application settings configured for testing mode.

    The `db_path` points to the temporary test database, and `testing` flag is set to True.

    Parameters
    ----------
    test_db_path : Path
        The path to the temporary database provided by `test_db_path` fixture.

    Returns
    -------
    Settings
        An instance of `Settings` configured for testing.
    """
    return Settings(db_path=test_db_path, testing=True)


@pytest.fixture
def non_testing_settings(test_db_path: Path) -> Settings:
    """
    Pytest fixture that returns application settings configured for non-testing mode.

    The `db_path` points to the temporary test database, but the `testing` flag is set to False.

    Parameters
    ----------
    test_db_path : Path
        The path to the temporary database provided by `test_db_path` fixture.

    Returns
    -------
    Settings
        An instance of `Settings` configured for non-testing.
    """
    return Settings(db_path=test_db_path, testing=False)


@pytest.fixture
def client(testing_settings: Settings) -> Generator[TestClient, None, None]:
    """
    Pytest fixture that provides a `TestClient` for the FastAPI application in testing mode.

    This client is configured to use the `testing_settings` fixture, ensuring
    that the application behaves as expected for test scenarios, including
    enabling testing-specific API routes.

    Parameters
    ----------
    testing_settings : Settings
        Application settings configured for testing mode.

    Yields
    ------
    TestClient
        A FastAPI `TestClient` instance.
    """
    # Create the FastAPI application with testing settings.
    app = create_app(settings=testing_settings)

    # Override the `get_settings` dependency to inject the testing settings.
    def get_test_settings() -> Settings:
        return testing_settings

    app.dependency_overrides[get_settings] = get_test_settings
    with TestClient(app) as c:
        yield c


@pytest.fixture
def non_testing_client(non_testing_settings: Settings) -> Generator[TestClient, None, None]:
    """
    Pytest fixture that provides a `TestClient` for the FastAPI application in non-testing mode.

    This client is configured to use the `non_testing_settings` fixture, ensuring
    that testing-specific API routes are disabled, mimicking a production environment.

    Parameters
    ----------
    non_testing_settings : Settings
        Application settings configured for non-testing mode.

    Yields
    ------
    TestClient
        A FastAPI `TestClient` instance.
    """
    # Create the FastAPI application with non-testing settings.
    app = create_app(settings=non_testing_settings)

    # Override the `get_settings` dependency to inject the non-testing settings.
    def get_non_test_settings() -> Settings:
        return non_testing_settings

    app.dependency_overrides[get_settings] = get_non_test_settings
    with TestClient(app) as c:
        yield c


def test_reset_db_endpoint_not_available_in_prod_mode(non_testing_client: TestClient) -> None:
    """
    Verifies that the `/api/testing/reset_db` endpoint returns a 404 Not Found
    error when the application is running in non-testing (production) mode.

    This ensures that sensitive testing functionalities are not exposed in production.

    Parameters
    ----------
    non_testing_client : TestClient
        A FastAPI test client configured for non-testing mode.
    """
    response = non_testing_client.post("/api/testing/reset_db")
    assert response.status_code == 404


def test_seed_db_endpoint_not_available_in_prod_mode(non_testing_client: TestClient) -> None:
    """
    Verifies that the `/api/testing/seed_db` endpoint returns a 404 Not Found
    error when the application is running in non-testing (production) mode.

    This ensures that sensitive testing functionalities are not exposed in production.

    Parameters
    ----------
    non_testing_client : TestClient
        A FastAPI test client configured for non-testing mode.
    """
    response = non_testing_client.post("/api/testing/seed_db", json={"fixture": "dummy.sql"})
    assert response.status_code == 404


def test_reset_db(client: TestClient, test_db_path: Path) -> None:
    """
    Tests the `/api/testing/reset_db` endpoint in testing mode.

    Verifies that calling this endpoint successfully deletes and recreates
    the database file, and that migrations are re-applied.

    Parameters
    ----------
    client : TestClient
        A FastAPI test client configured for testing mode.
    test_db_path : Path
        The path to the temporary database file.
    """
    # 1. Create a dummy file to ensure it gets deleted and recreated.
    test_db_path.touch()
    assert test_db_path.exists()

    # 2. Call the reset endpoint.
    response = client.post("/api/testing/reset_db")
    assert response.status_code == 204

    # 3. The db file should exist because migrations ran and recreated it.
    assert test_db_path.exists()

    # 4. Check if the migrations table exists as evidence of migration application.
    with duckdb.connect(str(test_db_path)) as con:
        tables = con.execute("SHOW TABLES").fetchall()
        assert ("schema_migrations",) in tables


def test_seed_db(client: TestClient, test_db_path: Path) -> None:
    """
    Tests the `/api/testing/seed_db` endpoint with a valid fixture file.

    Verifies that seeding the database with a SQL fixture successfully populates
    the database with the expected data.

    Parameters
    ----------
    client : TestClient
        A FastAPI test client configured for testing mode.
    test_db_path : Path
        The path to the temporary database file.
    """
    # 1. Reset the database to ensure a clean state before seeding.
    client.post("/api/testing/reset_db")

    # 2. Seed the database with a test-specific fixture file.
    fixture_path = "tests/fixtures/for_unit_testing.sql"
    # Assert that the fixture file actually exists.
    assert Path(fixture_path).exists(), "Test fixture is missing."
    payload = {"fixture": fixture_path}
    response = client.post("/api/testing/seed_db", json=payload)
    # Print response content if an error occurs for easier debugging.
    if response.status_code != 204:
        print(response.json())
    assert response.status_code == 204

    # 3. Check if the table created by the fixture was successfully inserted.
    with duckdb.connect(str(test_db_path)) as con:
        tables = con.execute("SHOW TABLES").fetchall()
        assert ("seeded_for_test",) in tables


def test_seed_db_file_not_found(client: TestClient) -> None:
    """
    Tests the `/api/testing/seed_db` endpoint with a non-existent fixture file.

    Verifies that attempting to seed the database with a non-existent fixture
    returns a 404 Not Found error.

    Parameters
    ----------
    client : TestClient
        A FastAPI test client configured for testing mode.
    """
    payload = {"fixture": "non_existent_fixture.sql"}
    response = client.post("/api/testing/seed_db", json=payload)
    assert response.status_code == 404
