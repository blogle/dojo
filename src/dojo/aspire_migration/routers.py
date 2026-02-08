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
    SeriesPoint,
)
from dojo.aspire_migration.sheets import parse_spreadsheet_id
from dojo.core.cache_rebuild import rebuild_caches
from dojo.investments.sql import load_sql as load_investments_sql
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


@router.get("/onboarding/aspire/mapping", response_model=GetAspireMappingResponse)
def get_mapping(
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
) -> GetAspireMappingResponse:
    session = _get_extracted_session(conn)
    migration_session_id = session["migration_session_id"]

    accounts, categories = _mapping_candidates(conn, migration_session_id)
    cfg_cards = set(session["cfg_cards"])
    hidden_accounts = set(session["hidden_accounts"])
    hidden_categories = set(session["hidden_categories"])

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
        mapping = _default_mapping(
            accounts=accounts,
            categories=categories,
            cfg_cards=cfg_cards,
            hidden_accounts=hidden_accounts,
            hidden_categories=hidden_categories,
        )

    return GetAspireMappingResponse(
        mapping_status=cast(Any, session["mapping_status"]),
        mapping=mapping,
        aspire_hidden_accounts=session["hidden_accounts"],
        aspire_hidden_categories=session["hidden_categories"],
        aspire_special_labels=session["special_labels"],
        aspire_status_symbols=session["status_symbols"],
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

    return GetAspireTransfersResponse(auto_pairs=auto_pairs, exceptions=exceptions, saved_resolutions=saved)


@router.post("/onboarding/aspire/transfers", status_code=status.HTTP_200_OK)
def save_transfers(
    payload: SaveTransferResolutionsRequest,
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
) -> dict[str, str]:
    session = _get_extracted_session(conn)
    if session["mapping_status"] != "completed" or not session["mapping_json"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Complete mapping first")

    migration_session_id = session["migration_session_id"]
    resolutions_json = _json_dumps({str(k): v.model_dump() for k, v in payload.resolutions.items()})
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

    return GetNetWorthDecisionsResponse(decisions=decisions)


@router.post("/onboarding/aspire/net-worth", status_code=status.HTTP_200_OK)
def save_net_worth_decisions(
    payload: SaveNetWorthDecisionsRequest,
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
) -> dict[str, str]:
    session = _get_extracted_session(conn)
    migration_session_id = session["migration_session_id"]

    decisions_json = _json_dumps({k: v.model_dump() for k, v in payload.decisions.items()})
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
) -> MigrationPreviewResponse:
    session = _get_extracted_session(conn)

    blockers: list[str] = []
    if session["mapping_status"] != "completed" or not session["mapping_json"]:
        blockers.append("mapping_incomplete")
        return MigrationPreviewResponse(blockers=blockers, can_apply=False)

    if session["import_status"] == "completed":
        blockers.append("already_imported")

    mapping = AspireBudgetMapping.model_validate(json.loads(session["mapping_json"]))

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

    unresolved = [row.row_index for row in exceptions if row.row_index not in saved]
    if unresolved:
        blockers.append("unresolved_transfer_exceptions")

    for idx, resolution in saved.items():
        if resolution.kind == "external" and not resolution.category_id:
            blockers.append(f"transfer_exception_missing_category:{idx}")

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

    can_apply = not blockers
    return MigrationPreviewResponse(
        legacy_net_worth_bucket=legacy_series,
        dojo_net_worth_month_end=[],
        duplicate_drift=[],
        budget_parity=None,
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

    unresolved = [row.row_index for row in exceptions if row.row_index not in saved]
    if unresolved and not payload.force and not settings.aspire_migration_allow_partial_mapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resolve transfer exceptions first",
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

    transfer_pair_indices: set[int] = set()
    for a, b in auto_pairs:
        transfer_pair_indices.add(int(a))
        transfer_pair_indices.add(int(b))
    exception_indices: set[int] = {row.row_index for row in exceptions}

    transfer_concept_by_pair: dict[tuple[int, int], uuid.UUID] = {}
    for a, b in auto_pairs:
        lo, hi = (int(a), int(b)) if int(a) <= int(b) else (int(b), int(a))
        transfer_concept_by_pair[(lo, hi)] = _uuid_for(dataset_fingerprint, "transfer", f"{lo}:{hi}")

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
                    updated_at = CURRENT_TIMESTAMP
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
                        updated_at = CURRENT_TIMESTAMP
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
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT (category_id) DO UPDATE
                    SET name = excluded.name,
                        group_id = excluded.group_id,
                        is_active = excluded.is_active,
                        updated_at = CURRENT_TIMESTAMP
                """,
                {
                    "category_id": category_id,
                    "name": cat.dojo_name,
                    "group_id": group_id,
                    "is_active": bool(cat.is_active),
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
                        updated_at = CURRENT_TIMESTAMP
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
                            updated_at = CURRENT_TIMESTAMP
                    """,
                    {"category_id": payment_category_id, "name": acct.dojo_name},
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
                else:
                    if not resolution.category_id:
                        if payload.force or settings.aspire_migration_allow_partial_mapping:
                            continue
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Missing category for transfer exception {idx}",
                        )
                    category_id = _map_category_name(resolution.category_id)
                    if not category_id:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Unknown category for transfer exception {idx}",
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
        for a, b in auto_pairs:
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
