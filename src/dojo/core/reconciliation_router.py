"""FastAPI router for account reconciliation."""

from __future__ import annotations

from dataclasses import asdict

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Response, status

from dojo.budgeting.schemas import TransactionListItem
from dojo.core.db import connection_dep
from dojo.core.reconciliation import create_reconciliation, get_latest_reconciliation, get_worksheet
from dojo.core.reconciliation_schemas import ReconciliationCreateRequest, ReconciliationResponse

router = APIRouter(tags=["reconciliation"])
_CONNECTION_DEP = Depends(connection_dep)


def _ensure_active_account(conn: duckdb.DuckDBPyConnection, account_id: str) -> None:
    exists = conn.execute(
        "SELECT 1 FROM accounts WHERE account_id = $account_id AND is_active = TRUE LIMIT 1;",
        {"account_id": account_id},
    ).fetchone()
    if exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Account not found: {account_id}")


@router.get(
    "/accounts/{account_id}/reconciliations/latest",
    response_model=ReconciliationResponse,
)
def latest_reconciliation(
    account_id: str,
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
) -> ReconciliationResponse | Response:
    """Return the most recent reconciliation checkpoint."""

    _ensure_active_account(conn, account_id)
    latest = get_latest_reconciliation(conn, account_id)
    if latest is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return ReconciliationResponse(**asdict(latest))


@router.get(
    "/accounts/{account_id}/reconciliations/worksheet",
    response_model=list[TransactionListItem],
)
def reconciliation_worksheet(
    account_id: str,
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
) -> list[TransactionListItem]:
    """Return worksheet items requiring reconciliation review."""

    _ensure_active_account(conn, account_id)
    latest = get_latest_reconciliation(conn, account_id)
    cutoff = latest.created_at if latest is not None else None
    worksheet = get_worksheet(conn, account_id, last_reconciled_at=cutoff)
    return [TransactionListItem(**asdict(item)) for item in worksheet]


@router.get(
    "/accounts/{account_id}/reconciliations/diff",
    response_model=list[TransactionListItem],
)
def reconciliation_diff(
    account_id: str,
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
) -> list[TransactionListItem]:
    """Alias for the reconciliation worksheet."""

    return reconciliation_worksheet(account_id, conn)


@router.post(
    "/accounts/{account_id}/reconciliations",
    response_model=ReconciliationResponse,
    status_code=status.HTTP_201_CREATED,
)
def commit_reconciliation(
    account_id: str,
    payload: ReconciliationCreateRequest,
    conn: duckdb.DuckDBPyConnection = _CONNECTION_DEP,
) -> ReconciliationResponse:
    """Create a new reconciliation checkpoint."""

    try:
        record = create_reconciliation(
            conn,
            account_id=account_id,
            statement_date=payload.statement_date,
            statement_balance_minor=payload.statement_balance_minor,
        )
    except ValueError as exc:
        message = str(exc)
        if message.startswith("Account not found"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc
    return ReconciliationResponse(**asdict(record))
