from datetime import timedelta

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query

from dojo.core.db import connection_dep
from dojo.core.net_worth import NetWorthSnapshot, current_snapshot, net_worth_history
from dojo.core.schemas import NetWorthHistoryPoint, NetWorthResponse

# Initialize the API router with a tag for core functionalities.
router = APIRouter(tags=["core"])
_CONNECTION_DEP = Depends(connection_dep)


@router.get("/health")
def health() -> dict[str, str]:
    """Simple health endpoint."""

    return {"status": "ok"}


@router.get("/net-worth/current", response_model=NetWorthResponse)
def net_worth_current(
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
) -> NetWorthResponse:
    """Return the current net worth snapshot."""

    snapshot: NetWorthSnapshot = current_snapshot(conn)
    return NetWorthResponse(
        assets_minor=snapshot.assets_minor,
        liabilities_minor=snapshot.liabilities_minor,
        positions_minor=snapshot.positions_minor,
        tangibles_minor=snapshot.tangibles_minor,
        net_worth_minor=snapshot.net_worth_minor,
        net_worth_decimal=snapshot.net_worth_decimal,
    )


@router.get("/net-worth/history", response_model=list[NetWorthHistoryPoint])
def net_worth_history_api(
    interval: str = Query("1M", description="1D, 1W, 1M, 3M, YTD, 1Y, 5Y, Max"),
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
) -> list[NetWorthHistoryPoint]:
    """Return a daily net worth series for the requested interval."""

    supported = {"1D", "1W", "1M", "3M", "YTD", "1Y", "5Y", "Max"}
    if interval not in supported:
        raise HTTPException(status_code=400, detail=f"Unsupported interval: {interval}")

    end_date_row = conn.execute("SELECT CURRENT_DATE").fetchone()
    if not end_date_row or end_date_row[0] is None:
        raise HTTPException(status_code=500, detail="Could not resolve current date")
    end_date = end_date_row[0]

    if interval == "1D":
        start_date = end_date - timedelta(days=1)
    elif interval == "1W":
        start_date = end_date - timedelta(days=7)
    elif interval == "1M":
        start_date = end_date - timedelta(days=30)
    elif interval == "3M":
        start_date = end_date - timedelta(days=90)
    elif interval == "YTD":
        start_date = end_date.replace(month=1, day=1)
    elif interval == "1Y":
        start_date = end_date - timedelta(days=365)
    elif interval == "5Y":
        start_date = end_date - timedelta(days=365 * 5)
    else:
        min_date_row = conn.execute(
            """
            WITH mins AS (
                SELECT MIN(transaction_date) AS min_date
                FROM transactions
                WHERE is_active = TRUE

                UNION ALL

                SELECT MIN(market_date) AS min_date
                FROM market_prices

                UNION ALL

                SELECT MIN(CAST(valid_from AS DATE)) AS min_date
                FROM positions

                UNION ALL

                SELECT MIN(CAST(valid_from AS DATE)) AS min_date
                FROM investment_account_details

                UNION ALL

                SELECT MIN(CAST(valid_from AS DATE)) AS min_date
                FROM tangible_assets
            )
            SELECT MIN(min_date) AS min_date
            FROM mins
            """
        ).fetchone()
        start_date = min_date_row[0] if min_date_row and min_date_row[0] else end_date

    points = net_worth_history(conn, start_date=start_date, end_date=end_date)
    return [NetWorthHistoryPoint(date=as_of_date, value_minor=value_minor) for as_of_date, value_minor in points]
