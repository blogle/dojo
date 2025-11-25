"""DuckDB connection utilities and FastAPI dependencies."""

import logging
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import duckdb
from fastapi import Depends

from dojo.core.config import Settings, get_settings

logger = logging.getLogger(__name__)
# The global lock serializes connection acquisition to prevent multiple concurrent
# FastAPI requests from racing to open handles to the same DuckDB file,
# which can cause binder errors during bursty UI traffic.
_CONNECTION_LOCK = threading.Lock()


@contextmanager
def get_connection(path: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    """Yield a short-lived DuckDB connection to the given path.

    DuckDB allows only a single writer per process. The global lock serializes
    connection acquisition so concurrent FastAPI requests do not race to open
    multiple handles to the same file, which previously triggered binder
    errors during bursty UI traffic.

    Parameters
    ----------
    path : Path
        The file path to the DuckDB database.

    Yields
    ------
    Iterator[duckdb.DuckDBPyConnection]
        A DuckDB database connection.
    """

    with _CONNECTION_LOCK:
        connection = duckdb.connect(database=str(path), read_only=False)
        logger.info("Opening DuckDB connection to %s", path)
        try:
            yield connection
        finally:
            connection.close()
            logger.info("Closed DuckDB connection to %s", path)


def connection_dep(
    settings: Settings = Depends(get_settings),
) -> Iterator[duckdb.DuckDBPyConnection]:
    """
    FastAPI dependency that yields a DuckDB connection.

    This dependency provides a database connection for request-scoped operations.
    The connection is managed by `get_connection`, ensuring proper acquisition
    and release.

    Parameters
    ----------
    settings : Settings, optional
        Application settings, injected via FastAPI's Depends.

    Yields
    ------
    Iterator[duckdb.DuckDBPyConnection]
        A DuckDB database connection instance for the current request.
    """

    with get_connection(settings.db_path) as connection:
        yield connection
