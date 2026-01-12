"""Unit tests for the account reconciliation services."""

from __future__ import annotations

from datetime import date

import duckdb

from dojo.budgeting.schemas import NewTransactionRequest, TransactionUpdateRequest
from dojo.budgeting.services import TransactionEntryService
from dojo.core.reconciliation import create_reconciliation, get_latest_reconciliation, get_worksheet


def test_reconciliation_worksheet_scope_matches_spec_2_10(
    in_memory_db: duckdb.DuckDBPyConnection,
) -> None:
    """Worksheet includes new/modified items + old pending items."""

    service = TransactionEntryService()

    tx_cleared = service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=date(2025, 1, 10),
            account_id="house_checking",
            category_id="balance_adjustment",
            amount_minor=-2000,
            status="cleared",
            memo="cleared-at-t1",
        ),
        current_date=date(2025, 1, 15),
    )
    tx_pending = service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=date(2025, 1, 11),
            account_id="house_checking",
            category_id="balance_adjustment",
            amount_minor=-1500,
            status="pending",
            memo="pending-at-t1",
        ),
        current_date=date(2025, 1, 15),
    )
    tx_old_pending = service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=date(2024, 10, 1),
            account_id="house_checking",
            category_id="balance_adjustment",
            amount_minor=-500,
            status="pending",
            memo="old-pending-at-t1",
        ),
        current_date=date(2025, 1, 15),
    )
    tx_stable_cleared = service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=date(2025, 1, 9),
            account_id="house_checking",
            category_id="balance_adjustment",
            amount_minor=-999,
            status="cleared",
            memo="cleared-stable",
        ),
        current_date=date(2025, 1, 15),
    )

    create_reconciliation(
        in_memory_db,
        account_id="house_checking",
        statement_date=date(2025, 1, 31),
        statement_balance_minor=0,
    )

    service.update_transaction(
        in_memory_db,
        tx_pending.concept_id,
        TransactionUpdateRequest(
            transaction_date=tx_pending.transaction_date,
            account_id=tx_pending.account.account_id,
            category_id=tx_pending.category.category_id,
            amount_minor=-2500,
            memo="pending-tip-adjusted",
        ),
        current_date=date(2025, 1, 15),
    )
    service.update_transaction(
        in_memory_db,
        tx_cleared.concept_id,
        TransactionUpdateRequest(
            transaction_date=date(2025, 1, 12),
            account_id=tx_cleared.account.account_id,
            category_id=tx_cleared.category.category_id,
            amount_minor=tx_cleared.amount_minor,
            memo="cleared-date-corrected",
        ),
        current_date=date(2025, 1, 15),
    )
    tx_new = service.create(
        in_memory_db,
        NewTransactionRequest(
            transaction_date=date(2025, 1, 13),
            account_id="house_checking",
            category_id="balance_adjustment",
            amount_minor=-333,
            status="cleared",
            memo="new-at-t2",
        ),
        current_date=date(2025, 1, 15),
    )

    latest = get_latest_reconciliation(in_memory_db, "house_checking")
    assert latest is not None

    worksheet = get_worksheet(in_memory_db, "house_checking", last_reconciled_at=latest.created_at)
    worksheet_concepts = {item.concept_id for item in worksheet}

    assert tx_pending.concept_id in worksheet_concepts
    assert tx_cleared.concept_id in worksheet_concepts
    assert tx_new.concept_id in worksheet_concepts
    assert tx_old_pending.concept_id in worksheet_concepts

    assert tx_stable_cleared.concept_id not in worksheet_concepts


def test_create_reconciliation_links_to_previous_checkpoint(
    in_memory_db: duckdb.DuckDBPyConnection,
) -> None:
    """Reconciliation checkpoints form a linked list via previous_reconciliation_id."""

    first = create_reconciliation(
        in_memory_db,
        account_id="house_checking",
        statement_date=date(2025, 1, 31),
        statement_balance_minor=123,
    )
    second = create_reconciliation(
        in_memory_db,
        account_id="house_checking",
        statement_date=date(2025, 2, 28),
        statement_balance_minor=456,
    )

    assert second.previous_reconciliation_id == first.reconciliation_id


def test_create_reconciliation_persists_pending_total_minor(
    in_memory_db: duckdb.DuckDBPyConnection,
) -> None:
    record = create_reconciliation(
        in_memory_db,
        account_id="house_checking",
        statement_date=date(2025, 3, 31),
        statement_balance_minor=0,
        statement_pending_total_minor=-123,
    )

    latest = get_latest_reconciliation(in_memory_db, "house_checking")
    assert latest is not None
    assert latest.reconciliation_id == record.reconciliation_id
    assert latest.statement_pending_total_minor == -123
