"""Budgeting API routers."""

from datetime import date
from decimal import Decimal
from typing import TypeVar

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
    BudgetAllocationEntry,
    BudgetAllocationRequest,
    BudgetAllocationsResponse,
    BudgetCategoryCreateRequest,
    BudgetCategoryDetail,
    BudgetCategoryGroupCreateRequest,
    BudgetCategoryGroupDetail,
    BudgetCategoryGroupUpdateRequest,
    BudgetCategoryUpdateRequest,
    CategorizedTransferRequest,
    CategorizedTransferResponse,
    CategoryState,
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

# Initialize the API router with a tag for budgeting functionalities.
router = APIRouter(tags=["budgeting"])

# Default and maximum limits for transaction listings.
TRANSACTION_LIMIT_DEFAULT = 50
TRANSACTION_LIMIT_MAX = 500
# Default and maximum limits for allocation listings.
ALLOCATIONS_LIMIT_DEFAULT = 100
ALLOCATIONS_LIMIT_MAX = 500

# Type variable for FastAPI service dependencies.
ServiceT = TypeVar("ServiceT")


def _ensure_service_type(
    service: object | None, attr: str, expected_type: type[ServiceT]
) -> ServiceT:
    """
    Ensures that a service retrieved from app.state is of the expected type.

    This helper function is used within dependency injection to provide
    type-safety and clear error messages if a service is not correctly configured.

    Parameters
    ----------
    service : object | None
        The service object retrieved from `request.app.state`.
    attr : str
        The attribute name used to retrieve the service (for error messages).
    expected_type : Type[ServiceT]
        The expected class type of the service.

    Returns
    -------
    ServiceT
        The service instance, cast to the expected type.

    Raises
    ------
    RuntimeError
        If the service is not configured or is not of the expected type.
    """
    # Raise an error if the service is None, indicating it wasn't configured.
    if service is None:
        raise RuntimeError(f"{expected_type.__name__} not configured on app.state")
    # Check if the service is an instance of the expected type.
    if not isinstance(service, expected_type):  # pragma: no cover
        raise RuntimeError(f"{attr} is not an instance of {expected_type.__name__}")
    return service


def transaction_service_dep(request: Request) -> TransactionEntryService:
    """
    FastAPI dependency that provides a `TransactionEntryService` instance.

    This dependency retrieves the `TransactionEntryService` from the application's state,
    ensuring it's properly initialized and type-checked.

    Parameters
    ----------
    request : Request
        The incoming FastAPI request object.

    Returns
    -------
    TransactionEntryService
        An instance of the TransactionEntryService.

    Raises
    ------
    RuntimeError
        If the TransactionEntryService is not configured on `app.state`.
    """
    try:
        # Attempt to retrieve the service from app.state.
        service = request.app.state.transaction_service
    except AttributeError as exc:
        # Raise an error if the attribute does not exist.
        raise RuntimeError(
            "TransactionEntryService not configured on app.state"
        ) from exc
    # Ensure the retrieved service is of the correct type.
    return _ensure_service_type(service, "transaction_service", TransactionEntryService)


def account_admin_service_dep(request: Request) -> AccountAdminService:
    """
    FastAPI dependency that provides an `AccountAdminService` instance.

    This dependency retrieves the `AccountAdminService` from the application's state,
    ensuring it's properly initialized and type-checked.

    Parameters
    ----------
    request : Request
        The incoming FastAPI request object.

    Returns
    -------
    AccountAdminService
        An instance of the AccountAdminService.

    Raises
    ------
    RuntimeError
        If the AccountAdminService is not configured on `app.state`.
    """
    try:
        # Attempt to retrieve the service from app.state.
        service = request.app.state.account_admin_service
    except AttributeError as exc:
        # Raise an error if the attribute does not exist.
        raise RuntimeError("AccountAdminService not configured on app.state") from exc
    # Ensure the retrieved service is of the correct type.
    return _ensure_service_type(service, "account_admin_service", AccountAdminService)


