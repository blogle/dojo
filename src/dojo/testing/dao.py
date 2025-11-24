"""Data access helpers for the testing utilities."""

from pathlib import Path

from dojo.core.db import get_connection


class TestingDAO:
    """Executes SQL scripts through the standard DuckDB connection path."""

    def __init__(self, db_path: Path):
        self._db_path = db_path

    def run_script(self, sql_script: str) -> None:
        """Execute the given SQL script inside a serialized DuckDB session."""
        if not sql_script.strip():
            return

        with get_connection(self._db_path) as conn:
            conn.execute(sql_script)


def get_testing_dao(db_path: Path) -> TestingDAO:
    """Factory to mirror other domains' DAO construction."""
    return TestingDAO(db_path=db_path)
