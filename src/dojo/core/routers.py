"""Core API routers."""

import duckdb
from fastapi import APIRouter, Depends

from dojo.core.db import connection_dep
from dojo.core.net_worth import NetWorthSnapshot, current_snapshot
from dojo.core.schemas import NetWorthResponse

router = APIRouter(prefix="/api", tags=["core"])


@router.get("/health")
def health() -> dict[str, str]:
    """Simple health endpoint."""

    return {"status": "ok"}


@router.get("/net-worth/current", response_model=NetWorthResponse)
def net_worth_current(conn: duckdb.DuckDBPyConnection = Depends(connection_dep)) -> NetWorthResponse:
    """Return the current net worth snapshot."""

    snapshot: NetWorthSnapshot = current_snapshot(conn)
    return NetWorthResponse(
        assets_minor=snapshot.assets_minor,
        liabilities_minor=snapshot.liabilities_minor,
        positions_minor=snapshot.positions_minor,
        net_worth_minor=snapshot.net_worth_minor,
        net_worth_decimal=snapshot.net_worth_decimal,
    )
