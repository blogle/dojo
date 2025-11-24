"""Net worth aggregation services."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, getcontext

import duckdb

from .dao import CoreDAO

getcontext().prec = 28


@dataclass(frozen=True)
class NetWorthSnapshot:
    """Domain representation of the consolidated net worth."""

    assets_minor: int
    liabilities_minor: int
    positions_minor: int
    tangibles_minor: int
    net_worth_minor: int

    @property
    def net_worth_decimal(self) -> Decimal:
        return Decimal(self.net_worth_minor).scaleb(-2).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def current_snapshot(conn: duckdb.DuckDBPyConnection) -> NetWorthSnapshot:
    """Return the instantaneous net worth."""

    dao = CoreDAO(conn)
    record = dao.net_worth_snapshot()
    if record is None:
        return NetWorthSnapshot(0, 0, 0, 0, 0)
    return NetWorthSnapshot(
        assets_minor=record.assets_minor,
        liabilities_minor=record.liabilities_minor,
        positions_minor=record.positions_minor,
        tangibles_minor=record.tangibles_minor,
        net_worth_minor=record.net_worth_minor,
    )
