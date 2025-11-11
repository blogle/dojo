"""Budgeting API routers."""

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from dojo.budgeting.errors import BudgetingError
from dojo.budgeting.schemas import (
    AccountState,
    CategoryState,
    NewTransactionRequest,
    ReferenceDataResponse,
    TransactionListItem,
    TransactionResponse,
)
from dojo.budgeting.sql import load_sql
from dojo.budgeting.services import TransactionEntryService
from dojo.core.db import connection_dep

router = APIRouter(prefix="/api", tags=["budgeting"])


def transaction_service_dep(request: Request) -> TransactionEntryService:
    service = getattr(request.app.state, "transaction_service", None)
    if service is None:
        raise RuntimeError("TransactionEntryService not configured on app.state")
    return service


@router.post(
    "/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(
    payload: NewTransactionRequest,
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: TransactionEntryService = Depends(transaction_service_dep),
) -> TransactionResponse:
    """Placeholder transaction endpoint."""

    try:
        return service.create(conn, payload)
    except BudgetingError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get("/transactions", response_model=list[TransactionListItem])
def list_transactions(
    limit: int = Query(50, ge=1, le=500),
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: TransactionEntryService = Depends(transaction_service_dep),
) -> list[TransactionListItem]:
    """Return the most recent transactions for the spreadsheet UI."""

    return service.list_recent(conn, limit)


@router.get("/reference-data", response_model=ReferenceDataResponse)
def get_reference_data(conn: duckdb.DuckDBPyConnection = Depends(connection_dep)) -> ReferenceDataResponse:
    """Return lightweight reference data for the SPA."""

    accounts_sql = load_sql("select_reference_accounts.sql")
    categories_sql = load_sql("select_reference_categories.sql")
    account_rows = conn.execute(accounts_sql).fetchall()
    category_rows = conn.execute(categories_sql).fetchall()
    accounts = [
        AccountState(account_id=row[0], name=row[1], current_balance_minor=int(row[2]))
        for row in account_rows
    ]
    # Category reference uses available = 0 until monthly state exists.
    categories = [
        CategoryState(category_id=row[0], name=row[1], available_minor=0) for row in category_rows
    ]
    return ReferenceDataResponse(
        accounts=accounts,
        categories=categories,
    )
