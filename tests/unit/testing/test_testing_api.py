import duckdb
import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from dojo.core.app import create_app
from dojo.core.config import Settings, get_settings


@pytest.fixture
def test_db_path(tmp_path: Path) -> Path:
    """Uses a temporary directory for the test database."""
    return tmp_path / "test_ledger.duckdb"


@pytest.fixture
def testing_settings(test_db_path: Path) -> Settings:
    """Returns settings for testing mode."""
    return Settings(db_path=test_db_path, testing=True)


@pytest.fixture
def non_testing_settings(test_db_path: Path) -> Settings:
    """Returns settings for non-testing (production) mode."""
    return Settings(db_path=test_db_path, testing=False)


@pytest.fixture
def client(testing_settings: Settings):
    """Returns a TestClient for the app in testing mode."""
    app = create_app(settings=testing_settings)

    def get_test_settings():
        return testing_settings

    app.dependency_overrides[get_settings] = get_test_settings
    with TestClient(app) as c:
        yield c


@pytest.fixture
def non_testing_client(non_testing_settings: Settings):
    """Returns a TestClient for the app in non-testing mode."""
    app = create_app(settings=non_testing_settings)

    def get_non_test_settings():
        return non_testing_settings

    app.dependency_overrides[get_settings] = get_non_test_settings
    with TestClient(app) as c:
        yield c


def test_reset_db_endpoint_not_available_in_prod_mode(non_testing_client):
    """Verifies that /testing/reset_db returns 404 when not in testing mode."""
    response = non_testing_client.post("/api/testing/reset_db")
    assert response.status_code == 404


def test_seed_db_endpoint_not_available_in_prod_mode(non_testing_client):
    """Verifies that /testing/seed_db returns 404 when not in testing mode."""
    response = non_testing_client.post("/api/testing/seed_db", json={"fixture": "dummy.sql"})
    assert response.status_code == 404


def test_reset_db(client, test_db_path: Path):
    """Tests the /testing/reset_db endpoint."""
    # 1. Create a dummy file to ensure it gets deleted and recreated.
    test_db_path.touch()
    assert test_db_path.exists()

    # 2. Call the reset endpoint.
    response = client.post("/api/testing/reset_db")
    assert response.status_code == 204

    # 3. The db file should exist because migrations ran and recreated it.
    assert test_db_path.exists()

    # 4. Check if the migrations table exists as evidence of migration.
    with duckdb.connect(str(test_db_path)) as con:
        tables = con.execute("SHOW TABLES").fetchall()
        assert ("schema_migrations",) in tables


def test_seed_db(client, test_db_path: Path):
    """Tests the /testing/seed_db endpoint with a valid fixture."""
    # 1. Reset db to have a clean state.
    client.post("/api/testing/reset_db")

    # 2. Seed the database with a test-specific fixture.
    fixture_path = "tests/fixtures/for_unit_testing.sql"
    assert Path(fixture_path).exists(), "Test fixture is missing."
    payload = {"fixture": fixture_path}
    response = client.post("/api/testing/seed_db", json=payload)
    if response.status_code != 204:
        print(response.json())
    assert response.status_code == 204

    # 3. Check if the table from the fixture was created.
    with duckdb.connect(str(test_db_path)) as con:
        tables = con.execute("SHOW TABLES").fetchall()
        assert ("seeded_for_test",) in tables


def test_seed_db_file_not_found(client):
    """Tests the /testing/seed_db endpoint with a non-existent fixture."""
    payload = {"fixture": "non_existent_fixture.sql"}
    response = client.post("/api/testing/seed_db", json=payload)
    assert response.status_code == 404