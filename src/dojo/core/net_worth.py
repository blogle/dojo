"""Net worth aggregation services."""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, getcontext

import duckdb

from .dao import CoreDAO

# Decimal precision for calculations to avoid floating-point inaccuracies
DECIMAL_PRECISION = 28
# Scale factor for converting minor units (e.g., cents) to major units (e.g., dollars)
NET_WORTH_DECIMAL_SCALE = -2
# Quantization value for rounding net worth to two decimal places
NET_WORTH_QUANTIZE = Decimal("0.01")
# Rounding strategy for net worth calculations
NET_WORTH_ROUNDING = ROUND_HALF_UP

# Set the global decimal context precision for all Decimal operations.
getcontext().prec = DECIMAL_PRECISION


@dataclass(frozen=True)
class NetWorthSnapshot:
    """
    Domain representation of the consolidated net worth.

    This dataclass holds the net worth components in minor units (e.g., cents)
    to avoid floating-point issues during financial calculations.

    Attributes
    ----------
    assets_minor : int
        Total assets in minor units (e.g., cents).
    liabilities_minor : int
        Total liabilities in minor units.
    positions_minor : int
        Value of investment positions in minor units.
    tangibles_minor : int
        Value of tangible assets in minor units.
    net_worth_minor : int
        Calculated net worth in minor units.
    """

    assets_minor: int
    liabilities_minor: int
    positions_minor: int
    tangibles_minor: int
    net_worth_minor: int

    @property
    def net_worth_decimal(self) -> Decimal:
        """
        Returns the net worth as a Decimal object, scaled and quantized.

        This property converts the `net_worth_minor` integer value into a
        properly scaled and rounded Decimal representation, suitable for
        display or further precise calculations.

        Returns
        -------
        Decimal
            The net worth value as a Decimal, rounded to two decimal places.
        """
        return (
            Decimal(self.net_worth_minor)
            .scaleb(NET_WORTH_DECIMAL_SCALE)
            .quantize(NET_WORTH_QUANTIZE, rounding=NET_WORTH_ROUNDING)
        )


def current_snapshot(conn: duckdb.DuckDBPyConnection) -> NetWorthSnapshot:
    """
    Returns the instantaneous net worth snapshot.

    This function retrieves the latest net worth data from the database
    using the CoreDAO and converts it into a `NetWorthSnapshot` object.
    If no data is found, it returns a zero-initialized snapshot.

    Parameters
    ----------
    conn : duckdb.DuckDBPyConnection
        The DuckDB connection object to use for data retrieval.

    Returns
    -------
    NetWorthSnapshot
        An object representing the current net worth.
    """
    # Initialize the Data Access Object (DAO) with the database connection.
    dao = CoreDAO(conn)
    # Retrieve the net worth record from the database.
    record = dao.net_worth_snapshot()
    # If no record is found, return a NetWorthSnapshot with all zeros.
    if record is None:
        return NetWorthSnapshot(0, 0, 0, 0, 0)
    # Otherwise, create and return a NetWorthSnapshot from the retrieved record.
    return NetWorthSnapshot(
        assets_minor=record.assets_minor,
        liabilities_minor=record.liabilities_minor,
        positions_minor=record.positions_minor,
        tangibles_minor=record.tangibles_minor,
        net_worth_minor=record.net_worth_minor,
    )


def net_worth_history(
    conn: duckdb.DuckDBPyConnection,
    *,
    start_date: date,
    end_date: date,
) -> list[tuple[date, int]]:
    """Returns daily net worth points between start_date and end_date."""
    dao = CoreDAO(conn)
    return dao.net_worth_history(start_date=start_date, end_date=end_date)