def category_admin_service_dep(request: Request) -> BudgetCategoryAdminService:
    """
    FastAPI dependency that provides a `BudgetCategoryAdminService` instance.

    This dependency retrieves the `BudgetCategoryAdminService` from the application's state,
    ensuring it's properly initialized and type-checked.

    Parameters
    ----------
    request : Request
        The incoming FastAPI request object.

    Returns
    -------
    BudgetCategoryAdminService
        An instance of the BudgetCategoryAdminService.

    Raises
    ------
    RuntimeError
        If the BudgetCategoryAdminService is not configured on `app.state`.
    """
    try:
        # Attempt to retrieve the service from app.state.
        service = request.app.state.budget_category_admin_service
    except AttributeError as exc:
        # Raise an error if the attribute does not exist.
        raise RuntimeError(
            "BudgetCategoryAdminService not configured on app.state"
        ) from exc
    # Ensure the retrieved service is of the correct type.
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
    """
    Creates a new transaction.

    This endpoint allows for the creation of new financial transactions,
    processing the provided payload through the transaction entry service.
    Handles various budgeting-related exceptions.

    Parameters
    ----------
    payload : NewTransactionRequest
        The data for the new transaction.
    conn : duckdb.DuckDBPyConnection
        Dependency that provides a DuckDB connection.
    service : TransactionEntryService
        Dependency that provides the transaction entry service.

    Returns
    -------
    TransactionResponse
        The details of the newly created transaction.

    Raises
    ------
    HTTPException
        400 Bad Request for budgeting-related errors (e.g., invalid input, unknown account).
        500 Internal Server Error for unexpected system errors.
    """
    try:
        # Attempt to create the transaction using the service.
        return service.create(conn, payload)
    except BudgetingError as exc:
        # Catch specific budgeting errors and return a 400 Bad Request.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        # Catch any other unexpected exceptions and return a 500 Internal Server Error.
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
    """
    Returns the most recent transactions.

    This endpoint retrieves a list of recent transactions, primarily for
    display in user interfaces, with configurable pagination.

    Parameters
    ----------
    limit : int, optional
        The maximum number of transactions to return. Defaults to `TRANSACTION_LIMIT_DEFAULT`.
        Must be between 1 and `TRANSACTION_LIMIT_MAX`.
    conn : duckdb.DuckDBPyConnection
        Dependency that provides a DuckDB connection.
    service : TransactionEntryService
        Dependency that provides the transaction entry service.

    Returns
    -------
    list[TransactionListItem]
        A list of `TransactionListItem` objects representing recent transactions.
    """
    # Retrieve and return a list of recent transactions using the service.
    return service.list_recent(conn, limit)


@router.get("/reference-data", response_model=ReferenceDataResponse)
def get_reference_data(
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
) -> ReferenceDataResponse:
    """
    Returns lightweight reference data for the Single Page Application (SPA).

    This endpoint provides essential data like lists of accounts and categories
    in a simplified format, optimized for frontend consumption.

    Parameters
    ----------
    conn : duckdb.DuckDBPyConnection
        Dependency that provides a DuckDB connection.

    Returns
    -------
    ReferenceDataResponse
        A Pydantic model containing lists of simplified account and category states.
    """
    # Initialize the DAO for data access.
    dao = BudgetingDAO(conn)
    # Retrieve reference account records and convert them to AccountState schemas.
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
    # Retrieve reference category records.
    # Note: Category reference uses available = 0 until monthly state exists.
    category_records = dao.list_reference_categories()
    categories = [
        CategoryState(
            category_id=record.category_id,
            name=record.name,
            available_minor=record.available_minor,
            activity_minor=0,  # Activity is zero for initial reference data.
        )
        for record in category_records
    ]
    # Return the combined reference data.
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
    """
    Performs a categorized transfer, potentially involving multiple transaction legs.

    This endpoint facilitates moving funds between accounts and/or categories,
    ensuring that all related financial movements are correctly recorded.

    Parameters
    ----------
    payload : CategorizedTransferRequest
        The details of the transfer, including source, destination, and amount.
    conn : duckdb.DuckDBPyConnection
        Dependency that provides a DuckDB connection.
    service : TransactionEntryService
        Dependency that provides the transaction entry service.

    Returns
    -------
    CategorizedTransferResponse
        The details of the completed transfer, including any generated transactions.

    Raises
    ------
    HTTPException
        400 Bad Request for budgeting-related errors.
    """
    try:
        # Attempt to perform the transfer using the service.
        return service.transfer(conn, payload)
    except BudgetingError as exc:
        # Catch specific budgeting errors and return a 400 Bad Request.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.get("/accounts", response_model=list[AccountDetail])
