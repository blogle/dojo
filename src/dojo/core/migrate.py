"""DuckDB migration runner with per-statement execution and validation."""

import argparse
import logging
import re
import shutil
import time
from collections.abc import Callable, Sequence
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path

import duckdb

from dojo.core.config import Settings, get_settings
from dojo.core.db import get_connection

logger = logging.getLogger(__name__)

# Simple regexes to classify statements; conservative on purpose.
INDEX_RE = re.compile(r"^\s*CREATE\s+(UNIQUE\s+)?INDEX", re.IGNORECASE)
DML_RE = re.compile(r"^\s*(INSERT|UPDATE|DELETE|MERGE)", re.IGNORECASE)
DDL_RE = re.compile(
    r"^\s*(CREATE\s+(TABLE|VIEW|SCHEMA)|ALTER\s+(TABLE|VIEW|SCHEMA)|DROP\s+(TABLE|VIEW|SCHEMA))",
    re.IGNORECASE,
)


def _ensure_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Ensure the `schema_migrations` table exists."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _list_sql_files(migrations_pkg: Traversable) -> list[Traversable]:
    """List SQL files in lexicographic order to define execution order."""
    return sorted(
        (child for child in migrations_pkg.iterdir() if child.name.endswith(".sql")),
        key=lambda child: child.name,
    )


def _split_statements(sql: str) -> list[str]:
    """Split SQL into statements on semicolons, respecting quoted strings."""
    statements: list[str] = []
    current: list[str] = []
    in_single = False
    in_double = False
    for char in sql:
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        if char == ";" and not in_single and not in_double:
            stmt = "".join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
            continue
        current.append(char)
    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return statements


def _validate_sequence(files: Sequence[Traversable]) -> None:
    expected = 1
    for child in files:
        prefix = child.name.split("_", 1)[0]
        if not prefix.isdigit():
            raise ValueError(f"Migration filename missing numeric prefix: {child.name}")
        number = int(prefix)
        if number != expected:
            raise ValueError(f"Migration numbering gap: expected {expected:04d}, found {number:04d} ({child.name})")
        expected += 1


def _classify_statements(statements: Sequence[str]) -> tuple[bool, bool]:
    """Return (has_dml, has_index) flags for the statements."""
    has_dml = any(DML_RE.match(stmt) for stmt in statements)
    has_index = any(INDEX_RE.match(stmt) for stmt in statements)
    return has_dml, has_index


def _log_plan(filename: str, statements: Sequence[str]) -> None:
    logger.info("plan file=%s statements=%d", filename, len(statements))
    for idx, stmt in enumerate(statements, start=1):
        logger.info("plan statement=%d file=%s sql=%s", idx, filename, stmt)


def _is_transient_error(exc: Exception) -> bool:
    message = str(exc)
    transient_patterns = (
        "TransactionContext Error",
        "another transaction has altered this table",
        "Serialization Error",
    )
    return any(pattern in message for pattern in transient_patterns)


def _run_with_retry(action: Callable[[], None], *, context: str, attempts: int = 3, delay: float = 0.25) -> None:
    for attempt in range(1, attempts + 1):
        try:
            action()
            return
        except Exception as exc:
            if not _is_transient_error(exc) or attempt == attempts:
                raise
            logger.warning("retrying file=%s attempt=%d/%d error=%s", context, attempt, attempts, exc)
            time.sleep(delay * attempt)


