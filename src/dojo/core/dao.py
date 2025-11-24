"""Data access helpers for core domain features."""

from dataclasses import dataclass
from typing import Sequence

import duckdb

from dojo.core.sql import load_sql


@dataclass(frozen=True)
class NetWorthRecord:
    assets_minor: int
    liabilities_minor: int
    positions_minor: int
    tangibles_minor: int
    net_worth_minor: int

    @classmethod
    def from_row(cls, row: Sequence[int]) -> "NetWorthRecord":
        return cls(
            assets_minor=int(row[0]),
            liabilities_minor=int(row[1]),
            positions_minor=int(row[2]),
            tangibles_minor=int(row[3]),
            net_worth_minor=int(row[4]),
        )


class CoreDAO:
    """Encapsulates DuckDB queries that back core services."""

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn

    def net_worth_snapshot(self) -> NetWorthRecord | None:
        sql = load_sql("net_worth_current.sql")
        row = self._conn.execute(sql).fetchone()
        if row is None:
            return None
        return NetWorthRecord.from_row(row)