def list_accounts(
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: AccountAdminService = Depends(account_admin_service_dep),
) -> list[AccountDetail]:
    """
    Returns all accounts for administration flows.

    This endpoint provides a detailed list of all financial accounts,
    suitable for display and management in an administrative interface.

    Parameters
    ----------
    conn : duckdb.DuckDBPyConnection
        Dependency that provides a DuckDB connection.
    service : AccountAdminService
        Dependency that provides the account administration service.

    Returns
    -------
    list[AccountDetail]
        A list of `AccountDetail` objects representing all accounts.
    """
    # Retrieve and return a list of all accounts using the service.
    return service.list_accounts(conn)


@router.post(
    "/accounts", response_model=AccountDetail, status_code=status.HTTP_201_CREATED
)
def create_account(
    payload: AccountCreateRequest,
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: AccountAdminService = Depends(account_admin_service_dep),
) -> AccountDetail:
    """
    Creates a new financial account.

    Parameters
    ----------
    payload : AccountCreateRequest
        The data for the new account, including name, type, class, role, and initial balance.
    conn : duckdb.DuckDBPyConnection
        Dependency that provides a DuckDB connection.
    service : AccountAdminService
        Dependency that provides the account administration service.

    Returns
    -------
    AccountDetail
        The details of the newly created account.

    Raises
    ------
    HTTPException
        409 Conflict if an account with the same ID already exists.
        400 Bad Request for other budgeting-related errors.
    """
    try:
        # Attempt to create the account using the service.
        return service.create_account(conn, payload)
    except AccountAlreadyExists as exc:
        # Handle cases where an account with the given ID already exists.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except BudgetingError as exc:
        # Handle other specific budgeting errors.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.put("/accounts/{account_id}", response_model=AccountDetail)
def update_account(
    account_id: str,
    payload: AccountUpdateRequest,
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: AccountAdminService = Depends(account_admin_service_dep),
) -> AccountDetail:
    """
    Updates an existing financial account.

    Parameters
    ----------
    account_id : str
        The ID of the account to update.
    payload : AccountUpdateRequest
        The updated data for the account.
    conn : duckdb.DuckDBPyConnection
        Dependency that provides a DuckDB connection.
    service : AccountAdminService
        Dependency that provides the account administration service.

    Returns
    -------
    AccountDetail
        The updated account details.

    Raises
    ------
    HTTPException
        404 Not Found if the account does not exist.
        400 Bad Request for other budgeting-related errors.
    """
    try:
        # Attempt to update the account using the service.
        return service.update_account(conn, account_id, payload)
    except AccountNotFound as exc:
        # Handle cases where the account to be updated is not found.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except BudgetingError as exc:
        # Handle other specific budgeting errors.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_account(
    account_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: AccountAdminService = Depends(account_admin_service_dep),
) -> Response:
    """
    Deactivates a financial account.

    Deactivating an account marks it as inactive without permanently deleting it.

    Parameters
    ----------
    account_id : str
        The ID of the account to deactivate.
    conn : duckdb.DuckDBPyConnection
        Dependency that provides a DuckDB connection.
    service : AccountAdminService
        Dependency that provides the account administration service.

    Returns
    -------
    Response
        An empty response with a 204 No Content status code on successful deactivation.

    Raises
    ------
    HTTPException
        404 Not Found if the account does not exist.
        400 Bad Request for other budgeting-related errors.
    """
    try:
        # Attempt to deactivate the account using the service.
        service.deactivate_account(conn, account_id)
    except AccountNotFound as exc:
        # Handle cases where the account to be deactivated is not found.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except BudgetingError as exc:
        # Handle other specific budgeting errors.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    # Return a 204 No Content response for successful deactivation.
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/budget-categories", response_model=list[BudgetCategoryDetail])
def list_categories(
    month: date | None = Query(
        None, description="Month start (YYYY-MM-01) for envelope state."
    ),
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: BudgetCategoryAdminService = Depends(category_admin_service_dep),
) -> list[BudgetCategoryDetail]:
    """
    Returns a list of budgeting categories with their details.

    The details can be optionally filtered for a specific month to reflect
    the category's state (e.g., available funds) for that period.

    Parameters
    ----------
    month : date | None, optional
        The start date of the month (YYYY-MM-01) for which to retrieve category states.
        If None, current category details without monthly state might be returned.
    conn : duckdb.DuckDBPyConnection
        Dependency that provides a DuckDB connection.
    service : BudgetCategoryAdminService
        Dependency that provides the budget category administration service.

    Returns
    -------
    list[BudgetCategoryDetail]
        A list of `BudgetCategoryDetail` objects.
    """
    # Retrieve and return a list of categories using the service, optionally filtered by month.
    return service.list_categories(conn, month_start=month)


