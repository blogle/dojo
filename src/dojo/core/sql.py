"""Helpers for loading SQL under `dojo.sql.core`."""

from functools import lru_cache
from importlib import resources


@lru_cache(maxsize=None)
def load_sql(name: str) -> str:
    """Load SQL text from the core SQL package."""

    sql_path = resources.files("dojo.sql.core").joinpath(name)
    return sql_path.read_text(encoding="utf-8")
