"""Core API routers."""

import duckdb
from fastapi import APIRouter, Depends

from dojo.core.db import connection_dep
from dojo.core.net_worth import NetWorthSnapshot, current_snapshot
from dojo.core.schemas import NetWorthResponse

# Initialize the API router with a tag for core functionalities.
router = APIRouter(tags=["core"])


@router.get("/health")
def health() -> dict[str, str]:
    """
    Simple health endpoint.

    Returns
    -------
    dict[str, str]
        A dictionary with a "status" key indicating the health of the service.
    """
    return {"status": "ok"}


@router.get("/net-worth/current", response_model=NetWorthResponse)
def net_worth_current(
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
) -> NetWorthResponse:
    """
    Return the current net worth snapshot.

    This endpoint retrieves the current financial snapshot, including assets,
    liabilities, positions, tangibles, and total net worth.

    Parameters
    ----------
    conn : duckdb.DuckDBPyConnection
        Dependency that provides a DuckDB connection.

    Returns
    -------
    NetWorthResponse
        A Pydantic model containing the current net worth details.
    """
    # Retrieve the current net worth snapshot using the provided database connection.
    snapshot: NetWorthSnapshot = current_snapshot(conn)
    # Construct and return the response model from the snapshot data.
    return NetWorthResponse(
        assets_minor=snapshot.assets_minor,
        liabilities_minor=snapshot.liabilities_minor,
        positions_minor=snapshot.positions_minor,
        tangibles_minor=snapshot.tangibles_minor,
        net_worth_minor=snapshot.net_worth_minor,
        net_worth_decimal=snapshot.net_worth_decimal,
    )
