"""Account reconciliation services.

Reconciliation provides a manual checkpoint/commit mechanism that lets users
assert their cleared balance matches an external bank statement.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from functools import cache
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import duckdb

from dojo.core import clock
from dojo.core.sql import load_sql

DEFAULT_RECONCILIATION_START = datetime(1970, 1, 1, tzinfo=UTC)


@cache
def _sql(name: str) -> str:
    return load_sql(name)


def _row_to_namespace(description: list[tuple[Any, ...]], row: tuple[Any, ...]) -> SimpleNamespace:
    columns = [desc[0] for desc in description]
    return SimpleNamespace(**{name: value for name, value in zip(columns, row, strict=True)})


def _fetchone_namespace(
    conn: duckdb.DuckDBPyConnection,
    sql: str,
    params: dict[str, Any] | None = None,
) -> SimpleNamespace | None:
    if params is None:
        cursor = conn.execute(sql)
    else:
        cursor = conn.execute(sql, params)
    row = cursor.fetchone()
    if row is None:
        return None
    return _row_to_namespace(cursor.description, row)


def _fetchall_namespaces(
    conn: duckdb.DuckDBPyConnection,
    sql: str,
    params: dict[str, Any] | None = None,
) -> list[SimpleNamespace]:
    if params is None:
        cursor = conn.execute(sql)
    else:
        cursor = conn.execute(sql, params)
    rows = cursor.fetchall()
    if not rows:
        return []
    return [_row_to_namespace(cursor.description, row) for row in rows]


@dataclass(frozen=True)
class AccountReconciliation:
    reconciliation_id: UUID
    account_id: str
    created_at: datetime
    statement_date: date
    statement_balance_minor: int
    statement_pending_total_minor: int
    previous_reconciliation_id: UUID | None

    @classmethod
    def from_row(cls, row: SimpleNamespace) -> AccountReconciliation:
        return cls(
            reconciliation_id=UUID(str(row.reconciliation_id)),
            account_id=str(row.account_id),
            created_at=row.created_at,
            statement_date=row.statement_date,
            statement_balance_minor=int(row.statement_balance_minor),
            statement_pending_total_minor=(
                int(row.statement_pending_total_minor) if row.statement_pending_total_minor is not None else 0
            ),
            previous_reconciliation_id=(
                UUID(str(row.previous_reconciliation_id)) if row.previous_reconciliation_id is not None else None
            ),
        )


@dataclass(frozen=True)
class WorksheetTransaction:
    transaction_version_id: UUID
    concept_id: UUID
    transaction_date: date
    account_id: str
    account_name: str
    category_id: str
    category_name: str
    amount_minor: int
    status: str
    memo: str | None
    recorded_at: datetime

    @classmethod
    def from_row(cls, row: SimpleNamespace) -> WorksheetTransaction:
        return cls(
            transaction_version_id=UUID(str(row.transaction_version_id)),
            concept_id=UUID(str(row.concept_id)),
            transaction_date=row.transaction_date,
            account_id=str(row.account_id),
            account_name=str(row.account_name),
            category_id=str(row.category_id),
            category_name=str(row.category_name),
            amount_minor=int(row.amount_minor),
            status=str(row.status),
            memo=str(row.memo) if row.memo is not None else None,
            recorded_at=row.recorded_at,
        )


def get_latest_reconciliation(
    conn: duckdb.DuckDBPyConnection,
    account_id: str,
) -> AccountReconciliation | None:
    """Return the most recent reconciliation for ``account_id`` (if any)."""

    row = _fetchone_namespace(
        conn,
        _sql("select_latest_reconciliation.sql"),
        {"account_id": account_id},
    )
    if row is None:
        return None
    return AccountReconciliation.from_row(row)


def get_worksheet(
    conn: duckdb.DuckDBPyConnection,
    account_id: str,
    *,
    last_reconciled_at: datetime | None,
) -> list[WorksheetTransaction]:
    """Return active transactions requiring reconciliation review."""

    cutoff = last_reconciled_at or DEFAULT_RECONCILIATION_START
    rows = _fetchall_namespaces(
        conn,
        _sql("select_reconciliation_worksheet.sql"),
        {
            "account_id": account_id,
            "last_reconciled_at": cutoff,
        },
    )
    return [WorksheetTransaction.from_row(row) for row in rows]


def create_reconciliation(
    conn: duckdb.DuckDBPyConnection,
    *,
    account_id: str,
    statement_date: date,
    statement_balance_minor: int,
    statement_pending_total_minor: int = 0,
) -> AccountReconciliation:
    """Insert a new reconciliation checkpoint for ``account_id``."""

    if statement_balance_minor is None:
        raise ValueError("statement_balance_minor is required")
    if statement_pending_total_minor is None:
        raise ValueError("statement_pending_total_minor is required")

    conn.execute("BEGIN")
    try:
        account_exists = conn.execute(
            "SELECT 1 FROM accounts WHERE account_id = $account_id AND is_active = TRUE LIMIT 1;",
            {"account_id": account_id},
        ).fetchone()
        if account_exists is None:
            raise ValueError(f"Account not found: {account_id}")

        latest = get_latest_reconciliation(conn, account_id)
        reconciliation_id = uuid4()
        created_at = clock.now()
        previous_reconciliation_id = latest.reconciliation_id if latest is not None else None

        conn.execute(
            _sql("insert_account_reconciliation.sql"),
            {
                "reconciliation_id": str(reconciliation_id),
                "account_id": account_id,
                "created_at": created_at,
                "statement_date": statement_date,
                "statement_balance_minor": statement_balance_minor,
                "statement_pending_total_minor": statement_pending_total_minor,
                "previous_reconciliation_id": (
                    str(previous_reconciliation_id) if previous_reconciliation_id is not None else None
                ),
            },
        )

        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    return AccountReconciliation(
        reconciliation_id=reconciliation_id,
        account_id=account_id,
        created_at=created_at,
        statement_date=statement_date,
        statement_balance_minor=int(statement_balance_minor),
        statement_pending_total_minor=int(statement_pending_total_minor),
        previous_reconciliation_id=previous_reconciliation_id,
    )
