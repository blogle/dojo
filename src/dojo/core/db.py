"""DuckDB connection utilities and FastAPI dependencies."""

from contextlib import contextmanager
import logging
import threading
from pathlib import Path
from typing import Iterator

import duckdb
from fastapi import Depends

from dojo.core.config import Settings, get_settings

logger = logging.getLogger(__name__)
_CONNECTION_LOCK = threading.Lock()


@contextmanager
def get_connection(path: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    """Yield a short-lived DuckDB connection to the given path.

    DuckDB allows only a single writer per process. The global lock serializes
    connection acquisition so concurrent FastAPI requests do not race to open
    multiple handles to the same file, which previously triggered binder
    errors during bursty UI traffic.
    """

    with _CONNECTION_LOCK:
        connection = duckdb.connect(database=str(path), read_only=False)
        logger.info("Opening DuckDB connection to %s", path)
        try:
            yield connection
        finally:
            connection.close()
            logger.info("Closed DuckDB connection to %s", path)


def connection_dep(settings: Settings = Depends(get_settings)) -> Iterator[duckdb.DuckDBPyConnection]:
    """FastAPI dependency that yields a DuckDB connection."""

    with get_connection(settings.db_path) as connection:
        yield connection
