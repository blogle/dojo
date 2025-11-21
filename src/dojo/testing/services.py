import os
from pathlib import Path

import duckdb

from ..core.migrate import migrate


def reset_db(db_path: Path):
    """Drops all tables and re-runs migrations."""
    if db_path.exists():
        os.remove(db_path)

    # After removing the file, we can re-create it and apply migrations
    migrate(db_path=db_path)


def seed_db(db_path: Path, fixture_path: str):
    """Seeds the database with data from a fixture file."""
    # Build an absolute path to the fixture file, assuming the path is relative to the project root.
    # The project root is assumed to be the grandparent of this file's directory.
    project_root = Path(__file__).parent.parent.parent.parent
    full_path = project_root / fixture_path

    if not full_path.exists():
        raise FileNotFoundError(f"Fixture file not found: {full_path}")

    with duckdb.connect(str(db_path)) as con:
        sql_script = full_path.read_text()
        con.execute(sql_script)
