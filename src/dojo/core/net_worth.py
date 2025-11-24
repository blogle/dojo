"""Net worth aggregation services."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, getcontext

import duckdb

from .dao import CoreDAO

DECIMAL_PRECISION = 28
NET_WORTH_DECIMAL_SCALE = -2
NET_WORTH_QUANTIZE = Decimal("0.01")
NET_WORTH_ROUNDING = ROUND_HALF_UP

getcontext().prec = DECIMAL_PRECISION


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
        return (
            Decimal(self.net_worth_minor)
            .scaleb(NET_WORTH_DECIMAL_SCALE)
            .quantize(NET_WORTH_QUANTIZE, rounding=NET_WORTH_ROUNDING)
        )


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
