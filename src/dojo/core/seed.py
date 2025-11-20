"""Seed runner for dev/demo data sets."""

import logging
from importlib.resources import files
from importlib.resources.abc import Traversable
from typing import Iterable

import duckdb

from dojo.core.config import Settings, get_settings
from dojo.core.db import get_connection

logger = logging.getLogger(__name__)


def _list_sql_files(seeds_pkg: Traversable) -> Iterable[Traversable]:
    return sorted(
        (child for child in seeds_pkg.iterdir() if child.name.endswith(".sql")),
        key=lambda child: child.name,
    )


def apply_seeds(conn: duckdb.DuckDBPyConnection, seeds_pkg: Traversable) -> None:
    """Execute each seed SQL file inside a transaction."""

    for sql_file in _list_sql_files(seeds_pkg):
        logger.info("Applying seed script %s", sql_file.name)
        sql = sql_file.read_text(encoding="utf-8")
        conn.execute("BEGIN")
        try:
            conn.execute(sql)
            conn.execute("COMMIT")
        except Exception:  # pragma: no cover - re-raised for context
            conn.execute("ROLLBACK")
            logger.exception("Seed script %s failed, rolled back", sql_file.name)
            raise


def main() -> None:
    """Entry point for `python -m dojo.core.seed`."""

    settings: Settings = get_settings()
    seeds_pkg = files("dojo.sql.seeds")
    with get_connection(settings.db_path) as conn:
        apply_seeds(conn, seeds_pkg)
    logger.info("Seed scripts applied to %s", settings.db_path)


if __name__ == "__main__":  # pragma: no cover - module entry
    main()
