"""Budgeting API routers."""

from datetime import date
from decimal import Decimal
from typing import Type, TypeVar

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from dojo.budgeting.errors import (
    AccountAlreadyExists,
    AccountNotFound,
    BudgetingError,
    CategoryAlreadyExists,
    CategoryNotFound,
)
from dojo.budgeting.schemas import (
    AccountCreateRequest,
    AccountDetail,
    AccountState,
    AccountUpdateRequest,
    BudgetCategoryCreateRequest,
    BudgetCategoryDetail,
    BudgetCategoryUpdateRequest,
    CategoryState,
    CategorizedTransferRequest,
    CategorizedTransferResponse,
    NewTransactionRequest,
    ReadyToAssignResponse,
    ReferenceDataResponse,
    TransactionListItem,
    TransactionResponse,
)
from dojo.budgeting.sql import load_sql
from dojo.budgeting.services import (
    AccountAdminService,
    BudgetCategoryAdminService,
    TransactionEntryService,
)
from dojo.core.db import connection_dep

router = APIRouter(prefix="/api", tags=["budgeting"])

ServiceT = TypeVar("ServiceT")


def _resolve_service(request: Request, attr: str, expected_type: Type[ServiceT]) -> ServiceT:
    service = getattr(request.app.state, attr, None)
    if service is None:
        raise RuntimeError(f"{expected_type.__name__} not configured on app.state")
    if not isinstance(service, expected_type):  # pragma: no cover
        raise RuntimeError(f"{attr} is not an instance of {expected_type.__name__}")
    return service


def transaction_service_dep(request: Request) -> TransactionEntryService:
    return _resolve_service(request, "transaction_service", TransactionEntryService)


def account_admin_service_dep(request: Request) -> AccountAdminService:
    return _resolve_service(request, "account_admin_service", AccountAdminService)


def category_admin_service_dep(request: Request) -> BudgetCategoryAdminService:
    return _resolve_service(
        request,
        "budget_category_admin_service",
        BudgetCategoryAdminService,
    )


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
        AccountState(
            account_id=row[0],
            name=row[1],
            account_type=row[2],
            account_class=row[3],
            account_role=row[4],
            current_balance_minor=int(row[5]),
        )
        for row in account_rows
    ]
    # Category reference uses available = 0 until monthly state exists.
    categories = [
        CategoryState(
            category_id=row[0],
            name=row[1],
            available_minor=0,
            activity_minor=0,
        )
        for row in category_rows
    ]
    return ReferenceDataResponse(
        accounts=accounts,
        categories=categories,
    )


@router.post(
    "/transfers",
    response_model=CategorizedTransferResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_transfer(
    payload: CategorizedTransferRequest,
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: TransactionEntryService = Depends(transaction_service_dep),
) -> CategorizedTransferResponse:
    """Perform a categorized transfer consisting of budgeted and transfer legs."""

    try:
        return service.transfer(conn, payload)
    except BudgetingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/accounts", response_model=list[AccountDetail])
def list_accounts(
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: AccountAdminService = Depends(account_admin_service_dep),
) -> list[AccountDetail]:
    """Return all accounts for administration flows."""

    return service.list_accounts(conn)


@router.post("/accounts", response_model=AccountDetail, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreateRequest,
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: AccountAdminService = Depends(account_admin_service_dep),
) -> AccountDetail:
    try:
        return service.create_account(conn, payload)
    except AccountAlreadyExists as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except BudgetingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/accounts/{account_id}", response_model=AccountDetail)
def update_account(
    account_id: str,
    payload: AccountUpdateRequest,
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: AccountAdminService = Depends(account_admin_service_dep),
) -> AccountDetail:
    try:
        return service.update_account(conn, account_id, payload)
    except AccountNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BudgetingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_account(
    account_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: AccountAdminService = Depends(account_admin_service_dep),
) -> Response:
    try:
        service.deactivate_account(conn, account_id)
    except AccountNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BudgetingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/budget-categories", response_model=list[BudgetCategoryDetail])
def list_categories(
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: BudgetCategoryAdminService = Depends(category_admin_service_dep),
) -> list[BudgetCategoryDetail]:
    return service.list_categories(conn)


@router.post(
    "/budget-categories",
    response_model=BudgetCategoryDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    payload: BudgetCategoryCreateRequest,
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: BudgetCategoryAdminService = Depends(category_admin_service_dep),
) -> BudgetCategoryDetail:
    try:
        return service.create_category(conn, payload)
    except CategoryAlreadyExists as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except BudgetingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/budget-categories/{category_id}", response_model=BudgetCategoryDetail)
def update_category(
    category_id: str,
    payload: BudgetCategoryUpdateRequest,
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: BudgetCategoryAdminService = Depends(category_admin_service_dep),
) -> BudgetCategoryDetail:
    try:
        return service.update_category(conn, category_id, payload)
    except CategoryNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BudgetingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/budget-categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_category(
    category_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: BudgetCategoryAdminService = Depends(category_admin_service_dep),
) -> Response:
    try:
        service.deactivate_category(conn, category_id)
    except CategoryNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BudgetingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/budget/ready-to-assign", response_model=ReadyToAssignResponse)
def ready_to_assign(
    month: date | None = Query(None, description="Month start (YYYY-MM-01)."),
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: TransactionEntryService = Depends(transaction_service_dep),
) -> ReadyToAssignResponse:
    """Return the Ready to Assign amount for the given month."""

    if month is None:
        month = date.today().replace(day=1)
    ready_minor = service.ready_to_assign(conn, month)
    return ReadyToAssignResponse(
        month_start=month,
        ready_to_assign_minor=ready_minor,
        ready_to_assign_decimal=Decimal(ready_minor).scaleb(-2).quantize(Decimal("0.01")),
    )
