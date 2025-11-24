"""Budgeting API routers."""

from datetime import date
from decimal import Decimal
from typing import Type, TypeVar

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from dojo.budgeting.dao import BudgetingDAO
from dojo.budgeting.errors import (
    AccountAlreadyExists,
    AccountNotFound,
    BudgetingError,
    CategoryAlreadyExists,
    CategoryNotFound,
    GroupAlreadyExists,
    GroupNotFound,
    InvalidTransaction,
)
from dojo.budgeting.schemas import (
    AccountCreateRequest,
    AccountDetail,
    AccountState,
    AccountUpdateRequest,
    BudgetAllocationRequest,
    BudgetAllocationEntry,
    BudgetAllocationsResponse,
    BudgetCategoryCreateRequest,
    BudgetCategoryDetail,
    BudgetCategoryGroupCreateRequest,
    BudgetCategoryGroupDetail,
    BudgetCategoryGroupUpdateRequest,
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
from dojo.budgeting.services import (
    AccountAdminService,
    BudgetCategoryAdminService,
    TransactionEntryService,
)
from dojo.core.db import connection_dep

router = APIRouter(tags=["budgeting"])

TRANSACTION_LIMIT_DEFAULT = 50
TRANSACTION_LIMIT_MAX = 500
ALLOCATIONS_LIMIT_DEFAULT = 100
ALLOCATIONS_LIMIT_MAX = 500

ServiceT = TypeVar("ServiceT")


def _ensure_service_type(
    service: object | None, attr: str, expected_type: Type[ServiceT]
) -> ServiceT:
    if service is None:
        raise RuntimeError(f"{expected_type.__name__} not configured on app.state")
    if not isinstance(service, expected_type):  # pragma: no cover
        raise RuntimeError(f"{attr} is not an instance of {expected_type.__name__}")
    return service


def transaction_service_dep(request: Request) -> TransactionEntryService:
    try:
        service = request.app.state.transaction_service
    except AttributeError as exc:
        raise RuntimeError("TransactionEntryService not configured on app.state") from exc
    return _ensure_service_type(service, "transaction_service", TransactionEntryService)


def account_admin_service_dep(request: Request) -> AccountAdminService:
    try:
        service = request.app.state.account_admin_service
    except AttributeError as exc:
        raise RuntimeError("AccountAdminService not configured on app.state") from exc
    return _ensure_service_type(service, "account_admin_service", AccountAdminService)


def category_admin_service_dep(request: Request) -> BudgetCategoryAdminService:
    try:
        service = request.app.state.budget_category_admin_service
    except AttributeError as exc:
        raise RuntimeError("BudgetCategoryAdminService not configured on app.state") from exc
    return _ensure_service_type(
        service,
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
    limit: int = Query(TRANSACTION_LIMIT_DEFAULT, ge=1, le=TRANSACTION_LIMIT_MAX),
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: TransactionEntryService = Depends(transaction_service_dep),
) -> list[TransactionListItem]:
    """Return the most recent transactions for the spreadsheet UI."""

    return service.list_recent(conn, limit)


@router.get("/reference-data", response_model=ReferenceDataResponse)
def get_reference_data(conn: duckdb.DuckDBPyConnection = Depends(connection_dep)) -> ReferenceDataResponse:
    """Return lightweight reference data for the SPA."""

    dao = BudgetingDAO(conn)
    account_records = dao.list_reference_accounts()
    accounts = [
        AccountState(
            account_id=record.account_id,
            name=record.name,
            account_type=record.account_type,
            account_class=record.account_class,
            account_role=record.account_role,
            current_balance_minor=record.current_balance_minor,
        )
        for record in account_records
    ]
    # Category reference uses available = 0 until monthly state exists.
    category_records = dao.list_reference_categories()
    categories = [
        CategoryState(
            category_id=record.category_id,
            name=record.name,
            available_minor=record.available_minor,
            activity_minor=0,
        )
        for record in category_records
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
    month: date | None = Query(None, description="Month start (YYYY-MM-01) for envelope state."),
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: BudgetCategoryAdminService = Depends(category_admin_service_dep),
) -> list[BudgetCategoryDetail]:
    return service.list_categories(conn, month_start=month)


@router.post(
    "/budget-categories",
    response_model=BudgetCategoryDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    payload: BudgetCategoryCreateRequest,
    month: date | None = Query(None, description="Month start (YYYY-MM-01) for envelope state."),
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: BudgetCategoryAdminService = Depends(category_admin_service_dep),
) -> BudgetCategoryDetail:
    try:
        return service.create_category(conn, payload, month_start=month)
    except CategoryAlreadyExists as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except BudgetingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/budget-categories/{category_id}", response_model=BudgetCategoryDetail)
def update_category(
    category_id: str,
    payload: BudgetCategoryUpdateRequest,
    month: date | None = Query(None, description="Month start (YYYY-MM-01) for envelope state."),
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: BudgetCategoryAdminService = Depends(category_admin_service_dep),
) -> BudgetCategoryDetail:
    try:
        return service.update_category(conn, category_id, payload, month_start=month)
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


@router.get("/budget-category-groups", response_model=list[BudgetCategoryGroupDetail])
def list_groups(
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: BudgetCategoryAdminService = Depends(category_admin_service_dep),
) -> list[BudgetCategoryGroupDetail]:
    return service.list_groups(conn)


@router.post(
    "/budget-category-groups",
    response_model=BudgetCategoryGroupDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_group(
    payload: BudgetCategoryGroupCreateRequest,
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: BudgetCategoryAdminService = Depends(category_admin_service_dep),
) -> BudgetCategoryGroupDetail:
    try:
        return service.create_group(conn, payload)
    except GroupAlreadyExists as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except BudgetingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/budget-category-groups/{group_id}", response_model=BudgetCategoryGroupDetail)
def update_group(
    group_id: str,
    payload: BudgetCategoryGroupUpdateRequest,
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: BudgetCategoryAdminService = Depends(category_admin_service_dep),
) -> BudgetCategoryGroupDetail:
    try:
        return service.update_group(conn, group_id, payload)
    except GroupNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BudgetingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/budget-category-groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_group(
    group_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: BudgetCategoryAdminService = Depends(category_admin_service_dep),
) -> Response:
    try:
        service.deactivate_group(conn, group_id)
    except GroupNotFound as exc:
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


@router.post("/budget/allocations", response_model=CategoryState, status_code=status.HTTP_201_CREATED)
def allocate_budget(
    payload: BudgetAllocationRequest,
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: TransactionEntryService = Depends(transaction_service_dep),
) -> CategoryState:
    target_category_id = payload.to_category_id or payload.category_id
    if not target_category_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="to_category_id is required")
    try:
        return service.allocate_envelope(
            conn,
            target_category_id,
            payload.amount_minor,
            payload.month_start,
            from_category_id=payload.from_category_id,
            memo=payload.memo,
            allocation_date=payload.allocation_date,
        )
    except (BudgetingError, InvalidTransaction) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/budget/allocations", response_model=BudgetAllocationsResponse)
def list_allocations(
    month: date | None = Query(None, description="Month start (YYYY-MM-01)."),
    limit: int = Query(ALLOCATIONS_LIMIT_DEFAULT, ge=1, le=ALLOCATIONS_LIMIT_MAX),
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: TransactionEntryService = Depends(transaction_service_dep),
) -> BudgetAllocationsResponse:
    month_start = (month or date.today()).replace(day=1)
    entries = service.list_allocations(conn, month_start, limit)
    allocation_models = [BudgetAllocationEntry(**entry) for entry in entries]
    ready_minor = service.ready_to_assign(conn, month_start)
    inflow_minor = service.month_cash_inflow(conn, month_start)
    return BudgetAllocationsResponse(
        month_start=month_start,
        inflow_minor=inflow_minor,
        inflow_decimal=Decimal(inflow_minor).scaleb(-2).quantize(Decimal("0.01")),
        ready_to_assign_minor=ready_minor,
        ready_to_assign_decimal=Decimal(ready_minor).scaleb(-2).quantize(Decimal("0.01")),
        allocations=allocation_models,
    )
