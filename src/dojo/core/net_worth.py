"""Net worth aggregation services."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, getcontext

import duckdb

from dojo.core.sql import load_sql

getcontext().prec = 28


@dataclass(frozen=True)
class NetWorthSnapshot:
    """Domain representation of the consolidated net worth."""

    assets_minor: int
    liabilities_minor: int
    positions_minor: int
    net_worth_minor: int

    @property
    def net_worth_decimal(self) -> Decimal:
        return Decimal(self.net_worth_minor).scaleb(-2).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def current_snapshot(conn: duckdb.DuckDBPyConnection) -> NetWorthSnapshot:
    """Return the instantaneous net worth."""

    sql = load_sql("net_worth_current.sql")
    row = conn.execute(sql).fetchone()
    if row is None:
        return NetWorthSnapshot(0, 0, 0, 0)
    assets, liabilities, positions, net_worth = row
    return NetWorthSnapshot(
        assets_minor=int(assets),
        liabilities_minor=int(liabilities),
        positions_minor=int(positions),
        net_worth_minor=int(net_worth),
    )
