"""API routers for onboarding + Aspire migration.

These endpoints back a first-run onboarding wizard, including an optional Aspire
Google Sheets migration.

Privacy note:
- Never log raw extracted values or OAuth credentials.
- Avoid returning raw staging rows; return only what the UI needs to validate
  and apply a migration.
"""

import json
import re

from collections.abc import Callable
from datetime import date
from typing import Any, cast

import uuid

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse

from dojo.budgeting.errors import AccountAlreadyExistsError, CategoryAlreadyExistsError, GroupAlreadyExistsError
from dojo.budgeting.schemas import (
    AccountCreateRequest,
    BudgetCategoryCreateRequest,
    BudgetCategoryGroupCreateRequest,
    CategorizedTransferRequest,
    NewTransactionRequest,
)
from dojo.budgeting.services import AccountAdminService, BudgetCategoryAdminService, TransactionEntryService

from dojo.aspire.gsheets_client import GoogleSheetsApiError, GoogleSheetsAuthError, GoogleSheetsClient
from dojo.aspire_migration.extract import AspireExtractionError, extract_aspire_rows, required_named_ranges
from dojo.aspire_migration.extraction_store import AspireExtractionStore, ExtractedAspireSummary
from dojo.aspire_migration.google_oauth import GoogleOAuthError, GoogleOAuthStore
from dojo.aspire_migration.schemas import (
    AspireBudgetParityResponse,
    AspireAccountMapping,
    AspireCategoryMapping,
    AspireMapping,
    AspireTransferCandidateGroup,
    AspireTransferRow,
    CancelOnboardingResponse,
    ExtractAspireRequest,
    ExtractAspireResponse,
    GetAspireMappingResponse,
    GetAspireTransfersResponse,
    GoogleOAuthStartResponse,
    GoogleOAuthStatusResponse,
    MappingCandidatesResponse,
    NetWorthDecision,
    OnboardingMode,
    OnboardingStatus,
    OnboardingStatusResponse,
    SaveAspireMappingRequest,
    SaveNetWorthDecisionsRequest,
    GetNetWorthDecisionsResponse,
    ApplyAspireMigrationRequest,
    ApplyAspireMigrationResponse,
    BudgetParityRow,
    StartOnboardingRequest,
    VerifyAspireSheetRequest,
    VerifyAspireSheetResponse,
)
from dojo.aspire_migration.sheets import parse_spreadsheet_id
from dojo.core.clock import get_system_date
from dojo.core.config import Settings, get_settings
from dojo.core.db import connection_dep

from dojo.budgeting.dao import BudgetingDAO

router = APIRouter(tags=["onboarding"])

_PRIMARY_ID = "primary"
_CONNECTION_DEP = Depends(connection_dep)
_SETTINGS_DEP = Depends(get_settings)
_SYSTEM_DATE_DEP = Depends(get_system_date)


def _ensure_service_type(service: object, attr: str, expected_type: type[Any]) -> Any:
    if service is None:
        raise RuntimeError(f"{expected_type.__name__} not configured on app.state")
    if not isinstance(service, expected_type):  # pragma: no cover
        raise RuntimeError(f"{attr} is not an instance of {expected_type.__name__}")
    return service


def _transaction_service_dep(request: Request) -> TransactionEntryService:
    try:
        service = request.app.state.transaction_service
    except AttributeError as exc:  # pragma: no cover - app wiring
        raise RuntimeError("TransactionEntryService not configured on app.state") from exc
    return _ensure_service_type(service, "transaction_service", TransactionEntryService)


def _account_admin_service_dep(request: Request) -> AccountAdminService:
    try:
        service = request.app.state.account_admin_service
    except AttributeError as exc:  # pragma: no cover - app wiring
        raise RuntimeError("AccountAdminService not configured on app.state") from exc
    return _ensure_service_type(service, "account_admin_service", AccountAdminService)


def _category_admin_service_dep(request: Request) -> BudgetCategoryAdminService:
    try:
        service = request.app.state.budget_category_admin_service
    except AttributeError as exc:  # pragma: no cover - app wiring
        raise RuntimeError("BudgetCategoryAdminService not configured on app.state") from exc
    return _ensure_service_type(service, "budget_category_admin_service", BudgetCategoryAdminService)


_TRANSACTION_SERVICE_DEP = Depends(_transaction_service_dep)
_ACCOUNT_ADMIN_SERVICE_DEP = Depends(_account_admin_service_dep)
_CATEGORY_ADMIN_SERVICE_DEP = Depends(_category_admin_service_dep)


def _oauth_store_dep(request: Request) -> GoogleOAuthStore:
    try:
        store = request.app.state.google_oauth_store
    except AttributeError as exc:  # pragma: no cover - app wiring
        raise RuntimeError("GoogleOAuthStore not configured on app.state") from exc
    if not isinstance(store, GoogleOAuthStore):  # pragma: no cover - app wiring
        raise RuntimeError("google_oauth_store is not a GoogleOAuthStore")
    return store


_OAUTH_STORE_DEP = Depends(_oauth_store_dep)


def _sheets_client_factory_dep(request: Request) -> Callable[[Any], GoogleSheetsClient]:
    try:
        factory = request.app.state.sheets_client_factory
    except AttributeError as exc:  # pragma: no cover - app wiring
        raise RuntimeError("sheets_client_factory not configured on app.state") from exc
    if not callable(factory):  # pragma: no cover - app wiring
        raise RuntimeError("sheets_client_factory is not callable")
    return cast(Callable[[Any], GoogleSheetsClient], factory)


def _extraction_store_dep(request: Request) -> AspireExtractionStore:
    try:
        store = request.app.state.aspire_extraction_store
    except AttributeError as exc:  # pragma: no cover - app wiring
        raise RuntimeError("AspireExtractionStore not configured on app.state") from exc
    if not isinstance(store, AspireExtractionStore):  # pragma: no cover - app wiring
        raise RuntimeError("aspire_extraction_store is not an AspireExtractionStore")
    return store


_SHEETS_FACTORY_DEP = Depends(_sheets_client_factory_dep)
_EXTRACTION_STORE_DEP = Depends(_extraction_store_dep)


def _read_onboarding_row(conn: duckdb.DuckDBPyConnection) -> tuple[OnboardingMode | None, OnboardingStatus, str | None]:
    row = conn.execute(
        """
        SELECT onboarding_mode, onboarding_status, migration_session_id
        FROM onboarding_state
        WHERE onboarding_id = $id
        """,
        {"id": _PRIMARY_ID},
    ).fetchone()

    # Defensive fallback (should be initialized by migration 0018).
    if row is None:
        conn.execute(
            """
            INSERT INTO onboarding_state (onboarding_id, onboarding_mode, onboarding_status)
            VALUES ($id, NULL, 'not_started')
            """,
            {"id": _PRIMARY_ID},
        )
        row = (None, "not_started", None)

    raw_mode, raw_status, migration_session_id = row[0], row[1], row[2]

    mode: OnboardingMode | None = raw_mode if raw_mode in {"manual", "aspire"} else None
    status_value: OnboardingStatus = (
        raw_status if raw_status in {"not_started", "in_progress", "completed"} else "not_started"
    )

    return (mode, status_value, migration_session_id)


