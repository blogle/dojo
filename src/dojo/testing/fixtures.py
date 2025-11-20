"""Shared helpers for loading SQL fixtures in tests."""

from pathlib import Path

import duckdb

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "tests" / "fixtures"


def apply_sql_fixture(conn: duckdb.DuckDBPyConnection, filename: str) -> None:
    """Execute the named SQL file inside tests/fixtures."""

    fixture_path = FIXTURES_DIR / filename
    if not fixture_path.exists():  # pragma: no cover - defensive guard for CI misconfig
        msg = f"Fixture file not found: {fixture_path}"
        raise FileNotFoundError(msg)
    sql = fixture_path.read_text(encoding="utf-8")
    conn.execute("BEGIN")
    try:
        conn.execute(sql)
        conn.execute("COMMIT")
    except Exception:  # pragma: no cover - pytest surfaces SQL errors better
        conn.execute("ROLLBACK")
        raise


def apply_base_budgeting_fixture(conn: duckdb.DuckDBPyConnection) -> None:
    """Load the canonical budgeting fixture used across suites."""

    apply_sql_fixture(conn, "base_budgeting.sql")