@router.post(
    "/budget-categories",
    response_model=BudgetCategoryDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    payload: BudgetCategoryCreateRequest,
    month: date | None = Query(
        None, description="Month start (YYYY-MM-01) for envelope state."
    ),
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: BudgetCategoryAdminService = Depends(category_admin_service_dep),
) -> BudgetCategoryDetail:
    """
    Creates a new budgeting category.

    Parameters
    ----------
    payload : BudgetCategoryCreateRequest
        The data for the new budgeting category.
    month : date | None, optional
        The start date of the month (YYYY-MM-01) relevant for initial category state.
    conn : duckdb.DuckDBPyConnection
        Dependency that provides a DuckDB connection.
    service : BudgetCategoryAdminService
        Dependency that provides the budget category administration service.

    Returns
    -------
    BudgetCategoryDetail
        The details of the newly created budgeting category.

    Raises
    ------
    HTTPException
        409 Conflict if a category with the same ID already exists.
        400 Bad Request for other budgeting-related errors.
    """
    try:
        # Attempt to create the category using the service.
        return service.create_category(conn, payload, month_start=month)
    except CategoryAlreadyExists as exc:
        # Handle cases where a category with the given ID already exists.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except BudgetingError as exc:
        # Handle other specific budgeting errors.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.put("/budget-categories/{category_id}", response_model=BudgetCategoryDetail)
