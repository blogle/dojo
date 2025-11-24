"""Helpers for loading SQL under `dojo.sql.core`."""

from functools import lru_cache
from importlib import resources


@lru_cache(maxsize=None)
def load_sql(name: str) -> str:
    """
    Loads SQL text from the `dojo.sql.core` package.

    This function provides a convenient way to retrieve SQL queries stored
    as separate files within the `dojo.sql.core` package. It uses `lru_cache`
    to memoize the results, ensuring that each SQL file is read from disk
    only once per application lifecycle.

    Parameters
    ----------
    name : str
        The name of the SQL file (e.g., "my_query.sql") to load.
        The file is expected to be located within the `dojo.sql.core` package.

    Returns
    -------
    str
        The content of the SQL file as a string.
    """
    # Use importlib.resources to locate the SQL file within the package.
    sql_path = resources.files("dojo.sql.core").joinpath(name)
    # Read the content of the SQL file and return it as a string.
    return sql_path.read_text(encoding="utf-8")
