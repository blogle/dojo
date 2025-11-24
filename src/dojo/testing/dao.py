"""Data access helpers for the testing utilities."""

from pathlib import Path

from dojo.core.db import get_connection


class TestingDAO:
    """
    Executes SQL scripts through the standard DuckDB connection path.

    This Data Access Object (DAO) is specifically designed for testing purposes,
    allowing direct execution of SQL scripts against a DuckDB database.
    """

    def __init__(self, db_path: Path):
        """
        Initializes the TestingDAO with the path to the DuckDB database.

        Parameters
        ----------
        db_path : Path
            The file path to the DuckDB database.
        """
        self._db_path = db_path

    def run_script(self, sql_script: str) -> None:
        """
        Executes the given SQL script inside a serialized DuckDB session.

        This method is useful for applying test fixtures, seeding data, or
        performing ad-hoc database operations within a testing context.

        Parameters
        ----------
        sql_script : str
            The SQL script to execute. Multiple statements can be included,
            separated by semicolons.
        """
        # Only execute if the script is not empty.
        if not sql_script.strip():
            return

        # Acquire a database connection and execute the script within its context.
        with get_connection(self._db_path) as conn:
            conn.execute(sql_script)


def get_testing_dao(db_path: Path) -> TestingDAO:
    """
    Factory function to construct a `TestingDAO` instance.

    This function mirrors the pattern of other domain DAO constructions,
    providing a consistent way to obtain a DAO for testing.

    Parameters
    ----------
    db_path : Path
        The file path to the DuckDB database.

    Returns
    -------
    TestingDAO
        An instance of `TestingDAO` configured for the specified database path.
    """
    return TestingDAO(db_path=db_path)
