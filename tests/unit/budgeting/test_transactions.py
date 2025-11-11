"""Unit tests for the transaction entry service."""

from datetime import date

import duckdb
import pytest

from dojo.budgeting.errors import InvalidTransaction
from dojo.budgeting.schemas import NewTransactionRequest
from dojo.budgeting.services import TransactionEntryService


def test_create_transaction_updates_account_and_category(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    service = TransactionEntryService()
    cmd = NewTransactionRequest(
        transaction_date=date.today(),
        account_id="house_checking",
        category_id="groceries",
        amount_minor=-12345,
        memo="weekly groceries",
    )

    response = service.create(in_memory_db, cmd)

    assert response.account.current_balance_minor == 500000 - 12345
    assert response.category.available_minor == 12345 * -1
    rows = in_memory_db.execute(
        "SELECT COUNT(*) FROM transactions WHERE concept_id = ?",
        [str(response.concept_id)],
    ).fetchone()
    assert rows[0] == 1


def test_edit_transaction_closes_previous_version(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    service = TransactionEntryService()
    first_cmd = NewTransactionRequest(
        transaction_date=date.today(),
        account_id="house_checking",
        category_id="groceries",
        amount_minor=-1000,
    )
    first = service.create(in_memory_db, first_cmd)

    edit_cmd = NewTransactionRequest(
        concept_id=first.concept_id,
        transaction_date=date.today(),
        account_id="house_checking",
        category_id="groceries",
        amount_minor=-2000,
    )
    service.create(in_memory_db, edit_cmd)

    counts = in_memory_db.execute(
        """
        SELECT
            SUM(CASE WHEN is_active THEN 1 ELSE 0 END) AS active_rows
        FROM transactions
        WHERE concept_id = ?
        """,
        [str(first.concept_id)],
    ).fetchone()
    assert counts[0] == 1


def test_zero_amount_rejected(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    service = TransactionEntryService()
    cmd = NewTransactionRequest(
        transaction_date=date.today(),
        account_id="house_checking",
        category_id="groceries",
        amount_minor=0,
    )
    with pytest.raises(InvalidTransaction):
        service.create(in_memory_db, cmd)


def test_list_recent_transactions_returns_latest_first(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    service = TransactionEntryService()
    first = service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=date.today(),
            account_id="house_checking",
            category_id="groceries",
            amount_minor=-100,
            memo="old",
        ),
    )
    second = service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=date.today(),
            account_id="house_checking",
            category_id="groceries",
            amount_minor=-200,
            memo="new",
        ),
    )

    rows = service.list_recent(in_memory_db, limit=5)
    assert rows
    assert rows[0].transaction_version_id == second.transaction_version_id
    assert rows[1].transaction_version_id == first.transaction_version_id
