"""Services related to database management for testing purposes."""

import os
from pathlib import Path

from ..core.migrate import migrate
from .dao import get_testing_dao


def reset_db(db_path: Path) -> None:
    """
    Drops all tables in the specified database and re-runs migrations.

    This function is crucial for ensuring a clean slate for tests. It
    removes the existing database file, then re-applies all schema migrations
    to create a fresh database structure.

    Parameters
    ----------
    db_path : Path
        The file path to the DuckDB database.
    """
    # Remove the existing database file to ensure a clean reset.
    if db_path.exists():
        os.remove(db_path)

    # After removing the file, re-create the database and apply all pending migrations.
    migrate(db_path=db_path)


def seed_db(db_path: Path, fixture_path: str) -> None:
    """
    Seeds the database with data from a SQL fixture file.

    This function reads a SQL script from a specified fixture path and
    executes it against the database to populate it with test data.

    Parameters
    ----------
    db_path : Path
        The file path to the DuckDB database.
    fixture_path : str
        The path to the SQL fixture file, relative to the project root.

    Raises
    ------
    FileNotFoundError
        If the specified fixture file does not exist.
    """
    # Construct an absolute path to the fixture file.
    # It assumes the fixture_path is relative to the project root.
    project_root = Path(__file__).parent.parent.parent.parent
    full_path = project_root / fixture_path

    # Verify that the fixture file actually exists.
    if not full_path.exists():
        raise FileNotFoundError(f"Fixture file not found: {full_path}")

    # Read the content of the SQL fixture file.
    sql_script = full_path.read_text()
    # Get a testing DAO instance and run the SQL script.
    dao = get_testing_dao(db_path=db_path)
    dao.run_script(sql_script=sql_script)
