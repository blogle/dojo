"""Helpers to load budgeting SQL statements packaged under `dojo.sql.budgeting`."""

from functools import lru_cache
from importlib import resources


@lru_cache(maxsize=None)
def load_sql(name: str) -> str:
    """Load an SQL file from the budgeting SQL package."""

    sql_path = resources.files("dojo.sql.budgeting").joinpath(name)
    return sql_path.read_text(encoding="utf-8")