def _write_onboarding_row(
    conn: duckdb.DuckDBPyConnection,
    *,
    onboarding_mode: str | None,
    onboarding_status: str,
    migration_session_id: str | None,
) -> None:
    # Avoid relying on DuckDB's ON CONFLICT support; keep it explicit + transactional.
    conn.execute("BEGIN")
    try:
        conn.execute(
            "DELETE FROM onboarding_state WHERE onboarding_id = $id",
            {"id": _PRIMARY_ID},
        )
        conn.execute(
            """
            INSERT INTO onboarding_state (
                onboarding_id,
                onboarding_mode,
                onboarding_status,
                migration_session_id,
                created_at,
                updated_at
            )
            VALUES ($id, $mode, $status, $session_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            {
                "id": _PRIMARY_ID,
                "mode": onboarding_mode,
                "status": onboarding_status,
                "session_id": migration_session_id,
            },
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


@router.get("/onboarding/status", response_model=OnboardingStatusResponse)
def get_onboarding_status(
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
) -> OnboardingStatusResponse:
    onboarding_mode, onboarding_status, migration_session_id = _read_onboarding_row(conn)
    should_onboard = onboarding_status != "completed"
    return OnboardingStatusResponse(
        onboarding_mode=onboarding_mode,
        onboarding_status=onboarding_status,
        migration_session_id=migration_session_id,
        should_onboard=should_onboard,
    )


@router.post(
    "/onboarding/start",
    response_model=OnboardingStatusResponse,
    status_code=status.HTTP_200_OK,
)
def start_onboarding(
    payload: StartOnboardingRequest,
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
) -> OnboardingStatusResponse:
    # Record the user's choice. For Aspire, create (or reuse) a migration_session_id.
    status_value: OnboardingStatus = "completed" if payload.onboarding_mode == "manual" else "in_progress"

    existing_mode, existing_status, existing_session_id = _read_onboarding_row(conn)
    migration_session_id = None
    if payload.onboarding_mode == "aspire":
        if existing_mode == "aspire" and existing_status == "in_progress" and existing_session_id:
            migration_session_id = existing_session_id
        else:
            migration_session_id = str(uuid.uuid4())

    _write_onboarding_row(
        conn,
        onboarding_mode=payload.onboarding_mode,
        onboarding_status=status_value,
        migration_session_id=migration_session_id,
    )
    return get_onboarding_status(conn)


@router.post(
    "/onboarding/cancel",
    response_model=CancelOnboardingResponse,
    status_code=status.HTTP_200_OK,
)
def cancel_onboarding(
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
) -> CancelOnboardingResponse:
    _write_onboarding_row(
        conn,
        onboarding_mode=None,
        onboarding_status="not_started",
        migration_session_id=None,
    )
    return CancelOnboardingResponse(ok=True)


def _oauth_exception_to_http(exc: GoogleOAuthError) -> HTTPException:
    message = str(exc)
    status_code = status.HTTP_400_BAD_REQUEST
    if message.startswith("Missing optional dependencies"):
        status_code = status.HTTP_501_NOT_IMPLEMENTED
    return HTTPException(status_code=status_code, detail=message)


@router.get("/onboarding/google-oauth/status", response_model=GoogleOAuthStatusResponse)
def google_oauth_status(
    store: GoogleOAuthStore = _OAUTH_STORE_DEP,
) -> GoogleOAuthStatusResponse:
    oauth_status = store.status()
    return GoogleOAuthStatusResponse(
        connected=oauth_status.connected,
        expires_at_s=oauth_status.expires_at_s,
    )


@router.get("/onboarding/google-oauth/start", response_model=GoogleOAuthStartResponse)
def google_oauth_start(
    request: Request,
    settings: Settings = _SETTINGS_DEP,
    store: GoogleOAuthStore = _OAUTH_STORE_DEP,
) -> GoogleOAuthStartResponse:
    redirect_uri = settings.google_oauth_redirect_uri or str(request.url_for("google_oauth_callback"))
    try:
        url = store.start(settings, redirect_uri=redirect_uri)
    except GoogleOAuthError as exc:
        raise _oauth_exception_to_http(exc) from exc
    return GoogleOAuthStartResponse(authorization_url=url)


@router.get("/onboarding/google-oauth/callback", include_in_schema=False)
def google_oauth_callback(
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    settings: Settings = _SETTINGS_DEP,
    store: GoogleOAuthStore = _OAUTH_STORE_DEP,
) -> RedirectResponse:
    # This endpoint is a browser redirect target; keep responses simple and avoid leaking details.
    redirect_base = "/#/onboarding"

    if error or not code or not state:
        return RedirectResponse(url=f"{redirect_base}?google=error", status_code=status.HTTP_302_FOUND)

    redirect_uri = settings.google_oauth_redirect_uri or str(request.url_for("google_oauth_callback"))

    try:
        store.finish(settings, code=code, state=state, redirect_uri=redirect_uri)
    except GoogleOAuthError:
        return RedirectResponse(url=f"{redirect_base}?google=error", status_code=status.HTTP_302_FOUND)

    return RedirectResponse(url=f"{redirect_base}?google=connected", status_code=status.HTTP_302_FOUND)


@router.post("/onboarding/google-oauth/disconnect", status_code=status.HTTP_204_NO_CONTENT)
def google_oauth_disconnect(
    store: GoogleOAuthStore = _OAUTH_STORE_DEP,
) -> None:
    store.clear_credentials()


@router.post("/onboarding/aspire/verify-sheet", response_model=VerifyAspireSheetResponse)
def verify_aspire_sheet(
    payload: VerifyAspireSheetRequest,
    store: GoogleOAuthStore = _OAUTH_STORE_DEP,
    sheets_factory: Callable[[Any], GoogleSheetsClient] = _SHEETS_FACTORY_DEP,
) -> VerifyAspireSheetResponse:
    try:
        spreadsheet_id = parse_spreadsheet_id(payload.spreadsheet)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        credentials = store.get_credentials()
    except GoogleOAuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        client = sheets_factory(credentials)
        metadata = client.get_spreadsheet_metadata(spreadsheet_id=spreadsheet_id)
    except (GoogleSheetsAuthError, GoogleSheetsApiError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read spreadsheet metadata. Reconnect Google and double-check the spreadsheet id.",
        ) from exc

    named_ranges = metadata.get("namedRanges") or []
    names = {r.get("name") for r in named_ranges if isinstance(r, dict)}
    names.discard(None)

    required = required_named_ranges()
    missing = sorted([name for name in required if name not in names])

    return VerifyAspireSheetResponse(
        readable=True,
        looks_like_aspire=len(missing) == 0,
        missing_named_ranges=missing,
        named_range_count=len(names),
    )


@router.get("/onboarding/aspire/extraction-summary", response_model=ExtractAspireResponse)
def get_extraction_summary(
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
    store: AspireExtractionStore = _EXTRACTION_STORE_DEP,
) -> ExtractAspireResponse:
    mode, status_value, migration_session_id = _read_onboarding_row(conn)
    if mode != "aspire" or not migration_session_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active Aspire migration session")

    session = conn.execute(
        "SELECT dataset_fingerprint FROM aspire_migration_sessions WHERE migration_session_id = $id",
        {"id": migration_session_id},
    ).fetchone()

    if session is None:
        # Temporary fallback while we transition from in-memory summaries.
        summary = store.get_summary(migration_session_id)
        if summary is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No extracted dataset for this session")

        return ExtractAspireResponse(
            migration_session_id=summary.migration_session_id,
            dataset_fingerprint=summary.dataset_fingerprint,
            transactions_count=summary.transactions_count,
            transactions_date_min=summary.transactions_date_min,
            transactions_date_max=summary.transactions_date_max,
            allocations_count=summary.allocations_count,
            allocations_date_min=summary.allocations_date_min,
            allocations_date_max=summary.allocations_date_max,
            net_worth_snapshots_count=summary.net_worth_snapshots_count,
            net_worth_date_min=summary.net_worth_date_min,
            net_worth_date_max=summary.net_worth_date_max,
        )

    dataset_fingerprint = str(session[0])

    trx_row = conn.execute(
        """
            SELECT COUNT(*), MIN(transaction_date), MAX(transaction_date)
            FROM aspire_staging_transactions
            WHERE migration_session_id = $id
            """,
        {"id": migration_session_id},
    ).fetchone() or (0, None, None)
    trx_count, trx_min, trx_max = trx_row

    alloc_row = conn.execute(
        """
            SELECT COUNT(*), MIN(allocation_date), MAX(allocation_date)
            FROM aspire_staging_allocations
            WHERE migration_session_id = $id
            """,
        {"id": migration_session_id},
    ).fetchone() or (0, None, None)
    alloc_count, alloc_min, alloc_max = alloc_row

    ntw_row = conn.execute(
        """
            SELECT COUNT(*), MIN(snapshot_date), MAX(snapshot_date)
            FROM aspire_staging_net_worth_snapshots
            WHERE migration_session_id = $id
            """,
        {"id": migration_session_id},
    ).fetchone() or (0, None, None)
    ntw_count, ntw_min, ntw_max = ntw_row

    return ExtractAspireResponse(
        migration_session_id=migration_session_id,
        dataset_fingerprint=dataset_fingerprint,
        transactions_count=int(trx_count),
        transactions_date_min=trx_min.isoformat() if trx_min else None,
        transactions_date_max=trx_max.isoformat() if trx_max else None,
        allocations_count=int(alloc_count),
        allocations_date_min=alloc_min.isoformat() if alloc_min else None,
        allocations_date_max=alloc_max.isoformat() if alloc_max else None,
        net_worth_snapshots_count=int(ntw_count),
        net_worth_date_min=ntw_min.isoformat() if ntw_min else None,
        net_worth_date_max=ntw_max.isoformat() if ntw_max else None,
    )


def _fetch_mapping_candidates(
    conn: duckdb.DuckDBPyConnection,
    *,
    migration_session_id: str,
    cfg_accounts: list[str],
    cfg_cards: list[str],
    hidden_accounts: list[str],
    hidden_categories: list[str],
    categories_minus_credit_cards: list[str],
    net_worth_categories: list[str],
) -> tuple[list[str], list[str]]:
    accounts_rows = conn.execute(
        """
        SELECT DISTINCT account_name
        FROM aspire_staging_transactions
        WHERE migration_session_id = $id AND account_name IS NOT NULL AND TRIM(account_name) != ''
        ORDER BY account_name
        """,
        {"id": migration_session_id},
    ).fetchall()
    trx_accounts = [str(r[0]) for r in accounts_rows]

    # Accounts should include configured, hidden, and net worth entities,
    # plus anything referenced in the transaction ledger.
    accounts = sorted(
        {
            *trx_accounts,
            *cfg_accounts,
            *cfg_cards,
            *hidden_accounts,
            *net_worth_categories,
        }
    )

    # Budget categories should come from Aspire's derived budget list (which
    # intentionally excludes credit card/debt rows) plus hidden categories.
    if categories_minus_credit_cards:
        categories = sorted({*categories_minus_credit_cards, *hidden_categories})
    else:
        # Fallback: use whatever appears in staging.
        category_rows = conn.execute(
            """
            WITH cats AS (
                SELECT category_name AS name
                FROM aspire_staging_transactions
                WHERE migration_session_id = $id

                UNION ALL

                SELECT from_category_name AS name
                FROM aspire_staging_allocations
                WHERE migration_session_id = $id

                UNION ALL

                SELECT to_category_name AS name
                FROM aspire_staging_allocations
                WHERE migration_session_id = $id
            )
            SELECT DISTINCT name
            FROM cats
            WHERE name IS NOT NULL AND TRIM(name) != ''
            ORDER BY name
            """,
            {"id": migration_session_id},
        ).fetchall()
        categories = [str(r[0]) for r in category_rows]

    return (accounts, categories)


def _default_mapping_from_candidates(
    *,
    accounts: list[str],
    categories: list[str],
    cfg_accounts: list[str],
    cfg_cards: list[str],
    hidden_accounts: list[str],
    hidden_categories: list[str],
    net_worth_assets: list[str],
    net_worth_debts: list[str],
    user_def_amounts_minor: dict[str, int],
    user_def_goals_minor: dict[str, int],
) -> AspireMapping:
    cfg_accounts_set = set(cfg_accounts)
    cfg_cards_set = set(cfg_cards)
    hidden_accounts_set = set(hidden_accounts)
    hidden_categories_set = set(hidden_categories)
    net_worth_assets_set = set(net_worth_assets)
    net_worth_debts_set = set(net_worth_debts)

    accounts_out: dict[str, AspireAccountMapping] = {}
    for name in accounts:
        is_net_worth = name in net_worth_assets_set or name in net_worth_debts_set

        if is_net_worth:
            # Net worth entities are tracking accounts in Dojo.
            if name in net_worth_debts_set:
                account_class = "loan"
            else:
                account_class = "tangible"
            account_role = "tracking"
            is_active = True
        else:
            # Prefer the config tables for the semantic account type.
            if name in cfg_cards_set:
                account_class = "credit"
            else:
                account_class = "cash"
            account_role = "on_budget"

            # HiddenAccounts is the explicit "retired" signal in Aspire. If config
            # lists are missing/malformed, fail open and assume accounts are active.
            is_known_config = name in cfg_accounts_set or name in cfg_cards_set
            has_cfg_lists = bool(cfg_accounts_set or cfg_cards_set)
            is_active = name not in hidden_accounts_set and (not has_cfg_lists or is_known_config)

        accounts_out[name] = AspireAccountMapping(
            dojo_name=name,
            account_class=account_class,
            account_role=account_role,
            is_active=is_active,
        )

    categories_out: dict[str, AspireCategoryMapping] = {}
    for name in categories:
        is_active = name not in hidden_categories_set

        amount_minor = int(user_def_amounts_minor.get(name, 0) or 0)
        goal_minor = int(user_def_goals_minor.get(name, 0) or 0)

        goal_type = None
        goal_frequency = None
        goal_amount_minor = None

        # Don't carry budget goal metadata onto retired categories.
        if is_active:
            if amount_minor > 0:
                goal_type = "recurring"
                goal_frequency = "monthly"
                goal_amount_minor = amount_minor
            elif goal_minor > 0:
                goal_type = "recurring"
                goal_frequency = "yearly"
                goal_amount_minor = goal_minor

        categories_out[name] = AspireCategoryMapping(
            dojo_name=name,
            group_name="Migrated",
            is_active=is_active,
            goal_type=goal_type,
            goal_amount_minor=goal_amount_minor,
            goal_target_date=None,
            goal_frequency=goal_frequency,
        )

    return AspireMapping(accounts=accounts_out, categories=categories_out)


def _validate_mapping_is_complete(
    *,
    mapping: AspireMapping,
    accounts: list[str],
    categories: list[str],
) -> None:
    missing_accounts = [name for name in accounts if name not in mapping.accounts]
    missing_categories = [name for name in categories if name not in mapping.categories]

    if missing_accounts or missing_categories:
        parts: list[str] = []
        if missing_accounts:
            parts.append(f"missing {len(missing_accounts)} account mappings")
        if missing_categories:
            parts.append(f"missing {len(missing_categories)} category mappings")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=", ".join(parts))


@router.get("/onboarding/aspire/mapping/candidates", response_model=MappingCandidatesResponse)
def mapping_candidates(
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
) -> MappingCandidatesResponse:
    mode, _status_value, migration_session_id = _read_onboarding_row(conn)
    if mode != "aspire" or not migration_session_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active Aspire migration session")

    (
        migration_session_id,
        _mapping_status,
        _mapping_json,
        cfg_accounts,
        cfg_cards,
        hidden_accounts,
        hidden_categories,
        categories_minus_credit_cards,
        _net_worth_assets,
        _net_worth_debts,
        net_worth_categories,
        _user_def_amounts_minor,
        _user_def_goals_minor,
        _special_labels,
    ) = _get_extracted_aspire_session(conn)

    accounts, categories = _fetch_mapping_candidates(
        conn,
        migration_session_id=migration_session_id,
        cfg_accounts=cfg_accounts,
        cfg_cards=cfg_cards,
        hidden_accounts=hidden_accounts,
        hidden_categories=hidden_categories,
        categories_minus_credit_cards=categories_minus_credit_cards,
        net_worth_categories=net_worth_categories,
    )
    return MappingCandidatesResponse(accounts=accounts, categories=categories)


def _get_extracted_aspire_session(
    conn: duckdb.DuckDBPyConnection,
) -> tuple[
    str,
    str,
    str | None,
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
    dict[str, int],
    dict[str, int],
    dict[str, str],
]:
    mode, _status_value, migration_session_id = _read_onboarding_row(conn)
    if mode != "aspire" or not migration_session_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active Aspire migration session")

    row = conn.execute(
        """
        SELECT extraction_status,
               mapping_status,
               mapping_json,
               cfg_accounts_json,
               cfg_cards_json,
               hidden_accounts_json,
               hidden_categories_json,
               categories_minus_credit_cards_json,
               net_worth_assets_json,
               net_worth_debts_json,
               net_worth_categories_json,
               user_def_amounts_minor_json,
               user_def_goals_minor_json,
               special_labels_json
        FROM aspire_migration_sessions
        WHERE migration_session_id = $id
        """,
        {"id": migration_session_id},
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No extracted dataset for this session")

    (
        extraction_status,
        mapping_status,
        mapping_json,
        cfg_accounts_json,
        cfg_cards_json,
        hidden_accounts_json,
        hidden_categories_json,
        categories_minus_credit_cards_json,
        net_worth_assets_json,
        net_worth_debts_json,
        net_worth_categories_json,
        user_def_amounts_minor_json,
        user_def_goals_minor_json,
        special_labels_json,
    ) = row

    if extraction_status != "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Extraction is not completed")

    def _parse_name_list(raw: object) -> list[str]:
        if raw is None:
            return []
        try:
            parsed = json.loads(str(raw))
        except Exception:
            return []
        if not isinstance(parsed, list):
            return []
        out: list[str] = []
        for item in parsed:
            if isinstance(item, str) and item.strip():
                out.append(item)
        return out

    cfg_accounts = _parse_name_list(cfg_accounts_json)
    cfg_cards = _parse_name_list(cfg_cards_json)
    hidden_accounts = _parse_name_list(hidden_accounts_json)
    hidden_categories = _parse_name_list(hidden_categories_json)

    categories_minus_credit_cards = _parse_name_list(categories_minus_credit_cards_json)
    net_worth_assets = _parse_name_list(net_worth_assets_json)
    net_worth_debts = _parse_name_list(net_worth_debts_json)
    net_worth_categories = _parse_name_list(net_worth_categories_json)

    def _parse_dict_str_int(raw: object) -> dict[str, int]:
        if raw is None:
            return {}
        try:
            parsed = json.loads(str(raw))
        except Exception:
            return {}
        if not isinstance(parsed, dict):
            return {}
        out: dict[str, int] = {}
        for k, v in parsed.items():
            if not isinstance(k, str) or not k.strip():
                continue
            if isinstance(v, bool):
                continue
            if isinstance(v, int):
                out[k] = v
                continue
            if isinstance(v, float) and v.is_integer():
                out[k] = int(v)
        return out

    def _parse_dict_str_str(raw: object) -> dict[str, str]:
        if raw is None:
            return {}
        try:
            parsed = json.loads(str(raw))
        except Exception:
            return {}
        if not isinstance(parsed, dict):
            return {}
        out: dict[str, str] = {}
        for k, v in parsed.items():
            if isinstance(k, str) and k.strip() and isinstance(v, str) and v.strip():
                out[k] = v
        return out

    user_def_amounts_minor = _parse_dict_str_int(user_def_amounts_minor_json)
    user_def_goals_minor = _parse_dict_str_int(user_def_goals_minor_json)
    special_labels = _parse_dict_str_str(special_labels_json)

    # Defensive cast to keep the API stable even if DB rows drift.
    mapping_status_value = str(mapping_status)
    if mapping_status_value not in {"not_started", "in_progress", "completed", "failed"}:
        mapping_status_value = "not_started"

    mapping_json_value = str(mapping_json) if mapping_json is not None else None

    return (
        migration_session_id,
        mapping_status_value,
        mapping_json_value,
        cfg_accounts,
        cfg_cards,
        hidden_accounts,
        hidden_categories,
        categories_minus_credit_cards,
        net_worth_assets,
        net_worth_debts,
        net_worth_categories,
        user_def_amounts_minor,
        user_def_goals_minor,
        special_labels,
    )


@router.get("/onboarding/aspire/mapping", response_model=GetAspireMappingResponse)
def get_aspire_mapping(
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
) -> GetAspireMappingResponse:
    (
        migration_session_id,
        mapping_status,
        mapping_json,
        cfg_accounts,
        cfg_cards,
        hidden_accounts,
        hidden_categories,
        categories_minus_credit_cards,
        net_worth_assets,
        net_worth_debts,
        net_worth_categories,
        user_def_amounts_minor,
        user_def_goals_minor,
        special_labels,
    ) = _get_extracted_aspire_session(conn)

    accounts, categories = _fetch_mapping_candidates(
        conn,
        migration_session_id=migration_session_id,
        cfg_accounts=cfg_accounts,
        cfg_cards=cfg_cards,
        hidden_accounts=hidden_accounts,
        hidden_categories=hidden_categories,
        categories_minus_credit_cards=categories_minus_credit_cards,
        net_worth_categories=net_worth_categories,
    )

    if mapping_json:
        try:
            mapping = AspireMapping.model_validate(json.loads(mapping_json))
        except Exception as exc:  # pragma: no cover - defensive
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stored mapping is invalid; please re-extract and try again.",
            ) from exc
    else:
        mapping = _default_mapping_from_candidates(
            accounts=accounts,
            categories=categories,
            cfg_accounts=cfg_accounts,
            cfg_cards=cfg_cards,
            hidden_accounts=hidden_accounts,
            hidden_categories=hidden_categories,
            net_worth_assets=net_worth_assets,
            net_worth_debts=net_worth_debts,
            user_def_amounts_minor=user_def_amounts_minor,
            user_def_goals_minor=user_def_goals_minor,
        )

    from dojo.aspire_migration.schemas import MappingStatus

    return GetAspireMappingResponse(
        mapping_status=cast(MappingStatus, str(mapping_status)),
        mapping=mapping,
        aspire_hidden_accounts=hidden_accounts,
        aspire_hidden_categories=hidden_categories,
        aspire_net_worth_assets=net_worth_assets,
        aspire_net_worth_debts=net_worth_debts,
        aspire_net_worth_categories=net_worth_categories,
        aspire_special_labels=special_labels,
    )


@router.post("/onboarding/aspire/mapping", response_model=GetAspireMappingResponse)
def save_aspire_mapping(
    payload: SaveAspireMappingRequest,
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
    settings: Settings = _SETTINGS_DEP,
) -> GetAspireMappingResponse:
    (
        migration_session_id,
        _mapping_status,
        _mapping_json,
        cfg_accounts,
        cfg_cards,
        hidden_accounts,
        hidden_categories,
        categories_minus_credit_cards,
        net_worth_assets,
        net_worth_debts,
        net_worth_categories,
        user_def_amounts_minor,
        user_def_goals_minor,
        special_labels,
    ) = _get_extracted_aspire_session(conn)

    accounts, categories = _fetch_mapping_candidates(
        conn,
        migration_session_id=migration_session_id,
        cfg_accounts=cfg_accounts,
        cfg_cards=cfg_cards,
        hidden_accounts=hidden_accounts,
        hidden_categories=hidden_categories,
        categories_minus_credit_cards=categories_minus_credit_cards,
        net_worth_categories=net_worth_categories,
    )

    if payload.complete and not settings.aspire_migration_allow_partial_mapping:
        _validate_mapping_is_complete(mapping=payload.mapping, accounts=accounts, categories=categories)

    mapping_status: str = "completed" if payload.complete else "in_progress"
    mapping_json = json.dumps(payload.mapping.model_dump(), separators=(",", ":"), sort_keys=True)

    conn.execute("BEGIN")
    try:
        conn.execute(
            """
            UPDATE aspire_migration_sessions
            SET mapping_status = $status,
                mapping_json = $mapping_json,
                updated_at = CURRENT_TIMESTAMP
            WHERE migration_session_id = $id
            """,
            {"id": migration_session_id, "status": mapping_status, "mapping_json": mapping_json},
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    from dojo.aspire_migration.schemas import MappingStatus

    return GetAspireMappingResponse(
        mapping_status=cast(MappingStatus, mapping_status),
        mapping=payload.mapping,
        aspire_hidden_accounts=hidden_accounts,
        aspire_hidden_categories=hidden_categories,
        aspire_net_worth_assets=net_worth_assets,
        aspire_net_worth_debts=net_worth_debts,
        aspire_net_worth_categories=net_worth_categories,
        aspire_special_labels=special_labels,
    )


@router.get("/onboarding/aspire/net-worth", response_model=GetNetWorthDecisionsResponse)
def get_net_worth_decisions(
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
) -> GetNetWorthDecisionsResponse:
    (
        migration_session_id,
        _mapping_status,
        _mapping_json,
        _cfg_accounts,
        _cfg_cards,
        _hidden_accounts,
        _hidden_categories,
        _categories_minus_credit_cards,
        _net_worth_assets,
        _net_worth_debts,
        _net_worth_categories,
        _user_def_amounts_minor,
        _user_def_goals_minor,
        _special_labels,
    ) = _get_extracted_aspire_session(conn)

    row = conn.execute(
        "SELECT net_worth_decisions_json FROM aspire_migration_sessions WHERE migration_session_id = $id",
        {"id": migration_session_id},
    ).fetchone()
    if row is None:
        return GetNetWorthDecisionsResponse(decisions={})

    raw = row[0]
    if not raw:
        return GetNetWorthDecisionsResponse(decisions={})

    decisions: dict[str, NetWorthDecision] = {}
    try:
        parsed = json.loads(str(raw))
        if isinstance(parsed, dict):
            for name, payload in parsed.items():
                if isinstance(name, str) and name.strip():
                    decisions[name] = NetWorthDecision.model_validate(payload)
    except Exception:
        return GetNetWorthDecisionsResponse(decisions={})

    return GetNetWorthDecisionsResponse(decisions=decisions)


@router.post("/onboarding/aspire/net-worth")
def save_net_worth_decisions(
    payload: SaveNetWorthDecisionsRequest,
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
    settings: Settings = _SETTINGS_DEP,
) -> dict[str, str]:
    """Persist net worth migration decisions."""
    (
        migration_session_id,
        _mapping_status,
        _mapping_json,
        _cfg_accounts,
        _cfg_cards,
        _hidden_accounts,
        _hidden_categories,
        _categories_minus_credit_cards,
        _net_worth_assets,
        _net_worth_debts,
        _net_worth_categories,
        _user_def_amounts_minor,
        _user_def_goals_minor,
        _special_labels,
    ) = _get_extracted_aspire_session(conn)

    net_worth_accounts = set(_net_worth_assets) | set(_net_worth_debts)

    # Normally we require a decision for every net worth entity.
    # For dev/testing, allow saving partial decisions so the wizard can advance.
    if not settings.aspire_migration_allow_partial_mapping:
        for account_name in net_worth_accounts:
            if account_name not in payload.decisions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing decision for net worth account: {account_name}",
                )

    # Validate only the provided decisions.
    for account_name, decision in payload.decisions.items():
        if account_name not in net_worth_accounts:
            continue

        # Validate based on treatment type
        if decision.treatment == "derive_from_ledger" and not decision.config.budget_account_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Treatment 'derive_from_ledger' requires budget_account_id for: {account_name}",
            )
        elif decision.treatment == "tracking_snapshots" and not decision.config.acknowledge_drift:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Treatment 'tracking_snapshots' requires acknowledge_drift for: {account_name}",
            )
        elif decision.treatment == "handoff":
            if not decision.config.destinations:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Treatment 'handoff' requires at least one destination for: {account_name}",
                )
        elif decision.treatment == "linked_budget" and not decision.config.linked_category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Treatment 'linked_budget' requires linked_category_id for: {account_name}",
            )

    # Persist decisions
    decisions_json = json.dumps(
        {k: v.model_dump() for k, v in payload.decisions.items()},
        separators=(",", ":"),
        sort_keys=True,
    )

    conn.execute("BEGIN")
    try:
        conn.execute(
            """
            UPDATE aspire_migration_sessions
            SET net_worth_decisions_json = $decisions,
                updated_at = CURRENT_TIMESTAMP
            WHERE migration_session_id = $id
            """,
            {"id": migration_session_id, "decisions": decisions_json},
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    return {"status": "saved"}


_ASPIRE_IMPORT_NAMESPACE = uuid.UUID("e9a92b04-bfc7-4eaa-b6bd-75f0a8c8f1d6")


def _slugify_id(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", (value or "").lower())
    return normalized.strip("_") or "item"


def _prefixed_id(prefix: str, name: str) -> str:
    return f"{prefix}{_slugify_id(name)}"


def _import_concept_id(dataset_fingerprint: str, kind: str, key: str) -> uuid.UUID:
    # Deterministic IDs are critical for safe retries.
    return uuid.uuid5(_ASPIRE_IMPORT_NAMESPACE, f"aspire:{dataset_fingerprint}:{kind}:{key}")


def _parse_saved_pairs(raw: object) -> list[tuple[int, int]]:
    if raw is None:
        return []
    try:
        parsed = json.loads(str(raw))
    except Exception:
        return []
    if not isinstance(parsed, dict):
        return []
    pairs = parsed.get("pairs", [])
    if not isinstance(pairs, list):
        return []
    out: list[tuple[int, int]] = []
    for item in pairs:
        if isinstance(item, (list, tuple)) and len(item) == 2 and isinstance(item[0], int) and isinstance(item[1], int):
            out.append((item[0], item[1]))
    return out


def _category_id_for_aspire_label(
    *,
    category_name: str,
    special_labels: dict[str, str],
    mapping: AspireMapping,
    category_ids: dict[str, str],
) -> str:
    if category_name == special_labels.get("v_AtoB"):
        return TransactionEntryService.AVAILABLE_TO_BUDGET_CATEGORY_ID
    if category_name == special_labels.get("v_StartingBalance"):
        return "opening_balance"
    if category_name == special_labels.get("v_BalanceAdjustment"):
        return "balance_adjustment"
    if category_name == special_labels.get("v_AccountTransfer"):
        return TransactionEntryService.TRANSFER_CATEGORY_ID

    if category_name not in mapping.categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown Aspire category in staging: {category_name}"
        )

    return category_ids[category_name]


@router.post("/onboarding/aspire/apply", response_model=ApplyAspireMigrationResponse)
def apply_aspire_migration(
    payload: ApplyAspireMigrationRequest,
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
    system_date: date = _SYSTEM_DATE_DEP,
    settings: Settings = _SETTINGS_DEP,
    transaction_service: TransactionEntryService = _TRANSACTION_SERVICE_DEP,
    account_admin_service: AccountAdminService = _ACCOUNT_ADMIN_SERVICE_DEP,
    category_admin_service: BudgetCategoryAdminService = _CATEGORY_ADMIN_SERVICE_DEP,
) -> ApplyAspireMigrationResponse:
    (
        migration_session_id,
        mapping_status,
        mapping_json,
        _cfg_accounts,
        _cfg_cards,
        _hidden_accounts,
        _hidden_categories,
        _categories_minus_credit_cards,
        _net_worth_assets,
        _net_worth_debts,
        _net_worth_categories,
        _user_def_amounts_minor,
        _user_def_goals_minor,
        special_labels,
    ) = _get_extracted_aspire_session(conn)

    row = conn.execute(
        """
        SELECT dataset_fingerprint, import_status, net_worth_decisions_json
        FROM aspire_migration_sessions
        WHERE migration_session_id = $id
        """,
        {"id": migration_session_id},
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No Aspire migration session")

    dataset_fingerprint, import_status, net_worth_decisions_json = row
    dataset_fingerprint_value = str(dataset_fingerprint)

    import_status_value = str(import_status) if import_status is not None else "not_started"
    if import_status_value == "completed" and not payload.force:
        return ApplyAspireMigrationResponse(import_status="completed")

    if mapping_status != "completed" or not mapping_json:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mapping must be completed first")

    try:
        mapping = AspireMapping.model_validate(json.loads(mapping_json))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stored mapping is invalid; re-open mapping and re-save.",
        ) from exc

    # Load net worth decisions
    net_worth_decisions: dict[str, NetWorthDecision] = {}
    if net_worth_decisions_json:
        try:
            decisions_raw = json.loads(str(net_worth_decisions_json))
            for name, decision_data in decisions_raw.items():
                net_worth_decisions[name] = NetWorthDecision.model_validate(decision_data)
        except Exception:
            pass  # Will validate below

    # Validate net worth decisions unless partial mapping is enabled.
    net_worth_accounts = set(_net_worth_assets) | set(_net_worth_debts)
    if not settings.aspire_migration_allow_partial_mapping:
        for account_name in net_worth_accounts:
            if account_name not in net_worth_decisions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Net worth decision required for: {account_name}. Please complete the net worth step.",
                )

    conn.execute(
        """
        UPDATE aspire_migration_sessions
        SET import_status = 'in_progress', updated_at = CURRENT_TIMESTAMP
        WHERE migration_session_id = $id
        """,
        {"id": migration_session_id},
    )

    accounts_created = 0
    groups_created = 0
    categories_created = 0
    transactions_imported = 0
    transfers_imported = 0

    try:
        account_ids: dict[str, str] = {}
        seen_account_ids: dict[str, str] = {}
        for aspire_name, account_mapping in mapping.accounts.items():
            account_id = _prefixed_id("aspire_", account_mapping.dojo_name)
            other = seen_account_ids.get(account_id)
            if other is not None and other != aspire_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Duplicate account name: '{account_mapping.dojo_name}' (from '{other}' and '{aspire_name}'). Rename one in the mapping.",
                )
            seen_account_ids[account_id] = aspire_name
            account_ids[aspire_name] = account_id

        group_ids: dict[str, str] = {}
        for category_mapping in mapping.categories.values():
            group_ids.setdefault(
                category_mapping.group_name, _prefixed_id("aspire_group_", category_mapping.group_name)
            )

        category_ids: dict[str, str] = {}
        seen_category_ids: dict[str, str] = {}
        for aspire_name, category_mapping in mapping.categories.items():
            category_id = _prefixed_id("aspire_cat_", category_mapping.dojo_name)
            other = seen_category_ids.get(category_id)
            if other is not None and other != aspire_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Duplicate category name: '{category_mapping.dojo_name}' (from '{other}' and '{aspire_name}'). Rename one in the mapping.",
                )
            seen_category_ids[category_id] = aspire_name
            category_ids[aspire_name] = category_id

        # Create accounts and categories active during import; apply "retired" flags after.
        for aspire_name, account_mapping in mapping.accounts.items():
            account_id = account_ids[aspire_name]
            account_type = "liability" if account_mapping.account_class in {"credit", "loan"} else "asset"
            try:
                account_admin_service.create_account(
                    conn,
                    AccountCreateRequest(
                        account_id=account_id,
                        name=account_mapping.dojo_name,
                        account_type=account_type,
                        account_class=account_mapping.account_class,
                        account_role=account_mapping.account_role,
                        current_balance_minor=0,
                        currency="USD",
                        opened_on=None,
                        is_active=True,
                        institution_name=None,
                    ),
                )
                accounts_created += 1
            except AccountAlreadyExistsError:
                conn.execute(
                    "UPDATE accounts SET is_active = TRUE, updated_at = CURRENT_TIMESTAMP WHERE account_id = $id",
                    {"id": account_id},
                )

        # Handle net worth accounts based on decisions
        for aspire_name in net_worth_accounts:
            decision = net_worth_decisions.get(aspire_name)
            if not decision or not decision.treatment:
                continue

            is_debt = aspire_name in _net_worth_debts
            account_type = "liability" if is_debt else "asset"

            if decision.treatment == "derive_from_ledger":
                # Map to budget account - no new account created
                if decision.config.budget_account_id:
                    account_ids[aspire_name] = decision.config.budget_account_id

            elif decision.treatment == "tracking_snapshots":
                # Create as tracking account for snapshots
                account_id = _prefixed_id("aspire_nw_", aspire_name)
                try:
                    account_admin_service.create_account(
                        conn,
                        AccountCreateRequest(
                            account_id=account_id,
                            name=aspire_name,
                            account_type=account_type,
                            account_class="investment" if not is_debt else "loan",
                            account_role="tracking",
                            current_balance_minor=0,
                            currency="USD",
                            opened_on=None,
                            is_active=True,
                            institution_name=None,
                        ),
                    )
                    accounts_created += 1
                    account_ids[aspire_name] = account_id
                    # TODO: Import snapshots as balance adjustments
                except AccountAlreadyExistsError:
                    conn.execute(
                        "UPDATE accounts SET is_active = TRUE, updated_at = CURRENT_TIMESTAMP WHERE account_id = $id",
                        {"id": account_id},
                    )
                    account_ids[aspire_name] = account_id

            elif decision.treatment == "handoff":
                # Create placeholder account for historical snapshots
                handoff_id = _prefixed_id("aspire_handoff_", aspire_name)
                try:
                    account_admin_service.create_account(
                        conn,
                        AccountCreateRequest(
                            account_id=handoff_id,
                            name=f"{aspire_name} (Historical)",
                            account_type=account_type,
                            account_class="investment",
                            account_role="tracking",
                            current_balance_minor=0,
                            currency="USD",
                            opened_on=None,
                            is_active=True,
                            institution_name=None,
                        ),
                    )
                    accounts_created += 1
                    # TODO: Import snapshots up to cutover date

                    # Create destination accounts
                    for dest in decision.config.destinations:
                        dest_id = _prefixed_id("aspire_dest_", dest.name)
                        try:
                            account_admin_service.create_account(
                                conn,
                                AccountCreateRequest(
                                    account_id=dest_id,
                                    name=dest.name,
                                    account_type=dest.account_type
                                    or ("liability" if dest.account_class in {"credit", "loan"} else "asset"),
                                    account_class=dest.account_class,
                                    account_role=dest.account_role,
                                    current_balance_minor=0,
                                    currency=dest.currency,
                                    opened_on=dest.opened_on,
                                    is_active=True,
                                    institution_name=dest.institution_name,
                                    interest_rate_apy=dest.interest_rate_apy,
                                    card_type=dest.card_type,
                                    apr=dest.apr,
                                    cash_advance_apr=dest.cash_advance_apr,
                                    term_end_date=dest.term_end_date,
                                    early_withdrawal_penalty=dest.early_withdrawal_penalty,
                                    risk_free_sweep_rate=dest.risk_free_sweep_rate,
                                    is_self_directed=dest.is_self_directed,
                                    tax_classification=dest.tax_classification,
                                    initial_principal_minor=dest.initial_principal_minor,
                                    mortgage_escrow_details=dest.mortgage_escrow_details,
                                    asset_name=dest.asset_name,
                                    acquisition_cost_minor=dest.acquisition_cost_minor,
                                ),
                            )
                            accounts_created += 1

                            # Optional opening balance (mirrors the Accounts page wizard).
                            if dest.opening_balance_minor is not None and int(dest.opening_balance_minor) != 0:
                                dest_account_type = dest.account_type or (
                                    "liability" if dest.account_class in {"credit", "loan"} else "asset"
                                )
                                signed_amount = (
                                    -int(dest.opening_balance_minor)
                                    if dest_account_type == "liability"
                                    else int(dest.opening_balance_minor)
                                )
                                balance_date = dest.opening_balance_date or system_date

                                concept_id = _import_concept_id(
                                    dataset_fingerprint_value,
                                    "opening_balance",
                                    f"handoff:{aspire_name}:{dest_id}",
                                )
                                transaction_service.create(
                                    conn,
                                    NewTransactionRequest(
                                        concept_id=concept_id,
                                        transaction_date=balance_date,
                                        account_id=dest_id,
                                        category_id="opening_balance",
                                        amount_minor=signed_amount,
                                        memo="Opening balance",
                                        status="cleared",
                                    ),
                                    current_date=balance_date,
                                )

                        except AccountAlreadyExistsError:
                            conn.execute(
                                "UPDATE accounts SET is_active = TRUE, updated_at = CURRENT_TIMESTAMP WHERE account_id = $id",
                                {"id": dest_id},
                            )
                    # TODO: Transfer balance at cutover
                except AccountAlreadyExistsError:
                    pass

            elif decision.treatment == "linked_budget":
                # Create tracking account linked to budget category
                account_id = _prefixed_id("aspire_nw_", aspire_name)
                try:
                    account_admin_service.create_account(
                        conn,
                        AccountCreateRequest(
                            account_id=account_id,
                            name=aspire_name,
                            account_type=account_type,
                            account_class="loan" if is_debt else "investment",
                            account_role="tracking",
                            current_balance_minor=0,
                            currency="USD",
                            opened_on=None,
                            is_active=True,
                            institution_name=None,
                        ),
                    )
                    accounts_created += 1
                    account_ids[aspire_name] = account_id
                    # TODO: Link to budget category and import snapshots for reconciliation
                except AccountAlreadyExistsError:
                    conn.execute(
                        "UPDATE accounts SET is_active = TRUE, updated_at = CURRENT_TIMESTAMP WHERE account_id = $id",
                        {"id": account_id},
                    )
                    account_ids[aspire_name] = account_id

        for group_name, group_id in group_ids.items():
            try:
                category_admin_service.create_group(
                    conn,
                    BudgetCategoryGroupCreateRequest(group_id=group_id, name=group_name, sort_order=0, is_active=True),
                )
                groups_created += 1
            except GroupAlreadyExistsError:
                pass

        for aspire_name, category_mapping in mapping.categories.items():
            category_id = category_ids[aspire_name]
            group_id = group_ids.get(category_mapping.group_name)
            try:
                category_admin_service.create_category(
                    conn,
                    BudgetCategoryCreateRequest(
                        category_id=category_id,
                        name=category_mapping.dojo_name,
                        group_id=group_id,
                        is_active=True,
                        goal_type=category_mapping.goal_type,
                        goal_amount_minor=category_mapping.goal_amount_minor,
                        goal_target_date=category_mapping.goal_target_date,
                        goal_frequency=category_mapping.goal_frequency,
                    ),
                )
                categories_created += 1
            except CategoryAlreadyExistsError:
                conn.execute(
                    "UPDATE budget_categories SET is_active = TRUE, updated_at = CURRENT_TIMESTAMP WHERE category_id = $id",
                    {"id": category_id},
                )

        transfer_label = special_labels.get("v_AccountTransfer")

        rows = conn.execute(
            """
            SELECT row_index, transaction_date, amount_minor, category_name, account_name, memo, status
            FROM aspire_staging_transactions
            WHERE migration_session_id = $id
            ORDER BY transaction_date NULLS LAST, row_index
            """,
            {"id": migration_session_id},
        ).fetchall()

        for row_index, trx_date, amount_minor, category_name, account_name, memo, status_text in rows:
            idx = int(row_index)
            if category_name is None or str(category_name).strip() == "":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Staging transaction missing category"
                )
            if account_name is None or str(account_name).strip() == "":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Staging transaction missing account"
                )
            if trx_date is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Staging transaction missing date")

            category_name_value = str(category_name)

            aspire_account_name = str(account_name)
            if aspire_account_name not in account_ids:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown Aspire account in staging")

            account_id = account_ids[aspire_account_name]
            category_id = _category_id_for_aspire_label(
                category_name=category_name_value,
                special_labels=special_labels,
                mapping=mapping,
                category_ids=category_ids,
            )

            status_raw = str(status_text or "").strip().lower()
            status_value = "pending" if status_raw in {"p", "pending"} else "cleared"

            concept_id = _import_concept_id(dataset_fingerprint_value, "transaction", str(idx))
            transaction_service.create(
                conn,
                NewTransactionRequest(
                    concept_id=concept_id,
                    transaction_date=trx_date,
                    account_id=account_id,
                    category_id=category_id,
                    amount_minor=int(amount_minor),
                    memo=str(memo) if memo is not None else None,
                    status=status_value,
                ),
                current_date=trx_date,
            )
            transactions_imported += 1

        # Apply "retired" flags after importing history.
        for aspire_name, account_mapping in mapping.accounts.items():
            if not account_mapping.is_active:
                account_admin_service.deactivate_account(conn, account_ids[aspire_name])

        for aspire_name, category_mapping in mapping.categories.items():
            if not category_mapping.is_active:
                category_admin_service.deactivate_category(conn, category_ids[aspire_name])

        conn.execute(
            """
            UPDATE aspire_migration_sessions
            SET import_status = 'completed', imported_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE migration_session_id = $id
            """,
            {"id": migration_session_id},
        )

        # Mark onboarding complete once import succeeds.
        _write_onboarding_row(
            conn,
            onboarding_mode="aspire",
            onboarding_status="completed",
            migration_session_id=migration_session_id,
        )

    except HTTPException:
        conn.execute(
            """
            UPDATE aspire_migration_sessions
            SET import_status = 'failed', updated_at = CURRENT_TIMESTAMP
            WHERE migration_session_id = $id
            """,
            {"id": migration_session_id},
        )
        raise
    except Exception as exc:
        conn.execute(
            """
            UPDATE aspire_migration_sessions
            SET import_status = 'failed', updated_at = CURRENT_TIMESTAMP
            WHERE migration_session_id = $id
            """,
            {"id": migration_session_id},
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Import failed") from exc

    return ApplyAspireMigrationResponse(
        import_status="completed",
        accounts_created=accounts_created,
        category_groups_created=groups_created,
        categories_created=categories_created,
        transactions_imported=transactions_imported,
    )


def _iter_month_starts(first_month: date, last_month: date) -> list[date]:
    if first_month > last_month:
        return []
    out: list[date] = []
    cur = first_month.replace(day=1)
    end = last_month.replace(day=1)
    while cur <= end:
        out.append(cur)
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)
    return out


@router.get("/onboarding/aspire/parity/budget", response_model=AspireBudgetParityResponse)
def budget_parity(
    month: date | None = Query(default=None, description="Month start (YYYY-MM-01). Defaults to Aspire v_Today month."),
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
    system_date: date = _SYSTEM_DATE_DEP,
) -> AspireBudgetParityResponse:
    (
        migration_session_id,
        mapping_status,
        mapping_json,
        _cfg_accounts,
        _cfg_cards,
        _hidden_accounts,
        _hidden_categories,
        _categories_minus_credit_cards,
        _net_worth_assets,
        _net_worth_debts,
        _net_worth_categories,
        _user_def_amounts_minor,
        _user_def_goals_minor,
        special_labels,
    ) = _get_extracted_aspire_session(conn)

    row = conn.execute(
        "SELECT dataset_fingerprint, import_status FROM aspire_migration_sessions WHERE migration_session_id = $id",
        {"id": migration_session_id},
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No Aspire migration session")

    dataset_fingerprint, import_status = row
    _ = str(dataset_fingerprint)
    import_status_value = str(import_status) if import_status is not None else "not_started"
    if import_status_value != "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Import must be completed first")

    if mapping_status != "completed" or not mapping_json:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mapping must be completed first")

    try:
        mapping = AspireMapping.model_validate(json.loads(mapping_json))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Stored mapping is invalid") from exc

    # Default month: Aspire's v_Today when present, otherwise the system date.
    month_start = (month or system_date).replace(day=1)
    v_today = special_labels.get("v_Today")
    if month is None and v_today:
        try:
            month_start = date.fromisoformat(v_today).replace(day=1)
        except ValueError:
            pass

    # Build deterministic Dojo category ids (must match apply).
    category_ids: dict[str, str] = {}
    for aspire_name, category_mapping in mapping.categories.items():
        category_ids[aspire_name] = _prefixed_id("aspire_cat_", category_mapping.dojo_name)

    # Find min event month for carry-forward availability.
    min_row = conn.execute(
        """
        SELECT
          LEAST(
            COALESCE(MIN(t.transaction_date), DATE '9999-12-31'),
            COALESCE(MIN(a.allocation_date), DATE '9999-12-31')
          ) AS min_date
        FROM aspire_migration_sessions s
        LEFT JOIN aspire_staging_transactions t ON t.migration_session_id = s.migration_session_id
        LEFT JOIN aspire_staging_allocations a ON a.migration_session_id = s.migration_session_id
        WHERE s.migration_session_id = $id
        """,
        {"id": migration_session_id},
    ).fetchone()

    min_date = min_row[0] if min_row else None
    if min_date is None or min_date == date(9999, 12, 31):
        first_month = month_start
    else:
        first_month = cast(date, min_date).replace(day=1)

    months = _iter_month_starts(first_month, month_start)

    # Aggregate staging transactions by month/category.
    trx_rows = conn.execute(
        """
        SELECT DATE_TRUNC('month', transaction_date)::DATE AS month_start,
               category_name,
               SUM(amount_minor) AS amount_minor_sum
        FROM aspire_staging_transactions
        WHERE migration_session_id = $id AND transaction_date IS NOT NULL
        GROUP BY 1, 2
        """,
        {"id": migration_session_id},
    ).fetchall()

    trx_sum: dict[tuple[str, date], int] = {}
    for m_start, cat_name, amount_sum in trx_rows:
        if cat_name is None:
            continue
        name = str(cat_name)
        if name not in category_ids:
            continue
        trx_sum[(name, cast(date, m_start))] = int(amount_sum or 0)

    # Aggregate staging allocations by month/from/to.
    alloc_rows = conn.execute(
        """
        SELECT DATE_TRUNC('month', allocation_date)::DATE AS month_start,
               from_category_name,
               to_category_name,
               SUM(amount_minor) AS amount_minor_sum
        FROM aspire_staging_allocations
        WHERE migration_session_id = $id AND allocation_date IS NOT NULL
        GROUP BY 1, 2, 3
        """,
        {"id": migration_session_id},
    ).fetchall()

    rta_label = special_labels.get("v_AtoB")
    alloc_available_delta: dict[tuple[str, date], int] = {}
    alloc_allocated_delta: dict[tuple[str, date], int] = {}

    def _bump(bucket: dict[tuple[str, date], int], key: tuple[str, date], delta: int) -> None:
        bucket[key] = int(bucket.get(key, 0)) + int(delta)

    for m_start, from_name, to_name, amount_sum in alloc_rows:
        if to_name is None:
            continue
        to_value = str(to_name)
        m_value = cast(date, m_start)
        amount = int(amount_sum or 0)

        # Destination always gets allocation.
        if to_value in category_ids:
            _bump(alloc_available_delta, (to_value, m_value), amount)
            _bump(alloc_allocated_delta, (to_value, m_value), amount)

        # Source category is decremented unless it is Ready-to-Assign.
        if from_name is None:
            continue
        from_value = str(from_name)
        if rta_label and from_value == rta_label:
            continue
        if from_value in category_ids:
            _bump(alloc_available_delta, (from_value, m_value), -amount)
            _bump(alloc_allocated_delta, (from_value, m_value), -amount)

    # Seed/ensure actual monthly rows exist so missing rows are treated as carry-forward.
    BudgetingDAO(conn).ensure_all_category_month_states(month_start)

    actual_rows = conn.execute(
        """
        SELECT category_id, allocated_minor, activity_minor, available_minor
        FROM budget_category_monthly_state
        WHERE month_start = $month
        """,
        {"month": month_start},
    ).fetchall()
    actual_by_id: dict[str, tuple[int, int, int]] = {}
    for cid, allocated_minor, activity_minor, available_minor in actual_rows:
        actual_by_id[str(cid)] = (int(allocated_minor), int(activity_minor), int(available_minor))

    rows_out: list[BudgetParityRow] = []
    mismatches = 0
    max_abs = 0

    for aspire_name, dojo_category_id in sorted(category_ids.items(), key=lambda kv: kv[0].lower()):
        available = 0
        expected_allocated = 0
        expected_activity = 0

        for m in months:
            amt = int(trx_sum.get((aspire_name, m), 0))
            alloc_av = int(alloc_available_delta.get((aspire_name, m), 0))
            alloc_al = int(alloc_allocated_delta.get((aspire_name, m), 0))

            if m == month_start:
                expected_activity = -amt
                expected_allocated = alloc_al

            available += amt + alloc_av

        actual_alloc, actual_act, actual_avail = actual_by_id.get(dojo_category_id, (0, 0, 0))
        diff_alloc = actual_alloc - expected_allocated
        diff_act = actual_act - expected_activity
        diff_avail = actual_avail - available

        row = BudgetParityRow(
            aspire_category_name=aspire_name,
            dojo_category_id=dojo_category_id,
            expected_allocated_minor=expected_allocated,
            actual_allocated_minor=actual_alloc,
            diff_allocated_minor=diff_alloc,
            expected_activity_minor=expected_activity,
            actual_activity_minor=actual_act,
            diff_activity_minor=diff_act,
            expected_available_minor=available,
            actual_available_minor=actual_avail,
            diff_available_minor=diff_avail,
        )
        rows_out.append(row)

        if diff_alloc or diff_act or diff_avail:
            mismatches += 1
            max_abs = max(max_abs, abs(diff_alloc), abs(diff_act), abs(diff_avail))

    return AspireBudgetParityResponse(
        month_start=month_start,
        mismatches=mismatches,
        max_abs_diff_minor=max_abs,
        rows=rows_out,
    )


@router.post("/onboarding/aspire/extract", response_model=ExtractAspireResponse)
def extract_aspire(
    payload: ExtractAspireRequest,
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
    oauth_store: GoogleOAuthStore = _OAUTH_STORE_DEP,
    sheets_factory: Callable[[Any], GoogleSheetsClient] = _SHEETS_FACTORY_DEP,
    store: AspireExtractionStore = _EXTRACTION_STORE_DEP,
) -> ExtractAspireResponse:
    # Ensure we have an Aspire session id.
    mode, status_value, migration_session_id = _read_onboarding_row(conn)
    if mode != "aspire" or status_value != "in_progress" or not migration_session_id:
        migration_session_id = str(uuid.uuid4())
        _write_onboarding_row(
            conn,
            onboarding_mode="aspire",
            onboarding_status="in_progress",
            migration_session_id=migration_session_id,
        )

    if not payload.force:
        # Prefer DB-backed extraction state so the flow resumes across refreshes.
        in_db = conn.execute(
            "SELECT 1 FROM aspire_migration_sessions WHERE migration_session_id = $id",
            {"id": migration_session_id},
        ).fetchone()
        if in_db is not None:
            return get_extraction_summary(conn=conn, store=store)

        # Temporary fallback for sessions created before staging was implemented.
        existing = store.get_summary(migration_session_id)
        if existing is not None:
            return ExtractAspireResponse(
                migration_session_id=existing.migration_session_id,
                dataset_fingerprint=existing.dataset_fingerprint,
                transactions_count=existing.transactions_count,
                transactions_date_min=existing.transactions_date_min,
                transactions_date_max=existing.transactions_date_max,
                allocations_count=existing.allocations_count,
                allocations_date_min=existing.allocations_date_min,
                allocations_date_max=existing.allocations_date_max,
                net_worth_snapshots_count=existing.net_worth_snapshots_count,
                net_worth_date_min=existing.net_worth_date_min,
                net_worth_date_max=existing.net_worth_date_max,
            )

    try:
        spreadsheet_id = parse_spreadsheet_id(payload.spreadsheet)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        credentials = oauth_store.get_credentials()
    except GoogleOAuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        client = sheets_factory(credentials)
        metadata = client.get_spreadsheet_metadata(spreadsheet_id=spreadsheet_id)
    except (GoogleSheetsAuthError, GoogleSheetsApiError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read spreadsheet metadata. Reconnect Google and double-check the spreadsheet id.",
        )

    named_ranges = metadata.get("namedRanges") or []
    names: set[str] = set()
    for r in named_ranges:
        if isinstance(r, dict):
            name = r.get("name")
            if isinstance(name, str):
                names.add(name)

    missing = sorted([name for name in required_named_ranges() if name not in names])
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Spreadsheet is missing required Aspire named ranges: {', '.join(missing)}",
        )

    try:
        extracted = extract_aspire_rows(
            client,
            spreadsheet_id=spreadsheet_id,
            available_named_ranges=names,
        )
    except AspireExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    dataset = extracted.dataset

    summary = ExtractedAspireSummary(
        migration_session_id=migration_session_id,
        dataset_fingerprint=dataset.dataset_fingerprint,
        transactions_count=dataset.transactions_count,
        transactions_date_min=dataset.transactions_date_min,
        transactions_date_max=dataset.transactions_date_max,
        allocations_count=dataset.allocations_count,
        allocations_date_min=dataset.allocations_date_min,
        allocations_date_max=dataset.allocations_date_max,
        net_worth_snapshots_count=dataset.net_worth_snapshots_count,
        net_worth_date_min=dataset.net_worth_date_min,
        net_worth_date_max=dataset.net_worth_date_max,
    )

    # Persist staging rows (resumable across browser refreshes).
    conn.execute("BEGIN")
    try:
        conn.execute(
            "DELETE FROM aspire_staging_transactions WHERE migration_session_id = $id",
            {"id": migration_session_id},
        )
        conn.execute(
            "DELETE FROM aspire_staging_allocations WHERE migration_session_id = $id",
            {"id": migration_session_id},
        )
        conn.execute(
            "DELETE FROM aspire_staging_net_worth_snapshots WHERE migration_session_id = $id",
            {"id": migration_session_id},
        )

        conn.execute(
            "DELETE FROM aspire_migration_sessions WHERE migration_session_id = $id",
            {"id": migration_session_id},
        )
        conn.execute(
            """
            INSERT INTO aspire_migration_sessions (
                migration_session_id,
                spreadsheet_id,
                spreadsheet_title,
                dataset_fingerprint,
                cfg_accounts_json,
                cfg_cards_json,
                hidden_accounts_json,
                hidden_categories_json,
                categories_minus_credit_cards_json,
                net_worth_assets_json,
                net_worth_debts_json,
                net_worth_categories_json,
                user_def_amounts_minor_json,
                user_def_goals_minor_json,
                special_labels_json,
                extraction_status,
                extracted_at,
                mapping_status,
                mapping_json,
                import_status,
                imported_at,
                verification_status,
                verification_summary_json,
                created_at,
                updated_at
            )
            VALUES (
                $id,
                $spreadsheet_id,
                $spreadsheet_title,
                $fingerprint,
                $cfg_accounts_json,
                $cfg_cards_json,
                $hidden_accounts_json,
                $hidden_categories_json,
                $categories_minus_credit_cards_json,
                $net_worth_assets_json,
                $net_worth_debts_json,
                $net_worth_categories_json,
                $user_def_amounts_minor_json,
                $user_def_goals_minor_json,
                $special_labels_json,
                'completed',
                CURRENT_TIMESTAMP,
                'not_started',
                NULL,
                'not_started',
                NULL,
                'not_started',
                NULL,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            """,
            {
                "id": migration_session_id,
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_title": (metadata.get("properties", {}) or {}).get("title"),
                "fingerprint": dataset.dataset_fingerprint,
                "cfg_accounts_json": json.dumps(extracted.cfg_accounts, separators=(",", ":"), ensure_ascii=True),
                "cfg_cards_json": json.dumps(extracted.cfg_cards, separators=(",", ":"), ensure_ascii=True),
                "hidden_accounts_json": json.dumps(extracted.hidden_accounts, separators=(",", ":"), ensure_ascii=True),
                "hidden_categories_json": json.dumps(
                    extracted.hidden_categories, separators=(",", ":"), ensure_ascii=True
                ),
                "categories_minus_credit_cards_json": json.dumps(
                    extracted.categories_minus_credit_cards, separators=(",", ":"), ensure_ascii=True
                ),
                "net_worth_assets_json": json.dumps(
                    extracted.net_worth_assets, separators=(",", ":"), ensure_ascii=True
                ),
                "net_worth_debts_json": json.dumps(extracted.net_worth_debts, separators=(",", ":"), ensure_ascii=True),
                "net_worth_categories_json": json.dumps(
                    extracted.net_worth_categories, separators=(",", ":"), ensure_ascii=True
                ),
                "user_def_amounts_minor_json": json.dumps(
                    extracted.user_def_amounts_minor, separators=(",", ":"), sort_keys=True, ensure_ascii=True
                ),
                "user_def_goals_minor_json": json.dumps(
                    extracted.user_def_goals_minor, separators=(",", ":"), sort_keys=True, ensure_ascii=True
                ),
                "special_labels_json": json.dumps(
                    extracted.special_labels, separators=(",", ":"), sort_keys=True, ensure_ascii=True
                ),
            },
        )

        for row in extracted.transactions:
            conn.execute(
                """
                INSERT INTO aspire_staging_transactions (
                    migration_session_id,
                    row_index,
                    transaction_date,
                    outflow_minor,
                    inflow_minor,
                    amount_minor,
                    category_name,
                    account_name,
                    memo,
                    status
                )
                VALUES (
                    $id,
                    $row_index,
                    $date,
                    $outflow_minor,
                    $inflow_minor,
                    $amount_minor,
                    $category_name,
                    $account_name,
                    $memo,
                    $status
                )
                """,
                {
                    "id": migration_session_id,
                    "row_index": row.row_index,
                    "date": row.transaction_date,
                    "outflow_minor": row.outflow_minor,
                    "inflow_minor": row.inflow_minor,
                    "amount_minor": row.amount_minor,
                    "category_name": row.category_name,
                    "account_name": row.account_name,
                    "memo": row.memo,
                    "status": row.status,
                },
            )

        for row in extracted.allocations:
            conn.execute(
                """
                INSERT INTO aspire_staging_allocations (
                    migration_session_id,
                    row_index,
                    allocation_date,
                    amount_minor,
                    from_category_name,
                    to_category_name
                )
                VALUES ($id, $row_index, $date, $amount_minor, $from_category_name, $to_category_name)
                """,
                {
                    "id": migration_session_id,
                    "row_index": row.row_index,
                    "date": row.allocation_date,
                    "amount_minor": row.amount_minor,
                    "from_category_name": row.from_category_name,
                    "to_category_name": row.to_category_name,
                },
            )

        for row in extracted.net_worth_snapshots:
            conn.execute(
                """
                INSERT INTO aspire_staging_net_worth_snapshots (
                    migration_session_id,
                    row_index,
                    snapshot_date,
                    amount_minor,
                    category_name,
                    note,
                    breakpoint
                )
                VALUES ($id, $row_index, $date, $amount_minor, $category_name, $note, $breakpoint)
                """,
                {
                    "id": migration_session_id,
                    "row_index": row.row_index,
                    "date": row.snapshot_date,
                    "amount_minor": row.amount_minor,
                    "category_name": row.category_name,
                    "note": row.note,
                    "breakpoint": row.breakpoint,
                },
            )

        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    store.put_summary(summary)

    return ExtractAspireResponse(
        migration_session_id=summary.migration_session_id,
        dataset_fingerprint=summary.dataset_fingerprint,
        transactions_count=summary.transactions_count,
        transactions_date_min=summary.transactions_date_min,
        transactions_date_max=summary.transactions_date_max,
        allocations_count=summary.allocations_count,
        allocations_date_min=summary.allocations_date_min,
        allocations_date_max=summary.allocations_date_max,
        net_worth_snapshots_count=summary.net_worth_snapshots_count,
        net_worth_date_min=summary.net_worth_date_min,
        net_worth_date_max=summary.net_worth_date_max,
    )