def update_category(
    category_id: str,
    payload: BudgetCategoryUpdateRequest,
    month: date | None = Query(
        None, description="Month start (YYYY-MM-01) for envelope state."
    ),
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: BudgetCategoryAdminService = Depends(category_admin_service_dep),
) -> BudgetCategoryDetail:
    """
    Updates an existing budgeting category.

    Parameters
    ----------
    category_id : str
        The ID of the category to update.
    payload : BudgetCategoryUpdateRequest
        The updated data for the budgeting category.
    month : date | None, optional
        The start date of the month (YYYY-MM-01) relevant for updating category state.
    conn : duckdb.DuckDBPyConnection
        Dependency that provides a DuckDB connection.
    service : BudgetCategoryAdminService
        Dependency that provides the budget category administration service.

    Returns
    -------
    BudgetCategoryDetail
        The updated budgeting category details.

    Raises
    ------
    HTTPException
        404 Not Found if the category does not exist.
        400 Bad Request for other budgeting-related errors.
    """
    try:
        # Attempt to update the category using the service.
        return service.update_category(conn, category_id, payload, month_start=month)
    except CategoryNotFound as exc:
        # Handle cases where the category to be updated is not found.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except BudgetingError as exc:
        # Handle other specific budgeting errors.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.delete(
    "/budget-categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT
)
def deactivate_category(
    category_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: BudgetCategoryAdminService = Depends(category_admin_service_dep),
) -> Response:
    """
    Deactivates a budgeting category.

    Deactivating a category marks it as inactive without permanently deleting it.

    Parameters
    ----------
    category_id : str
        The ID of the category to deactivate.
    conn : duckdb.DuckDBPyConnection
        Dependency that provides a DuckDB connection.
    service : BudgetCategoryAdminService
        Dependency that provides the budget category administration service.

    Returns
    -------
    Response
        An empty response with a 204 No Content status code on successful deactivation.

    Raises
    ------
    HTTPException
        404 Not Found if the category does not exist.
        400 Bad Request for other budgeting-related errors.
    """
    try:
        # Attempt to deactivate the category using the service.
        service.deactivate_category(conn, category_id)
    except CategoryNotFound as exc:
        # Handle cases where the category to be deactivated is not found.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except BudgetingError as exc:
        # Handle other specific budgeting errors.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    # Return a 204 No Content response for successful deactivation.
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/budget-category-groups", response_model=list[BudgetCategoryGroupDetail])
def list_groups(
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: BudgetCategoryAdminService = Depends(category_admin_service_dep),
) -> list[BudgetCategoryGroupDetail]:
    """
    Returns a list of all budgeting category groups.

    Parameters
    ----------
    conn : duckdb.DuckDBPyConnection
        Dependency that provides a DuckDB connection.
    service : BudgetCategoryAdminService
        Dependency that provides the budget category administration service.

    Returns
    -------
    list[BudgetCategoryGroupDetail]
        A list of `BudgetCategoryGroupDetail` objects.
    """
    # Retrieve and return a list of all category groups using the service.
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
    """
    Creates a new budgeting category group.

    Parameters
    ----------
    payload : BudgetCategoryGroupCreateRequest
        The data for the new budgeting category group.
    conn : duckdb.DuckDBPyConnection
        Dependency that provides a DuckDB connection.
    service : BudgetCategoryAdminService
        Dependency that provides the budget category administration service.

    Returns
    -------
    BudgetCategoryGroupDetail
        The details of the newly created budgeting category group.

    Raises
    ------
    HTTPException
        409 Conflict if a group with the same ID already exists.
        400 Bad Request for other budgeting-related errors.
    """
    try:
        # Attempt to create the category group using the service.
        return service.create_group(conn, payload)
    except GroupAlreadyExists as exc:
        # Handle cases where a group with the given ID already exists.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except BudgetingError as exc:
        # Handle other specific budgeting errors.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.put(
    "/budget-category-groups/{group_id}", response_model=BudgetCategoryGroupDetail
)
def update_group(
    group_id: str,
    payload: BudgetCategoryGroupUpdateRequest,
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: BudgetCategoryAdminService = Depends(category_admin_service_dep),
) -> BudgetCategoryGroupDetail:
    """
    Updates an existing budgeting category group.

    Parameters
    ----------
    group_id : str
        The ID of the category group to update.
    payload : BudgetCategoryGroupUpdateRequest
        The updated data for the budgeting category group.
    conn : duckdb.DuckDBPyConnection
        Dependency that provides a DuckDB connection.
    service : BudgetCategoryAdminService
        Dependency that provides the budget category administration service.

    Returns
    -------
    BudgetCategoryGroupDetail
        The updated budgeting category group details.

    Raises
    ------
    HTTPException
        404 Not Found if the group does not exist.
        400 Bad Request for other budgeting-related errors.
    """
    try:
        # Attempt to update the category group using the service.
        return service.update_group(conn, group_id, payload)
    except GroupNotFound as exc:
        # Handle cases where the group to be updated is not found.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except BudgetingError as exc:
        # Handle other specific budgeting errors.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.delete(
    "/budget-category-groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT
)
def deactivate_group(
    group_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: BudgetCategoryAdminService = Depends(category_admin_service_dep),
) -> Response:
    """
    Deactivates a budgeting category group.

    Deactivating a group marks it as inactive without permanently deleting it.

    Parameters
    ----------
    group_id : str
        The ID of the category group to deactivate.
    conn : duckdb.DuckDBPyConnection
        Dependency that provides a DuckDB connection.
    service : BudgetCategoryAdminService
        Dependency that provides the budget category administration service.

    Returns
    -------
    Response
        An empty response with a 204 No Content status code on successful deactivation.

    Raises
    ------
    HTTPException
        404 Not Found if the group does not exist.
        400 Bad Request for other budgeting-related errors.
    """
    try:
        # Attempt to deactivate the category group using the service.
        service.deactivate_group(conn, group_id)
    except GroupNotFound as exc:
        # Handle cases where the group to be deactivated is not found.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except BudgetingError as exc:
        # Handle other specific budgeting errors.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    # Return a 204 No Content response for successful deactivation.
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/budget/ready-to-assign", response_model=ReadyToAssignResponse)
def ready_to_assign(
    month: date | None = Query(None, description="Month start (YYYY-MM-01)."),
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: TransactionEntryService = Depends(transaction_service_dep),
) -> ReadyToAssignResponse:
    """
    Returns the "Ready to Assign" amount for a given month.

    This represents the total unallocated funds available for budgeting categories
    for the specified month.

    Parameters
    ----------
    month : date | None, optional
        The start date of the month (YYYY-MM-01) for which to retrieve "Ready to Assign".
        Defaults to the first day of the current month if not provided.
    conn : duckdb.DuckDBPyConnection
        Dependency that provides a DuckDB connection.
    service : TransactionEntryService
        Dependency that provides the transaction entry service.

    Returns
    -------
    ReadyToAssignResponse
        A Pydantic model containing the "Ready to Assign" amount in minor and decimal units.
    """
    # Default to the first day of the current month if no month is specified.
    if month is None:
        month = date.today().replace(day=1)
    # Retrieve the ready-to-assign amount from the service.
    ready_minor = service.ready_to_assign(conn, month)
    # Construct and return the response model, converting minor units to decimal.
    return ReadyToAssignResponse(
        month_start=month,
        ready_to_assign_minor=ready_minor,
        ready_to_assign_decimal=Decimal(ready_minor)
        .scaleb(-2)
        .quantize(Decimal("0.01")),
    )