def _execute_statements(
    conn: duckdb.DuckDBPyConnection,
    filename: str,
    statements: Sequence[str],
    *,
    dry_run: bool,
) -> None:
    """Execute statements with transaction boundaries that keep indexes separate from DML."""
    if dry_run:
        logger.info("dry-run file=%s skipping execution", filename)
        return

    dml_buffer: list[str] = []

    def execute_single_statement(stmt: str) -> None:
        def action() -> None:
            conn.execute("BEGIN")
            try:
                conn.execute(stmt)
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

        _run_with_retry(action, context=f"{filename}:{stmt[:32]}")

    def flush_dml() -> None:
        nonlocal dml_buffer
        if not dml_buffer:
            return

        def action() -> None:
            conn.execute("BEGIN")
            try:
                for stmt in dml_buffer:
                    conn.execute(stmt)
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

        _run_with_retry(action, context=f"{filename}:dml_batch")
        dml_buffer = []

    for stmt in statements:
        if INDEX_RE.match(stmt):
            flush_dml()
            execute_single_statement(stmt)
            continue
        if DDL_RE.match(stmt):
            flush_dml()
            execute_single_statement(stmt)
            continue
        dml_buffer.append(stmt)

    flush_dml()


def apply_migrations(
    conn: duckdb.DuckDBPyConnection,
    migrations_pkg: Traversable,
    *,
    dry_run: bool = False,
    target: str | None = None,
    log_plan: bool = False,
) -> None:
    """Apply unapplied SQL migration files with validation and logging."""
    _ensure_schema(conn)
    applied = {filename for (filename,) in conn.execute("SELECT filename FROM schema_migrations").fetchall()}
    files = _list_sql_files(migrations_pkg)
    _validate_sequence(files)
    for sql_file in files:
        if target and sql_file.name > target:
            logger.info("Reached target %s; stopping", target)
            break
        if sql_file.name in applied:
            logger.info("Skipping %s (already applied)", sql_file.name)
            continue
        sql = sql_file.read_text(encoding="utf-8")
        statements = _split_statements(sql)
        has_dml, has_index = _classify_statements(statements)
        if has_dml and has_index:
            logger.info("validation file=%s has_dml=true has_index=true action=split_transactions", sql_file.name)
        if log_plan:
            _log_plan(sql_file.name, statements)
        try:
            _execute_statements(conn, sql_file.name, statements, dry_run=dry_run)
            if not dry_run:
                conn.execute(
                    "INSERT INTO schema_migrations (filename) VALUES ($filename)",
                    {"filename": sql_file.name},
                )
        except Exception:
            logger.exception("Migration %s failed; already rolled back statement batches", sql_file.name)
            raise
    logger.info("Migration processing complete")


def migrate(
    db_path: Path | str,
    *,
    dry_run: bool = False,
    target: str | None = None,
    log_plan: bool = False,
) -> None:
    """Entry point to apply migrations to a specified database."""
    migrations_pkg = files("dojo.sql.migrations")
    path: Path = db_path if isinstance(db_path, Path) else Path(db_path)
    with get_connection(path) as conn:
        apply_migrations(conn, migrations_pkg, dry_run=dry_run, target=target, log_plan=log_plan)
    logger.info("Migrations complete for %s", path)


def _backup_db(db_path: Path) -> None:
    """Create a timestamped backup of the database file."""
    if not db_path.exists():
        logger.info("backup status=skipped reason=no-db-file path=%s", db_path)
        return
    backup = db_path.with_suffix(db_path.suffix + f".bak.{int(time.time())}")
    shutil.copy2(db_path, backup)
    logger.info("backup status=ok path=%s", backup)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply Dojo DuckDB migrations")
    parser.add_argument("--database", "-d", dest="database", default=None, help="Path to DuckDB file")
    parser.add_argument("--dry-run", action="store_true", help="Parse and log plan without executing")
    parser.add_argument("--target", dest="target", default=None, help="Apply up to and including filename")
    parser.add_argument("--log-plan", action="store_true", help="Log planned statements before execution")
    parser.add_argument("--backup", action="store_true", help="Backup the database before migrating")
    return parser.parse_args()


def main() -> None:
    """CLI entrypoint for `python -m dojo.core.migrate`."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    args = _parse_args()
    settings: Settings = get_settings()
    db_path = Path(args.database) if args.database else settings.db_path
    if args.backup:
        _backup_db(db_path)
    migrate(db_path, dry_run=args.dry_run, target=args.target, log_plan=args.log_plan)


if __name__ == "__main__":
    main()
