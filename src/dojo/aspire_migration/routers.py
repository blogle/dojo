"""API routers for onboarding + Aspire migration wizard.

Privacy:
- Never log raw extracted values or OAuth credentials.
- Return only what the UI needs for trust/validation.
"""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any, cast

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
import logging
from urllib.parse import urlparse, urlunparse

from dojo.aspire.gsheets_client import GoogleSheetsApiError, GoogleSheetsAuthError, GoogleSheetsClient
from dojo.aspire_migration.extract import AspireExtractionError, extract_aspire_rows, required_named_ranges
from dojo.aspire_migration.google_oauth import GoogleOAuthError, GoogleOAuthStore
from dojo.aspire_migration.normalize import normalize_label
from dojo.aspire_migration.pairing import TransferLeg, pair_transfer_legs
from dojo.aspire_migration.schemas import (
    ApplyAspireMigrationRequest,
    ApplyAspireMigrationResponse,
    CancelOnboardingResponse,
    ExtractAspireRequest,
    ExtractAspireResponse,
    GetAspireMappingResponse,
    GetAspireTransfersResponse,
    GetNetWorthDecisionsResponse,
    GoogleOAuthStartResponse,
    GoogleOAuthStatusResponse,
    MigrationPreviewResponse,
    OnboardingStatusResponse,
    SaveAspireMappingRequest,
    SaveNetWorthDecisionsRequest,
    SaveTransferResolutionsRequest,
    StartOnboardingRequest,
    VerifyAspireSheetRequest,
    VerifyAspireSheetResponse,
    AspireBudgetMapping,
    AspireAccountMapping,
    AspireCategoryMapping,
    AspireTransferExceptionRow,
    TransferResolutionKind,
    NetWorthDecision,
    BudgetParityResponse,
    BudgetParityRow,
    SeriesPoint,
)
from dojo.aspire_migration.sheets import parse_spreadsheet_id
from dojo.core.cache_rebuild import rebuild_caches
from dojo.investments.sql import load_sql as load_investments_sql
from dojo.budgeting.sql import load_sql as load_budgeting_sql
from dojo.budgeting.services import derive_payment_category_id
from dojo.aspire_migration.legacy_marks import LegacyMark, aspire_bucket_series
from dojo.core.clock import get_system_date
from dojo.core.config import Settings, get_settings
from dojo.core.db import connection_dep


router = APIRouter(tags=["onboarding"])

_PRIMARY_ID = "primary"
_CONNECTION_DEP = Depends(connection_dep)
_SETTINGS_DEP = Depends(get_settings)
_SYSTEM_DATE_DEP = Depends(get_system_date)


def _oauth_store_dep(request: Request) -> GoogleOAuthStore:
    store = getattr(request.app.state, "google_oauth_store", None)
    if not isinstance(store, GoogleOAuthStore):  # pragma: no cover
        raise RuntimeError("GoogleOAuthStore not configured on app.state")
    return store


_OAUTH_STORE_DEP = Depends(_oauth_store_dep)


def _sheets_client_factory_dep(request: Request) -> Callable[[Any], GoogleSheetsClient]:
    factory = getattr(request.app.state, "sheets_client_factory", None)
    if not callable(factory):  # pragma: no cover
        raise RuntimeError("sheets_client_factory not configured on app.state")
    return cast(Callable[[Any], GoogleSheetsClient], factory)


_SHEETS_FACTORY_DEP = Depends(_sheets_client_factory_dep)


def _now_ts() -> datetime:
    return datetime.utcnow()


_ASPIRE_IMPORT_NAMESPACE = uuid.UUID("e9a92b04-bfc7-4eaa-b6bd-75f0a8c8f1d6")
_KNOWN_BUDGET_PARITY_DIFFERENCES = ("month_rollover_overspending",)


