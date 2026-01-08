"""Helpers for loading SQL under `dojo.sql.investments`."""

from functools import cache
from importlib import resources


@cache
def load_sql(name: str) -> str:
    """Load SQL text from the `dojo.sql.investments` package."""

    sql_path = resources.files("dojo.sql.investments").joinpath(name)
    return sql_path.read_text(encoding="utf-8")