@router.post(
    "/budget/allocations",
    response_model=CategoryState,
    status_code=status.HTTP_201_CREATED,
)
def allocate_budget(
    payload: BudgetAllocationRequest,
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: TransactionEntryService = Depends(transaction_service_dep),
) -> CategoryState:
    """
    Allocates funds to a budgeting category.

    This endpoint handles the movement of funds from "Ready to Assign" or
    between categories, updating the budget envelope.

    Parameters
    ----------
    payload : BudgetAllocationRequest
        The details of the allocation, including target category, amount, and month.
    conn : duckdb.DuckDBPyConnection
        Dependency that provides a DuckDB connection.
    service : TransactionEntryService
        Dependency that provides the transaction entry service.

    Returns
    -------
    CategoryState
        The updated state of the target category after the allocation.

    Raises
    ------
    HTTPException
        400 Bad Request if `to_category_id` is missing or for budgeting-related errors.
    """
    # Determine the target category ID for the allocation.
    target_category_id = payload.to_category_id or payload.category_id
    if not target_category_id:
        # Raise an error if the target category ID is not provided.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="to_category_id is required"
        )
    try:
        # Attempt to allocate the envelope using the service.
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
        # Handle budgeting and invalid transaction errors.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.get("/budget/allocations", response_model=BudgetAllocationsResponse)
def list_allocations(
    month: date | None = Query(None, description="Month start (YYYY-MM-01)."),
    limit: int = Query(ALLOCATIONS_LIMIT_DEFAULT, ge=1, le=ALLOCATIONS_LIMIT_MAX),
    conn: duckdb.DuckDBPyConnection = Depends(connection_dep),
    service: TransactionEntryService = Depends(transaction_service_dep),
) -> BudgetAllocationsResponse:
    """
    Lists budget allocations for a specific month.

    Retrieves a list of all allocation events for a given month, along with
    the "Ready to Assign" and cash inflow figures for that month.

    Parameters
    ----------
    month : date | None, optional
        The start date of the month (YYYY-MM-01) for which to list allocations.
        Defaults to the first day of the current month if not provided.
    limit : int, optional
        The maximum number of allocations to return. Defaults to `ALLOCATIONS_LIMIT_DEFAULT`.
        Must be between 1 and `ALLOCATIONS_LIMIT_MAX`.
    conn : duckdb.DuckDBPyConnection
        Dependency that provides a DuckDB connection.
    service : TransactionEntryService
        Dependency that provides the transaction entry service.

    Returns
    -------
    BudgetAllocationsResponse
        A Pydantic model containing the monthly inflow, "Ready to Assign" amounts,
        and a list of budget allocation entries.
    """
    # Determine the month start, defaulting to the current month's first day.
    month_start = (month or date.today()).replace(day=1)
    # Retrieve budget allocation entries from the service.
    entries = service.list_allocations(conn, month_start, limit)
    # Convert DAO records to Pydantic models for the response.
    allocation_models = [BudgetAllocationEntry(**entry) for entry in entries]
    # Get the "Ready to Assign" amount for the month.
    ready_minor = service.ready_to_assign(conn, month_start)
    # Get the cash inflow for the month.
    inflow_minor = service.month_cash_inflow(conn, month_start)
    # Construct and return the comprehensive budget allocations response.
    return BudgetAllocationsResponse(
        month_start=month_start,
        inflow_minor=inflow_minor,
        inflow_decimal=Decimal(inflow_minor).scaleb(-2).quantize(Decimal("0.01")),
        ready_to_assign_minor=ready_minor,
        ready_to_assign_decimal=Decimal(ready_minor)
        .scaleb(-2)
        .quantize(Decimal("0.01")),
        allocations=allocation_models,
    )
