"""Data access helpers for core domain features."""

from dataclasses import dataclass
from typing import Any

import duckdb

from dojo.core.sql import load_sql


@dataclass(frozen=True)
class NetWorthRecord:
    """
    Represents a snapshot of net worth components at a given time.

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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NetWorthRecord":
        """
        Creates a NetWorthRecord instance from a dictionary.

        Parameters
        ----------
        data : dict[str, Any]
            A dictionary containing the net worth components.

        Returns
        -------
        NetWorthRecord
            An instance of NetWorthRecord.
        """
        return cls(
            assets_minor=data["assets_minor"],
            liabilities_minor=data["liabilities_minor"],
            positions_minor=data["positions_minor"],
            tangibles_minor=data["tangibles_minor"],
            net_worth_minor=data["net_worth_minor"],
        )


class CoreDAO:
    """
    Encapsulates DuckDB queries that back core services.

    This class provides methods to interact with the database for core
    application functionalities, such as retrieving net worth snapshots.
    """

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        """
        Initializes the CoreDAO with a DuckDB connection.

        Parameters
        ----------
        conn : duckdb.DuckDBPyConnection
            The DuckDB connection object to be used for database operations.
        """
        self._conn = conn

    def net_worth_snapshot(self) -> NetWorthRecord | None:
        """
        Retrieves the current net worth snapshot from the database.

        This method executes a SQL query to calculate the current net worth
        based on available assets, liabilities, and positions.

        Returns
        -------
        NetWorthRecord | None
            A NetWorthRecord object if data is available, otherwise None.
        """
        # Load the SQL query for current net worth calculation from an external file.
        sql = load_sql("net_worth_current.sql")
        # Execute the query and fetch the result as a Pandas DataFrame.
        df = self._conn.execute(sql).fetchdf()
        # If the DataFrame is empty, it means no net worth data is available.
        if df.empty:
            return None
        # Convert the first row of the DataFrame to a dictionary and create a NetWorthRecord.
        return NetWorthRecord.from_dict(df.iloc[0].to_dict())
