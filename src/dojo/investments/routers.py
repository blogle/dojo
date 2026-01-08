"""Investments API routers."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

from dojo.core.db import connection_dep, get_connection
from dojo.investments.domain import PortfolioHistoryPoint, PortfolioState, ReconcilePortfolioRequest
from dojo.investments.service import InvestmentService

router = APIRouter(tags=["investments"])
_CONNECTION_DEP = Depends(connection_dep)


def _ensure_service_type(obj: object, attr: str, expected_type: type[object]) -> object:
    if not isinstance(obj, expected_type):  # pragma: no cover
        raise RuntimeError(f"{attr} is not an instance of {expected_type.__name__}")
    return obj


def investment_service_dep(request: Request) -> InvestmentService:
    try:
        service = request.app.state.investment_service
    except AttributeError as exc:
        raise RuntimeError("InvestmentService not configured on app.state") from exc
    return _ensure_service_type(service, "investment_service", InvestmentService)  # type: ignore[return-value]


_INVESTMENT_SERVICE_DEP = Depends(investment_service_dep)


@router.get("/investments/accounts/{account_id}", response_model=PortfolioState)
def get_investment_account(
    account_id: str,
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
    service: InvestmentService = _INVESTMENT_SERVICE_DEP,
) -> PortfolioState:
    try:
        return service.get_portfolio_state(conn, account_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/investments/accounts/{account_id}/history",
    response_model=list[PortfolioHistoryPoint],
)
def get_investment_account_history(
    account_id: str,
    start_date: date,
    end_date: date,
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
    service: InvestmentService = _INVESTMENT_SERVICE_DEP,
) -> list[PortfolioHistoryPoint]:
    try:
        return service.get_portfolio_history(conn, account_id, start_date=start_date, end_date=end_date)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/investments/accounts/{account_id}/reconcile",
    response_model=PortfolioState,
)
def reconcile_investment_account(
    account_id: str,
    payload: ReconcilePortfolioRequest,
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
    service: InvestmentService = _INVESTMENT_SERVICE_DEP,
) -> PortfolioState:
    try:
        return service.reconcile_portfolio(
            conn,
            account_id,
            uninvested_cash_minor=payload.uninvested_cash_minor,
            positions=payload.positions,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


def _run_market_update(db_path: Path, service: InvestmentService) -> None:
    with get_connection(db_path) as conn:
        service.sync_market_data(conn)


@router.post("/jobs/market-update", status_code=status.HTTP_202_ACCEPTED)
def trigger_market_update(
    background_tasks: BackgroundTasks,
    request: Request,
    service: InvestmentService = _INVESTMENT_SERVICE_DEP,
) -> dict[str, str]:
    settings = request.app.state.settings
    background_tasks.add_task(_run_market_update, settings.db_path, service)
    return {"status": "accepted"}
