"""Simple DuckDB migration runner."""

import logging
from collections.abc import Iterable
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path

import duckdb

from dojo.core.config import Settings, get_settings
from dojo.core.db import get_connection

logger = logging.getLogger(__name__)


def _ensure_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """
    Ensures the existence of the `schema_migrations` table.

    This table tracks which migration files have already been applied to the database.

    Parameters
    ----------
    conn : duckdb.DuckDBPyConnection
        The DuckDB connection object.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _list_sql_files(migrations_pkg: Traversable) -> Iterable[Traversable]:
    """
    Lists all SQL files within the specified package path, sorted by name.

    Parameters
    ----------
    migrations_pkg : Traversable
        The package path (e.g., from `importlib.resources.files`) to search for SQL files.

    Returns
    -------
    Iterable[Traversable]
        An iterable of `Traversable` objects, each representing a sorted SQL migration file.
    """
    # Sort files by name to ensure migrations are applied in a consistent order.
    return sorted(
        (child for child in migrations_pkg.iterdir() if child.name.endswith(".sql")),
        key=lambda child: child.name,
    )


def apply_migrations(conn: duckdb.DuckDBPyConnection, migrations_pkg: Traversable) -> None:
    """
    Applies unapplied SQL migration files from a package to the database.

    This function ensures that each migration is applied exactly once by tracking
    them in the `schema_migrations` table. Each migration is run within a
    transaction to ensure atomicity.

    Parameters
    ----------
    conn : duckdb.DuckDBPyConnection
        The DuckDB connection object.
    migrations_pkg : Traversable
        The package path containing the SQL migration files.

    Raises
    ------
    Exception
        If any migration fails, the transaction is rolled back and the exception re-raised.
    """
    _ensure_schema(conn)
    # Fetch already applied migrations to avoid re-applying them.
    applied = {filename for (filename,) in conn.execute("SELECT filename FROM schema_migrations").fetchall()}
    for sql_file in _list_sql_files(migrations_pkg):
        if sql_file.name in applied:
            logger.info("Skipping %s (already applied)", sql_file.name)
            continue
        logger.info("Applying migration %s", sql_file.name)
        # Read SQL content from the file.
        sql = sql_file.read_text(encoding="utf-8")
        # Start a transaction for the migration.
        conn.execute("BEGIN")
        try:
            # Execute the migration SQL.
            conn.execute(sql)
            # Record the applied migration in the schema_migrations table.
            conn.execute(
                "INSERT INTO schema_migrations (filename) VALUES ($filename)",
                {"filename": sql_file.name},
            )
            # Commit the transaction if successful.
            conn.execute("COMMIT")
        except Exception:
            # Rollback on any error during migration.
            conn.execute("ROLLBACK")
            logger.exception("Migration %s failed, rolled back", sql_file.name)
            raise


def migrate(db_path: Path | str) -> None:
    """
    Entry point for `python -m dojo.core.migrate` to apply migrations to a specified database.

    Parameters
    ----------
    db_path : Path | str
        The path to the DuckDB database file.
    """
    # Get the package path where migration SQL files are located.
    migrations_pkg = files("dojo.sql.migrations")
    # Ensure db_path is a Path object.
    path: Path = db_path if isinstance(db_path, Path) else Path(db_path)
    # Establish a connection and apply all pending migrations.
    with get_connection(path) as conn:
        apply_migrations(conn, migrations_pkg)
    logger.info("Migrations complete for %s", path)


def main() -> None:
    """
    Main entry point for the migration script when run as a standalone module.

    Loads settings and initiates the migration process for the configured database path.
    """
    settings: Settings = get_settings()
    migrate(settings.db_path)


if __name__ == "__main__":
    # This block allows the script to be run directly for database migrations.
    main()
