"""Simple DuckDB migration runner."""

import logging
from pathlib import Path
from importlib.resources import files
from importlib.resources.abc import Traversable
from typing import Iterable

import duckdb

from dojo.core.config import Settings, get_settings
from dojo.core.db import get_connection

logger = logging.getLogger(__name__)


def _ensure_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _list_sql_files(migrations_pkg: Traversable) -> Iterable[Traversable]:
    return sorted(
        (child for child in migrations_pkg.iterdir() if child.name.endswith(".sql")),
        key=lambda child: child.name,
    )


def apply_migrations(conn: duckdb.DuckDBPyConnection, migrations_pkg: Traversable) -> None:
    """Apply unapplied SQL files under the provided package path."""

    _ensure_schema(conn)
    applied = {
        filename
        for (filename,)
        in conn.execute("SELECT filename FROM schema_migrations").fetchall()
    }
    for sql_file in _list_sql_files(migrations_pkg):
        if sql_file.name in applied:
            logger.info("Skipping %s (already applied)", sql_file.name)
            continue
        logger.info("Applying migration %s", sql_file.name)
        sql = sql_file.read_text(encoding="utf-8")
        conn.execute("BEGIN")
        try:
            conn.execute(sql)
            conn.execute(
                "INSERT INTO schema_migrations (filename) VALUES (?)",
                [sql_file.name],
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            logger.exception("Migration %s failed, rolled back", sql_file.name)
            raise


def migrate(db_path: Path | str) -> None:
    """Entry point for `python -m dojo.core.migrate`."""

    migrations_pkg = files("dojo.sql.migrations")
    path: Path = db_path if isinstance(db_path, Path) else Path(db_path)
    with get_connection(path) as conn:
        apply_migrations(conn, migrations_pkg)
    logger.info("Migrations complete for %s", path)


def main() -> None:
    """Entry point for `python -m dojo.core.migrate`."""
    settings: Settings = get_settings()
    migrate(settings.db_path)


if __name__ == "__main__":
    main()