def _uuid_for(dataset_fingerprint: str, kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(_ASPIRE_IMPORT_NAMESPACE, f"aspire:{dataset_fingerprint}:{kind}:{key}")


def _json_dumps(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True, ensure_ascii=True)


def _slugify_id(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", (value or "").lower())
    return normalized.strip("_") or "item"


def _prefixed_id(prefix: str, name: str) -> str:
    return f"{prefix}{_slugify_id(name)}"


def _json_loads_list(raw: object) -> list[str]:
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


def _json_loads_dict_str_str(raw: object) -> dict[str, str]:
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


def _json_loads_dict_str_int(raw: object) -> dict[str, int]:
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
        try:
            out[k] = int(v)
        except Exception:
            continue
    return out


def _json_loads_list_obj(raw: object) -> list[object]:
    if raw is None:
        return []
    try:
        parsed = json.loads(str(raw))
    except Exception:
        return []
    if not isinstance(parsed, list):
        return []
    return list(parsed)


def _json_loads_dict_str_obj(raw: object) -> dict[str, object]:
    if raw is None:
        return {}
    try:
        parsed = json.loads(str(raw))
    except Exception:
        return {}
    if not isinstance(parsed, dict):
        return {}
    out: dict[str, object] = {}
    for k, v in parsed.items():
        if not isinstance(k, str) or not k.strip():
            continue
        out[k] = v
    return out


def _json_loads_dict_int_obj(raw: object) -> dict[int, object]:
    if raw is None:
        return {}
    try:
        parsed = json.loads(str(raw))
    except Exception:
        return {}
    if not isinstance(parsed, dict):
        return {}
    out: dict[int, object] = {}
    for k, v in parsed.items():
        try:
            idx = int(k)
        except Exception:
            continue
        out[idx] = v
    return out


def _read_onboarding_row(conn: duckdb.DuckDBPyConnection) -> tuple[str | None, str, str | None]:
    row = conn.execute(
        "SELECT onboarding_mode, onboarding_status, migration_session_id FROM onboarding_state WHERE onboarding_id = $id",
        {"id": _PRIMARY_ID},
    ).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO onboarding_state (onboarding_id, onboarding_mode, onboarding_status) VALUES ($id, NULL, 'not_started')",
            {"id": _PRIMARY_ID},
        )
        return (None, "not_started", None)
    return (row[0], row[1], row[2])


def _write_onboarding_row(
    conn: duckdb.DuckDBPyConnection,
    *,
    onboarding_mode: str | None,
    onboarding_status: str,
    migration_session_id: str | None,
) -> None:
    conn.execute("BEGIN")
    try:
        conn.execute("DELETE FROM onboarding_state WHERE onboarding_id = $id", {"id": _PRIMARY_ID})
        conn.execute(
            """
            INSERT INTO onboarding_state (
                onboarding_id,
                onboarding_mode,
                onboarding_status,
                migration_session_id,
                created_at,
                updated_at
            ) VALUES ($id, $mode, $status, $session_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
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


def _ensure_session_row(conn: duckdb.DuckDBPyConnection, migration_session_id: str) -> None:
    conn.execute(
        """
        INSERT INTO aspire_migration_sessions (migration_session_id)
        SELECT $id
        WHERE NOT EXISTS (SELECT 1 FROM aspire_migration_sessions WHERE migration_session_id = $id)
        """,
        {"id": migration_session_id},
    )


def _purge_abandoned_sessions(conn: duckdb.DuckDBPyConnection, *, ttl_days: int) -> None:
    if ttl_days <= 0:
        return
    cutoff = datetime.utcnow() - timedelta(days=ttl_days)

    old_ids = [
        str(r[0])
        for r in conn.execute(
            """
            SELECT migration_session_id
            FROM aspire_migration_sessions
            WHERE import_status != 'completed' AND updated_at < $cutoff
            """,
            {"cutoff": cutoff},
        ).fetchall()
    ]
    if not old_ids:
        return

    for session_id in old_ids:
        conn.execute("DELETE FROM aspire_staging_transactions WHERE migration_session_id = $id", {"id": session_id})
        conn.execute("DELETE FROM aspire_staging_allocations WHERE migration_session_id = $id", {"id": session_id})
        conn.execute("DELETE FROM aspire_staging_net_worth_marks WHERE migration_session_id = $id", {"id": session_id})
        conn.execute("DELETE FROM aspire_migration_sessions WHERE migration_session_id = $id", {"id": session_id})


@router.get("/onboarding/status", response_model=OnboardingStatusResponse)
def get_onboarding_status(
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
    settings: Settings = _SETTINGS_DEP,
) -> OnboardingStatusResponse:
    mode, status_value, migration_session_id = _read_onboarding_row(conn)

    # Only force onboarding on a fresh ledger by default. This keeps existing
    # datasets (including fixtures/tests) from being gated by the onboarding
    # state table.
    row = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()
    accounts_count = int(row[0] or 0) if row else 0

    row = conn.execute("SELECT COUNT(*) FROM transactions WHERE is_active = TRUE").fetchone()
    trx_count = int(row[0] or 0) if row else 0
    is_fresh_ledger = accounts_count == 0 and trx_count == 0

    should_onboard = False
    if status_value == "in_progress":
        should_onboard = True
    elif status_value != "completed":
        should_onboard = is_fresh_ledger
    onboarding_mode: str | None = mode if mode in {"manual", "aspire"} else None
    onboarding_status: str = (
        status_value if status_value in {"not_started", "in_progress", "completed"} else "not_started"
    )

    return OnboardingStatusResponse(
        onboarding_mode=cast(Any, onboarding_mode),
        onboarding_status=cast(Any, onboarding_status),
        migration_session_id=str(migration_session_id) if migration_session_id else None,
        should_onboard=should_onboard,
        aspire_migration_allow_partial_mapping=settings.aspire_migration_allow_partial_mapping,
    )


@router.post("/onboarding/start", response_model=OnboardingStatusResponse)
def start_onboarding(
    payload: StartOnboardingRequest,
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
    settings: Settings = _SETTINGS_DEP,
) -> OnboardingStatusResponse:
    status_value = "completed" if payload.onboarding_mode == "manual" else "in_progress"

    existing_mode, existing_status, existing_session_id = _read_onboarding_row(conn)
    migration_session_id: str | None = None
    if payload.onboarding_mode == "aspire":
        if existing_mode == "aspire" and existing_status == "in_progress" and existing_session_id:
            migration_session_id = str(existing_session_id)
        else:
            migration_session_id = str(uuid.uuid4())

    if migration_session_id:
        _ensure_session_row(conn, migration_session_id)

    _write_onboarding_row(
        conn,
        onboarding_mode=payload.onboarding_mode,
        onboarding_status=status_value,
        migration_session_id=migration_session_id,
    )
    return get_onboarding_status(conn=conn, settings=settings)


@router.post("/onboarding/cancel", response_model=CancelOnboardingResponse)
def cancel_onboarding(conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP) -> CancelOnboardingResponse:
    _write_onboarding_row(conn, onboarding_mode=None, onboarding_status="not_started", migration_session_id=None)
    return CancelOnboardingResponse(ok=True)


def _oauth_exception_to_http(exc: GoogleOAuthError) -> HTTPException:
    message = str(exc)
    status_code = status.HTTP_400_BAD_REQUEST
    if message.startswith("Google OAuth client libraries are unavailable"):
        status_code = status.HTTP_501_NOT_IMPLEMENTED
    return HTTPException(status_code=status_code, detail=message)


def _effective_oauth_redirect_uri(request: Request, settings: Settings) -> str:
    if settings.google_oauth_redirect_uri:
        return settings.google_oauth_redirect_uri

    uri = str(request.url_for("google_oauth_callback"))
    parsed = urlparse(uri)
    # Prefer localhost over 127.0.0.1 for dev convenience; this tends to match
    # OAuth console config and avoids subtle hostname mismatches.
    if parsed.hostname == "127.0.0.1":
        netloc = "localhost"
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        parsed = parsed._replace(netloc=netloc)
        uri = urlunparse(parsed)
    return uri


@router.get("/onboarding/google-oauth/status", response_model=GoogleOAuthStatusResponse)
def google_oauth_status(store: GoogleOAuthStore = _OAUTH_STORE_DEP) -> GoogleOAuthStatusResponse:
    oauth_status = store.status()
    return GoogleOAuthStatusResponse(connected=oauth_status.connected, expires_at_s=oauth_status.expires_at_s)


@router.get("/onboarding/google-oauth/start", response_model=GoogleOAuthStartResponse)
def google_oauth_start(
    request: Request,
    origin: str | None = Query(default=None, description="Frontend origin for post-auth redirect"),
    settings: Settings = _SETTINGS_DEP,
    store: GoogleOAuthStore = _OAUTH_STORE_DEP,
) -> GoogleOAuthStartResponse:
    redirect_uri = _effective_oauth_redirect_uri(request, settings)
    frontend_origin = origin or request.headers.get("origin") or request.headers.get("referer")
    try:
        url = store.start(settings, redirect_uri=redirect_uri, frontend_origin=frontend_origin)
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
    def _redirect_base_for(state_value: str | None) -> str:
        origin = store.pending_frontend_origin(state_value) if state_value else None
        if origin:
            return f"{origin.rstrip('/')}/#/onboarding"
        return "/#/onboarding"

    redirect_base = _redirect_base_for(state)
    if error or not code or not state:
        return RedirectResponse(url=f"{redirect_base}?google=error", status_code=status.HTTP_302_FOUND)

    redirect_uri = _effective_oauth_redirect_uri(request, settings)
    try:
        origin = store.finish(settings, code=code, state=state, redirect_uri=redirect_uri)
    except GoogleOAuthError as exc:
        reason = "error"
        message = str(exc)
        if message.startswith("OAuth state is missing"):
            reason = "state"
        elif message.startswith("oauth_token_exchange_failed:"):
            reason = message.split(":", 1)[1] or "token"
        elif message.startswith("oauth_token_exchange_failed"):
            reason = "token"

        logger.info("Google OAuth callback failed: %s", message)
        return RedirectResponse(url=f"{redirect_base}?google=error&reason={reason}", status_code=status.HTTP_302_FOUND)

    if origin:
        redirect_base = f"{origin.rstrip('/')}/#/onboarding"
    return RedirectResponse(url=f"{redirect_base}?google=connected", status_code=status.HTTP_302_FOUND)


@router.post("/onboarding/google-oauth/disconnect", status_code=status.HTTP_204_NO_CONTENT)
def google_oauth_disconnect(store: GoogleOAuthStore = _OAUTH_STORE_DEP) -> None:
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


def _require_active_session(conn: duckdb.DuckDBPyConnection) -> str:
    mode, status_value, session_id = _read_onboarding_row(conn)
    if mode != "aspire" or status_value != "in_progress" or not session_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active Aspire migration session")
    return str(session_id)


@router.post("/onboarding/aspire/extract", response_model=ExtractAspireResponse)
def extract_aspire(
    payload: ExtractAspireRequest,
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
    settings: Settings = _SETTINGS_DEP,
    store: GoogleOAuthStore = _OAUTH_STORE_DEP,
    sheets_factory: Callable[[Any], GoogleSheetsClient] = _SHEETS_FACTORY_DEP,
) -> ExtractAspireResponse:
    migration_session_id = _require_active_session(conn)
    _purge_abandoned_sessions(conn, ttl_days=settings.aspire_migration_session_ttl_days)
    _ensure_session_row(conn, migration_session_id)

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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to read spreadsheet") from exc

    named_ranges = metadata.get("namedRanges") or []
    names = {r.get("name") for r in named_ranges if isinstance(r, dict)}
    names.discard(None)

    try:
        extracted = extract_aspire_rows(
            client, spreadsheet_id=spreadsheet_id, available_named_ranges=cast(set[str], names)
        )
    except AspireExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    # Map Aspire symbols to Dojo statuses and break markers.
    approved = extracted.status_symbols.get("v_ApprovedSymbol")
    pending = extracted.status_symbols.get("v_PendingSymbol")
    brk = extracted.status_symbols.get("v_BreakSymbol")

    def _dojo_status(raw: str | None) -> tuple[str | None, bool]:
        if raw is None:
            return ("cleared", False)
        if brk and raw == brk:
            return (None, True)
        if pending and raw == pending:
            return ("pending", False)
        if approved and raw == approved:
            return ("cleared", False)
        # Fall back to cleared when unknown.
        return ("cleared", False)

    # Persist session + staging rows.
    conn.execute("BEGIN")
    try:
        conn.execute(
            """
            UPDATE aspire_migration_sessions
            SET
                extraction_status = 'completed',
                spreadsheet_id = $spreadsheet_id,
                dataset_fingerprint = $fingerprint,
                extracted_at = CURRENT_TIMESTAMP,
                special_labels_json = $special,
                status_symbols_json = $symbols,
                user_def_amounts_json = $user_def_amounts,
                user_def_goals_json = $user_def_goals,
                category_type_symbols_json = $category_type_symbols,
                configuration_rows_json = $configuration_rows,
                dashboard_category_proxy_json = $dashboard_proxy,
                cfg_accounts_json = $cfg_accounts,
                cfg_cards_json = $cfg_cards,
                hidden_accounts_json = $hidden_accounts,
                hidden_categories_json = $hidden_categories,
                categories_minus_credit_cards_json = $categories_minus_cards,
                net_worth_assets_json = $nw_assets,
                net_worth_debts_json = $nw_debts,
                net_worth_categories_json = $nw_cats,
                distinct_ntw_categories_json = $distinct_marks,
                updated_at = CURRENT_TIMESTAMP
            WHERE migration_session_id = $id
            """,
            {
                "id": migration_session_id,
                "spreadsheet_id": spreadsheet_id,
                "fingerprint": extracted.dataset.dataset_fingerprint,
                "special": _json_dumps(extracted.special_labels),
                "symbols": _json_dumps(extracted.status_symbols),
                "user_def_amounts": _json_dumps(extracted.user_def_amounts_minor),
                "user_def_goals": _json_dumps(extracted.user_def_goals_minor),
                "category_type_symbols": _json_dumps(extracted.category_type_symbols),
                "configuration_rows": _json_dumps(
                    [
                        {
                            "row_type_symbol": row.row_type_symbol,
                            "name": row.name,
                            "monthly_target_minor": row.monthly_target_minor,
                            "due_date": row.due_date.isoformat() if row.due_date else None,
                            "goal_amount_minor": row.goal_amount_minor,
                        }
                        for row in extracted.configuration_rows
                    ]
                ),
                "dashboard_proxy": _json_dumps(
                    {
                        name: {
                            "configured_budget_minor": row.configured_budget_minor,
                            "budgeted_minor": row.budgeted_minor,
                            "activity_minor": row.activity_minor,
                            "available_minor": row.available_minor,
                        }
                        for name, row in extracted.dashboard_category_proxy.items()
                    }
                ),
                "cfg_accounts": _json_dumps(extracted.cfg_accounts),
                "cfg_cards": _json_dumps(extracted.cfg_cards),
                "hidden_accounts": _json_dumps(extracted.hidden_accounts),
                "hidden_categories": _json_dumps(extracted.hidden_categories),
                "categories_minus_cards": _json_dumps(extracted.categories_minus_credit_cards),
                "nw_assets": _json_dumps(extracted.net_worth_assets),
                "nw_debts": _json_dumps(extracted.net_worth_debts),
                "nw_cats": _json_dumps(extracted.net_worth_categories),
                "distinct_marks": _json_dumps(
                    sorted({m.category_name for m in extracted.net_worth_marks if m.category_name})
                ),
            },
        )

        conn.execute(
            "DELETE FROM aspire_staging_transactions WHERE migration_session_id = $id", {"id": migration_session_id}
        )
        conn.execute(
            "DELETE FROM aspire_staging_allocations WHERE migration_session_id = $id", {"id": migration_session_id}
        )
        conn.execute(
            "DELETE FROM aspire_staging_net_worth_marks WHERE migration_session_id = $id", {"id": migration_session_id}
        )

        trx_rows: list[dict[str, object]] = []
        for t in extracted.transactions:
            status_value, is_break = _dojo_status(t.status_raw)
            trx_rows.append(
                {
                    "migration_session_id": migration_session_id,
                    "row_index": t.row_index,
                    "transaction_date": t.transaction_date,
                    "amount_minor": int(t.amount_minor),
                    "category_name": t.category_name,
                    "account_name": t.account_name,
                    "memo": t.memo,
                    "status_raw": t.status_raw,
                    "status": status_value,
                    "is_break": bool(is_break),
                }
            )
        if trx_rows:
            conn.executemany(
                """
                INSERT INTO aspire_staging_transactions (
                    migration_session_id, row_index, transaction_date, amount_minor,
                    category_name, account_name, memo, status_raw, status, is_break
                ) VALUES (
                    $migration_session_id, $row_index, $transaction_date, $amount_minor,
                    $category_name, $account_name, $memo, $status_raw, $status, $is_break
                )
                """,
                trx_rows,
            )

        alloc_rows: list[dict[str, object]] = []
        for a in extracted.allocations:
            alloc_rows.append(
                {
                    "migration_session_id": migration_session_id,
                    "row_index": a.row_index,
                    "allocation_date": a.allocation_date,
                    "amount_minor": int(a.amount_minor),
                    "from_category_name": a.from_category_name,
                    "to_category_name": a.to_category_name,
                }
            )
        if alloc_rows:
            conn.executemany(
                """
                INSERT INTO aspire_staging_allocations (
                    migration_session_id, row_index, allocation_date, amount_minor,
                    from_category_name, to_category_name
                ) VALUES (
                    $migration_session_id, $row_index, $allocation_date, $amount_minor,
                    $from_category_name, $to_category_name
                )
                """,
                alloc_rows,
            )

        mark_rows: list[dict[str, object]] = []
        for m in extracted.net_worth_marks:
            mark_rows.append(
                {
                    "migration_session_id": migration_session_id,
                    "row_index": m.row_index,
                    "mark_date": m.mark_date,
                    "amount_minor": int(m.amount_minor),
                    "category_name": m.category_name,
                    "note": m.note,
                    "breakpoint": m.breakpoint,
                }
            )
        if mark_rows:
            conn.executemany(
                """
                INSERT INTO aspire_staging_net_worth_marks (
                    migration_session_id, row_index, mark_date, amount_minor,
                    category_name, note, breakpoint
                ) VALUES (
                    $migration_session_id, $row_index, $mark_date, $amount_minor,
                    $category_name, $note, $breakpoint
                )
                """,
                mark_rows,
            )

        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    ds = extracted.dataset
    return ExtractAspireResponse(
        migration_session_id=migration_session_id,
        dataset_fingerprint=ds.dataset_fingerprint,
        transactions_count=ds.transactions_count,
        transactions_date_min=ds.transactions_date_min,
        transactions_date_max=ds.transactions_date_max,
        allocations_count=ds.allocations_count,
        allocations_date_min=ds.allocations_date_min,
        allocations_date_max=ds.allocations_date_max,
        net_worth_marks_count=ds.net_worth_marks_count,
        net_worth_date_min=ds.net_worth_date_min,
        net_worth_date_max=ds.net_worth_date_max,
    )


def _get_extracted_session(conn: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    migration_session_id = _require_active_session(conn)
    row = conn.execute(
        """
        SELECT
            extraction_status,
            dataset_fingerprint,
            mapping_status,
            mapping_json,
            transfer_resolutions_json,
            net_worth_decisions_json,
            special_labels_json,
            status_symbols_json,
            user_def_amounts_json,
            user_def_goals_json,
            category_type_symbols_json,
            configuration_rows_json,
            dashboard_category_proxy_json,
            cfg_accounts_json,
            cfg_cards_json,
            hidden_accounts_json,
            hidden_categories_json,
            categories_minus_credit_cards_json,
            net_worth_assets_json,
            net_worth_debts_json,
            net_worth_categories_json,
            distinct_ntw_categories_json,
            import_status
        FROM aspire_migration_sessions
        WHERE migration_session_id = $id
        """,
        {"id": migration_session_id},
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Migration session not found")

    (
        extraction_status,
        dataset_fingerprint,
        mapping_status,
        mapping_json,
        transfer_resolutions_json,
        net_worth_decisions_json,
        special_labels_json,
        status_symbols_json,
        user_def_amounts_json,
        user_def_goals_json,
        category_type_symbols_json,
        configuration_rows_json,
        dashboard_category_proxy_json,
        cfg_accounts_json,
        cfg_cards_json,
        hidden_accounts_json,
        hidden_categories_json,
        categories_minus_credit_cards_json,
        net_worth_assets_json,
        net_worth_debts_json,
        net_worth_categories_json,
        distinct_ntw_categories_json,
        import_status,
    ) = row

    if str(extraction_status) != "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Extraction is not completed")

    return {
        "migration_session_id": migration_session_id,
        "dataset_fingerprint": str(dataset_fingerprint) if dataset_fingerprint else "",
        "mapping_status": str(mapping_status) if mapping_status else "not_started",
        "mapping_json": str(mapping_json) if mapping_json else None,
        "transfer_resolutions_json": str(transfer_resolutions_json) if transfer_resolutions_json else None,
        "net_worth_decisions_json": str(net_worth_decisions_json) if net_worth_decisions_json else None,
        "special_labels": _json_loads_dict_str_str(special_labels_json),
        "status_symbols": _json_loads_dict_str_str(status_symbols_json),
        "user_def_amounts_minor": _json_loads_dict_str_int(user_def_amounts_json),
        "user_def_goals_minor": _json_loads_dict_str_int(user_def_goals_json),
        "category_type_symbols": _json_loads_dict_str_str(category_type_symbols_json),
        "configuration_rows": _json_loads_list_obj(configuration_rows_json),
        "dashboard_category_proxy": _json_loads_dict_str_obj(dashboard_category_proxy_json),
        "cfg_accounts": _json_loads_list(cfg_accounts_json),
        "cfg_cards": _json_loads_list(cfg_cards_json),
        "hidden_accounts": _json_loads_list(hidden_accounts_json),
        "hidden_categories": _json_loads_list(hidden_categories_json),
        "categories_minus_credit_cards": _json_loads_list(categories_minus_credit_cards_json),
        "net_worth_assets": _json_loads_list(net_worth_assets_json),
        "net_worth_debts": _json_loads_list(net_worth_debts_json),
        "net_worth_categories": _json_loads_list(net_worth_categories_json),
        "distinct_marks_categories": _json_loads_list(distinct_ntw_categories_json),
        "import_status": str(import_status) if import_status else "not_started",
    }


def _mapping_candidates(conn: duckdb.DuckDBPyConnection, migration_session_id: str) -> tuple[list[str], list[str]]:
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

    # Categories: prefer the backend-derived list (matches Aspire UI) if present.
    categories_rows = conn.execute(
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
    categories = [str(r[0]) for r in categories_rows]

    return (sorted(set(trx_accounts)), categories)


def _staging_categories(conn: duckdb.DuckDBPyConnection, migration_session_id: str) -> list[str]:
    categories_rows = conn.execute(
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
    return [str(r[0]) for r in categories_rows]


def _configuration_categories(session: dict[str, Any]) -> list[dict[str, Any]]:
    symbols = session.get("category_type_symbols") or {}
    group_symbol = symbols.get("v_CategoryGroupSymbol")
    debt_symbol = symbols.get("v_DebtAccountSymbol")
    reportable_symbol = symbols.get("v_ReportableCategorySymbol")
    non_reportable_symbol = symbols.get("v_NonReportableCategorySymbol")

    rows = session.get("configuration_rows")
    if not isinstance(rows, list):
        return []

    current_group = "Uncategorized"
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue

        row_type = str(row.get("row_type_symbol") or "").strip() or None
        name = str(row.get("name") or "").strip() or None
        if not name:
            continue

        monthly_target_minor = 0
        try:
            monthly_target_minor = int(row.get("monthly_target_minor") or 0)
        except Exception:
            monthly_target_minor = 0

        goal_amount_minor = 0
        try:
            goal_amount_minor = int(row.get("goal_amount_minor") or 0)
        except Exception:
            goal_amount_minor = 0

        due_date: date | None = None
        due_raw = row.get("due_date")
        if isinstance(due_raw, str) and due_raw.strip():
            try:
                due_date = date.fromisoformat(due_raw)
            except ValueError:
                due_date = None

        if group_symbol and row_type == group_symbol:
            current_group = name
            continue

        if debt_symbol and row_type == debt_symbol:
            continue

        # Only treat explicit reportable/non-reportable rows as categories when symbols exist.
        if (reportable_symbol or non_reportable_symbol) and row_type not in {reportable_symbol, non_reportable_symbol}:
            continue

        out.append(
            {
                "name": name,
                "group_name": current_group,
                "monthly_target_minor": monthly_target_minor,
                "due_date": due_date,
                "goal_amount_minor": goal_amount_minor,
            }
        )

    return out


def _goal_config_label(cat: AspireCategoryMapping) -> str:
    if cat.goal_type == "target_date" and cat.goal_target_date:
        return f"Target date ({cat.goal_target_date.isoformat()})"
    if cat.goal_type == "recurring" and cat.goal_frequency and cat.goal_amount_minor is not None:
        return f"Recurring ({cat.goal_frequency})"
    return "-"


def _default_mapping(
    *,
    accounts: list[str],
    categories: list[str],
    cfg_cards: set[str],
    hidden_accounts: set[str],
    hidden_categories: set[str],
) -> AspireBudgetMapping:
    accounts_out: dict[str, AspireAccountMapping] = {}
    for name in accounts:
        account_class: Any = "credit" if name in cfg_cards else "cash"
        accounts_out[name] = AspireAccountMapping(
            dojo_name=name,
            account_class=account_class,
            account_role="on_budget",
            is_active=name not in hidden_accounts,
        )

    categories_out: dict[str, AspireCategoryMapping] = {}
    for name in categories:
        categories_out[name] = AspireCategoryMapping(
            dojo_name=name,
            group_name="Migrated",
            is_active=name not in hidden_categories,
        )

    return AspireBudgetMapping(accounts=accounts_out, categories=categories_out)


def _default_mapping_from_configuration(
    *,
    accounts: list[str],
    cfg_cards: set[str],
    hidden_accounts: set[str],
    hidden_categories: set[str],
    configuration_categories: list[dict[str, Any]],
    extra_historical_categories: list[str],
) -> AspireBudgetMapping:
    accounts_out: dict[str, AspireAccountMapping] = {}
    for name in accounts:
        account_class: Any = "credit" if name in cfg_cards else "cash"
        accounts_out[name] = AspireAccountMapping(
            dojo_name=name,
            account_class=account_class,
            account_role="on_budget",
            is_active=name not in hidden_accounts,
        )

    categories_out: dict[str, AspireCategoryMapping] = {}
    for row in configuration_categories:
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        group_name = str(row.get("group_name") or "Uncategorized").strip() or "Uncategorized"
        target_minor = int(row.get("monthly_target_minor") or 0)
        goal_minor = int(row.get("goal_amount_minor") or 0)
        due_date = row.get("due_date")
        due = due_date if isinstance(due_date, date) else None

        goal_type: Any = None
        goal_amount_minor: int | None = None
        goal_target_date: date | None = None
        goal_frequency: Any = None

        if due and goal_minor > 0 and target_minor <= 0:
            goal_type = "target_date"
            goal_amount_minor = goal_minor
            goal_target_date = due
        elif target_minor > 0:
            goal_type = "recurring"
            goal_amount_minor = target_minor
            goal_frequency = "monthly"

        categories_out[name] = AspireCategoryMapping(
            dojo_name=name,
            group_name=group_name,
            is_active=name not in hidden_categories,
            goal_type=goal_type,
            goal_amount_minor=goal_amount_minor,
            goal_target_date=goal_target_date,
            goal_frequency=goal_frequency,
        )

    for name in extra_historical_categories:
        if name in categories_out:
            continue
        categories_out[name] = AspireCategoryMapping(
            dojo_name=name,
            group_name="Historical",
            is_active=False,
        )

    return AspireBudgetMapping(accounts=accounts_out, categories=categories_out)


@router.get("/onboarding/aspire/mapping", response_model=GetAspireMappingResponse)
def get_mapping(
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
    system_date: date = _SYSTEM_DATE_DEP,
) -> GetAspireMappingResponse:
    session = _get_extracted_session(conn)
    migration_session_id = session["migration_session_id"]

    accounts, _ = _mapping_candidates(conn, migration_session_id)
    cfg_cards = set(session["cfg_cards"])
    hidden_accounts = set(session["hidden_accounts"])
    hidden_categories = set(session["hidden_categories"])

    configured = _configuration_categories(session)
    configured_names = {str(row.get("name") or "").strip() for row in configured if isinstance(row, dict)}
    configured_names.discard("")

    staging_categories = _staging_categories(conn, migration_session_id)
    special = session["special_labels"]
    excluded = {
        special.get("v_AtoB"),
        special.get("v_AccountTransfer"),
        special.get("v_StartingBalance"),
        special.get("v_BalanceAdjustment"),
    }
    excluded.discard(None)
    excluded_names = {str(v) for v in excluded if isinstance(v, str)}

    # Treat categories that match account labels as transfer-like, not envelopes.
    account_name_set = set(accounts)

    extra_historical = sorted(
        {
            name
            for name in staging_categories
            if name not in configured_names and name not in excluded_names and name not in account_name_set
        }
    )

    mapping_json = session["mapping_json"]
    if mapping_json:
        try:
            mapping = AspireBudgetMapping.model_validate(json.loads(mapping_json))
        except Exception as exc:  # pragma: no cover
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stored mapping is invalid; re-extract and try again.",
            ) from exc
    else:
        if configured:
            mapping = _default_mapping_from_configuration(
                accounts=accounts,
                cfg_cards=cfg_cards,
                hidden_accounts=hidden_accounts,
                hidden_categories=hidden_categories,
                configuration_categories=configured,
                extra_historical_categories=extra_historical,
            )
        else:
            mapping = _default_mapping(
                accounts=accounts,
                categories=staging_categories,
                cfg_cards=cfg_cards,
                hidden_accounts=hidden_accounts,
                hidden_categories=hidden_categories,
            )

    # Populate preview-only account balances (as-of v_Today inclusive).
    as_of_date = system_date
    v_today = session["special_labels"].get("v_Today")
    if v_today:
        try:
            as_of_date = date.fromisoformat(v_today)
        except ValueError:
            as_of_date = system_date

    account_balances_rows = conn.execute(
        """
        SELECT
            account_name,
            COALESCE(SUM(CASE WHEN status = 'cleared' THEN amount_minor ELSE 0 END), 0) AS settled_minor,
            COALESCE(SUM(CASE WHEN status = 'pending' THEN amount_minor ELSE 0 END), 0) AS pending_minor
        FROM aspire_staging_transactions
        WHERE migration_session_id = $id
          AND is_break = FALSE
          AND (transaction_date IS NULL OR transaction_date <= $as_of)
          AND account_name IS NOT NULL
          AND TRIM(account_name) != ''
        GROUP BY account_name
        """,
        {"id": migration_session_id, "as_of": as_of_date},
    ).fetchall()
    balances_by_account = {str(name): (int(settled), int(pending)) for name, settled, pending in account_balances_rows}

    for aspire_name, acct in mapping.accounts.items():
        settled, pending = balances_by_account.get(aspire_name, (0, 0))
        acct.current_balance_minor = settled
        acct.pending_balance_minor = pending
        if acct.account_class == "credit":
            acct.display_type = "Credit Card"
        elif acct.account_class == "cash":
            acct.display_type = "Cash"
        else:
            acct.display_type = acct.account_class

    # Populate preview-only category envelope state (all computed from staged rows).
    month_start = as_of_date.replace(day=1)
    as_of_end = as_of_date

    configured_by_category: dict[str, int] = {}
    for cfg_row in configured:
        if not isinstance(cfg_row, dict):
            continue
        name = str(cfg_row.get("name") or "").strip()
        if not name:
            continue
        try:
            configured_by_category[name] = int(cfg_row.get("monthly_target_minor") or 0)
        except Exception:
            configured_by_category[name] = 0
    for name, amount_minor in (session.get("user_def_amounts_minor") or {}).items():
        if not isinstance(name, str) or not name.strip():
            continue
        configured_by_category[name] = int(amount_minor)

    dashboard_proxy = session.get("dashboard_category_proxy") or {}

    def _proxy_value(row_obj: object, key: str) -> int | None:
        if not isinstance(row_obj, dict):
            return None
        raw = row_obj.get(key)
        if raw is None:
            return None
        try:
            return int(raw)
        except Exception:
            return None

    trx_all_rows = conn.execute(
        """
        SELECT category_name, COALESCE(SUM(amount_minor), 0) AS total_minor
        FROM aspire_staging_transactions
        WHERE migration_session_id = $id
          AND is_break = FALSE
          AND (transaction_date IS NULL OR transaction_date <= $as_of)
          AND category_name IS NOT NULL
          AND TRIM(category_name) != ''
        GROUP BY category_name
        """,
        {"id": migration_session_id, "as_of": as_of_end},
    ).fetchall()
    trx_all_by_cat = {str(name): int(total) for name, total in trx_all_rows}

    trx_month_rows = conn.execute(
        """
        SELECT category_name, COALESCE(SUM(amount_minor), 0) AS total_minor
        FROM aspire_staging_transactions
        WHERE migration_session_id = $id
          AND is_break = FALSE
          AND transaction_date BETWEEN $start AND $end
          AND category_name IS NOT NULL
          AND TRIM(category_name) != ''
        GROUP BY category_name
        """,
        {"id": migration_session_id, "start": month_start, "end": as_of_end},
    ).fetchall()
    trx_month_by_cat = {str(name): int(total) for name, total in trx_month_rows}

    alloc_all_rows = conn.execute(
        """
        SELECT to_category_name AS name, COALESCE(SUM(amount_minor), 0) AS delta_minor
        FROM aspire_staging_allocations
        WHERE migration_session_id = $id
          AND (allocation_date IS NULL OR allocation_date <= $as_of)
          AND to_category_name IS NOT NULL
          AND TRIM(to_category_name) != ''
        GROUP BY to_category_name
        UNION ALL
        SELECT from_category_name AS name, -COALESCE(SUM(amount_minor), 0) AS delta_minor
        FROM aspire_staging_allocations
        WHERE migration_session_id = $id
          AND (allocation_date IS NULL OR allocation_date <= $as_of)
          AND from_category_name IS NOT NULL
          AND TRIM(from_category_name) != ''
        GROUP BY from_category_name
        """,
        {"id": migration_session_id, "as_of": as_of_end},
    ).fetchall()
    alloc_all_by_cat: dict[str, int] = {}
    for name, delta in alloc_all_rows:
        key = str(name)
        alloc_all_by_cat[key] = int(alloc_all_by_cat.get(key, 0)) + int(delta)

    alloc_month_rows = conn.execute(
        """
        SELECT to_category_name AS name, COALESCE(SUM(amount_minor), 0) AS delta_minor
        FROM aspire_staging_allocations
        WHERE migration_session_id = $id
          AND allocation_date BETWEEN $start AND $end
          AND to_category_name IS NOT NULL
          AND TRIM(to_category_name) != ''
        GROUP BY to_category_name
        UNION ALL
        SELECT from_category_name AS name, -COALESCE(SUM(amount_minor), 0) AS delta_minor
        FROM aspire_staging_allocations
        WHERE migration_session_id = $id
          AND allocation_date BETWEEN $start AND $end
          AND from_category_name IS NOT NULL
          AND TRIM(from_category_name) != ''
        GROUP BY from_category_name
        """,
        {"id": migration_session_id, "start": month_start, "end": as_of_end},
    ).fetchall()
    alloc_month_by_cat: dict[str, int] = {}
    for name, delta in alloc_month_rows:
        key = str(name)
        alloc_month_by_cat[key] = int(alloc_month_by_cat.get(key, 0)) + int(delta)

    proxy_coverage_count = 0
    proxy_drift_count = 0
    for aspire_name, cat in mapping.categories.items():
        trx_all = int(trx_all_by_cat.get(aspire_name, 0))
        trx_month = int(trx_month_by_cat.get(aspire_name, 0))
        alloc_all = int(alloc_all_by_cat.get(aspire_name, 0))
        alloc_month = int(alloc_month_by_cat.get(aspire_name, 0))

        available_minor = trx_all + alloc_all
        cat.available_minor = available_minor
        cat.activity_minor = trx_month
        cat.budgeted_minor = alloc_month
        cat.configured_budget_minor = int(configured_by_category.get(aspire_name, 0))
        cat.config_label = _goal_config_label(cat)
        if cat.config_label == "-" and cat.configured_budget_minor:
            cat.config_label = "Recurring (monthly)"

        proxy_row = dashboard_proxy.get(aspire_name)
        proxy_configured = _proxy_value(proxy_row, "configured_budget_minor")
        proxy_budgeted = _proxy_value(proxy_row, "budgeted_minor")
        proxy_activity = _proxy_value(proxy_row, "activity_minor")
        proxy_available = _proxy_value(proxy_row, "available_minor")

        if proxy_configured is None and aspire_name in configured_by_category:
            proxy_configured = int(configured_by_category[aspire_name])

        cat.proxy_configured_budget_minor = proxy_configured
        cat.proxy_budgeted_minor = proxy_budgeted
        cat.proxy_activity_minor = proxy_activity
        cat.proxy_available_minor = proxy_available

        cat.drift_configured_budget_minor = (
            int(cat.configured_budget_minor) - int(proxy_configured) if proxy_configured is not None else None
        )
        cat.drift_budgeted_minor = int(cat.budgeted_minor) - int(proxy_budgeted) if proxy_budgeted is not None else None
        cat.drift_activity_minor = int(cat.activity_minor) - int(proxy_activity) if proxy_activity is not None else None
        cat.drift_available_minor = (
            int(cat.available_minor) - int(proxy_available) if proxy_available is not None else None
        )

        drift_values = [
            cat.drift_configured_budget_minor,
            cat.drift_budgeted_minor,
            cat.drift_activity_minor,
            cat.drift_available_minor,
        ]
        if any(value is not None for value in drift_values):
            proxy_coverage_count += 1
        if any((value is not None and value != 0) for value in drift_values):
            proxy_drift_count += 1

    return GetAspireMappingResponse(
        mapping_status=cast(Any, session["mapping_status"]),
        mapping=mapping,
        aspire_hidden_accounts=session["hidden_accounts"],
        aspire_hidden_categories=session["hidden_categories"],
        aspire_special_labels=session["special_labels"],
        aspire_status_symbols=session["status_symbols"],
        category_proxy_coverage_count=proxy_coverage_count,
        category_proxy_drift_count=proxy_drift_count,
    )


@router.post("/onboarding/aspire/mapping", response_model=GetAspireMappingResponse)
def save_mapping(
    payload: SaveAspireMappingRequest,
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
    settings: Settings = _SETTINGS_DEP,
) -> GetAspireMappingResponse:
    session = _get_extracted_session(conn)
    migration_session_id = session["migration_session_id"]

    mapping_status = "completed" if payload.complete else "in_progress"
    mapping_json = _json_dumps(payload.mapping.model_dump())

    conn.execute(
        """
        UPDATE aspire_migration_sessions
        SET mapping_status = $status,
            mapping_json = $mapping,
            updated_at = CURRENT_TIMESTAMP
        WHERE migration_session_id = $id
        """,
        {"id": migration_session_id, "status": mapping_status, "mapping": mapping_json},
    )

    return GetAspireMappingResponse(
        mapping_status=cast(Any, mapping_status),
        mapping=payload.mapping,
        aspire_hidden_accounts=session["hidden_accounts"],
        aspire_hidden_categories=session["hidden_categories"],
        aspire_special_labels=session["special_labels"],
        aspire_status_symbols=session["status_symbols"],
    )


def _compute_transfer_candidates(
    conn: duckdb.DuckDBPyConnection,
    *,
    migration_session_id: str,
    mapping: AspireBudgetMapping,
    special_labels: dict[str, str],
) -> tuple[list[tuple[int, int]], list[AspireTransferExceptionRow]]:
    transfer_label = special_labels.get("v_AccountTransfer")
    atob = special_labels.get("v_AtoB")
    starting = special_labels.get("v_StartingBalance")
    adjust = special_labels.get("v_BalanceAdjustment")

    known_accounts = set(mapping.accounts.keys())

    rows = conn.execute(
        """
        SELECT row_index, transaction_date, amount_minor, category_name, account_name, memo
        FROM aspire_staging_transactions
        WHERE migration_session_id = $id AND is_break = FALSE
        ORDER BY transaction_date NULLS LAST, row_index
        """,
        {"id": migration_session_id},
    ).fetchall()

    legs: list[TransferLeg] = []
    row_by_idx: dict[int, tuple[Any, ...]] = {}
    for row in rows:
        row_index, trx_date, amount_minor, category_name, account_name, memo = row
        if trx_date is None:
            continue
        if account_name is None or not str(account_name).strip():
            continue
        if amount_minor is None or int(amount_minor) == 0:
            continue
        cat = str(category_name) if category_name is not None else None
        if cat in {atob, starting, adjust}:
            continue
        is_candidate = False
        if transfer_label and cat == transfer_label:
            is_candidate = True
        if cat and cat in known_accounts:
            is_candidate = True
        if not is_candidate:
            continue
        leg = TransferLeg(
            row_index=int(row_index),
            transaction_date=trx_date,
            account_name=str(account_name),
            category_name=cat,
            amount_minor=int(amount_minor),
        )
        legs.append(leg)
        row_by_idx[int(row_index)] = row

    result = pair_transfer_legs(legs, tolerance_days=3, transfer_label=transfer_label)

    exceptions: list[AspireTransferExceptionRow] = []
    for idx in result.exceptions:
        row = row_by_idx.get(idx)
        if not row:
            continue
        row_index, trx_date, amount_minor, category_name, account_name, memo = row
        exceptions.append(
            AspireTransferExceptionRow(
                row_index=int(row_index),
                transaction_date=trx_date.isoformat() if trx_date else None,
                account_name=str(account_name) if account_name else None,
                category_name=str(category_name) if category_name else None,
                amount_minor=int(amount_minor),
                memo=str(memo) if memo is not None else None,
            )
        )

    return (result.pairs, exceptions)


def _validate_transfer_resolutions(
    *,
    exceptions: list[AspireTransferExceptionRow],
    resolutions: dict[int, TransferResolutionKind],
) -> dict[int, TransferResolutionKind]:
    exception_rows: dict[int, AspireTransferExceptionRow] = {int(row.row_index): row for row in exceptions}
    exception_indices = set(exception_rows.keys())

    normalized: dict[int, TransferResolutionKind] = {}
    for idx, resolution in resolutions.items():
        row_index = int(idx)
        if row_index not in exception_indices:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transfer resolution row {row_index} is not an active exception",
            )
        normalized[row_index] = resolution

    for row_index, resolution in normalized.items():
        if resolution.kind != "linked":
            continue
        linked_row_index = resolution.linked_row_index
        if linked_row_index is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Linked resolution for row {row_index} requires linked_row_index",
            )
        linked_row_index = int(linked_row_index)
        if linked_row_index == row_index:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Linked resolution for row {row_index} cannot reference itself",
            )
        if linked_row_index not in exception_indices:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Linked resolution for row {row_index} references non-exception row {linked_row_index}",
            )

        partner = normalized.get(linked_row_index)
        if partner is None or partner.kind != "linked" or int(partner.linked_row_index or -1) != row_index:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Linked resolution for row {row_index} must be mirrored by row {linked_row_index}",
            )

        current_row = exception_rows[row_index]
        partner_row = exception_rows[linked_row_index]
        if (
            current_row.account_name
            and partner_row.account_name
            and current_row.account_name == partner_row.account_name
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Linked rows {row_index} and {linked_row_index} must be in different accounts",
            )

        if int(current_row.amount_minor) != -int(partner_row.amount_minor):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Linked rows {row_index} and {linked_row_index} must have opposite signed amounts",
            )

    return normalized


def _mapping_collision_blockers(mapping: AspireBudgetMapping) -> list[str]:
    blockers: list[str] = []

    account_names: dict[str, list[str]] = {}
    for aspire_name, account in mapping.accounts.items():
        key = normalize_label(account.dojo_name)
        account_names.setdefault(key, []).append(aspire_name)
    for key, names in sorted(account_names.items()):
        if len(names) > 1:
            blockers.append(f"duplicate_mapping_collision:account:{key}")

    category_names: dict[str, list[str]] = {}
    for aspire_name, category in mapping.categories.items():
        key = normalize_label(category.dojo_name)
        category_names.setdefault(key, []).append(aspire_name)
    for key, names in sorted(category_names.items()):
        if len(names) > 1:
            blockers.append(f"duplicate_mapping_collision:category:{key}")

    return blockers


def _load_net_worth_decisions(raw: str | None) -> dict[str, NetWorthDecision]:
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}

    out: dict[str, NetWorthDecision] = {}
    for name, value in payload.items():
        if not isinstance(name, str) or not name.strip():
            continue
        try:
            out[name] = NetWorthDecision.model_validate(value)
        except Exception:
            continue
    return out


def _net_worth_classification_blockers(decisions: dict[str, NetWorthDecision]) -> list[str]:
    blockers: list[str] = []
    for name, decision in decisions.items():
        if (
            decision.decision in {"duplicate_derive_from_ledger", "track_forward"}
            and decision.classification == "unknown"
        ):
            blockers.append(f"missing_net_worth_classification:{name}")
        if decision.decision == "track_forward" and not decision.destinations:
            blockers.append(f"missing_net_worth_destinations:{name}")
    return blockers


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


def _build_preview_category_ids(
    conn: duckdb.DuckDBPyConnection,
    mapping: AspireBudgetMapping,
) -> dict[str, str]:
    category_id_by_aspire_name: dict[str, str] = {}
    used_category_ids: set[str] = set(
        r[0] for r in conn.execute("SELECT category_id FROM budget_categories").fetchall() if r and r[0] is not None
    )
    for aspire_name in sorted(mapping.categories.keys()):
        dojo_name = mapping.categories[aspire_name].dojo_name
        base = _prefixed_id("aspire_", dojo_name)
        category_id = base
        suffix = 2
        while category_id in used_category_ids:
            category_id = f"{base}_{suffix}"
            suffix += 1
        used_category_ids.add(category_id)
        category_id_by_aspire_name[aspire_name] = category_id
    return category_id_by_aspire_name


def _compute_budget_parity(
    conn: duckdb.DuckDBPyConnection,
    *,
    migration_session_id: str,
    mapping: AspireBudgetMapping,
    special_labels: dict[str, str],
    auto_pairs: list[tuple[int, int]],
    exceptions: list[AspireTransferExceptionRow],
    saved: dict[int, TransferResolutionKind],
    month_start: date,
) -> BudgetParityResponse:
    first_month_row = conn.execute(
        """
        SELECT
            LEAST(
                COALESCE(MIN(transaction_date), DATE '9999-12-31'),
                COALESCE((
                    SELECT MIN(allocation_date)
                    FROM aspire_staging_allocations
                    WHERE migration_session_id = $id
                ), DATE '9999-12-31')
            ) AS min_date
        FROM aspire_staging_transactions
        WHERE migration_session_id = $id
        """,
        {"id": migration_session_id},
    ).fetchone()
    min_date = first_month_row[0] if first_month_row else None
    first_month = (
        month_start if min_date is None or min_date == date(9999, 12, 31) else cast(date, min_date).replace(day=1)
    )
    months = _iter_month_starts(first_month, month_start)

    manual_pairs: list[tuple[int, int]] = []
    seen_manual_pairs: set[tuple[int, int]] = set()
    for idx, resolution in saved.items():
        if resolution.kind != "linked" or resolution.linked_row_index is None:
            continue
        a, b = sorted((int(idx), int(resolution.linked_row_index)))
        pair = (a, b)
        if pair in seen_manual_pairs:
            continue
        seen_manual_pairs.add(pair)
        manual_pairs.append(pair)
    paired_indices: set[int] = set()
    for a, b in [*auto_pairs, *manual_pairs]:
        paired_indices.add(int(a))
        paired_indices.add(int(b))

    exception_indices: set[int] = {int(row.row_index) for row in exceptions}

    trx_rows = conn.execute(
        """
        SELECT row_index, transaction_date, amount_minor, category_name
        FROM aspire_staging_transactions
        WHERE migration_session_id = $id
          AND transaction_date IS NOT NULL
          AND is_break = FALSE
        """,
        {"id": migration_session_id},
    ).fetchall()

    rta_label = special_labels.get("v_AtoB")
    category_names = set(mapping.categories.keys())

    trx_by_month_category: dict[tuple[date, str], int] = {}
    trx_rta_by_month: dict[date, int] = {}
    for row_index, trx_date, amount_minor, category_name in trx_rows:
        idx = int(row_index)
        if idx in paired_indices:
            continue
        if idx in exception_indices:
            resolution = saved.get(idx)
            if resolution is None:
                continue
            if resolution.kind in {"linked", "opening_balance", "balance_adjustment"}:
                continue

        if category_name is None:
            continue
        month_key = cast(date, trx_date).replace(day=1)
        cat_name = str(category_name)
        amount = int(amount_minor or 0)
        if cat_name in category_names:
            key = (month_key, cat_name)
            trx_by_month_category[key] = int(trx_by_month_category.get(key, 0)) + amount
        if rta_label and cat_name == rta_label:
            trx_rta_by_month[month_key] = int(trx_rta_by_month.get(month_key, 0)) + amount

    alloc_rows = conn.execute(
        """
        SELECT allocation_date, from_category_name, to_category_name, amount_minor
        FROM aspire_staging_allocations
        WHERE migration_session_id = $id
          AND allocation_date IS NOT NULL
        """,
        {"id": migration_session_id},
    ).fetchall()

    alloc_available_by_month_category: dict[tuple[date, str], int] = {}
    alloc_allocated_by_month_category: dict[tuple[date, str], int] = {}
    rta_alloc_delta_by_month: dict[date, int] = {}

    def _bump(bucket: dict[tuple[date, str], int], key: tuple[date, str], delta: int) -> None:
        bucket[key] = int(bucket.get(key, 0)) + int(delta)

    for alloc_date, from_name, to_name, amount_minor in alloc_rows:
        month_key = cast(date, alloc_date).replace(day=1)
        amount = int(amount_minor or 0)
        to_value = str(to_name) if to_name is not None else ""
        from_value = str(from_name) if from_name is not None else ""

        if to_value in category_names:
            _bump(alloc_available_by_month_category, (month_key, to_value), amount)
            _bump(alloc_allocated_by_month_category, (month_key, to_value), amount)
        if from_value and from_value in category_names:
            _bump(alloc_available_by_month_category, (month_key, from_value), -amount)
            if not rta_label or from_value != rta_label:
                _bump(alloc_allocated_by_month_category, (month_key, from_value), -amount)

        if rta_label:
            if to_value == rta_label:
                rta_alloc_delta_by_month[month_key] = int(rta_alloc_delta_by_month.get(month_key, 0)) + amount
            if from_value == rta_label:
                rta_alloc_delta_by_month[month_key] = int(rta_alloc_delta_by_month.get(month_key, 0)) - amount

    category_ids = _build_preview_category_ids(conn, mapping)

    rows: list[BudgetParityRow] = []
    mismatches = 0
    max_abs_diff = 0

    for aspire_name in sorted(mapping.categories.keys(), key=lambda item: item.lower()):
        available = 0
        expected_allocated = 0
        expected_activity = 0
        projected_allocated = 0
        projected_activity = 0
        projected_available = 0

        for month in months:
            trx_amount = int(trx_by_month_category.get((month, aspire_name), 0))
            alloc_available = int(alloc_available_by_month_category.get((month, aspire_name), 0))
            alloc_allocated = int(alloc_allocated_by_month_category.get((month, aspire_name), 0))

            available += trx_amount + alloc_available
            projected_available += trx_amount + alloc_available

            if month == month_start:
                expected_activity = -trx_amount
                expected_allocated = alloc_allocated
                projected_activity = -trx_amount
                projected_allocated = alloc_allocated

        diff_allocated = projected_allocated - expected_allocated
        diff_activity = projected_activity - expected_activity
        diff_available = projected_available - available

        if diff_allocated or diff_activity or diff_available:
            mismatches += 1
            max_abs_diff = max(
                max_abs_diff,
                abs(diff_allocated),
                abs(diff_activity),
                abs(diff_available),
            )

        rows.append(
            BudgetParityRow(
                category_id=category_ids[aspire_name],
                category_name=mapping.categories[aspire_name].dojo_name,
                expected_allocated_minor=expected_allocated,
                actual_allocated_minor=projected_allocated,
                diff_allocated_minor=diff_allocated,
                expected_activity_minor=expected_activity,
                actual_activity_minor=projected_activity,
                diff_activity_minor=diff_activity,
                expected_available_minor=available,
                actual_available_minor=projected_available,
                diff_available_minor=diff_available,
            )
        )

    if rta_label:
        expected_rta = 0
        actual_rta = 0
        for month in months:
            expected_rta += int(rta_alloc_delta_by_month.get(month, 0)) + int(trx_rta_by_month.get(month, 0))
            actual_rta += int(rta_alloc_delta_by_month.get(month, 0)) + int(trx_rta_by_month.get(month, 0))
        diff_rta = actual_rta - expected_rta
        if diff_rta:
            mismatches += 1
            max_abs_diff = max(max_abs_diff, abs(diff_rta))
        rows.append(
            BudgetParityRow(
                category_id="available_to_budget",
                category_name="Ready to Assign",
                expected_allocated_minor=0,
                actual_allocated_minor=0,
                diff_allocated_minor=0,
                expected_activity_minor=0,
                actual_activity_minor=0,
                diff_activity_minor=0,
                expected_available_minor=expected_rta,
                actual_available_minor=actual_rta,
                diff_available_minor=diff_rta,
            )
        )

    return BudgetParityResponse(
        month_start=month_start,
        mismatches=mismatches,
        max_abs_diff_minor=max_abs_diff,
        rows=rows,
    )


@router.get("/onboarding/aspire/transfers", response_model=GetAspireTransfersResponse)
def get_transfers(
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
) -> GetAspireTransfersResponse:
    session = _get_extracted_session(conn)
    if session["mapping_status"] != "completed" or not session["mapping_json"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Complete mapping first")

    mapping = AspireBudgetMapping.model_validate(json.loads(session["mapping_json"]))

    auto_pairs, exceptions = _compute_transfer_candidates(
        conn,
        migration_session_id=session["migration_session_id"],
        mapping=mapping,
        special_labels=session["special_labels"],
    )

    saved_raw = _json_loads_dict_int_obj(session["transfer_resolutions_json"])
    saved: dict[int, TransferResolutionKind] = {}
    for idx, payload in saved_raw.items():
        try:
            saved[idx] = TransferResolutionKind.model_validate(payload)
        except Exception:
            continue

    try:
        saved = _validate_transfer_resolutions(exceptions=exceptions, resolutions=saved)
    except HTTPException:
        saved = {}

    return GetAspireTransfersResponse(auto_pairs=auto_pairs, exceptions=exceptions, saved_resolutions=saved)


@router.post("/onboarding/aspire/transfers", status_code=status.HTTP_200_OK)
def save_transfers(
    payload: SaveTransferResolutionsRequest,
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
) -> dict[str, str]:
    session = _get_extracted_session(conn)
    if session["mapping_status"] != "completed" or not session["mapping_json"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Complete mapping first")

    mapping = AspireBudgetMapping.model_validate(json.loads(session["mapping_json"]))
    auto_pairs, exceptions = _compute_transfer_candidates(
        conn,
        migration_session_id=session["migration_session_id"],
        mapping=mapping,
        special_labels=session["special_labels"],
    )
    _ = auto_pairs

    normalized = _validate_transfer_resolutions(
        exceptions=exceptions,
        resolutions={int(k): v for k, v in payload.resolutions.items()},
    )

    migration_session_id = session["migration_session_id"]
    resolutions_json = _json_dumps({str(k): v.model_dump() for k, v in normalized.items()})
    conn.execute(
        """
        UPDATE aspire_migration_sessions
        SET transfer_resolutions_json = $resolutions, updated_at = CURRENT_TIMESTAMP
        WHERE migration_session_id = $id
        """,
        {"id": migration_session_id, "resolutions": resolutions_json},
    )
    return {"status": "saved"}


@router.get("/onboarding/aspire/net-worth", response_model=GetNetWorthDecisionsResponse)
def get_net_worth_decisions(
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
) -> GetNetWorthDecisionsResponse:
    session = _get_extracted_session(conn)
    migration_session_id = session["migration_session_id"]

    row = conn.execute(
        "SELECT net_worth_decisions_json FROM aspire_migration_sessions WHERE migration_session_id = $id",
        {"id": migration_session_id},
    ).fetchone()
    raw = row[0] if row else None

    saved: dict[str, NetWorthDecision] = {}
    if raw:
        try:
            parsed = json.loads(str(raw))
            if isinstance(parsed, dict):
                for name, payload in parsed.items():
                    if isinstance(name, str) and name.strip():
                        saved[name] = NetWorthDecision.model_validate(payload)
        except Exception:
            saved = {}

    # Default decisions.
    if session["mapping_status"] == "completed" and session["mapping_json"]:
        mapping = AspireBudgetMapping.model_validate(json.loads(session["mapping_json"]))
        budget_accounts = list(mapping.accounts.keys())
    else:
        budget_accounts = []

    assets = set(session["net_worth_assets"])
    debts = set(session["net_worth_debts"])
    names = sorted({*session["net_worth_categories"], *session["distinct_marks_categories"], *assets, *debts})

    normalized_budget: dict[str, list[str]] = {}
    for acct in budget_accounts:
        normalized_budget.setdefault(normalize_label(acct), []).append(acct)

    decisions: dict[str, NetWorthDecision] = {}
    for name in names:
        if name in saved:
            decisions[name] = saved[name]
            continue

        classification: Any = "unknown"
        if name in assets:
            classification = "asset"
        elif name in debts:
            classification = "debt"

        matches = normalized_budget.get(normalize_label(name), [])
        if len(matches) == 1:
            decisions[name] = NetWorthDecision(
                decision="duplicate_derive_from_ledger",
                classification=classification,
                ledger_account_id=matches[0],
            )
        else:
            decisions[name] = NetWorthDecision(decision="legacy_only", classification=classification)

    # Last-reported balances (per category) from the staged marks stream.
    marks_rows = conn.execute(
        """
        SELECT category_name, mark_date, amount_minor
        FROM aspire_staging_net_worth_marks
        WHERE migration_session_id = $id
          AND mark_date IS NOT NULL
          AND category_name IS NOT NULL
          AND TRIM(category_name) != ''
        QUALIFY
          ROW_NUMBER() OVER (
            PARTITION BY category_name
            ORDER BY mark_date DESC, row_index DESC
          ) = 1
        """,
        {"id": migration_session_id},
    ).fetchall()

    last_reported_by_category_minor: dict[str, int] = {}
    for category_name, _mark_date, amount_minor in marks_rows:
        key = str(category_name)
        magnitude = abs(int(amount_minor or 0))
        decision = decisions.get(key)
        if decision and decision.classification == "debt":
            last_reported_by_category_minor[key] = -magnitude
        else:
            last_reported_by_category_minor[key] = magnitude

    return GetNetWorthDecisionsResponse(
        decisions=decisions,
        last_reported_by_category_minor=last_reported_by_category_minor,
    )


@router.post("/onboarding/aspire/net-worth", status_code=status.HTTP_200_OK)
def save_net_worth_decisions(
    payload: SaveNetWorthDecisionsRequest,
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
) -> dict[str, str]:
    session = _get_extracted_session(conn)
    migration_session_id = session["migration_session_id"]

    decisions_json = _json_dumps({k: v.model_dump(mode="json") for k, v in payload.decisions.items()})
    conn.execute(
        """
        UPDATE aspire_migration_sessions
        SET net_worth_decisions_json = $decisions, updated_at = CURRENT_TIMESTAMP
        WHERE migration_session_id = $id
        """,
        {"id": migration_session_id, "decisions": decisions_json},
    )
    return {"status": "saved"}


@router.get("/onboarding/aspire/preview", response_model=MigrationPreviewResponse)
def preview_migration(
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
    system_date: date = _SYSTEM_DATE_DEP,
) -> MigrationPreviewResponse:
    session = _get_extracted_session(conn)

    blockers: list[str] = []
    if session["mapping_status"] != "completed" or not session["mapping_json"]:
        blockers.append("mapping_incomplete")
        return MigrationPreviewResponse(blockers=blockers, can_apply=False)

    if session["import_status"] == "completed":
        blockers.append("already_imported")

    mapping = AspireBudgetMapping.model_validate(json.loads(session["mapping_json"]))
    blockers.extend(_mapping_collision_blockers(mapping))

    decisions = _load_net_worth_decisions(session["net_worth_decisions_json"])
    blockers.extend(_net_worth_classification_blockers(decisions))

    supported_account_classes = {"cash", "credit", "investment", "loan"}
    for acct_name, acct in mapping.accounts.items():
        if acct.account_class not in supported_account_classes:
            blockers.append(f"unsupported_account_class:{acct_name}")

    auto_pairs, exceptions = _compute_transfer_candidates(
        conn,
        migration_session_id=session["migration_session_id"],
        mapping=mapping,
        special_labels=session["special_labels"],
    )

    saved_raw = _json_loads_dict_int_obj(session["transfer_resolutions_json"])
    saved: dict[int, TransferResolutionKind] = {}
    for idx, payload in saved_raw.items():
        try:
            saved[idx] = TransferResolutionKind.model_validate(payload)
        except Exception:
            continue

    try:
        saved = _validate_transfer_resolutions(exceptions=exceptions, resolutions=saved)
    except HTTPException as exc:
        blockers.append(f"invalid_transfer_resolution:{exc.detail}")
        saved = {}

    unresolved = [row.row_index for row in exceptions if row.row_index not in saved]
    if unresolved:
        blockers.append("unresolved_transfer_exceptions")

    preview_month = system_date.replace(day=1)
    v_today = session["special_labels"].get("v_Today")
    if v_today:
        try:
            preview_month = date.fromisoformat(v_today).replace(day=1)
        except ValueError:
            preview_month = preview_month

    budget_parity = _compute_budget_parity(
        conn,
        migration_session_id=session["migration_session_id"],
        mapping=mapping,
        special_labels=session["special_labels"],
        auto_pairs=auto_pairs,
        exceptions=exceptions,
        saved=saved,
        month_start=preview_month,
    )
    if budget_parity.mismatches > 0:
        blockers.append("budget_parity_mismatch")

    # Legacy net worth series (Aspire parity).
    legacy_marks_rows = conn.execute(
        """
        SELECT mark_date, category_name, amount_minor
        FROM aspire_staging_net_worth_marks
        WHERE migration_session_id = $id
          AND mark_date IS NOT NULL
          AND category_name IS NOT NULL
          AND TRIM(category_name) != ''
        """,
        {"id": session["migration_session_id"]},
    ).fetchall()

    legacy_marks: list[LegacyMark] = []
    for mark_date, category_name, amount_minor in legacy_marks_rows:
        legacy_marks.append(
            LegacyMark(
                mark_date=mark_date,
                category_name=str(category_name),
                amount_minor=abs(int(amount_minor or 0)),
            )
        )

    legacy_points = aspire_bucket_series(
        legacy_marks,
        net_worth_assets=set(session["net_worth_assets"]),
        net_worth_debts=set(session["net_worth_debts"]),
    )
    legacy_series = [SeriesPoint(date=d.isoformat(), value_minor=v) for (d, v) in legacy_points]

    blockers = sorted(set(blockers))
    can_apply = not blockers
    return MigrationPreviewResponse(
        legacy_net_worth_bucket=legacy_series,
        dojo_net_worth_month_end=[],
        duplicate_drift=[],
        budget_parity=budget_parity,
        budget_parity_known_differences=list(_KNOWN_BUDGET_PARITY_DIFFERENCES),
        blockers=blockers,
        can_apply=can_apply,
    )


@router.post("/onboarding/aspire/apply", response_model=ApplyAspireMigrationResponse)
def apply_migration(
    payload: ApplyAspireMigrationRequest,
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
    system_date: date = _SYSTEM_DATE_DEP,
    settings: Settings = _SETTINGS_DEP,
) -> ApplyAspireMigrationResponse:
    session = _get_extracted_session(conn)
    migration_session_id = session["migration_session_id"]
    dataset_fingerprint = session["dataset_fingerprint"]

    if session["import_status"] == "completed":
        return ApplyAspireMigrationResponse(import_status="completed")

    if session["mapping_status"] != "completed" or not session["mapping_json"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Complete mapping first")

    mapping = AspireBudgetMapping.model_validate(json.loads(session["mapping_json"]))

    mapping_collisions = _mapping_collision_blockers(mapping)
    if mapping_collisions and not payload.force and not settings.aspire_migration_allow_partial_mapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Resolve duplicate mapping collisions first: {', '.join(mapping_collisions)}",
        )

    decisions = _load_net_worth_decisions(session["net_worth_decisions_json"])
    net_worth_blockers = _net_worth_classification_blockers(decisions)
    if net_worth_blockers and not payload.force and not settings.aspire_migration_allow_partial_mapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Resolve net worth blockers first: {', '.join(net_worth_blockers)}",
        )

    supported_account_classes = {"cash", "credit", "investment", "loan"}
    for acct_name, acct in mapping.accounts.items():
        if acct.account_class not in supported_account_classes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported account class for `{acct_name}`: {acct.account_class}",
            )

    auto_pairs, exceptions = _compute_transfer_candidates(
        conn,
        migration_session_id=migration_session_id,
        mapping=mapping,
        special_labels=session["special_labels"],
    )

    saved_raw = _json_loads_dict_int_obj(session["transfer_resolutions_json"])
    saved: dict[int, TransferResolutionKind] = {}
    for idx, payload_obj in saved_raw.items():
        try:
            saved[idx] = TransferResolutionKind.model_validate(payload_obj)
        except Exception:
            continue

    saved = _validate_transfer_resolutions(exceptions=exceptions, resolutions=saved)

    unresolved = [row.row_index for row in exceptions if row.row_index not in saved]
    if unresolved and not payload.force and not settings.aspire_migration_allow_partial_mapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resolve transfer exceptions first",
        )

    apply_month = system_date.replace(day=1)
    v_today = session["special_labels"].get("v_Today")
    if v_today:
        try:
            apply_month = date.fromisoformat(v_today).replace(day=1)
        except ValueError:
            apply_month = apply_month
    budget_parity = _compute_budget_parity(
        conn,
        migration_session_id=migration_session_id,
        mapping=mapping,
        special_labels=session["special_labels"],
        auto_pairs=auto_pairs,
        exceptions=exceptions,
        saved=saved,
        month_start=apply_month,
    )
    if budget_parity.mismatches > 0 and not settings.aspire_migration_allow_partial_mapping:
        acknowledged = bool(payload.ack_budget_parity_mismatch)
        semantic_difference = payload.budget_parity_semantic_difference
        if not acknowledged:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Budget parity mismatch detected. Review preview and acknowledge a documented semantic "
                    "difference before apply."
                ),
            )
        if semantic_difference not in _KNOWN_BUDGET_PARITY_DIFFERENCES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Budget parity mismatch acknowledgment requires a documented semantic difference "
                    f"({', '.join(_KNOWN_BUDGET_PARITY_DIFFERENCES)})."
                ),
            )

    # Build stable ID maps, de-duplicating dojo_name collisions.
    account_id_by_aspire_name: dict[str, str] = {}
    used_account_ids: set[str] = set()
    for aspire_name in sorted(mapping.accounts.keys()):
        dojo_name = mapping.accounts[aspire_name].dojo_name
        base = _prefixed_id("aspire_", dojo_name)
        account_id = base
        suffix = 2
        while account_id in used_account_ids:
            account_id = f"{base}_{suffix}"
            suffix += 1
        used_account_ids.add(account_id)
        account_id_by_aspire_name[aspire_name] = account_id

    track_forward_destination_account_ids: dict[tuple[str, int], str] = {}
    for source_name in sorted(decisions.keys(), key=str.lower):
        decision = decisions[source_name]
        if decision.decision != "track_forward":
            continue
        for destination_idx, destination in enumerate(decision.destinations):
            base = _prefixed_id("aspire_nw_", f"{source_name}_{destination.name}")
            account_id = base
            suffix = 2
            while account_id in used_account_ids:
                account_id = f"{base}_{suffix}"
                suffix += 1
            used_account_ids.add(account_id)
            track_forward_destination_account_ids[(source_name, destination_idx)] = account_id

    group_id_by_name: dict[str, str] = {}
    for group_name in sorted({m.group_name for m in mapping.categories.values()}):
        group_id_by_name[group_name] = _prefixed_id("aspire_group_", group_name)

    category_id_by_aspire_name: dict[str, str] = {}
    used_category_ids: set[str] = set(
        r[0] for r in conn.execute("SELECT category_id FROM budget_categories").fetchall() if r and r[0] is not None
    )
    for aspire_name in sorted(mapping.categories.keys()):
        dojo_name = mapping.categories[aspire_name].dojo_name
        base = _prefixed_id("aspire_", dojo_name)
        category_id = base
        suffix = 2
        while category_id in used_category_ids:
            category_id = f"{base}_{suffix}"
            suffix += 1
        used_category_ids.add(category_id)
        category_id_by_aspire_name[aspire_name] = category_id

    def _map_category_name(raw: str | None) -> str | None:
        if raw is None:
            return None
        name = str(raw).strip()
        if not name:
            return None

        labels = session["special_labels"]
        if name == labels.get("v_StartingBalance"):
            return "opening_balance"
        if name == labels.get("v_BalanceAdjustment"):
            return "balance_adjustment"
        if name == labels.get("v_AtoB"):
            return "available_to_budget"
        if name == labels.get("v_AccountTransfer"):
            return "account_transfer"

        mapped = category_id_by_aspire_name.get(name)
        return mapped

    def _map_allocation_category_name(raw: str | None) -> str:
        labels = session["special_labels"]
        if raw is None or not str(raw).strip() or str(raw).strip() == labels.get("v_AtoB"):
            return "available_to_budget"
        mapped = category_id_by_aspire_name.get(str(raw).strip())
        if not mapped:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown allocation category: {raw}")
        return mapped

    now = _now_ts()

    # Pull staging rows once.
    trx_rows = conn.execute(
        """
        SELECT row_index, transaction_date, amount_minor, category_name, account_name, memo, status
        FROM aspire_staging_transactions
        WHERE migration_session_id = $id
        ORDER BY transaction_date NULLS LAST, row_index
        """,
        {"id": migration_session_id},
    ).fetchall()

    trx_by_idx: dict[int, tuple[Any, ...]] = {int(r[0]): r for r in trx_rows}

    alloc_rows = conn.execute(
        """
        SELECT row_index, allocation_date, amount_minor, from_category_name, to_category_name
        FROM aspire_staging_allocations
        WHERE migration_session_id = $id
        ORDER BY allocation_date NULLS LAST, row_index
        """,
        {"id": migration_session_id},
    ).fetchall()

    manual_pairs: list[tuple[int, int]] = []
    seen_manual_pairs: set[tuple[int, int]] = set()
    for idx, resolution in saved.items():
        if resolution.kind != "linked" or resolution.linked_row_index is None:
            continue
        a, b = sorted((int(idx), int(resolution.linked_row_index)))
        pair = (a, b)
        if pair in seen_manual_pairs:
            continue
        seen_manual_pairs.add(pair)
        manual_pairs.append(pair)

    transfer_pair_indices: set[int] = set()
    all_pairs = [*auto_pairs, *manual_pairs]
    for a, b in all_pairs:
        transfer_pair_indices.add(int(a))
        transfer_pair_indices.add(int(b))
    exception_indices: set[int] = {row.row_index for row in exceptions}

    transfer_concept_by_pair: dict[tuple[int, int], uuid.UUID] = {}
    for a, b in auto_pairs:
        lo, hi = (int(a), int(b)) if int(a) <= int(b) else (int(b), int(a))
        transfer_concept_by_pair[(lo, hi)] = _uuid_for(dataset_fingerprint, "transfer", f"{lo}:{hi}")
    for a, b in manual_pairs:
        lo, hi = (int(a), int(b)) if int(a) <= int(b) else (int(b), int(a))
        transfer_concept_by_pair[(lo, hi)] = _uuid_for(dataset_fingerprint, "manual_transfer", f"{lo}:{hi}")

    accounts_created = 0
    category_groups_created = 0
    categories_created = 0
    transactions_imported = 0
    allocations_imported = 0
    legacy_marks_imported = 0

    conn.execute("BEGIN")
    try:
        conn.execute(
            """
            UPDATE aspire_migration_sessions
            SET import_status = 'in_progress', import_error = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE migration_session_id = $id
            """,
            {"id": migration_session_id},
        )

        # Ensure the credit payment group exists.
        conn.execute(
            """
            INSERT INTO budget_category_groups (group_id, name, sort_order, is_active)
            VALUES ('credit_card_payments', 'Credit Card Payments', -1000, TRUE)
                ON CONFLICT (group_id) DO UPDATE
                    SET name = excluded.name,
                        sort_order = excluded.sort_order,
                        is_active = TRUE,
                        updated_at = NOW()
            """
        )

        # Groups from mapping.
        for group_name, group_id in group_id_by_name.items():
            if group_id == "credit_card_payments":
                continue
            conn.execute(
                """
                INSERT INTO budget_category_groups (group_id, name, sort_order, is_active)
                VALUES ($group_id, $name, 1000, TRUE)
                ON CONFLICT (group_id) DO UPDATE
                    SET name = excluded.name,
                        is_active = excluded.is_active,
                        updated_at = NOW()
                """,
                {"group_id": group_id, "name": group_name},
            )
            category_groups_created += 1

        # Categories from mapping.
        for aspire_name, cat in mapping.categories.items():
            category_id = category_id_by_aspire_name[aspire_name]
            group_id = group_id_by_name.get(cat.group_name)
            if not group_id:
                group_id = _prefixed_id("aspire_group_", cat.group_name)
            conn.execute(
                """
                INSERT INTO budget_categories (
                    category_id,
                    name,
                    group_id,
                    is_active,
                    is_system,
                    allow_transactions,
                    allow_allocations,
                    is_envelope,
                    is_payment,
                    goal_type,
                    goal_amount_minor,
                    goal_target_date,
                    goal_frequency,
                    created_at,
                    updated_at
                ) VALUES (
                    $category_id,
                    $name,
                    $group_id,
                    $is_active,
                    FALSE,
                    TRUE,
                    TRUE,
                    TRUE,
                    FALSE,
                    $goal_type,
                    $goal_amount_minor,
                    $goal_target_date,
                    $goal_frequency,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT (category_id) DO UPDATE
                    SET name = excluded.name,
                        group_id = excluded.group_id,
                        is_active = excluded.is_active,
                        goal_type = excluded.goal_type,
                        goal_amount_minor = excluded.goal_amount_minor,
                        goal_target_date = excluded.goal_target_date,
                        goal_frequency = excluded.goal_frequency,
                        updated_at = NOW()
                """,
                {
                    "category_id": category_id,
                    "name": cat.dojo_name,
                    "group_id": group_id,
                    "is_active": bool(cat.is_active),
                    "goal_type": cat.goal_type,
                    "goal_amount_minor": int(cat.goal_amount_minor) if cat.goal_amount_minor is not None else None,
                    "goal_target_date": cat.goal_target_date,
                    "goal_frequency": cat.goal_frequency,
                },
            )
            categories_created += 1

        # Accounts from mapping.
        for aspire_name, acct in mapping.accounts.items():
            account_id = account_id_by_aspire_name[aspire_name]
            account_type = "asset"
            if acct.account_class in {"credit", "loan"}:
                account_type = "liability"
            conn.execute(
                """
                INSERT INTO accounts (
                    account_id,
                    name,
                    account_type,
                    account_class,
                    account_role,
                    current_balance_minor,
                    currency,
                    is_active,
                    include_in_net_worth,
                    created_at,
                    updated_at
                ) VALUES (
                    $account_id,
                    $name,
                    $account_type,
                    $account_class,
                    $account_role,
                    0,
                    'USD',
                    $is_active,
                    $include_in_net_worth,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT (account_id) DO UPDATE
                    SET name = excluded.name,
                        account_type = excluded.account_type,
                        account_class = excluded.account_class,
                        account_role = excluded.account_role,
                        is_active = excluded.is_active,
                        include_in_net_worth = excluded.include_in_net_worth,
                        updated_at = NOW()
                """,
                {
                    "account_id": account_id,
                    "name": acct.dojo_name,
                    "account_type": account_type,
                    "account_class": acct.account_class,
                    "account_role": acct.account_role,
                    "is_active": bool(acct.is_active),
                    "include_in_net_worth": bool(acct.is_active),
                },
            )
            accounts_created += 1

            if acct.account_class == "credit":
                payment_category_id = derive_payment_category_id(account_id)
                conn.execute(
                    """
                    INSERT INTO budget_categories (
                        category_id,
                        name,
                        group_id,
                        is_active,
                        is_system,
                        allow_transactions,
                        allow_allocations,
                        is_envelope,
                        is_payment,
                        created_at,
                        updated_at
                    ) VALUES (
                        $category_id,
                        $name,
                        'credit_card_payments',
                        TRUE,
                        FALSE,
                        FALSE,
                        TRUE,
                        TRUE,
                        TRUE,
                        CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP
                    )
                    ON CONFLICT (category_id) DO UPDATE
                        SET name = excluded.name,
                            group_id = excluded.group_id,
                            is_active = TRUE,
                            allow_transactions = excluded.allow_transactions,
                            allow_allocations = excluded.allow_allocations,
                            is_envelope = excluded.is_envelope,
                            is_payment = excluded.is_payment,
                            updated_at = NOW()
                    """,
                    {"category_id": payment_category_id, "name": acct.dojo_name},
                )

        # Track-forward net worth destinations.
        for source_name in sorted(decisions.keys(), key=str.lower):
            decision = decisions[source_name]
            if decision.decision != "track_forward":
                continue
            cutover_date = decision.cutover_date or system_date

            for destination_idx, destination in enumerate(decision.destinations):
                account_id = track_forward_destination_account_ids.get((source_name, destination_idx))
                if not account_id:
                    continue

                if destination.account_type == "liability" or destination.account_class in {"loan", "credit"}:
                    account_type = "liability"
                else:
                    account_type = "asset"

                conn.execute(
                    """
                    INSERT INTO accounts (
                        account_id,
                        name,
                        institution_name,
                        account_type,
                        account_class,
                        account_role,
                        current_balance_minor,
                        currency,
                        is_active,
                        include_in_net_worth,
                        created_at,
                        updated_at
                    ) VALUES (
                        $account_id,
                        $name,
                        $institution_name,
                        $account_type,
                        $account_class,
                        'tracking',
                        0,
                        'USD',
                        TRUE,
                        TRUE,
                        CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP
                    )
                    ON CONFLICT (account_id) DO UPDATE
                        SET name = excluded.name,
                            institution_name = excluded.institution_name,
                            account_type = excluded.account_type,
                            account_class = excluded.account_class,
                            account_role = excluded.account_role,
                            is_active = TRUE,
                            include_in_net_worth = TRUE,
                            updated_at = NOW()
                    """,
                    {
                        "account_id": account_id,
                        "name": destination.name,
                        "institution_name": destination.institution_name,
                        "account_type": account_type,
                        "account_class": destination.account_class,
                    },
                )
                accounts_created += 1

                starting_value_minor = int(destination.starting_value_minor or 0)

                if destination.account_class == "investment" and starting_value_minor == 0:
                    computed_holdings_minor = 0
                    for holding in destination.holdings:
                        ticker = holding.ticker.strip().upper()
                        if not ticker:
                            continue
                        price_minor = int(getattr(holding, "current_price_minor", 0) or 0)
                        if price_minor <= 0:
                            price_minor = int(holding.avg_cost_minor or 0)
                        if price_minor <= 0:
                            continue
                        try:
                            qty = float(holding.quantity)
                        except Exception:
                            qty = 0.0
                        computed_holdings_minor += int(round(qty * price_minor))

                    computed_start_minor = int(destination.statement_cash_minor or 0) + computed_holdings_minor
                    if computed_start_minor != 0:
                        starting_value_minor = computed_start_minor

                if (
                    destination.account_class in {"cash", "accessible", "credit", "investment", "loan"}
                    and starting_value_minor != 0
                ):
                    concept_id = _uuid_for(
                        dataset_fingerprint,
                        "track_forward_opening",
                        f"{source_name}:{destination_idx}",
                    )
                    version_id = _uuid_for(
                        dataset_fingerprint,
                        "track_forward_opening_version",
                        f"{source_name}:{destination_idx}",
                    )
                    conn.execute(
                        """
                        INSERT INTO transactions (
                            transaction_version_id,
                            concept_id,
                            account_id,
                            category_id,
                            transaction_date,
                            amount_minor,
                            memo,
                            status,
                            recorded_at,
                            valid_from,
                            valid_to,
                            is_active,
                            source
                        ) VALUES (
                            $transaction_version_id,
                            $concept_id,
                            $account_id,
                            'opening_balance',
                            $transaction_date,
                            $amount_minor,
                            $memo,
                            'cleared',
                            $recorded_at,
                            $recorded_at,
                            TIMESTAMP '9999-12-31 00:00:00',
                            TRUE,
                            'aspire_import'
                        )
                        ON CONFLICT (transaction_version_id) DO NOTHING
                        """,
                        {
                            "transaction_version_id": str(version_id),
                            "concept_id": str(concept_id),
                            "account_id": account_id,
                            "transaction_date": cutover_date,
                            "amount_minor": starting_value_minor,
                            "memo": f"Aspire cutover opening balance: {source_name}",
                            "recorded_at": now,
                        },
                    )
                    transactions_imported += 1

                if destination.account_class == "cash":
                    detail_id = _uuid_for(dataset_fingerprint, "track_forward_cash_detail", account_id)
                    conn.execute(
                        load_budgeting_sql("insert_cash_account_detail.sql"),
                        {
                            "detail_id": str(detail_id),
                            "account_id": account_id,
                            "interest_rate_apy": None,
                        },
                    )

                elif destination.account_class == "accessible":
                    detail_id = _uuid_for(dataset_fingerprint, "track_forward_accessible_detail", account_id)
                    conn.execute(
                        load_budgeting_sql("insert_accessible_asset_detail.sql"),
                        {
                            "detail_id": str(detail_id),
                            "account_id": account_id,
                            "term_end_date": None,
                            "interest_rate_apy": None,
                            "early_withdrawal_penalty": None,
                        },
                    )

                elif destination.account_class == "credit":
                    detail_id = _uuid_for(dataset_fingerprint, "track_forward_credit_detail", account_id)
                    conn.execute(
                        load_budgeting_sql("insert_credit_account_detail.sql"),
                        {
                            "detail_id": str(detail_id),
                            "account_id": account_id,
                            "apr": None,
                            "card_type": None,
                            "cash_advance_apr": None,
                        },
                    )

                elif destination.account_class == "investment":
                    detail_id = _uuid_for(
                        dataset_fingerprint,
                        "track_forward_investment_detail",
                        account_id,
                    )
                    conn.execute(
                        load_investments_sql("insert_investment_account_detail_version.sql"),
                        {
                            "detail_id": str(detail_id),
                            "account_id": account_id,
                            "risk_free_sweep_rate": 0.0,
                            "manager": None,
                            "is_self_directed": destination.is_self_directed,
                            "tax_classification": destination.tax_classification,
                            "uninvested_cash_minor": int(destination.statement_cash_minor or 0),
                            "ledger_baseline_minor": starting_value_minor,
                            "valid_from": now,
                            "valid_to": "9999-12-31 00:00:00",
                            "created_at": now,
                            "updated_at": now,
                        },
                    )

                    for holding_idx, holding in enumerate(destination.holdings):
                        ticker = holding.ticker.strip().upper()
                        if not ticker:
                            continue

                        # Starting-price seed for NAV / net worth reporting.
                        # Prefer explicit current price, fall back to legacy avg_cost input.
                        price_minor = int(getattr(holding, "current_price_minor", 0) or 0)
                        if price_minor <= 0:
                            price_minor = int(holding.avg_cost_minor or 0)

                        # Positions store per-share avg cost basis.
                        cost_basis_total_minor = getattr(holding, "cost_basis_total_minor", None)
                        avg_cost_minor = int(holding.avg_cost_minor or 0)
                        if cost_basis_total_minor is not None:
                            try:
                                quantity = float(holding.quantity)
                            except Exception:
                                quantity = 0.0
                            if quantity > 0:
                                avg_cost_minor = int(round(int(cost_basis_total_minor) / quantity))
                            else:
                                avg_cost_minor = 0

                        security_row = conn.execute(
                            "SELECT security_id FROM securities WHERE ticker = $ticker",
                            {"ticker": ticker},
                        ).fetchone()
                        if security_row:
                            security_id = str(security_row[0])
                        else:
                            security_id = str(_uuid_for(dataset_fingerprint, "track_forward_security", ticker))
                            conn.execute(
                                """
                                INSERT INTO securities (
                                    security_id,
                                    ticker,
                                    name,
                                    type,
                                    currency,
                                    created_at,
                                    updated_at
                                ) VALUES (
                                    $security_id,
                                    $ticker,
                                    $name,
                                    'STOCK',
                                    'USD',
                                    $recorded_at,
                                    $recorded_at
                                )
                                ON CONFLICT (ticker) DO NOTHING
                                """,
                                {
                                    "security_id": security_id,
                                    "ticker": ticker,
                                    "name": ticker,
                                    "recorded_at": now,
                                },
                            )

                        position_key = f"{account_id}:{ticker}:{holding_idx}"
                        position_id = _uuid_for(dataset_fingerprint, "track_forward_position", position_key)
                        position_concept_id = _uuid_for(
                            dataset_fingerprint,
                            "track_forward_position_concept",
                            position_key,
                        )
                        conn.execute(
                            """
                            INSERT INTO positions (
                                position_id,
                                concept_id,
                                account_id,
                                security_id,
                                quantity,
                                avg_cost_minor,
                                valid_from,
                                valid_to,
                                is_active,
                                recorded_at
                            ) VALUES (
                                $position_id,
                                $concept_id,
                                $account_id,
                                $security_id,
                                $quantity,
                                $avg_cost_minor,
                                $recorded_at,
                                TIMESTAMP '9999-12-31 00:00:00',
                                TRUE,
                                $recorded_at
                            )
                            ON CONFLICT (position_id) DO NOTHING
                            """,
                            {
                                "position_id": str(position_id),
                                "concept_id": str(position_concept_id),
                                "account_id": account_id,
                                "security_id": security_id,
                                "quantity": float(holding.quantity),
                                "avg_cost_minor": avg_cost_minor,
                                "recorded_at": now,
                            },
                        )

                        conn.execute(
                            """
                            INSERT INTO market_prices (
                                security_id,
                                market_date,
                                open_minor,
                                high_minor,
                                low_minor,
                                close_minor,
                                adj_close_minor,
                                volume,
                                recorded_at
                            ) VALUES (
                                $security_id,
                                $market_date,
                                $price_minor,
                                $price_minor,
                                $price_minor,
                                $price_minor,
                                $price_minor,
                                NULL,
                                $recorded_at
                            )
                            ON CONFLICT (security_id, market_date) DO NOTHING
                            """,
                            {
                                "security_id": security_id,
                                "market_date": cutover_date,
                                "price_minor": price_minor,
                                "recorded_at": now,
                            },
                        )

                elif destination.account_class == "loan":
                    detail_id = _uuid_for(dataset_fingerprint, "track_forward_loan_detail", account_id)
                    conn.execute(
                        load_budgeting_sql("insert_loan_account_detail.sql"),
                        {
                            "detail_id": str(detail_id),
                            "account_id": account_id,
                            "initial_principal_minor": int(
                                abs(
                                    destination.original_principal_minor
                                    if destination.original_principal_minor is not None
                                    else starting_value_minor
                                )
                            ),
                            "interest_rate_apy": float(destination.interest_rate_apy or 0.0),
                            "mortgage_escrow_details": destination.note,
                        },
                    )

                elif destination.account_class == "tangible":
                    detail_id = _uuid_for(dataset_fingerprint, "track_forward_tangible_detail", account_id)
                    conn.execute(
                        load_budgeting_sql("insert_tangible_asset_detail.sql"),
                        {
                            "detail_id": str(detail_id),
                            "account_id": account_id,
                            "asset_name": destination.name,
                            "acquisition_cost_minor": int(abs(starting_value_minor)),
                        },
                    )

                    tangible_id = _uuid_for(dataset_fingerprint, "track_forward_tangible_value", account_id)
                    conn.execute(
                        """
                        INSERT INTO tangible_assets (
                            tangible_id,
                            account_id,
                            asset_name,
                            acquisition_cost_minor,
                            current_fair_value_minor,
                            valid_from,
                            valid_to,
                            is_active,
                            recorded_at,
                            created_at,
                            updated_at
                        ) VALUES (
                            $tangible_id,
                            $account_id,
                            $asset_name,
                            $acquisition_cost_minor,
                            $current_fair_value_minor,
                            $recorded_at,
                            TIMESTAMP '9999-12-31 00:00:00',
                            TRUE,
                            $recorded_at,
                            $recorded_at,
                            $recorded_at
                        )
                        ON CONFLICT (tangible_id) DO NOTHING
                        """,
                        {
                            "tangible_id": str(tangible_id),
                            "account_id": account_id,
                            "asset_name": destination.name,
                            "acquisition_cost_minor": int(abs(starting_value_minor)),
                            "current_fair_value_minor": starting_value_minor,
                            "recorded_at": now,
                        },
                    )

        # Allocations.
        for row_index, alloc_date, amount_minor, from_name, to_name in alloc_rows:
            if amount_minor is None or int(amount_minor) == 0:
                continue
            allocation_date = alloc_date or system_date
            month_start = allocation_date.replace(day=1)
            from_category_id = _map_allocation_category_name(from_name)
            to_category_id = _map_allocation_category_name(to_name)

            concept_id = _uuid_for(dataset_fingerprint, "allocation", str(int(row_index)))
            allocation_id = _uuid_for(dataset_fingerprint, "allocation_version", str(int(row_index)))

            conn.execute(
                """
                INSERT INTO budget_allocations (
                    allocation_id,
                    concept_id,
                    allocation_date,
                    month_start,
                    from_category_id,
                    to_category_id,
                    amount_minor,
                    memo,
                    recorded_at,
                    valid_from,
                    valid_to,
                    is_active,
                    created_at,
                    updated_at
                ) VALUES (
                    $allocation_id,
                    $concept_id,
                    $allocation_date,
                    $month_start,
                    $from_category_id,
                    $to_category_id,
                    $amount_minor,
                    'Aspire import',
                    $recorded_at,
                    $recorded_at,
                    TIMESTAMP '9999-12-31 00:00:00',
                    TRUE,
                    $recorded_at,
                    $recorded_at
                )
                ON CONFLICT (allocation_id) DO NOTHING
                """,
                {
                    "allocation_id": str(allocation_id),
                    "concept_id": str(concept_id),
                    "allocation_date": allocation_date,
                    "month_start": month_start,
                    "from_category_id": from_category_id,
                    "to_category_id": to_category_id,
                    "amount_minor": abs(int(amount_minor)),
                    "recorded_at": now,
                },
            )
            allocations_imported += 1

        # Transactions and transfers.
        labels = session["special_labels"]
        transfer_label = labels.get("v_AccountTransfer")

        for row_index, trx_date, amount_minor, category_name, account_name, memo, status_value in trx_rows:
            idx = int(row_index)
            if trx_date is None:
                if payload.force or settings.aspire_migration_allow_partial_mapping:
                    continue
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing transaction date at row {idx}"
                )
            if amount_minor is None or int(amount_minor) == 0:
                continue
            if account_name is None or not str(account_name).strip():
                if payload.force or settings.aspire_migration_allow_partial_mapping:
                    continue
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing account name at row {idx}"
                )

            if idx in transfer_pair_indices:
                continue

            if idx in exception_indices:
                resolution = saved.get(idx)
                if resolution is None:
                    if payload.force or settings.aspire_migration_allow_partial_mapping:
                        continue
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unresolved transfer exception")
                if resolution.kind == "opening_balance":
                    category_id = "opening_balance"
                elif resolution.kind == "balance_adjustment":
                    category_id = "balance_adjustment"
                elif resolution.kind == "linked":
                    continue
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Unknown transfer resolution kind for row {idx}: {resolution.kind}",
                    )
            else:
                raw_cat = str(category_name).strip() if category_name is not None else None
                if raw_cat and (raw_cat == transfer_label or raw_cat in mapping.accounts):
                    # Transfer candidate rows should have been paired or resolved.
                    if payload.force or settings.aspire_migration_allow_partial_mapping:
                        continue
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unpaired transfer-like row {idx}"
                    )

                category_id = _map_category_name(raw_cat)
                if category_id is None:
                    if payload.force or settings.aspire_migration_allow_partial_mapping:
                        continue
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown category at row {idx}"
                    )

            aspire_account = str(account_name).strip()
            account_id = account_id_by_aspire_name.get(aspire_account)
            if not account_id:
                if payload.force or settings.aspire_migration_allow_partial_mapping:
                    continue
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown account at row {idx}")

            concept_id = _uuid_for(dataset_fingerprint, "transaction", str(idx))
            version_id = _uuid_for(dataset_fingerprint, "transaction_version", str(idx))

            conn.execute(
                """
                INSERT INTO transactions (
                    transaction_version_id,
                    concept_id,
                    account_id,
                    category_id,
                    transaction_date,
                    amount_minor,
                    memo,
                    status,
                    recorded_at,
                    valid_from,
                    valid_to,
                    is_active,
                    source
                ) VALUES (
                    $transaction_version_id,
                    $concept_id,
                    $account_id,
                    $category_id,
                    $transaction_date,
                    $amount_minor,
                    $memo,
                    $status,
                    $recorded_at,
                    $recorded_at,
                    TIMESTAMP '9999-12-31 00:00:00',
                    TRUE,
                    'aspire_import'
                )
                ON CONFLICT (transaction_version_id) DO NOTHING
                """,
                {
                    "transaction_version_id": str(version_id),
                    "concept_id": str(concept_id),
                    "account_id": account_id,
                    "category_id": category_id,
                    "transaction_date": trx_date,
                    "amount_minor": int(amount_minor),
                    "memo": str(memo) if memo is not None else None,
                    "status": str(status_value) if status_value else "cleared",
                    "recorded_at": now,
                },
            )
            transactions_imported += 1

        # Transfer pairs (neutral; account_transfer on both legs).
        for a, b in all_pairs:
            lo, hi = (int(a), int(b)) if int(a) <= int(b) else (int(b), int(a))
            concept_id = transfer_concept_by_pair[(lo, hi)]

            row_a = trx_by_idx.get(lo)
            row_b = trx_by_idx.get(hi)
            if not row_a or not row_b:
                continue

            for idx, row in ((lo, row_a), (hi, row_b)):
                _, trx_date, amount_minor, _, account_name, memo, status_value = row
                if trx_date is None or amount_minor is None:
                    continue
                aspire_account = str(account_name).strip() if account_name is not None else ""
                account_id = account_id_by_aspire_name.get(aspire_account)
                if not account_id:
                    continue

                version_id = _uuid_for(dataset_fingerprint, "transfer_leg", str(idx))
                conn.execute(
                    """
                    INSERT INTO transactions (
                        transaction_version_id,
                        concept_id,
                        account_id,
                        category_id,
                        transaction_date,
                        amount_minor,
                        memo,
                        status,
                        recorded_at,
                        valid_from,
                        valid_to,
                        is_active,
                        source
                    ) VALUES (
                        $transaction_version_id,
                        $concept_id,
                        $account_id,
                        'account_transfer',
                        $transaction_date,
                        $amount_minor,
                        $memo,
                        $status,
                        $recorded_at,
                        $recorded_at,
                        TIMESTAMP '9999-12-31 00:00:00',
                        TRUE,
                        'aspire_import'
                    )
                    ON CONFLICT (transaction_version_id) DO NOTHING
                    """,
                    {
                        "transaction_version_id": str(version_id),
                        "concept_id": str(concept_id),
                        "account_id": account_id,
                        "transaction_date": trx_date,
                        "amount_minor": int(amount_minor),
                        "memo": str(memo) if memo is not None else None,
                        "status": str(status_value) if status_value else "cleared",
                        "recorded_at": now,
                    },
                )
                transactions_imported += 1

        # Persist legacy marks verbatim for parity views.
        marks_rows = conn.execute(
            """
            SELECT mark_date, category_name, amount_minor, note, breakpoint
            FROM aspire_staging_net_worth_marks
            WHERE migration_session_id = $id
              AND mark_date IS NOT NULL
              AND category_name IS NOT NULL
              AND TRIM(category_name) != ''
            """,
            {"id": migration_session_id},
        ).fetchall()
        for mark_date, category_name, amount_minor, note, breakpoint in marks_rows:
            mark_id = _uuid_for(
                dataset_fingerprint, "legacy_mark", f"{mark_date}:{category_name}:{int(amount_minor or 0)}"
            )
            conn.execute(
                """
                INSERT INTO aspire_legacy_net_worth_marks (
                    mark_id,
                    migration_session_id,
                    dataset_fingerprint,
                    mark_date,
                    category_name,
                    amount_minor,
                    note,
                    breakpoint,
                    recorded_at
                ) VALUES (
                    $mark_id,
                    $migration_session_id,
                    $dataset_fingerprint,
                    $mark_date,
                    $category_name,
                    $amount_minor,
                    $note,
                    $breakpoint,
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT (mark_id) DO NOTHING
                """,
                {
                    "mark_id": str(mark_id),
                    "migration_session_id": migration_session_id,
                    "dataset_fingerprint": dataset_fingerprint,
                    "mark_date": mark_date,
                    "category_name": str(category_name),
                    "amount_minor": int(amount_minor or 0),
                    "note": str(note) if note is not None else None,
                    "breakpoint": str(breakpoint) if breakpoint is not None else None,
                },
            )
            legacy_marks_imported += 1

        rebuild_caches(conn, in_transaction=True)

        # Baseline investment accounts so ledger cash is not double-counted.
        investment_accounts = [
            account_id_by_aspire_name[name]
            for name, acct in mapping.accounts.items()
            if acct.account_class == "investment"
        ]
        for account_id in investment_accounts:
            row = conn.execute(
                "SELECT COUNT(*) FROM investment_account_details WHERE account_id = $id AND is_active = TRUE",
                {"id": account_id},
            ).fetchone()
            if row and int(row[0] or 0) > 0:
                continue
            bal_row = conn.execute(
                "SELECT current_balance_minor FROM accounts WHERE account_id = $id",
                {"id": account_id},
            ).fetchone()
            ledger_cash_minor = int(bal_row[0] or 0) if bal_row else 0

            detail_id = _uuid_for(dataset_fingerprint, "investment_detail", account_id)
            conn.execute(
                load_investments_sql("insert_investment_account_detail_version.sql"),
                {
                    "detail_id": str(detail_id),
                    "account_id": account_id,
                    "risk_free_sweep_rate": 0.0,
                    "manager": None,
                    "is_self_directed": None,
                    "tax_classification": None,
                    "uninvested_cash_minor": ledger_cash_minor,
                    "ledger_baseline_minor": ledger_cash_minor,
                    "valid_from": now,
                    "valid_to": "9999-12-31 00:00:00",
                    "created_at": now,
                    "updated_at": now,
                },
            )

        conn.execute(
            """
            UPDATE aspire_migration_sessions
            SET import_status = 'completed', imported_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE migration_session_id = $id
            """,
            {"id": migration_session_id},
        )

        conn.execute("DELETE FROM onboarding_state WHERE onboarding_id = $id", {"id": _PRIMARY_ID})
        conn.execute(
            """
            INSERT INTO onboarding_state (
                onboarding_id,
                onboarding_mode,
                onboarding_status,
                migration_session_id,
                created_at,
                updated_at
            ) VALUES ($id, $mode, $status, $session_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            {
                "id": _PRIMARY_ID,
                "mode": "aspire",
                "status": "completed",
                "session_id": migration_session_id,
            },
        )

        conn.execute("COMMIT")
    except Exception as exc:
        conn.execute("ROLLBACK")
        conn.execute(
            """
            UPDATE aspire_migration_sessions
            SET import_status = 'failed', import_error = $err, updated_at = CURRENT_TIMESTAMP
            WHERE migration_session_id = $id
            """,
            {"id": migration_session_id, "err": str(exc)},
        )
        raise

    return ApplyAspireMigrationResponse(
        import_status="completed",
        accounts_created=accounts_created,
        category_groups_created=category_groups_created,
        categories_created=categories_created,
        transactions_imported=transactions_imported,
        allocations_imported=allocations_imported,
        legacy_marks_imported=legacy_marks_imported,
    )


logger = logging.getLogger(__name__)
