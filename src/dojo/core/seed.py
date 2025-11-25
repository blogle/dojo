"""Seed runner for dev/demo data sets."""

import logging
from collections.abc import Iterable
from importlib.resources import files
from importlib.resources.abc import Traversable

import duckdb

from dojo.core.config import Settings, get_settings
from dojo.core.db import get_connection

logger = logging.getLogger(__name__)


def _list_sql_files(seeds_pkg: Traversable) -> Iterable[Traversable]:
    """
    Lists all SQL files within the specified package path, sorted by name.

    Parameters
    ----------
    seeds_pkg : Traversable
        The package path (e.g., from `importlib.resources.files`) to search for SQL files.

    Returns
    -------
    Iterable[Traversable]
        An iterable of `Traversable` objects, each representing a sorted SQL seed file.
    """
    # Sort files by name to ensure seeds are applied in a consistent order.
    return sorted(
        (child for child in seeds_pkg.iterdir() if child.name.endswith(".sql")),
        key=lambda child: child.name,
    )


def apply_seeds(conn: duckdb.DuckDBPyConnection, seeds_pkg: Traversable) -> None:
    """
    Execute each seed SQL file inside a transaction.

    This function iterates through all SQL files in the provided package,
    executing each one within its own database transaction. This is typically
    used to populate a database with initial or demo data.

    Parameters
    ----------
    conn : duckdb.DuckDBPyConnection
        The DuckDB connection object.
    seeds_pkg : Traversable
        The package path containing the SQL seed files.

    Raises
    ------
    Exception
        If any seed script fails, the transaction is rolled back and the exception re-raised.
    """
    for sql_file in _list_sql_files(seeds_pkg):
        logger.info("Applying seed script %s", sql_file.name)
        # Read SQL content from the file.
        sql = sql_file.read_text(encoding="utf-8")
        # Start a transaction for the seed script.
        conn.execute("BEGIN")
        try:
            # Execute the seed SQL.
            conn.execute(sql)
            # Commit the transaction if successful.
            conn.execute("COMMIT")
        except Exception:  # pragma: no cover - re-raised for context
            # Rollback on any error during seed application.
            conn.execute("ROLLBACK")
            logger.exception("Seed script %s failed, rolled back", sql_file.name)
            raise


def main() -> None:
    """
    Main entry point for the seed script when run as a standalone module.

    Loads settings and initiates the seed application process for the configured database path.
    This is typically used in development or testing environments to populate data.
    """
    settings: Settings = get_settings()
    # Get the package path where seed SQL files are located.
    seeds_pkg = files("dojo.sql.seeds")
    # Establish a connection and apply all seed scripts.
    with get_connection(settings.db_path) as conn:
        apply_seeds(conn, seeds_pkg)
    logger.info("Seed scripts applied to %s", settings.db_path)


if __name__ == "__main__":  # pragma: no cover - module entry
    main()
