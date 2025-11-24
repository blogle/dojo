"""Data access helpers for core domain features."""

from dataclasses import dataclass
from typing import Any

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
    def from_dict(cls, data: dict[str, Any]) -> "NetWorthRecord":
        return cls(
            assets_minor=data["assets_minor"],
            liabilities_minor=data["liabilities_minor"],
            positions_minor=data["positions_minor"],
            tangibles_minor=data["tangibles_minor"],
            net_worth_minor=data["net_worth_minor"],
        )


class CoreDAO:
    """Encapsulates DuckDB queries that back core services."""

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn

    def net_worth_snapshot(self) -> NetWorthRecord | None:
        sql = load_sql("net_worth_current.sql")
        df = self._conn.execute(sql).fetchdf()
        if df.empty:
            return None
        return NetWorthRecord.from_dict(df.iloc[0].to_dict())
